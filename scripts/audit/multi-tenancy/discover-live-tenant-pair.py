#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def artifact_root() -> Path:
    artifact_dir = os.environ.get("AUDIT_ARTIFACT_DIR")
    if not artifact_dir:
        raise SystemExit("AUDIT_ARTIFACT_DIR is required")
    return Path(artifact_dir)


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


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def write_env(path: Path, payload: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}={json.dumps(value)}" for key, value in payload.items()]
    path.write_text("\n".join(lines) + "\n")


def run_psql_json(postgres_url: str, sql: str) -> object:
    result = subprocess.run(
        [
            "psql",
            postgres_url,
            "-X",
            "-A",
            "-t",
            "-q",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            sql,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    stdout = result.stdout.strip()
    if not stdout:
        return None
    return json.loads(stdout)


def collect_tenant_counts(postgres_url: str) -> list[dict[str, object]]:
    sql = """
BEGIN;
SET LOCAL app.is_superadmin = 'true';
CREATE TEMP TABLE audit_pair_candidates (
    schema_name text,
    table_name text,
    tenant_id text,
    row_count bigint
) ON COMMIT DROP;
DO $audit$
DECLARE
    rec RECORD;
BEGIN
    FOR rec IN
        SELECT c.table_schema, c.table_name
        FROM information_schema.columns c
        JOIN information_schema.tables t
          ON t.table_schema = c.table_schema
         AND t.table_name = c.table_name
        WHERE c.column_name = 'tenant_id'
          AND t.table_type = 'BASE TABLE'
          AND c.table_schema NOT IN ('pg_catalog', 'information_schema')
    LOOP
        EXECUTE format(
            'INSERT INTO audit_pair_candidates (schema_name, table_name, tenant_id, row_count) '
            'SELECT %L, %L, tenant_id::text, count(*) '
            'FROM %I.%I '
            'WHERE tenant_id IS NOT NULL '
            'GROUP BY tenant_id::text '
            'HAVING count(*) > 0',
            rec.table_schema,
            rec.table_name,
            rec.table_schema,
            rec.table_name
        );
    END LOOP;
END
$audit$;
SELECT COALESCE(
    json_agg(row_to_json(x) ORDER BY x.schema_name, x.table_name, x.row_count DESC, x.tenant_id),
    '[]'::json
)::text
FROM (
    SELECT schema_name, table_name, tenant_id, row_count
    FROM audit_pair_candidates
) x;
ROLLBACK;
"""
    return run_psql_json(postgres_url, sql) or []


def build_pair_candidates(
    rows: list[dict[str, object]],
    per_table_limit: int,
) -> tuple[list[dict[str, object]], dict[str, object] | None]:
    table_entries: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = (str(row["schema_name"]), str(row["table_name"]))
        table_entries[key].append(
            {
                "schema_name": str(row["schema_name"]),
                "table_name": str(row["table_name"]),
                "tenant_id": str(row["tenant_id"]),
                "row_count": int(row["row_count"]),
            }
        )

    pair_map: dict[tuple[str, str], dict[str, object]] = {}
    for (schema_name, table_name), entries in table_entries.items():
        ranked = sorted(entries, key=lambda item: (-item["row_count"], item["tenant_id"]))[:per_table_limit]
        if len(ranked) < 2:
            continue
        for left, right in combinations(ranked, 2):
            tenant_a_id, tenant_b_id = sorted((left["tenant_id"], right["tenant_id"]))
            key = (tenant_a_id, tenant_b_id)
            candidate = pair_map.setdefault(
                key,
                {
                    "tenant_a_id": tenant_a_id,
                    "tenant_b_id": tenant_b_id,
                    "supporting_tables": [],
                    "supporting_table_count": 0,
                    "supporting_row_total": 0,
                },
            )
            candidate["supporting_tables"].append(
                {
                    "schema_name": schema_name,
                    "table_name": table_name,
                    "tenant_a_count": left["row_count"] if left["tenant_id"] == tenant_a_id else right["row_count"],
                    "tenant_b_count": right["row_count"] if right["tenant_id"] == tenant_b_id else left["row_count"],
                }
            )
            candidate["supporting_table_count"] += 1
            candidate["supporting_row_total"] += left["row_count"] + right["row_count"]

    candidates = sorted(
        pair_map.values(),
        key=lambda item: (
            -int(item["supporting_table_count"]),
            -int(item["supporting_row_total"]),
            str(item["tenant_a_id"]),
            str(item["tenant_b_id"]),
        ),
    )
    selected = candidates[0] if candidates else None
    return candidates, selected


def main() -> int:
    output_root = artifact_root() / "rls-report"
    output_root.mkdir(parents=True, exist_ok=True)

    postgres_url = os.environ.get("POSTGRES_URL", "").strip()
    per_table_limit = int(os.environ.get("AUDIT_DISCOVERY_PER_TABLE_LIMIT", "5"))

    metadata: dict[str, object] = {
        "status": "skipped",
        "postgres_url": redact_postgres_url(postgres_url) if postgres_url else "",
        "psql_available": shutil.which("psql") is not None,
        "per_table_limit": per_table_limit,
        "selected_pair": None,
        "candidate_pair_count": 0,
        "notes": [],
    }

    if not postgres_url:
        metadata["notes"].append("POSTGRES_URL is not configured.")
        write_json(output_root / "live-inputs.json", metadata)
        return 0

    if not metadata["psql_available"]:
        metadata["notes"].append("psql is not installed.")
        write_json(output_root / "live-inputs.json", metadata)
        return 0

    try:
        rows = collect_tenant_counts(postgres_url)
    except Exception as exc:  # pragma: no cover - exercised in local script execution
        metadata["status"] = "failed"
        metadata["notes"].append(f"Tenant-pair discovery failed: {exc}")
        write_json(output_root / "live-inputs.json", metadata)
        return 0

    metadata["tenant_count_rows"] = len(rows)
    candidates, selected = build_pair_candidates(rows, per_table_limit=per_table_limit)
    metadata["candidate_pair_count"] = len(candidates)
    metadata["candidate_pairs_preview"] = candidates[:10]

    if not selected:
        metadata["status"] = "skipped"
        metadata["notes"].append("No live table exposed at least two tenant IDs with data.")
        write_json(output_root / "live-inputs.json", metadata)
        return 0

    metadata["status"] = "passed"
    metadata["selected_pair"] = selected
    write_json(output_root / "live-inputs.json", metadata)
    write_env(
        output_root / "live-inputs.env",
        {
            "AUDIT_TENANT_A_ID": str(selected["tenant_a_id"]),
            "AUDIT_TENANT_B_ID": str(selected["tenant_b_id"]),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
