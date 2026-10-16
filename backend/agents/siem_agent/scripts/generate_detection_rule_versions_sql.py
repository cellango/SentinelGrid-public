"""
Generate SQL to upsert detection_rule_versions from the catalog-based monitor definitions.

Usage:
  python scripts/generate_detection_rule_versions_sql.py > out.sql
Then run out.sql against the database to replace the placeholder match_all versions.
"""

import json
from textwrap import dedent
from typing import List

from app.config.monitor_definitions import get_all_monitor_definitions

# Use the same system/demo tenant IDs used by seeding; override via env if needed.
import os
SYS_TENANT = os.getenv("SYSTEM_TENANT", "9c7df7a9-5a0b-4412-a41c-0c0ea777b2f0")
DEMO_TENANT = os.getenv("DEMO_TENANT", "c6d82f67-36f1-4c7e-af66-d1333e45cde7")
VERSION = os.getenv("VERSION", "v1")


def build_upsert_sql(monitors: List[dict], tenant_id: str) -> str:
    statements = []
    for mon in monitors:
        rule_key = mon.get("rule_key")
        if not rule_key:
            continue
        sql = dedent(
            f"""
            WITH rule_row AS (
                SELECT id FROM detection_rules
                WHERE rule_key = '{rule_key}' AND tenant_id = '{tenant_id}'
            )
            INSERT INTO detection_rule_versions (
                rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
            )
            SELECT
                rule_row.id,
                '{VERSION}',
                '{mon.get("index_pattern")}',
                '{json.dumps(mon.get("query"))}',
                '{json.dumps(mon.get("trigger_condition"))}',
                '{mon.get("severity", "medium")}',
                '{{}}'::jsonb,
                jsonb_build_object(
                    'alert_type', '{mon.get("alert_type")}',
                    'playbook_id', '{mon.get("playbook_id")}',
                    'mitre_techniques', '{json.dumps(mon.get("metadata", {}).get("mitre_techniques", []))}'::jsonb,
                    'mitre_tactics', '{json.dumps(mon.get("metadata", {}).get("mitre_tactics", []))}'::jsonb,
                    'nist_controls', '{json.dumps(mon.get("metadata", {}).get("nist_controls", []))}'::jsonb
                )
            FROM rule_row
            ON CONFLICT (rule_id, version) DO UPDATE
            SET index_pattern = EXCLUDED.index_pattern,
                query = EXCLUDED.query,
                trigger_condition = EXCLUDED.trigger_condition,
                severity = EXCLUDED.severity,
                metadata = EXCLUDED.metadata;
            """
        ).strip()
        statements.append(sql)
    return "\n\n".join(statements)


if __name__ == "__main__":
    monitors = get_all_monitor_definitions()
    print("-- Generated from catalog monitors; apply to system and demo tenants to replace match_all placeholders.")
    print(build_upsert_sql(monitors, SYS_TENANT))
    print()
    print(build_upsert_sql(monitors, DEMO_TENANT))
