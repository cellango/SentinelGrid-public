#!/usr/bin/env python3
"""
Seed detections, detection rule versions, playbooks, and mappings from cfg catalogs
into the system and demo tenants. This replaces legacy migration-based seeding.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set
import sys

import psycopg2
import yaml

# Tenants (override via env when local Keycloak uses a different demo/system tenant)
SYSTEM_TENANT = os.getenv("SYSTEM_TENANT", "9c7df7a9-5a0b-4412-a41c-0c0ea777b2f0")
DEMO_TENANT = os.getenv("DEMO_TENANT", "c6d82f67-36f1-4c7e-af66-d1333e45cde7")

if SYSTEM_TENANT == DEMO_TENANT:
    print("❌ SYSTEM_TENANT and DEMO_TENANT must differ to avoid duplicating catalog assets into a tenant scope.")
    sys.exit(1)

# DB
DB_URL = os.getenv("DB_URL", "postgresql://sg:sg@localhost:5432/sg")
EMIT_SQL_ONLY = os.getenv("EMIT_SQL", "0").lower() in ("1", "true", "yes")

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
  sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "backend") not in sys.path:
  sys.path.insert(0, str(REPO_ROOT / "backend"))
if str(REPO_ROOT / "backend" / "agents") not in sys.path:
  sys.path.insert(0, str(REPO_ROOT / "backend" / "agents"))
DETECTIONS_PATH = REPO_ROOT / "cfg" / "detections" / "catalog.yaml"
PLAYBOOKS_PATH = REPO_ROOT / "cfg" / "playbooks" / "catalog.yaml"

# Monitor definitions builder (uses catalog)
from agents.siem_agent.app.config.monitor_definitions import get_all_monitor_definitions  # type: ignore


SOC2_DEFAULT_MAP: Dict[str, List[str]] = {
    "identity": ["CC6.1", "CC4.1"],  # Logical access + monitoring
    "phish": ["CC2.1", "CC6.1", "CC4.1"],  # Comms + access monitoring
    "endpoint": ["CC6.1", "CC7.1", "CC4.1"],  # Access + ops + monitoring
    "network": ["CC7.1", "CC4.1"],  # System ops + monitoring
    "cloud": ["CC7.1", "CC8.1", "CC9.1"],  # Ops + change mgmt + risk mitigation
    "exec": ["CC1.1", "CC2.1"],  # Control environment + comms
    "ai": ["CC2.1", "CC3.1"],  # Comms + risk assessment
    "vuln": ["CC7.1", "CC8.1", "CC9.1"],  # Ops + change + risk mitigation
}


def load_yaml(path: Path) -> Dict[str, Any]:
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def _derive_soc2_criteria(entry: Dict[str, Any]) -> List[str]:
    """Heuristic SOC 2 mapping from category/incident type."""
    incident = (
        entry.get("incident_type")
        or entry.get("category")
        or entry.get("owner")
        or entry.get("alert_type")
        or ""
    ).lower()
    severity = (entry.get("severity") or "").lower()
    criteria: Set[str] = set()

    for key, mapped in SOC2_DEFAULT_MAP.items():
        if key in incident:
            criteria.update(mapped)

    if "public_exposure" in incident or "exposure" in incident:
        criteria.update(["CC7.1", "CC8.1", "CC9.1"])
    if "scan" in incident or "vulnerability" in incident:
        criteria.update(SOC2_DEFAULT_MAP["vuln"])
    if severity in ("critical", "high"):
        criteria.add("CC3.1")

    if not criteria:
        criteria.add("CC4.1")

    return sorted(criteria)


def connect():
    return psycopg2.connect(DB_URL)


def upsert_playbooks(cur, tenant_id: str, playbooks: List[Dict[str, Any]], as_builtin: bool) -> Dict[str, str]:
    """Insert playbooks and return mapping playbook_key -> id for this tenant."""
    mapping = {}
    def default_workflow(pb: Dict[str, Any]) -> Dict[str, Any]:
        """Simple day-one workflow to make OOTB playbooks usable in the editor."""
        steps_by_type = {
            "identity_privilege_escalation": [
                ("ingest", "Validate alert context", "Confirm source user, role change, and device risk."),
                ("contain", "Disable sessions / step-up auth", "Require MFA reset or block account if risk high."),
                ("notify", "Notify IAM/SOC", "Escalate to IAM/SOC channel with details and MITRE/NIST context.")
            ],
            "identity_auth_anomaly": [
                ("ingest", "Review failed logins", "Correlate IP/user agent and geo anomalies."),
                ("contain", "Temporarily lock account", "Lockout or require password reset if spray suspected."),
                ("notify", "Notify user + SOC", "Send user notification and SOC ticket.")
            ],
            "phishing_user_report": [
                ("ingest", "Collect reported message", "Pull headers/body, hashes, URLs."),
                ("contain", "Quarantine similar mail", "Search-and-quarantine campaign across mailboxes."),
                ("notify", "User follow-up", "Acknowledge reporter and advise next steps.")
            ],
            "phishing_gateway_alert": [
                ("ingest", "Validate gateway alert", "Confirm rule hit, IOC, and prevalence."),
                ("contain", "Quarantine/Block indicators", "Block sender domains/URLs/attachments in SEG."),
                ("notify", "Ticket + comms", "Open ticket and inform affected users if needed.")
            ],
            "endpoint_malware_ransomware": [
                ("contain", "Isolate endpoint", "Quarantine host via EDR, stop spread."),
                ("eradicate", "Kill process/remove artifact", "Kill malicious processes, delete/quarantine files."),
                ("recover", "Reimage/restore", "Rebuild device or restore from known-good backup.")
            ],
            "endpoint_suspicious_activity": [
                ("ingest", "Collect triage data", "Process tree, network connections, user context."),
                ("contain", "Isolate if high risk", "Quarantine if C2/lateral movement suspected."),
                ("investigate", "Hunt similar events", "Search for same hash/IP across fleet.")
            ],
            "ai_data_leak": [
                ("ingest", "Review prompt/response", "Check PII/secrets flags and destination."),
                ("contain", "Block app/user", "Disable offending app/user until reviewed."),
                ("notify", "Privacy/Security review", "Open ticket to privacy/SOC for follow-up.")
            ],
            "ai_prompt_injection": [
                ("ingest", "Inspect prompt injection", "Review guardrail signal and payload."),
                ("contain", "Block source IP/app", "Add deny rule or stricter policy for actor."),
                ("notify", "Guardrail tuning", "Feed sample to guardrail tuning backlog.")
            ],
            "cloud_public_exposure": [
                ("ingest", "Enumerate exposed assets", "List buckets/objects marked public; capture ACL/policy diff."),
                ("contain", "Remove public access", "Apply block-public-acls/policies and restrict access to principals."),
                ("investigate", "Check access/egress logs", "Review CloudTrail/storage access logs for downloads."),
                ("notify", "Owners + compliance", "Notify bucket owners, create ticket, document NIST/ATT&CK mapping.")
            ],
            "default": [
                ("ingest", "Validate alert", "Confirm scope, asset, and severity."),
                ("contain", "Containment", "Apply containment appropriate to source."),
                ("notify", "Notify/Document", "Open ticket, document actions and timeline.")
            ],
        }
        key = (pb.get("incident_type") or pb.get("owner") or "default").lower()
        steps = steps_by_type.get(key, steps_by_type["default"])
        nodes = []
        edges = []
        for idx, (_stype, label, desc) in enumerate(steps):
            node_id = f"n{idx+1}"
            nodes.append({
                "id": node_id,
                "type": "action" if idx > 0 else "trigger",
                "position": {"x": 80, "y": 80 + idx * 140},
                "data": {
                    "label": label,
                    "description": desc,
                    "step_type": "action",
                    "owner": pb.get("owner") or pb.get("incident_type") or "soar",
                    "mitre": pb.get("mitre_techniques") or pb.get("mitre_tactics") or [],
                    "nist": pb.get("nist_controls") or [],
                },
              })
            if idx > 0:
                edges.append({
                    "id": f"e{idx}-{idx+1}",
                    "source": f"n{idx}",
                    "target": node_id,
                    "type": "smoothstep"
                })
        return {"nodes": nodes, "edges": edges, "viewport": {"x": 0, "y": 0, "zoom": 1}}

    for pb in playbooks:
        key = pb.get("id")
        if not key:
            continue
        name = pb.get("name", key)
        runbook_ref = pb.get("runbook_ref") or key
        triggers = pb.get("triggers") or [f"Alert: {key}"]
        category = pb.get("owner") or pb.get("incident_type") or "general"
        category_filter = {"categories": [category]}
        mitre_tactics = pb.get("mitre_tactics", [])
        mitre_techniques = pb.get("mitre_techniques", [])
        nist_controls = pb.get("nist_controls", [])
        soc2_criteria = pb.get("soc2_criteria") or _derive_soc2_criteria(pb)
        automation_default = pb.get("automation_default", "manual")
        is_builtin = as_builtin
        # Built-in/catalog playbooks should not require approval by default
        requires_approval = False
        workflow = default_workflow(pb)

        cur.execute(
            """
            INSERT INTO playbooks (
                tenant_id, key, name, description, target_type, severity_filter,
                category_filter, workflow_ref, requires_approval, is_enabled,
                triggers, playbook_key, is_builtin, category, workflow,
                nist_controls, mitre_tactics, mitre_techniques, soc2_criteria, tags
            )
            VALUES (%s, %s, %s, %s, 'alert', %s, %s, %s, %s, true,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (playbook_key) WHERE is_builtin = true DO UPDATE
              SET name = EXCLUDED.name,
                  description = EXCLUDED.description,
                  category = EXCLUDED.category,
                  category_filter = EXCLUDED.category_filter,
                  workflow = EXCLUDED.workflow,
                  triggers = COALESCE(playbooks.triggers, EXCLUDED.triggers)
            RETURNING id;
            """,
            (
                tenant_id,
                key,
                name,
                pb.get("description", ""),
                json.dumps(None),
                json.dumps(category_filter),
                runbook_ref,
                requires_approval,
                triggers,
                key,
                is_builtin,
                category,
                json.dumps(workflow),
                nist_controls,
                mitre_tactics,
                mitre_techniques,
                soc2_criteria,
                pb.get("tags", []),
            ),
        )
        playbook_id = cur.fetchone()[0]
        mapping[key] = playbook_id
    return mapping


def upsert_detection_rules(cur, tenant_id: str, detections: List[Dict[str, Any]], as_builtin: bool) -> Dict[str, str]:
    """Insert detection_rules for tenant, return rule_key -> id."""
    mapping = {}
    for det in detections:
        key = det.get("id")
        if not key:
            continue
        cur.execute(
            """
            INSERT INTO detection_rules (
                rule_key, name, description, category, current_version, is_builtin,
                created_by, tenant_id, approval_required
            )
            VALUES (%s, %s, %s, %s, 'v1', %s, %s, %s, false)
            ON CONFLICT (rule_key, tenant_id) DO UPDATE
              SET name = EXCLUDED.name,
                  description = EXCLUDED.description,
                  category = EXCLUDED.category,
                  current_version = EXCLUDED.current_version
            RETURNING id;
            """,
            (
                key,
                det.get("name", key),
                det.get("description", det.get("incident_type", "")),
                det.get("category", "general"),
                as_builtin,
                "seed_catalog",
                tenant_id,
            ),
        )
        rule_id = cur.fetchone()[0]
        mapping[key] = rule_id
    return mapping


def upsert_detection_versions(cur, tenant_id: str, rule_ids: Dict[str, str], detections: List[Dict[str, Any]], monitors: List[Dict[str, Any]]):
    # Build a combined map of rule_key -> version payload, preferring catalog detections.
    combined = {}
    for det in detections:
        rk = det.get("id")
        if not rk:
            continue
        soc2_criteria = det.get("soc2_criteria") or _derive_soc2_criteria(det)
        combined[rk] = {
            "rule_key": rk,
            "index_pattern": det.get("index_pattern", "sg-{tenant_id}-*"),
            "query": det.get("query"),
            "trigger_condition": det.get("trigger_condition"),
            "severity": det.get("severity", "medium"),
            "metadata": {
                "alert_type": det.get("alert_type") or det.get("incident_type") or det.get("category"),
                "mitre_techniques": det.get("mitre_techniques", []),
                "mitre_tactics": det.get("mitre_tactics", []),
                "nist_controls": det.get("nist_controls", []),
                "soc2_criteria": soc2_criteria,
            },
        }
    for mon in monitors:
        rk = mon.get("rule_key")
        if not rk or rk in combined:
            continue
        soc2_criteria = mon.get("metadata", {}).get("soc2_criteria") or _derive_soc2_criteria(mon)
        combined[rk] = {
            "rule_key": rk,
            "index_pattern": mon.get("index_pattern"),
            "query": mon.get("query"),
            "trigger_condition": mon.get("trigger_condition"),
            "severity": mon.get("severity", "medium"),
            "metadata": {
                "alert_type": mon.get("alert_type"),
                "playbook_id": mon.get("playbook_id"),
                "mitre_techniques": mon.get("metadata", {}).get("mitre_techniques", []),
                "mitre_tactics": mon.get("metadata", {}).get("mitre_tactics", []),
                "nist_controls": mon.get("metadata", {}).get("nist_controls", []),
                "soc2_criteria": soc2_criteria,
            },
        }

    for rk, payload in combined.items():
        if rk not in rule_ids:
            continue
        cur.execute(
            """
            INSERT INTO detection_rule_versions (
                rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, '{}'::jsonb, %s)
            ON CONFLICT (rule_id, version) DO UPDATE
              SET index_pattern = EXCLUDED.index_pattern,
                  query = EXCLUDED.query,
                  trigger_condition = EXCLUDED.trigger_condition,
                  severity = EXCLUDED.severity,
                  metadata = EXCLUDED.metadata;
            """,
            (
                rule_ids[rk],
                "v1",
                payload.get("index_pattern"),
                json.dumps(payload.get("query")),
                json.dumps(payload.get("trigger_condition")),
                payload.get("severity", "medium"),
                json.dumps(payload.get("metadata", {})),
            ),
        )


def upsert_mappings(cur, tenant_id: str, detections: List[Dict[str, Any]], rule_ids: Dict[str, str], playbook_ids: Dict[str, str]):
    for det in detections:
        rule_key = det.get("id")
        if not rule_key or rule_key not in rule_ids:
            continue
        pb_key = det.get("default_playbook_key")
        playbook_id = playbook_ids.get(pb_key) if pb_key else None
        cur.execute(
            """
            INSERT INTO detection_playbook_mappings (
                tenant_id, rule_id, alert_type, playbook_id, playbook_key, auto_execute, requires_approval, severity_threshold
            )
            VALUES (%s, %s, %s, %s, %s, false, false, NULL)
            ON CONFLICT (tenant_id, alert_type) DO NOTHING;
            """,
            (
                tenant_id,
                rule_ids[rule_key],
                det.get("alert_type") or det.get("incident_type") or det.get("category"),
                playbook_id,
                pb_key,
            ),
        )


def main():
    detections = load_yaml(DETECTIONS_PATH).get("detections", [])
    playbooks = load_yaml(PLAYBOOKS_PATH).get("playbooks", [])
    monitors = get_all_monitor_definitions()

    if EMIT_SQL_ONLY:
        statements = []
        for tenant_id, as_builtin in [(SYSTEM_TENANT, True), (DEMO_TENANT, False)]:
            statements += [
                f"DELETE FROM detection_rule_executions WHERE rule_id IN (SELECT id FROM detection_rules WHERE tenant_id = '{tenant_id}');",
                f"DELETE FROM detection_bindings WHERE detection_rule_id IN (SELECT id FROM detection_rules WHERE tenant_id = '{tenant_id}');",
                f"DELETE FROM detection_suppression_events WHERE suppression_rule_id IN (SELECT id FROM detection_suppression_rules WHERE tenant_id = '{tenant_id}');",
                f"DELETE FROM detection_suppression_rules WHERE tenant_id = '{tenant_id}';",
                f"DELETE FROM detection_deduplication WHERE rule_id IN (SELECT id FROM detection_rules WHERE tenant_id = '{tenant_id}');",
                f"DELETE FROM detection_playbook_mappings WHERE tenant_id = '{tenant_id}';",
                f"DELETE FROM tenant_detection_monitors WHERE tenant_id = '{tenant_id}';",
                f"DELETE FROM detection_rule_versions WHERE rule_id IN (SELECT id FROM detection_rules WHERE tenant_id = '{tenant_id}');",
                f"DELETE FROM detection_rules WHERE tenant_id = '{tenant_id}';",
                f"DELETE FROM playbook_execution_audit WHERE playbook_id IN (SELECT id FROM playbooks WHERE tenant_id = '{tenant_id}');",
                f"DELETE FROM playbook_executions WHERE playbook_id IN (SELECT id FROM playbooks WHERE tenant_id = '{tenant_id}');",
                f"DELETE FROM playbook_observables WHERE playbook_id IN (SELECT id FROM playbooks WHERE tenant_id = '{tenant_id}');",
                f"DELETE FROM playbook_analyzers WHERE playbook_id IN (SELECT id FROM playbooks WHERE tenant_id = '{tenant_id}');",
                f"DELETE FROM alert_playbook_triggers WHERE playbook_id IN (SELECT id FROM playbooks WHERE tenant_id = '{tenant_id}');",
                f"DELETE FROM playbooks WHERE tenant_id = '{tenant_id}';",
            ]
            for pb in playbooks:
                key = pb.get("id")
                if not key:
                    continue
                name = pb.get("name", key).replace("'", "''")
                desc = pb.get("description", "").replace("'", "''")
                runbook_ref = (pb.get("runbook_ref") or key).replace("'", "''")
                triggers = pb.get("triggers") or [f"Alert: {key}"]
                category = (pb.get("owner") or pb.get("incident_type") or "general").replace("'", "''")
                category_filter = json.dumps({"categories": [category]}).replace("'", "''")
                def sql_array(values):
                    if not values:
                        return "ARRAY[]::text[]"
                    return "ARRAY[" + ",".join("'" + v.replace("'", "''") + "'" for v in values) + "]"

                nist_controls_arr = sql_array(pb.get("nist_controls", []))
                mitre_tactics_arr = sql_array(pb.get("mitre_tactics", []))
                mitre_techniques_arr = sql_array(pb.get("mitre_techniques", []))
                soc2_arr = sql_array(pb.get("soc2_criteria") or _derive_soc2_criteria(pb))
                tags_arr = sql_array(pb.get("tags", []))
                requires_approval = "false"
                is_builtin = str(as_builtin).lower()
                workflow = json.dumps({"nodes": [], "edges": []}).replace("'", "''")
                sanitized_triggers = [t.replace("'", "''") for t in triggers]
                triggers_arr = "ARRAY[" + ",".join("'" + t + "'" for t in sanitized_triggers) + "]"
                statements.append(
                    f"INSERT INTO playbooks (tenant_id, key, name, description, target_type, severity_filter, category_filter, workflow_ref, requires_approval, is_enabled, triggers, playbook_key, is_builtin, category, workflow, nist_controls, mitre_tactics, mitre_techniques, soc2_criteria, tags) "
                    f"VALUES ('{tenant_id}', '{key}', '{name}', '{desc}', 'alert', NULL, '{category_filter}', '{runbook_ref}', {requires_approval}, true, {triggers_arr}, '{key}', {is_builtin}, '{category}', '{workflow}', {nist_controls_arr}, {mitre_tactics_arr}, {mitre_techniques_arr}, {soc2_arr}, {tags_arr}) "
                    f"ON CONFLICT (playbook_key) WHERE is_builtin = true DO UPDATE SET category = EXCLUDED.category, category_filter = EXCLUDED.category_filter, triggers = COALESCE(playbooks.triggers, EXCLUDED.triggers);"
                )
            for det in detections:
                key = det.get("id")
                if not key:
                    continue
                name = det.get("name", key).replace("'", "''")
                desc = det.get("description", det.get("incident_type", "")).replace("'", "''")
                cat = det.get("category", "general").replace("'", "''")
                statements.append(
                    f"INSERT INTO detection_rules (rule_key, name, description, category, current_version, is_builtin, created_by, tenant_id, approval_required) "
                    f"VALUES ('{key}', '{name}', '{desc}', '{cat}', 'v1', {str(as_builtin).lower()}, 'seed_catalog', '{tenant_id}', false) "
                    f"ON CONFLICT (rule_key, tenant_id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, category = EXCLUDED.category;"
                )
        for tenant_id in [SYSTEM_TENANT, DEMO_TENANT]:
            for mon in monitors:
                rk = mon.get("rule_key")
                if not rk:
                    continue
                soc2 = mon.get("metadata", {}).get("soc2_criteria") or _derive_soc2_criteria(mon)
                query_json = json.dumps(mon.get("query")).replace("'", "''")
                trigger_json = json.dumps(mon.get("trigger_condition")).replace("'", "''")
                metadata_json = json.dumps(
                    {
                        "alert_type": mon.get("alert_type"),
                        "playbook_id": mon.get("playbook_id"),
                        "mitre_techniques": mon.get("metadata", {}).get("mitre_techniques", []),
                        "mitre_tactics": mon.get("metadata", {}).get("mitre_tactics", []),
                        "nist_controls": mon.get("metadata", {}).get("nist_controls", []),
                        "soc2_criteria": soc2,
                    }
                ).replace("'", "''")
                statements.append(
                    f"INSERT INTO detection_rule_versions (rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata) "
                    f"SELECT id, 'v1', '{mon.get('index_pattern')}', '{query_json}', '{trigger_json}', '{mon.get('severity','medium')}', '{{}}'::jsonb, '{metadata_json}' "
                    f"FROM detection_rules WHERE rule_key = '{rk}' AND tenant_id = '{tenant_id}' "
                    f"ON CONFLICT (rule_id, version) DO UPDATE SET index_pattern = EXCLUDED.index_pattern, query = EXCLUDED.query, trigger_condition = EXCLUDED.trigger_condition, severity = EXCLUDED.severity, metadata = EXCLUDED.metadata;"
                )
            for det in detections:
                rk = det.get("id")
                if not rk:
                    continue
                pb_key = det.get("default_playbook_key")
                alert_type = det.get("alert_type") or det.get("incident_type") or det.get("category")
                statements.append(
                    f"INSERT INTO detection_playbook_mappings (tenant_id, rule_id, alert_type, playbook_id, playbook_key, auto_execute, requires_approval, severity_threshold) "
                    f"SELECT '{tenant_id}', dr.id, '{alert_type}', pb.id, '{pb_key}', false, false, NULL "
                    f"FROM detection_rules dr "
                    f"LEFT JOIN playbooks pb ON pb.playbook_key = '{pb_key}' AND pb.tenant_id = '{tenant_id}' "
                    f"WHERE dr.rule_key = '{rk}' AND dr.tenant_id = '{tenant_id}' "
                    f"ON CONFLICT (tenant_id, alert_type) DO UPDATE SET playbook_id = EXCLUDED.playbook_id, playbook_key = EXCLUDED.playbook_key, rule_id = EXCLUDED.rule_id;"
                )
        print("-- SQL statements to seed catalog detections/playbooks")
        print("\n".join(statements))
        return

    with connect() as conn:
        with conn.cursor() as cur:
            # System tenant
            sys_playbooks = upsert_playbooks(cur, SYSTEM_TENANT, playbooks, as_builtin=True)
            sys_rules = upsert_detection_rules(cur, SYSTEM_TENANT, detections, as_builtin=True)
            upsert_detection_versions(cur, SYSTEM_TENANT, sys_rules, detections, monitors)
            upsert_mappings(cur, SYSTEM_TENANT, detections, sys_rules, sys_playbooks)

            # Demo tenant: do NOT duplicate built-ins. Only map to canonical system rules/playbooks.
            upsert_mappings(cur, DEMO_TENANT, detections, sys_rules, sys_playbooks)

        conn.commit()
    print("Seeded catalog detections/playbooks for system and demo tenants.")


if __name__ == "__main__":
    main()
