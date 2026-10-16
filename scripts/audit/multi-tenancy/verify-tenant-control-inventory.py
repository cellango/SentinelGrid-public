#!/usr/bin/env python3

from __future__ import annotations

import ast
import csv
import json
import re
from pathlib import Path


HTTP_METHODS = {"get", "post", "put", "delete", "patch"}
ROUTE_SOURCES = [
    {
        "service": "api_gateway",
        "default_visibility": "public",
        "patterns": ["backend/services/api_gateway/app/api/routes_*.py"],
    },
    {
        "service": "iam_agent",
        "default_visibility": "public",
        "patterns": ["backend/agents/iam_agent/app/api/*.py"],
    },
    {
        "service": "ticketing_service",
        "default_visibility": "internal",
        "patterns": ["backend/services/ticketing_service/app/api/*.py"],
    },
]
OWNER_BY_SERVICE = {
    "api_gateway": "API Gateway",
    "iam_agent": "IAM Agent",
    "ticketing_service": "Ticketing Service",
}
QUERY_TENANT_ID_RE = re.compile(
    r"tenant_id\s*:\s*(?:Optional\[[^\]]+\]|[A-Za-z_][A-Za-z0-9_\.]*)\s*=\s*Query\("
)
BODY_TENANT_ID_RE = re.compile(
    r"\b(?:request|payload|pattern|[A-Za-z_][A-Za-z0-9_]*_data)\.tenant_id\b"
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def artifact_root() -> Path:
    import os

    artifact_dir = os.environ.get("AUDIT_ARTIFACT_DIR")
    if not artifact_dir:
        raise SystemExit("AUDIT_ARTIFACT_DIR is required")
    return Path(artifact_dir)


def load_source_files(root: Path) -> list[dict]:
    files: list[dict] = []
    for source in ROUTE_SOURCES:
        for pattern in source["patterns"]:
            for path in sorted(root.glob(pattern)):
                if path.name == "__init__.py":
                    continue
                files.append(
                    {
                        "service": source["service"],
                        "default_visibility": source["default_visibility"],
                        "path": path,
                    }
                )
    return files


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
    if not full:
        return "/"
    return full or "/"


def extract_node_source(text: str, node: ast.AST) -> str:
    lines = text.splitlines()
    start = getattr(node, "lineno", 1) - 1
    end = getattr(node, "end_lineno", getattr(node, "lineno", 1))
    return "\n".join(lines[start:end])


def extract_called_helpers(node: ast.AST) -> list[str]:
    helper_names: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
            helper_names.append(child.func.id)
        elif isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            if isinstance(child.func.value, ast.Name):
                helper_names.append(child.func.value.id)
    return helper_names


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
    source_parts = [extract_node_source(text, node)]
    helper_names = extract_called_helpers(node) + extract_dependency_helpers(node)
    for helper_name in helper_names:
        helper = function_nodes.get(helper_name)
        if helper is None or helper is node:
            continue
        source_parts.append(extract_node_source(text, helper))
    return "\n".join(source_parts)


def detect_tenant_sources(source_text: str) -> list[str]:
    found: list[str] = []
    patterns = [
        ("dependency:get_current_tenant", "Depends(get_current_tenant)"),
        (
            "dependency:TenantIsolationValidator.get_current_user_id",
            "TenantIsolationValidator.get_current_user_id",
        ),
        ("dependency:get_current_user_info", "Depends(get_current_user_info)"),
        ("dependency:get_iam_service", "Depends(get_iam_service)"),
        ("dependency:get_current_user_id", "Depends(get_current_user_id)"),
        ("dependency:get_current_user", "Depends(get_current_user)"),
        ("dependency:get_current_request_context", "Depends(get_current_request_context)"),
        ("helper:get_customer_id_from_token", "get_customer_id_from_token"),
        ("helper:get_token_data", "get_token_data("),
        ("authz:verify_internal_token", "verify_internal_token"),
        ("authn:verify_scim_token", "Depends(verify_scim_token)"),
        ("header:X-Tenant-ID", 'alias="X-Tenant-ID"'),
        ("header:X-Tenant-ID", "request.headers.get(\"x-tenant-id\")"),
        ("header:X-Tenant-ID", "request.headers.get(\"X-Tenant-ID\")"),
        ("header:Authorization", 'alias="authorization"'),
        ("header:Authorization", 'req.headers.get("authorization"'),
        ("header:Authorization", 'request.headers.get("authorization"'),
        ("body:tenant_id", "tenant_id=request.tenant_id"),
        ("body:tenant_id", "tenant_id = request.tenant_id"),
        ("body:tenant_id", "request.tenant_id"),
    ]
    for label, needle in patterns:
        if needle in source_text and label not in found:
            found.append(label)
    if QUERY_TENANT_ID_RE.search(source_text) and "query:tenant_id" not in found:
        found.append("query:tenant_id")
    if BODY_TENANT_ID_RE.search(source_text) and "body:tenant_id" not in found:
        found.append("body:tenant_id")
    return found or ["unknown"]


def primary_tenant_source(tenant_sources: list[str]) -> str:
    priority = [
        "dependency:get_current_tenant",
        "dependency:TenantIsolationValidator.get_current_user_id",
        "dependency:get_current_user_info",
        "dependency:get_iam_service",
        "dependency:get_current_user_id",
        "dependency:get_current_user",
        "dependency:get_current_request_context",
        "helper:get_customer_id_from_token",
        "helper:get_token_data",
        "authz:verify_internal_token",
        "authn:verify_scim_token",
        "header:X-Tenant-ID",
        "header:Authorization",
        "query:tenant_id",
        "body:tenant_id",
        "unknown",
    ]
    for item in priority:
        if item in tenant_sources:
            return item
    return "unknown"


def detect_override_inputs(source_text: str, full_path: str) -> list[str]:
    override_inputs: list[str] = []
    if "{tenant_id}" in full_path:
        override_inputs.append("path:tenant_id")
    if "{tenant_slug}" in full_path:
        override_inputs.append("path:tenant_slug")
    if "tenant_slug" in source_text and "path:tenant_slug" not in override_inputs:
        override_inputs.append("query_or_body:tenant_slug")
    if (
        'alias="X-Tenant-ID"' in source_text
        or "request.headers.get(\"x-tenant-id\")" in source_text
        or "request.headers.get(\"X-Tenant-ID\")" in source_text
        or "x-tenant-id" in source_text.lower()
    ):
        override_inputs.append("header:X-Tenant-ID")
    if QUERY_TENANT_ID_RE.search(source_text):
        override_inputs.append("query:tenant_id")
    if "request.tenant_id" in source_text or BODY_TENANT_ID_RE.search(source_text):
        override_inputs.append("body:tenant_id")
    return override_inputs


def detect_risk_flags(
    source_text: str,
    full_path: str,
    visibility: str,
    tenant_source: str,
) -> list[str]:
    flags: list[str] = []
    if "get_customer_id_from_token" in source_text:
        flags.append("header_or_fallback_tenant_resolution")
    if (
        'request.headers.get("x-tenant-id")' in source_text
        or 'request.headers.get("X-Tenant-ID")' in source_text
        or "x-tenant-id" in source_text.lower()
    ):
        flags.append("raw_header_tenant_usage")
    if visibility == "internal" and "header:X-Tenant-ID" in tenant_source:
        flags.append("internal_header_trust_model")
    if "{tenant_id}" in full_path:
        flags.append("path_tenant_input_present")
    if tenant_source in {"query:tenant_id", "body:tenant_id"}:
        flags.append("caller_supplied_tenant_input")
    return flags


def infer_route_family(
    service: str,
    visibility: str,
    method: str,
    full_path: str,
    primary_source: str,
) -> tuple[str, str | None, list[str]]:
    if primary_source != "unknown":
        return primary_source, None, []

    if service == "iam_agent":
        if full_path.startswith("/api/v1/leads/create") or full_path.startswith("/api/v1/leads/demo-request"):
            return "public:lead_capture", "baseline", []
        if full_path.startswith("/api/v1/leads/") and "{lead_id}" in full_path:
            return "public:lead_record_lookup", "review_required", [
                "public_record_lookup_by_identifier"
            ]
        if full_path == "/api/v1/marketing/events":
            return "public:marketing_telemetry", "baseline", []
        if full_path == "/api/v1/marketing/funnel/summary":
            return "internal:business_analytics_report", "review_required", [
                "internal_reporting_surface_without_auth_context"
            ]
        if full_path == "/api/v1/payment/calculate":
            return "public:commercial_pricing_flow", "baseline", []
        if full_path == "/api/v1/payment/create-pentest-session":
            return "public:commercial_checkout_flow", "baseline", []
        if full_path == "/api/v1/payment/create-checkout-session":
            return "public:lead_checkout_flow", "review_required", [
                "public_lead_conversion_surface"
            ]
        if full_path == "/api/v1/payment/success":
            return "public:payment_completion_flow", "review_required", [
                "public_account_conversion_surface"
            ]
        if full_path == "/api/v1/payment/webhook":
            return "public:billing_webhook", "review_required", [
                "external_billing_callback"
            ]
        if full_path.startswith("/api/v1/auth/passwordless/") or full_path.startswith("/api/v1/auth/"):
            return "public_auth_flow", "baseline", []
        if full_path.startswith("/api/v1/self/"):
            return "dependency:get_current_user", "baseline", []
        if full_path.startswith("/api/v1/scim/v2/"):
            return "authn:verify_scim_token", "baseline", []
        if full_path.startswith("/api/v1/idp/test/"):
            return "public:idp_diagnostic_surface", "review_required", [
                "external_provider_probe_surface"
            ]
        if full_path.startswith("/api/v1/realms") or full_path.startswith("/api/iam-portal/organizations"):
            return "platform:provisioning_boundary", "review_required", [
                "platform_admin_boundary_requires_authz"
            ]
        if full_path.startswith("/api/v1/agents") or full_path.startswith("/api/v1/hardened-images"):
            return "shared:product_catalog", "baseline", []
        if full_path == "/api/v1/authorize/batch":
            return "body:tenant_id", "review_required", [
                "caller_supplied_batch_tenant_input"
            ]
        if full_path == "/api/v1/authorize/cache":
            return "administrative:authorization_cache_control", "review_required", [
                "cache_control_without_request_identity"
            ]
        if full_path == "/api/v1/entitlements" and method == "POST":
            return "body:tenant_id", "review_required", [
                "caller_supplied_tenant_input"
            ]
        if full_path == "/api/v1/entitlements/bulk" and method in {"PUT", "DELETE"}:
            return "resource:tenant_bound_record_lookup", "review_required", [
                "record_lookup_without_request_tenant_scope"
            ]
        if full_path.startswith("/api/v1/entitlements/") and "{entitlement_id}" in full_path:
            return "resource:tenant_bound_record_lookup", "review_required", [
                "record_lookup_without_request_tenant_scope"
            ]
        if full_path.startswith("/api/v1/role-mappings/") and "{pattern_id}" in full_path:
            return "resource:tenant_bound_record_lookup", "review_required", [
                "record_lookup_without_request_tenant_scope"
            ]
        if full_path.startswith("/internal/iam/auth"):
            return "internal:identity_service_boundary", "baseline", []
        if visibility == "internal" and full_path.startswith("/internal/iam/"):
            return "internal:service_boundary", "review_required", [
                "internal_service_surface_requires_boundary_proof"
            ]

    return primary_source, None, []


def classify_visibility(service: str, default_visibility: str, full_path: str) -> str:
    if full_path.startswith("/internal/"):
        return "internal"
    if service == "ticketing_service":
        return "internal"
    return default_visibility


def load_overrides(root: Path) -> dict:
    path = root / "scripts/audit/multi-tenancy/config/route-overrides.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def apply_override(record: dict, overrides: dict) -> dict:
    key = f"{record['service']}:{record['method']}:{record['surface']}"
    override = overrides.get(key)
    if not override:
        return record

    updated = dict(record)
    for field in [
        "visibility",
        "primary_tenant_source",
        "status",
        "owner",
    ]:
        if field in override:
            updated[field] = override[field]
    if "tenant_sources" in override:
        updated["tenant_sources"] = override["tenant_sources"]
    if "override_inputs" in override:
        updated["override_inputs"] = override["override_inputs"]
    if "risk_flags" in override:
        updated["risk_flags"] = override["risk_flags"]
    if "notes" in override:
        updated["override_notes"] = override["notes"]
    return updated


def build_route_records(root: Path) -> list[dict]:
    records: list[dict] = []
    overrides = load_overrides(root)
    for file_info in load_source_files(root):
        path = file_info["path"]
        text = path.read_text()
        tree = ast.parse(text)
        router_prefixes = extract_router_prefixes(tree)
        function_nodes = extract_function_nodes(tree)
        rel_path = path.relative_to(root).as_posix()

        for node in getattr(tree, "body", []):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            node_source = expanded_source_text(text, node, function_nodes)
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                if not isinstance(decorator.func, ast.Attribute):
                    continue
                if decorator.func.attr not in HTTP_METHODS:
                    continue
                if not isinstance(decorator.func.value, ast.Name):
                    continue

                router_name = decorator.func.value.id
                prefix = router_prefixes.get(router_name, "")
                route_path = extract_route_path(decorator)
                full_path = join_path(prefix, route_path)
                visibility = classify_visibility(
                    file_info["service"],
                    file_info["default_visibility"],
                    full_path,
                )
                tenant_sources = detect_tenant_sources(node_source)
                primary_source = primary_tenant_source(tenant_sources)
                primary_source, inferred_status, inferred_flags = infer_route_family(
                    file_info["service"],
                    visibility,
                    decorator.func.attr.upper(),
                    full_path,
                    primary_source,
                )
                if primary_source not in tenant_sources and primary_source != "unknown":
                    tenant_sources.append(primary_source)
                override_inputs = detect_override_inputs(node_source, full_path)
                risk_flags = detect_risk_flags(node_source, full_path, visibility, primary_source)
                for flag in inferred_flags:
                    if flag not in risk_flags:
                        risk_flags.append(flag)

                status = "baseline"
                if primary_source == "unknown":
                    status = "needs_classification"
                if risk_flags:
                    status = "review_required"
                if inferred_status and not risk_flags:
                    status = inferred_status

                records.append(
                    apply_override(
                        {
                        "service": file_info["service"],
                        "owner": OWNER_BY_SERVICE.get(file_info["service"], file_info["service"]),
                        "visibility": visibility,
                        "method": decorator.func.attr.upper(),
                        "surface": full_path,
                        "router_name": router_name,
                        "handler": node.name,
                        "file": rel_path,
                        "line": node.lineno,
                        "source_ref": f"{rel_path}:{node.lineno}",
                        "tenant_sources": tenant_sources,
                        "primary_tenant_source": primary_source,
                        "override_inputs": override_inputs,
                        "risk_flags": risk_flags,
                        "status": status,
                        },
                        overrides,
                    )
                )
    return sorted(records, key=lambda row: (row["service"], row["surface"], row["method"], row["handler"]))


def write_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "service",
        "visibility",
        "method",
        "surface",
        "handler",
        "owner",
        "file",
        "line",
        "primary_tenant_source",
        "override_inputs",
        "risk_flags",
        "status",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "service": row["service"],
                    "visibility": row["visibility"],
                    "method": row["method"],
                    "surface": row["surface"],
                    "handler": row["handler"],
                    "owner": row["owner"],
                    "file": row["file"],
                    "line": row["line"],
                    "primary_tenant_source": row["primary_tenant_source"],
                    "override_inputs": ";".join(row["override_inputs"]),
                    "risk_flags": ";".join(row["risk_flags"]),
                    "status": row["status"],
                }
            )


