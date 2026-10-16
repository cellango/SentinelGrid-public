#!/usr/bin/env python3

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


HTTP_METHODS = {"get", "post", "put", "delete", "patch"}
ROUTE_ROOTS = [
    ("services", "backend/services"),
    ("agents", "backend/agents"),
]
HELPER_TARGETS = [
    ("backend/libs/sg_core/db.py", "get_db"),
    ("backend/libs/sg_core/db.py", "get_tenant_db"),
    ("backend/libs/sg_core/db.py", "get_superadmin_db"),
    ("backend/libs/sg_core/db.py", "get_tenant_session"),
    ("backend/services/model_gateway/app/core/database.py", "set_tenant_context"),
]
TENANT_SIGNAL_PATTERNS = [
    ("dependency:get_current_tenant", "Depends(get_current_tenant)"),
    ("dependency:get_current_user", "Depends(get_current_user)"),
    ("dependency:get_current_request_context", "Depends(get_current_request_context)"),
    ("dependency:get_current_user_info", "Depends(get_current_user_info)"),
    ("dependency:get_current_user_id", "Depends(get_current_user_id)"),
    ("authn:verify_scim_token", "Depends(verify_scim_token)"),
    ("helper:get_token_data", "get_token_data("),
    ("header:X-Tenant-ID", 'alias="X-Tenant-ID"'),
    ("header:X-Tenant-ID", "request.headers.get(\"X-Tenant-ID\")"),
    ("header:X-Tenant-ID", "request.headers.get(\"x-tenant-id\")"),
    ("header:Authorization", "request.headers.get(\"authorization\")"),
    ("header:Authorization", "req.headers.get(\"authorization\")"),
    ("header:Authorization", 'req.headers.get("authorization"'),
    ("header:Authorization", 'request.headers.get("authorization"'),
]
QUERY_TENANT_ID_RE = re.compile(
    r"tenant_id\s*:\s*(?:Optional\[[^\]]+\]|[A-Za-z_][A-Za-z0-9_\.]*)\s*=\s*Query\("
)
BODY_TENANT_ID_RE = re.compile(
    r"\b(?:request|payload|body|pattern|ctx|[A-Za-z_][A-Za-z0-9_]*_data)\.tenant_id\b"
)
V003_VALUES_RE = re.compile(
    r"FROM\s+\(VALUES(?P<body>.*?)\)\s+AS\s+t\(schema_name,\s*table_name\)",
    re.S,
)
V003_TABLE_RE = re.compile(r"\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)")
ALTER_ENABLE_RE = re.compile(
    r"ALTER TABLE\s+([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\s+ENABLE ROW LEVEL SECURITY;",
    re.I,
)
ALTER_FORCE_RE = re.compile(
    r"ALTER TABLE\s+([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\s+FORCE ROW LEVEL SECURITY;",
    re.I,
)
CREATE_POLICY_RE = re.compile(
    r"CREATE POLICY\s+([A-Za-z0-9_]+)\s+ON\s+([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\s+(.*?);",
    re.S | re.I,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def artifact_root() -> Path:
    artifact_dir = os.environ.get("AUDIT_ARTIFACT_DIR")
    if not artifact_dir:
        raise SystemExit("AUDIT_ARTIFACT_DIR is required")
    return Path(artifact_dir)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def relative_path(path: Path) -> str:
    return path.relative_to(repo_root()).as_posix()


def string_constant(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def extract_router_prefixes(tree: ast.AST) -> dict[str, str]:
    prefixes: dict[str, str] = {}
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        if not isinstance(node.value.func, ast.Name) or node.value.func.id != "APIRouter":
            continue
        prefix = ""
        for keyword in node.value.keywords:
            if keyword.arg == "prefix":
                prefix = string_constant(keyword.value) or ""
        for target in node.targets:
            if isinstance(target, ast.Name):
                prefixes[target.id] = prefix
    return prefixes


def extract_function_nodes(tree: ast.AST) -> dict[str, ast.AST]:
    functions: dict[str, ast.AST] = {}
    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions[node.name] = node
    return functions


def extract_node_source(text: str, node: ast.AST) -> str:
    lines = text.splitlines()
    start = getattr(node, "lineno", 1) - 1
    end = getattr(node, "end_lineno", getattr(node, "lineno", 1))
    return "\n".join(lines[start:end])


def extract_route_definitions(
    tree: ast.AST,
    router_prefixes: dict[str, str],
) -> list[dict[str, object]]:
    routes: list[dict[str, object]] = []
    for node in getattr(tree, "body", []):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            if not isinstance(func, ast.Attribute):
                continue
            methods: list[str]
            if func.attr in HTTP_METHODS:
                methods = [func.attr.upper()]
            elif func.attr == "api_route":
                methods = []
                for keyword in decorator.keywords:
                    if keyword.arg == "methods" and isinstance(keyword.value, (ast.List, ast.Tuple)):
                        for element in keyword.value.elts:
                            value = string_constant(element)
                            if value:
                                methods.append(value.upper())
                if not methods:
                    methods = ["ANY"]
            else:
                continue

            router_name = func.value.id if isinstance(func.value, ast.Name) else ""
            route_path = extract_route_path(decorator)
            routes.append(
                {
                    "function_name": node.name,
                    "methods": methods,
                    "router_name": router_name,
                    "path": join_path(router_prefixes.get(router_name, ""), route_path),
                    "lineno": getattr(node, "lineno", 1),
                    "node": node,
                }
            )
    return routes


def extract_route_path(decorator: ast.Call) -> str:
    if decorator.args:
        return string_constant(decorator.args[0]) or ""
    for keyword in decorator.keywords:
        if keyword.arg in {"path", "route"}:
            return string_constant(keyword.value) or ""
    return ""


def join_path(prefix: str, route_path: str) -> str:
    prefix = (prefix or "").strip()
    route_path = (route_path or "").strip()
    if prefix and not prefix.startswith("/"):
        prefix = "/" + prefix
    if route_path and not route_path.startswith("/"):
        route_path = "/" + route_path
    full = f"{prefix.rstrip('/')}{route_path}"
    return full or "/"


def extract_called_helpers(node: ast.AST) -> list[str]:
    helper_names: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
            helper_names.append(child.func.id)
        elif isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            if isinstance(child.func.value, ast.Name):
                helper_names.append(child.func.attr)
    return helper_names


def load_route_overrides(root: Path) -> dict[str, object]:
    path = root / "scripts/audit/multi-tenancy/config/route-overrides.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def extract_dependency_helpers(node: ast.AST) -> list[str]:
    helper_names: list[str] = []
    parameters = list(node.args.posonlyargs) + list(node.args.args) + list(node.args.kwonlyargs)
    defaults = [None] * (len(parameters) - len(node.args.defaults) - len(node.args.kw_defaults))
    defaults += list(node.args.defaults) + list(node.args.kw_defaults)

    for default in defaults:
        if not isinstance(default, ast.Call):
            continue
        if not isinstance(default.func, ast.Name) or default.func.id != "Depends":
            continue
        if not default.args:
            continue
        dependency = default.args[0]
        if isinstance(dependency, ast.Name):
            helper_names.append(dependency.id)
    return helper_names


def expanded_source_text(
    text: str,
    node: ast.AST,
    function_nodes: dict[str, ast.AST],
) -> str:
    seen: set[str] = set()
    collected: list[str] = []

    def visit(current_node: ast.AST) -> None:
        source = extract_node_source(text, current_node)
        if source not in collected:
            collected.append(source)
        helper_names = extract_called_helpers(current_node) + extract_dependency_helpers(current_node)
        for helper_name in helper_names:
            if helper_name in seen:
                continue
            seen.add(helper_name)
            helper_node = function_nodes.get(helper_name)
            if helper_node is None or helper_node is current_node:
                continue
            visit(helper_node)

    visit(node)
    return "\n".join(collected)


def infer_service(path: Path) -> str:
    parts = path.parts
    if "services" in parts:
        index = parts.index("services")
        return parts[index + 1]
    if "agents" in parts:
        index = parts.index("agents")
        return parts[index + 1]
    return "unknown"


def discover_route_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for _, base in ROUTE_ROOTS:
        base_path = root / base
        if not base_path.exists():
            continue
        for path in sorted(base_path.rglob("*.py")):
            relative = relative_path(path)
            if "/tests/" in relative or "/__pycache__/" in relative:
                continue
            if "/app/" not in relative:
                continue
            paths.append(path)
    return paths


def normalize_sql(sql: str) -> str:
    return " ".join(sql.split())


def env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def redact_postgres_url(url: str) -> str:
    parsed = urlsplit(url)
    username = parsed.username or ""
    password = parsed.password
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    userinfo = ""
    if username:
        userinfo = username
        if password is not None:
            userinfo += ":***"
        userinfo += "@"
    netloc = f"{userinfo}{host}{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def run_psql_json(postgres_url: str, sql: str) -> object:
    result = subprocess.run(
        [
            "psql",
            postgres_url,
            "-X",
            "-q",
            "-A",
            "-t",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            sql,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "psql execution failed")
    output = result.stdout.strip()
    if not output:
        return None
    return json.loads(output)


def classify_policy(policy_name: str, policy_sql: str) -> str:
    normalized = normalize_sql(policy_sql).lower()
    if "app.is_superadmin" in normalized:
        return "superadmin_bypass"
    if "for select" in normalized:
        return "tenant_select"
    if "with check" in normalized or "for all" in normalized:
        return "tenant_modify"
    if "tenant_id is null" in normalized:
        return "shared_row_access"
    return "custom"


def build_rls_inventory(root: Path) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    v001_path = root / "backend/migrations_consolidated/V001__initial_schema.sql"
    v003_path = root / "backend/migrations_consolidated/V003__row_level_security.sql"
    v001_text = v001_path.read_text()
    v003_text = v003_path.read_text()

    table_index: dict[str, dict[str, object]] = {}
    policies: list[dict[str, object]] = []

    def ensure_table(schema_name: str, table_name: str) -> dict[str, object]:
        key = f"{schema_name}.{table_name}"
        record = table_index.get(key)
        if record is None:
            record = {
                "key": key,
                "schema": schema_name,
                "table": table_name,
                "source_migrations": [],
                "rls_enabled": False,
                "force_rls": False,
                "policies": [],
                "allows_shared_rows": False,
            }
            table_index[key] = record
        return record

    def add_policy(
        schema_name: str,
        table_name: str,
        policy_name: str,
        source_migration: str,
        policy_sql: str,
    ) -> None:
        table_record = ensure_table(schema_name, table_name)
        if source_migration not in table_record["source_migrations"]:
            table_record["source_migrations"].append(source_migration)
        policy_type = classify_policy(policy_name, policy_sql)
        policy_record = {
            "schema": schema_name,
            "table": table_name,
            "policy_name": policy_name,
            "policy_type": policy_type,
            "source_migration": source_migration,
            "policy_sql": normalize_sql(policy_sql),
            "references_current_tenant": (
                "current_tenant_id()" in policy_sql
                or "app.current_tenant_id" in policy_sql
            ),
            "references_superadmin_flag": "app.is_superadmin" in policy_sql,
            "allows_shared_rows": "tenant_id IS NULL" in policy_sql,
        }
        policies.append(policy_record)
        table_record["policies"].append(policy_record)
        if policy_record["allows_shared_rows"]:
            table_record["allows_shared_rows"] = True

    for schema_name, table_name in ALTER_ENABLE_RE.findall(v001_text):
        table_record = ensure_table(schema_name, table_name)
        table_record["rls_enabled"] = True
        if "V001__initial_schema.sql" not in table_record["source_migrations"]:
            table_record["source_migrations"].append("V001__initial_schema.sql")
    for schema_name, table_name in ALTER_FORCE_RE.findall(v001_text):
        table_record = ensure_table(schema_name, table_name)
        table_record["force_rls"] = True
        if "V001__initial_schema.sql" not in table_record["source_migrations"]:
            table_record["source_migrations"].append("V001__initial_schema.sql")
    for policy_name, schema_name, table_name, policy_sql in CREATE_POLICY_RE.findall(v001_text):
        add_policy(
            schema_name,
            table_name,
            policy_name,
            "V001__initial_schema.sql",
            policy_sql,
        )

    values_match = V003_VALUES_RE.search(v003_text)
    if not values_match:
        raise SystemExit("Could not locate V003 VALUES table list")
    for schema_name, table_name in V003_TABLE_RE.findall(values_match.group("body")):
        table_record = ensure_table(schema_name, table_name)
        table_record["rls_enabled"] = True
        table_record["force_rls"] = True
        if "V003__row_level_security.sql" not in table_record["source_migrations"]:
            table_record["source_migrations"].append("V003__row_level_security.sql")
        add_policy(
            schema_name,
            table_name,
            "tenant_isolation_select",
            "V003__row_level_security.sql",
            "FOR SELECT USING (tenant_id = current_tenant_id())",
        )
        add_policy(
            schema_name,
            table_name,
            "tenant_isolation_modify",
            "V003__row_level_security.sql",
            "FOR ALL USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id())",
        )
        add_policy(
            schema_name,
            table_name,
            "superadmin_bypass",
            "V003__row_level_security.sql",
            "USING (current_setting('app.is_superadmin', true) = 'true')",
        )

    tables = sorted(table_index.values(), key=lambda record: record["key"])
    summary = {
        "table_count": len(tables),
        "rls_enabled_tables": sum(1 for table in tables if table["rls_enabled"]),
        "force_rls_tables": sum(1 for table in tables if table["force_rls"]),
        "policy_count": len(policies),
        "shared_row_tables": sum(1 for table in tables if table["allows_shared_rows"]),
        "current_tenant_helper_present": "CREATE OR REPLACE FUNCTION current_tenant_id()" in v003_text,
        "source_migrations": [
            relative_path(v001_path),
            relative_path(v003_path),
        ],
    }
    return tables, policies, summary


def build_helper_inventory(root: Path) -> list[dict[str, object]]:
    helper_inventory: list[dict[str, object]] = []
    for relative, function_name in HELPER_TARGETS:
        path = root / relative
        tree = ast.parse(path.read_text(), filename=str(path))
        function_nodes = extract_function_nodes(tree)
        node = function_nodes.get(function_name)
        if node is None:
            continue
        source_text = extract_node_source(path.read_text(), node)
        normalized = normalize_sql(source_text)
        helper_inventory.append(
            {
                "helper_name": function_name,
                "qualified_name": f"{relative_path(path)}::{function_name}",
                "path": relative_path(path),
                "line": getattr(node, "lineno", 1),
                "sets_current_tenant": "app.current_tenant_id" in source_text,
                "sets_superadmin": "app.is_superadmin" in source_text,
                "uses_set_local": "SET LOCAL" in source_text,
                "uses_plain_session_factory": "SessionLocal()" in source_text,
                "source_excerpt": normalized,
            }
        )
    return helper_inventory


def detect_tenant_signals(source_text: str) -> list[str]:
    found: list[str] = []
    for label, needle in TENANT_SIGNAL_PATTERNS:
        if needle in source_text and label not in found:
            found.append(label)
    if QUERY_TENANT_ID_RE.search(source_text) and "query:tenant_id" not in found:
        found.append("query:tenant_id")
    if BODY_TENANT_ID_RE.search(source_text) and "body:tenant_id" not in found:
        found.append("body:tenant_id")
    return found


def classify_session_modes(source_text: str) -> list[str]:
    modes: list[str] = []
    if "Depends(get_tenant_session)" in source_text or "get_tenant_db(" in source_text:
        modes.append("tenant_scoped_dependency")
    if "Depends(get_superadmin_db)" in source_text:
        modes.append("superadmin_dependency")
    if "Depends(get_db)" in source_text:
        modes.append("plain_db_dependency")
    if "set_tenant_context(" in source_text or "SET LOCAL app.current_tenant_id" in source_text:
        modes.append("custom_tenant_context")
    return modes or ["no_db_dependency"]


def primary_session_mode(session_modes: list[str]) -> str:
    priority = [
        "superadmin_dependency",
        "tenant_scoped_dependency",
        "custom_tenant_context",
        "plain_db_dependency",
        "no_db_dependency",
    ]
    for mode in priority:
        if mode in session_modes:
            return mode
    return "no_db_dependency"


def route_record(
    path: Path,
    route: dict[str, object],
    source_text: str,
    function_nodes: dict[str, ast.AST],
    overrides: dict[str, object],
) -> dict[str, object]:
    route_node = route["node"]
    assert isinstance(route_node, ast.AST)
    expanded_source = expanded_source_text(source_text, route_node, function_nodes)
    session_modes = classify_session_modes(expanded_source)
    tenant_signals = detect_tenant_signals(expanded_source)
    primary_mode = primary_session_mode(session_modes)
    has_db_access = primary_mode != "no_db_dependency"
    uses_plain_db = primary_mode == "plain_db_dependency"
    risk_level = "low"
    risk_reason = ""
    if uses_plain_db and tenant_signals:
        risk_level = "high"
        risk_reason = "Plain DB session used with tenant-aware route logic but without provable session-level RLS context."
    elif uses_plain_db:
        risk_level = "critical"
        risk_reason = "Plain DB session used without tenant-scoped DB context or visible tenant signal."
    elif primary_mode == "superadmin_dependency":
        risk_level = "review"
        risk_reason = "Superadmin bypass path requires explicit reviewer approval and compensating controls."

    service = infer_service(path)
    record = {
        "service": service,
        "path": relative_path(path),
        "line": route["lineno"],
        "function_name": route["function_name"],
        "methods": route["methods"],
        "route_path": route["path"],
        "session_modes": session_modes,
        "primary_session_mode": primary_mode,
        "tenant_signals": tenant_signals,
        "has_db_access": has_db_access,
        "uses_plain_db_dependency": uses_plain_db,
        "uses_tenant_scoped_dependency": primary_mode == "tenant_scoped_dependency",
        "uses_superadmin_dependency": primary_mode == "superadmin_dependency",
        "uses_custom_tenant_context": primary_mode == "custom_tenant_context",
        "risk_level": risk_level,
        "risk_reason": risk_reason,
    }
    override = overrides.get(f"{service}:{route['methods'][0]}:{route['path']}")
    if isinstance(override, dict):
        override_status = str(override.get("status", ""))
        override_notes = str(override.get("notes", "")).strip()
        override_sources = override.get("tenant_sources", [])
        if isinstance(override_sources, list):
            for source in override_sources:
                if source not in record["tenant_signals"]:
                    record["tenant_signals"].append(source)
        record["override_inputs"] = override.get("override_inputs", [])
        record["override_status"] = override_status or None
        if override_status == "review_required":
            record["risk_level"] = "review"
            record["risk_reason"] = override_notes or "Explicitly reviewed boundary route."
        elif override_status == "baseline":
            record["risk_level"] = "low"
            record["risk_reason"] = override_notes or ""
    return record


def build_runtime_session_usage(root: Path) -> tuple[dict[str, object], list[str]]:
    route_files = discover_route_files(root)
    routes: list[dict[str, object]] = []
    skipped_files: list[str] = []
    overrides = load_route_overrides(root)

    for path in route_files:
        try:
            source_text = path.read_text()
            tree = ast.parse(source_text, filename=str(path))
        except SyntaxError:
            skipped_files.append(relative_path(path))
            continue
        router_prefixes = extract_router_prefixes(tree)
        function_nodes = extract_function_nodes(tree)
        for route in extract_route_definitions(tree, router_prefixes):
            routes.append(route_record(path, route, source_text, function_nodes, overrides))

    high_risk_routes = [
        route
        for route in routes
        if route["primary_session_mode"] == "plain_db_dependency"
        and route["risk_level"] in {"high", "critical"}
    ]
    critical_routes = [route for route in high_risk_routes if route["risk_level"] == "critical"]
    summary = {
        "route_count": len(routes),
        "db_route_count": sum(1 for route in routes if route["has_db_access"]),
        "tenant_scoped_routes": sum(
            1 for route in routes if route["primary_session_mode"] == "tenant_scoped_dependency"
        ),
        "superadmin_routes": sum(
            1 for route in routes if route["primary_session_mode"] == "superadmin_dependency"
        ),
        "plain_db_routes": sum(
            1 for route in routes if route["primary_session_mode"] == "plain_db_dependency"
        ),
        "custom_tenant_context_routes": sum(
            1 for route in routes if route["primary_session_mode"] == "custom_tenant_context"
        ),
        "no_db_routes": sum(
            1 for route in routes if route["primary_session_mode"] == "no_db_dependency"
        ),
        "plain_db_routes_with_tenant_signal": sum(
            1
            for route in routes
            if route["primary_session_mode"] == "plain_db_dependency" and route["tenant_signals"]
        ),
        "plain_db_routes_without_tenant_signal": sum(
            1
            for route in routes
            if route["primary_session_mode"] == "plain_db_dependency" and not route["tenant_signals"]
        ),
        "high_risk_routes": len(high_risk_routes),
        "critical_routes": len(critical_routes),
        "skipped_files": len(skipped_files),
    }
    payload = {
        "summary": summary,
        "routes": sorted(
            routes,
            key=lambda route: (
                route["risk_level"],
                route["service"],
                route["path"],
                route["route_path"],
                route["function_name"],
            ),
            reverse=True,
        ),
        "high_risk_routes": high_risk_routes,
        "critical_routes": critical_routes,
    }
    return payload, skipped_files


def build_expected_policy_map(policies: list[dict[str, object]]) -> dict[str, list[str]]:
    expected: dict[str, set[str]] = {}
    for policy in policies:
        key = f"{policy['schema']}.{policy['table']}"
        expected.setdefault(key, set()).add(str(policy["policy_name"]))
    return {key: sorted(value) for key, value in expected.items()}


def build_live_catalog_snapshot(
    postgres_url: str,
    tables: list[dict[str, object]],
    expected_policy_map: dict[str, list[str]],
) -> dict[str, object]:
    values_sql = ",\n        ".join(
        f"({sql_literal(str(table['schema']))}, {sql_literal(str(table['table']))})"
        for table in tables
    )
    sql = f"""
WITH expected(schema_name, table_name) AS (
    VALUES
        {values_sql}
)
SELECT COALESCE(
    json_agg(
        json_build_object(
            'schema', e.schema_name,
            'table', e.table_name,
            'exists', c.oid IS NOT NULL,
            'rls_enabled', COALESCE(c.relrowsecurity, false),
            'force_rls', COALESCE(c.relforcerowsecurity, false),
            'has_tenant_id_column', EXISTS(
                SELECT 1
                FROM information_schema.columns ic
                WHERE ic.table_schema = e.schema_name
                  AND ic.table_name = e.table_name
                  AND ic.column_name = 'tenant_id'
            ),
            'policies', COALESCE((
                SELECT json_agg(p.policyname ORDER BY p.policyname)
                FROM pg_policies p
                WHERE p.schemaname = e.schema_name
                  AND p.tablename = e.table_name
            ), '[]'::json)
        )
        ORDER BY e.schema_name, e.table_name
    ),
    '[]'::json
)::text
FROM expected e
LEFT JOIN pg_namespace n
  ON n.nspname = e.schema_name
LEFT JOIN pg_class c
  ON c.relnamespace = n.oid
 AND c.relname = e.table_name
 AND c.relkind = 'r';
"""
    rows = run_psql_json(postgres_url, sql) or []
    mismatches: list[dict[str, object]] = []
    for row in rows:
        key = f"{row['schema']}.{row['table']}"
        expected_policies = expected_policy_map.get(key, [])
        live_policies = sorted(row.get("policies") or [])
        mismatch_reasons: list[str] = []
        if not row.get("exists"):
            mismatch_reasons.append("table missing in live catalog")
        if not row.get("rls_enabled"):
            mismatch_reasons.append("RLS not enabled")
        if not row.get("force_rls"):
            mismatch_reasons.append("FORCE RLS not enabled")
        if not row.get("has_tenant_id_column"):
            mismatch_reasons.append("tenant_id column missing")
        if expected_policies != live_policies:
            mismatch_reasons.append(
                f"policy mismatch expected={expected_policies} live={live_policies}"
            )
        if mismatch_reasons:
            mismatches.append(
                {
                    "key": key,
                    "schema": row["schema"],
                    "table": row["table"],
                    "reasons": mismatch_reasons,
                    "expected_policies": expected_policies,
                    "live_policies": live_policies,
                }
            )
    return {
        "rows": rows,
        "summary": {
            "table_count": len(rows),
            "tables_present": sum(1 for row in rows if row.get("exists")),
            "rls_enabled_tables": sum(1 for row in rows if row.get("rls_enabled")),
            "force_rls_tables": sum(1 for row in rows if row.get("force_rls")),
            "tables_with_tenant_id_column": sum(1 for row in rows if row.get("has_tenant_id_column")),
            "policy_mismatch_tables": len(mismatches),
        },
        "mismatches": mismatches,
    }


def build_live_candidate_counts(
    postgres_url: str,
    catalog_rows: list[dict[str, object]],
    tenant_a_id: str,
    tenant_b_id: str,
) -> list[dict[str, object]]:
    values_sql = ",\n        ".join(
        f"({sql_literal(str(row['schema']))}, {sql_literal(str(row['table']))})"
        for row in catalog_rows
        if row.get("has_tenant_id_column")
    )
    if not values_sql:
        return []
    sql = f"""
BEGIN;
SET LOCAL app.is_superadmin = 'true';
CREATE TEMP TABLE audit_rls_counts (
    schema_name text,
    table_name text,
    total_count bigint,
    tenant_a_count bigint,
    tenant_b_count bigint,
    shared_count bigint
) ON COMMIT DROP;
DO $audit$
DECLARE
    rec RECORD;
    tenant_a text := {sql_literal(tenant_a_id)};
    tenant_b text := {sql_literal(tenant_b_id)};
BEGIN
    FOR rec IN
        SELECT *
        FROM (VALUES
            {values_sql}
        ) AS t(schema_name, table_name)
    LOOP
        EXECUTE format(
            'INSERT INTO audit_rls_counts (schema_name, table_name, total_count, tenant_a_count, tenant_b_count, shared_count) '
            'SELECT %L, %L, count(*), '
            'count(*) FILTER (WHERE tenant_id::text = %L), '
            'count(*) FILTER (WHERE tenant_id::text = %L), '
            'count(*) FILTER (WHERE tenant_id IS NULL) '
            'FROM %I.%I',
            rec.schema_name,
            rec.table_name,
            tenant_a,
            tenant_b,
            rec.schema_name,
            rec.table_name
        );
    END LOOP;
END
$audit$;
SELECT COALESCE(
    json_agg(row_to_json(x) ORDER BY x.schema_name, x.table_name),
    '[]'::json
)::text
FROM audit_rls_counts x;
ROLLBACK;
"""
    return run_psql_json(postgres_url, sql) or []


def fetch_context_counts(
    postgres_url: str,
    schema_name: str,
    table_name: str,
    tenant_a_id: str,
    tenant_b_id: str,
    verifier_role: str = "",
) -> dict[str, object]:
    qualified_table = f"{quote_ident(schema_name)}.{quote_ident(table_name)}"

    def context_query(superadmin: bool, tenant_id: str) -> dict[str, object]:
        set_role_sql = f"SET LOCAL ROLE {quote_ident(verifier_role)};" if verifier_role else ""
        sql = f"""
BEGIN;
{set_role_sql}
SET LOCAL app.is_superadmin = {'true' if superadmin else 'false'};
SET LOCAL app.current_tenant_id = {sql_literal(tenant_id)};
SELECT json_build_object(
    'visible_total', (SELECT count(*) FROM {qualified_table}),
    'visible_tenant_a', (SELECT count(*) FROM {qualified_table} WHERE tenant_id::text = {sql_literal(tenant_a_id)}),
    'visible_tenant_b', (SELECT count(*) FROM {qualified_table} WHERE tenant_id::text = {sql_literal(tenant_b_id)})
)::text;
ROLLBACK;
"""
        return run_psql_json(postgres_url, sql) or {}

    return {
        "tenant_a_context": context_query(False, tenant_a_id),
        "tenant_b_context": context_query(False, tenant_b_id),
        "no_context": context_query(False, ""),
        "superadmin_context": context_query(True, ""),
    }


def build_live_runtime_verification(
    postgres_url: str,
    tables: list[dict[str, object]],
    policies: list[dict[str, object]],
    rls_summary: dict[str, object],
) -> dict[str, object]:
    require_live = env_flag("AUDIT_REQUIRE_LIVE_RLS", False)
    tenant_a_id = os.environ.get("AUDIT_TENANT_A_ID", "").strip()
    tenant_b_id = os.environ.get("AUDIT_TENANT_B_ID", "").strip()
    verifier_role = os.environ.get("AUDIT_RLS_VERIFIER_ROLE", "").strip()
    sample_limit = int(os.environ.get("AUDIT_RLS_LIVE_SAMPLE_LIMIT", "5"))

    metadata = {
        "status": "skipped",
        "required": require_live,
        "fatal": False,
        "psql_available": shutil.which("psql") is not None,
        "postgres_url": redact_postgres_url(postgres_url) if postgres_url else "",
        "tenant_pair_present": bool(tenant_a_id and tenant_b_id),
        "sample_limit": sample_limit,
        "notes": [],
    }

    if not postgres_url:
        metadata["notes"].append("POSTGRES_URL is not configured.")
        if require_live:
            metadata["status"] = "failed"
            metadata["fatal"] = True
        return metadata
    if not metadata["psql_available"]:
        metadata["notes"].append("psql is not installed.")
        if require_live:
            metadata["status"] = "failed"
            metadata["fatal"] = True
        return metadata
    if not tenant_a_id or not tenant_b_id:
        metadata["notes"].append("AUDIT_TENANT_A_ID and AUDIT_TENANT_B_ID are required for live RLS proof.")
        if require_live:
            metadata["status"] = "failed"
            metadata["fatal"] = True
        return metadata

    try:
        connection_sql = """
SELECT json_build_object(
    'session_user', session_user,
    'current_user', current_user,
    'current_database', current_database(),
    'server_version', current_setting('server_version'),
    'row_security', current_setting('row_security', true),
    'rolsuper', (SELECT rolsuper FROM pg_roles WHERE rolname = current_user),
    'rolbypassrls', (SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user)
)::text;
"""
        if verifier_role:
            connection_sql = f"""
BEGIN;
SET LOCAL ROLE {quote_ident(verifier_role)};
{connection_sql}
ROLLBACK;
"""
        connection_info = run_psql_json(
            postgres_url,
            connection_sql,
        ) or {}
        live_catalog = build_live_catalog_snapshot(
            postgres_url,
            tables,
            build_expected_policy_map(policies),
        )
        candidate_counts = build_live_candidate_counts(
            postgres_url,
            live_catalog["rows"],
            tenant_a_id,
            tenant_b_id,
        )
    except Exception as exc:
        metadata["notes"].append(f"Live database verification could not run: {exc}")
        if require_live:
            metadata["status"] = "failed"
            metadata["fatal"] = True
        return metadata

    table_map = {f"{table['schema']}.{table['table']}": table for table in tables}
    candidates = [
        count
        for count in candidate_counts
        if int(count["tenant_a_count"]) > 0 and int(count["tenant_b_count"]) > 0
    ]
    candidates.sort(key=lambda row: int(row["total_count"]), reverse=True)
    selected_candidates = candidates[:sample_limit]

    if connection_info.get("rolsuper") or connection_info.get("rolbypassrls"):
        metadata["status"] = "failed" if require_live else "skipped"
        metadata["fatal"] = bool(require_live)
        metadata["notes"].append(
            "Current database role bypasses RLS. Use a non-superuser, non-bypass verifier role for live row-visibility proof."
        )
        metadata["connection"] = connection_info
        metadata["live_catalog_summary"] = live_catalog["summary"]
        metadata["candidate_tables_with_both_tenants"] = len(candidates)
        metadata["selected_candidate_tables"] = len(selected_candidates)
        metadata["candidate_preview"] = [
            {
                "schema": row["schema_name"],
                "table": row["table_name"],
                "tenant_a_count": row["tenant_a_count"],
                "tenant_b_count": row["tenant_b_count"],
                "shared_count": row["shared_count"],
                "total_count": row["total_count"],
            }
            for row in selected_candidates
        ]
        return metadata

    table_results: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    for candidate in selected_candidates:
        key = f"{candidate['schema_name']}.{candidate['table_name']}"
        static_table = table_map.get(key, {})
        counts = fetch_context_counts(
            postgres_url,
            str(candidate["schema_name"]),
            str(candidate["table_name"]),
            tenant_a_id,
            tenant_b_id,
            verifier_role=verifier_role,
        )
        no_context_expected = int(candidate["shared_count"]) if static_table.get("allows_shared_rows") else 0
        assertions = {
            "tenant_a_can_see_own_rows": int(counts["tenant_a_context"]["visible_tenant_a"]) == int(candidate["tenant_a_count"]),
            "tenant_a_cannot_see_tenant_b_rows": int(counts["tenant_a_context"]["visible_tenant_b"]) == 0,
            "tenant_b_can_see_own_rows": int(counts["tenant_b_context"]["visible_tenant_b"]) == int(candidate["tenant_b_count"]),
            "tenant_b_cannot_see_tenant_a_rows": int(counts["tenant_b_context"]["visible_tenant_a"]) == 0,
            "no_context_is_bounded": int(counts["no_context"]["visible_total"]) == no_context_expected,
            "superadmin_sees_total_rows": int(counts["superadmin_context"]["visible_total"]) == int(candidate["total_count"]),
        }
        passed = all(assertions.values())
        result = {
            "schema": candidate["schema_name"],
            "table": candidate["table_name"],
            "allows_shared_rows": bool(static_table.get("allows_shared_rows")),
            "baseline_counts": candidate,
            "context_counts": counts,
            "assertions": assertions,
            "status": "passed" if passed else "failed",
        }
        table_results.append(result)
        if not passed:
            failures.append(result)

    if not selected_candidates:
        metadata["notes"].append("No RLS table had rows for both configured tenants in the target database.")
        metadata["status"] = "skipped"
        metadata["connection"] = connection_info
        metadata["live_catalog_summary"] = live_catalog["summary"]
        metadata["candidate_tables_with_both_tenants"] = 0
        if require_live:
            metadata["status"] = "failed"
            metadata["fatal"] = True
        return metadata

    metadata.update(
        {
            "status": "passed" if not failures and not live_catalog["mismatches"] else "failed",
            "connection": connection_info,
            "live_catalog_summary": live_catalog["summary"],
            "candidate_tables_with_both_tenants": len(candidates),
            "selected_candidate_tables": len(selected_candidates),
            "evaluated_tables": table_results,
            "live_catalog_mismatches": live_catalog["mismatches"],
            "candidate_preview": [
                {
                    "schema": row["schema_name"],
                    "table": row["table_name"],
                    "tenant_a_count": row["tenant_a_count"],
                    "tenant_b_count": row["tenant_b_count"],
                    "shared_count": row["shared_count"],
                    "total_count": row["total_count"],
                }
                for row in selected_candidates
            ],
        }
    )
    return metadata


def build_summary_markdown(
    rls_summary: dict[str, object],
    runtime_usage: dict[str, object],
    helper_inventory: list[dict[str, object]],
    skipped_files: list[str],
    live_runtime: dict[str, object],
) -> str:
    runtime_summary = runtime_usage["summary"]
    critical_preview = runtime_usage["critical_routes"][:10]
    high_risk_preview = runtime_usage["high_risk_routes"][:10]

    lines = [
        "# RLS Coverage Summary",
        "",
        "## Schema-Level Coverage",
        "",
        f"- RLS tables inventoried: {rls_summary['table_count']}",
        f"- Tables with `FORCE ROW LEVEL SECURITY`: {rls_summary['force_rls_tables']}",
        f"- Policy records inventoried: {rls_summary['policy_count']}",
        f"- Tables allowing shared rows (`tenant_id IS NULL`): {rls_summary['shared_row_tables']}",
        f"- `current_tenant_id()` helper present in migration set: {'yes' if rls_summary['current_tenant_helper_present'] else 'no'}",
        "",
        "## Runtime Session Usage",
        "",
        f"- Routes analyzed: {runtime_summary['route_count']}",
        f"- Routes with explicit DB session usage: {runtime_summary['db_route_count']}",
        f"- Tenant-scoped DB dependency routes: {runtime_summary['tenant_scoped_routes']}",
        f"- Superadmin DB dependency routes: {runtime_summary['superadmin_routes']}",
        f"- Custom tenant-context routes: {runtime_summary['custom_tenant_context_routes']}",
        f"- Plain DB dependency routes: {runtime_summary['plain_db_routes']}",
        f"- Plain DB routes with tenant signal but no provable DB scoping: {runtime_summary['plain_db_routes_with_tenant_signal']}",
        f"- Plain DB routes without visible tenant signal: {runtime_summary['plain_db_routes_without_tenant_signal']}",
        "",
        "## Helper Inventory",
        "",
        f"- Tenant/session helpers inventoried: {len(helper_inventory)}",
        "",
        "## Live Runtime Verification",
        "",
        f"- Status: {live_runtime.get('status', 'unknown')}",
        f"- Required for this profile: {'yes' if live_runtime.get('required') else 'no'}",
        f"- Candidate tables with both tenants: {live_runtime.get('candidate_tables_with_both_tenants', 0)}",
        f"- Selected candidate tables: {live_runtime.get('selected_candidate_tables', 0)}",
        "",
        "## Audit Notes",
        "",
        "- This report combines static evidence from repo source and migration files with live runtime proof when a database target and tenant pair are configured.",
        "- It proves which tables are configured for RLS in migrations and where route code does or does not use tenant-scoped session helpers.",
    ]

    if live_runtime.get("notes"):
        lines.extend(["", "## Live Verification Notes", ""])
        for note in live_runtime["notes"]:
            lines.append(f"- {note}")

    if live_runtime.get("status") == "passed":
        lines.extend(["", "## Live Runtime Snapshot", ""])
        live_catalog_summary = live_runtime.get("live_catalog_summary", {})
        lines.append(f"- Live catalog RLS tables present: {live_catalog_summary.get('tables_present', 0)}")
        lines.append(f"- Live catalog FORCE RLS tables: {live_catalog_summary.get('force_rls_tables', 0)}")
        lines.append(f"- Live catalog mismatch tables: {live_catalog_summary.get('policy_mismatch_tables', 0)}")
        for result in live_runtime.get("evaluated_tables", [])[:5]:
            lines.append(
                f"- `{result['schema']}.{result['table']}` "
                f"A->B denied={result['assertions']['tenant_a_cannot_see_tenant_b_rows']}, "
                f"B->A denied={result['assertions']['tenant_b_cannot_see_tenant_a_rows']}, "
                f"superadmin_total={result['assertions']['superadmin_sees_total_rows']}"
            )

    if critical_preview:
        lines.extend(["", "## Critical Plain-Session Routes", ""])
        for route in critical_preview:
            lines.append(
                f"- `{route['service']}` `{','.join(route['methods'])} {route['route_path']}` "
                f"at `{route['path']}:{route['line']}`"
            )

    elif high_risk_preview:
        lines.extend(["", "## High-Risk Plain-Session Routes", ""])
        for route in high_risk_preview:
            lines.append(
                f"- `{route['service']}` `{','.join(route['methods'])} {route['route_path']}` "
                f"at `{route['path']}:{route['line']}`"
            )

    if skipped_files:
        lines.extend(["", "## Skipped Files", ""])
        for path in skipped_files[:20]:
            lines.append(f"- `{path}`")

    return "\n".join(lines) + "\n"


def main() -> int:
    root = repo_root()
    output_dir = artifact_root() / "rls-report"
    output_dir.mkdir(parents=True, exist_ok=True)

    tables, policies, rls_summary = build_rls_inventory(root)
    helper_inventory = build_helper_inventory(root)
    runtime_usage, skipped_files = build_runtime_session_usage(root)
    live_runtime = build_live_runtime_verification(
        os.environ.get("POSTGRES_URL", "").strip(),
        tables,
        policies,
        rls_summary,
    )
    runtime_usage["helper_inventory"] = helper_inventory
    runtime_usage["skipped_files"] = skipped_files

    write_json(output_dir / "rls-tables.json", tables)
    write_json(output_dir / "rls-policies.json", policies)
    write_json(output_dir / "runtime-session-usage.json", runtime_usage)
    write_json(output_dir / "live-runtime-verification.json", live_runtime)
    write_json(
        output_dir / "summary.json",
        {
            "schema_summary": rls_summary,
            "runtime_summary": runtime_usage["summary"],
            "live_runtime_summary": {
                "status": live_runtime.get("status"),
                "required": live_runtime.get("required"),
                "candidate_tables_with_both_tenants": live_runtime.get("candidate_tables_with_both_tenants", 0),
                "selected_candidate_tables": live_runtime.get("selected_candidate_tables", 0),
                "live_catalog_summary": live_runtime.get("live_catalog_summary", {}),
            },
            "helper_inventory_count": len(helper_inventory),
            "skipped_files": skipped_files,
        },
    )
    (output_dir / "rls-summary.md").write_text(
        build_summary_markdown(rls_summary, runtime_usage, helper_inventory, skipped_files, live_runtime)
    )
    if live_runtime.get("required") and live_runtime.get("status") != "passed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
