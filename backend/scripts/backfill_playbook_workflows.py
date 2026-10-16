#!/usr/bin/env python3
"""
Backfill playbook.workflow for catalog playbooks that have empty/null workflows.
Uses the same default workflow generator as the catalog seeder.
"""

import json
import os
from pathlib import Path
import psycopg2

DB_URL = os.getenv("DB_URL", "postgresql://sg:sg@localhost:5432/sg")
REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "cfg" / "playbooks" / "catalog.yaml"

import yaml  # noqa


def default_workflow(pb):
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


def load_catalog():
    data = yaml.safe_load(CATALOG_PATH.read_text()) or {}
    return {pb["id"]: pb for pb in data.get("playbooks", [])}


def backfill():
    catalog = load_catalog()
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute("""
      SELECT id, playbook_key, workflow, category_filter, category
      FROM playbooks
      WHERE workflow IS NULL OR workflow = '{}'::jsonb OR (workflow->'nodes') = '[]'::jsonb
    """)
    rows = cur.fetchall()
    updated = 0
    for row in rows:
        pb_id, key, wf, category_filter, category = row
        owner = None
        if isinstance(category_filter, dict):
            cats = category_filter.get("categories") or []
            owner = cats[0] if cats else category
        elif isinstance(category_filter, list) and category_filter:
            owner = category_filter[0]
        else:
            owner = category
        cat = catalog.get(key) or {"incident_type": owner, "owner": owner}
        wf_json = json.dumps(default_workflow(cat))
        cur.execute("UPDATE playbooks SET workflow = %s WHERE id = %s", (wf_json, pb_id))
        updated += 1
    conn.commit()
    print(f"Backfilled {updated} playbooks with default workflows")
    conn.close()


if __name__ == "__main__":
    backfill()