def write_summary(path: Path, rows: list[dict]) -> None:
    public_count = sum(1 for row in rows if row["visibility"] == "public")
    internal_count = sum(1 for row in rows if row["visibility"] == "internal")
    review_required = sum(1 for row in rows if row["status"] == "review_required")
    needs_classification = sum(1 for row in rows if row["status"] == "needs_classification")

    by_source: dict[str, int] = {}
    for row in rows:
        by_source[row["primary_tenant_source"]] = by_source.get(row["primary_tenant_source"], 0) + 1

    lines = [
        "# Control Inventory Summary",
        "",
        f"- Total routes inventoried: {len(rows)}",
        f"- Public routes: {public_count}",
        f"- Internal routes: {internal_count}",
        f"- Review required: {review_required}",
        f"- Needs classification: {needs_classification}",
        "",
        "## Primary Tenant Source Counts",
        "",
    ]
    for source_name, count in sorted(by_source.items()):
        lines.append(f"- {source_name}: {count}")
    lines.append("")
    path.write_text("\n".join(lines) + "\n")


def write_review_queue(repo_root: Path, root: Path, rows: list[dict]) -> None:
    queue = [row for row in rows if row["status"] in {"review_required", "needs_classification"}]
    queue = sorted(queue, key=lambda row: (row["owner"], row["service"], row["status"], row["surface"]))

    (root / "review-queue.json").write_text(
        json.dumps({"status": "generated", "items": queue}, indent=2) + "\n"
    )

    with (root / "review-queue.csv").open("w", newline="") as handle:
        fieldnames = [
            "owner",
            "service",
            "status",
            "method",
            "surface",
            "handler",
            "file",
            "line",
            "primary_tenant_source",
            "risk_flags",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in queue:
            writer.writerow(
                {
                    "owner": row["owner"],
                    "service": row["service"],
                    "status": row["status"],
                    "method": row["method"],
                    "surface": row["surface"],
                    "handler": row["handler"],
                    "file": row["file"],
                    "line": row["line"],
                    "primary_tenant_source": row["primary_tenant_source"],
                    "risk_flags": ";".join(row["risk_flags"]),
                }
            )

    by_owner: dict[str, list[dict]] = {}
    for row in queue:
        by_owner.setdefault(row["owner"], []).append(row)

    lines = [
        "# Review Queue",
        "",
        f"- Total items: {len(queue)}",
        "",
    ]
    for owner, items in sorted(by_owner.items()):
        lines.append(f"## {owner}")
        lines.append("")
        for row in items[:25]:
            source_path = (repo_root / row["file"]).resolve()
            lines.append(
                f"- `{row['status']}` `{row['method']} {row['surface']}` "
                f"via `{row['primary_tenant_source']}` "
                f"([source]({source_path}))"
            )
        if len(items) > 25:
            lines.append(f"- ... {len(items) - 25} more")
        lines.append("")
    (root / "review-queue.md").write_text("\n".join(lines) + "\n")


def load_register(root: Path, relative_path: str) -> dict:
    return json.loads((root / relative_path).read_text())


def write_register_copy(register: dict, destination: Path) -> None:
    destination.write_text(json.dumps(register, indent=2) + "\n")


def main() -> int:
    root = repo_root()
    artifact = artifact_root()
    out_dir = artifact / "control-matrix"
    exceptions_dir = artifact / "exceptions"
    out_dir.mkdir(parents=True, exist_ok=True)
    exceptions_dir.mkdir(parents=True, exist_ok=True)

    rows = build_route_records(root)
    public_rows = [row for row in rows if row["visibility"] == "public"]
    internal_rows = [row for row in rows if row["visibility"] == "internal"]

    inventory = {
        "status": "generated",
        "notes": [
            "Route inventory generated from Python API files using AST-based extraction.",
            "This is a heuristic control export and should be reviewed alongside the approved exception register.",
        ],
        "rows": rows,
    }

    (out_dir / "control-matrix.json").write_text(json.dumps(inventory, indent=2) + "\n")
    write_csv(out_dir / "control-matrix.csv", rows)
    (out_dir / "public-routes.json").write_text(
        json.dumps({"status": "generated", "routes": public_rows}, indent=2) + "\n"
    )
    (out_dir / "internal-routes.json").write_text(
        json.dumps({"status": "generated", "routes": internal_rows}, indent=2) + "\n"
    )
    write_summary(out_dir / "inventory-summary.md", rows)
    write_review_queue(root, out_dir, rows)

    shared_data_register = load_register(
        root,
        "scripts/audit/multi-tenancy/config/registers/shared-data-register.json",
    )
    approved_exceptions = load_register(
        root,
        "scripts/audit/multi-tenancy/config/registers/approved-exceptions.json",
    )
    write_register_copy(shared_data_register, exceptions_dir / "shared-data-register.json")
    write_register_copy(approved_exceptions, exceptions_dir / "approved-exceptions.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
