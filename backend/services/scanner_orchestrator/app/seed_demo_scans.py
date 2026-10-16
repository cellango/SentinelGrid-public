"""
Best-effort seeding of demo scans for the demo tenant so the UI has data.
"""

import os
import uuid
from datetime import datetime, timedelta
import psycopg2
import json

DEMO_TENANT = os.getenv("DEMO_TENANT_ID", "ff1c2b60-1fd6-46d1-8458-b0484f5d58f8")
DB_URL = os.getenv("DB_URL", "postgresql://sg:sg@postgres:5432/sg")


def seed():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    now = datetime.utcnow()
    sample_cves = ["CVE-2024-1234", "CVE-2023-9999", "CVE-2022-5555"]
    scans = [
        {
            "id": uuid.uuid4(),
            "scanner_id": "cloud",
            "scan_type": "cloud",
            "target_ref": "aws-demo",
            "status": "completed",
            "started_at": now - timedelta(minutes=30),
            "finished_at": now - timedelta(minutes=25),
            "summary": {
                "findings": 2,
                "severity": "high",
                "type": "cloud",
                "soc2_criteria": ["CC7.1", "CC8.1", "CC9.1"],
                "externally_exposed": False,
                "nist_controls": ["RA-5", "CM-6"],
                "mitre_techniques": ["T1580"],
                "failing_controls": [
                    {"id": "S3-001", "description": "Public bucket access allowed", "remediation": "Enable block public access"},
                    {"id": "IAM-002", "description": "IAM key older than 90 days", "remediation": "Rotate access keys"},
                ],
                "remediation": {
                    "summary": "Tighten cloud posture controls.",
                    "steps": [
                        "Enable GuardDuty/CloudTrail for all regions",
                        "Restrict public buckets and rotate IAM keys",
                        "Re-run cloud posture scan",
                    ],
                    "validation": ["Cloud posture scan returns zero high-risk findings"],
                },
            },
        },
        {
            "id": uuid.uuid4(),
            "scanner_id": "trivy",
            "scan_type": "vuln",
            "target_ref": "device-demo-01",
            "status": "completed",
            "started_at": now - timedelta(hours=1, minutes=15),
            "finished_at": now - timedelta(hours=1, minutes=10),
            "summary": {
                "findings": 5,
                "severity": "critical",
                "type": "vuln",
                "target_kind": "device",
                "soc2_criteria": ["CC7.1", "CC8.1", "CC9.1"],
                "cves": [
                    {"id": "CVE-2024-1234", "cvss": 9.1, "description": "OpenSSL critical vuln", "fix": "Upgrade to OpenSSL 3.0.14"},
                    {"id": "CVE-2023-9999", "cvss": 8.2, "description": "Kernel privilege escalation", "fix": "Apply kernel patch >= 5.15.120"},
                ],
                "nist_controls": ["RA-5", "SI-2"],
                "mitre_techniques": ["T1190", "T1059.004"],
                "remediation": {
                    "summary": "Rebuild the base image with patched OpenSSL and kernel updates.",
                    "steps": [
                        "Update base image to latest LTS with patched OpenSSL",
                        "Rebuild and redeploy containers consuming this image",
                        "Re-run container vulnerability scan to verify closure",
                    ],
                    "validation": ["Re-run the originating scan", "Check CI pipeline for zero critical vulns"],
                },
            },
        },
        {
            "id": uuid.uuid4(),
            "scanner_id": "git",
            "scan_type": "git",
            "target_ref": "github/demo/repo",
            "status": "completed",
            "started_at": now - timedelta(hours=2),
            "finished_at": now - timedelta(hours=2, minutes=10),
            "summary": {
                "findings": 0,
                "severity": "low",
                "type": "git",
                "repo": "github/demo/repo",
                "branch": "main",
                "last_commit": "abcdef123456",
                "soc2_criteria": ["CC8.1", "CC4.1"],
                "remediation": {"summary": "No action required", "steps": [], "validation": []},
            },
        },
        {
            "id": uuid.uuid4(),
            "scanner_id": "zap",
            "scan_type": "dast",
            "target_ref": "https://demo.app/login",
            "status": "completed",
            "started_at": now - timedelta(hours=3),
            "finished_at": now - timedelta(hours=2, minutes=55),
            "summary": {
                "findings": 3,
                "severity": "high",
                "type": "dast",
                "target_url": "https://demo.app/login",
                "evidence": "Reflected parameter accepted script payload",
                "target_kind": "app",
                "soc2_criteria": ["CC7.1", "CC9.1"],
                "externally_exposed": True,
                "cves": [
                    {"id": "CVE-2022-5555", "cvss": 7.5, "description": "Input validation flaw on login form", "fix": "Apply input validation patch"},
                ],
                "nist_controls": ["RA-5", "SI-10"],
                "mitre_techniques": ["T1190", "T1059.007"],
                "remediation": {
                    "summary": "Patch the login form and tighten input validation.",
                    "steps": [
                        "Enable server-side validation for login parameters",
                        "Deploy WAF rule to block injection attempts",
                        "Re-test with DAST to confirm issue is closed",
                    ],
                    "validation": ["Re-run DAST scan", "Verify no high findings remain"],
                },
            },
        },
        {
            "id": uuid.uuid4(),
            "scanner_id": "host",
            "scan_type": "host",
            "target_ref": "vm-demo-01",
            "status": "completed",
            "started_at": now - timedelta(hours=4, minutes=10),
            "finished_at": now - timedelta(hours=4, minutes=5),
            "summary": {
                "findings": 4,
                "severity": "high",
                "type": "host",
                "target_kind": "vm",
                "externally_exposed": False,
                "cves": [
                    {"id": "CVE-2024-2001", "cvss": 8.0, "description": "Kernel network stack vuln", "fix": "Update kernel to 5.15.120"},
                    {"id": "CVE-2023-7777", "cvss": 7.2, "description": "OpenSSH privilege issue", "fix": "Upgrade to OpenSSH 9.8p1"},
                ],
                "nist_controls": ["RA-5", "SI-2"],
                "mitre_techniques": ["T1068", "T1047"],
                "remediation": {
                    "summary": "Patch kernel and OpenSSH, then re-run host scan.",
                    "steps": [
                        "Apply latest distro kernel and reboot during a maintenance window",
                        "Upgrade OpenSSH to 9.8p1 and rotate keys if needed",
                        "Re-run host vulnerability scan to confirm closure",
                    ],
                    "validation": ["Host scan reports zero high findings", "Confirm OpenSSH version matches patched release"],
                },
            },
        },
        {
            "id": uuid.uuid4(),
            "scanner_id": "semgrep",
            "scan_type": "sast",
            "target_ref": "github.com/demo/api@main",
            "status": "completed",
            "started_at": now - timedelta(hours=1, minutes=50),
            "finished_at": now - timedelta(hours=1, minutes=45),
            "summary": {
                "findings": 4,
                "severity": "high",
                "type": "sast",
                "file_path": "src/auth/login.py",
                "line": 128,
                "rule_id": "sg.auth.injection",
                "cwe": "CWE-89",
                "nist_controls": ["RA-5", "CM-7"],
                "mitre_techniques": ["T1036"],
                "remediation": {
                    "summary": "Sanitize SQL inputs in login flow.",
                    "steps": [
                        "Use parameterized queries for DB access",
                        "Add input validation for username/password fields",
                        "Re-run SAST on the repo",
                    ],
                    "validation": ["SAST scan reports zero high findings for CWE-89"],
                },
            },
        },
        {
            "id": uuid.uuid4(),
            "scanner_id": "gitleaks",
            "scan_type": "secrets",
            "target_ref": "github.com/demo/api@main",
            "status": "completed",
            "started_at": now - timedelta(hours=2, minutes=20),
            "finished_at": now - timedelta(hours=2, minutes=15),
            "summary": {
                "findings": 1,
                "severity": "high",
                "type": "secrets",
                "file_path": "config/.env",
                "line": 12,
                "secret_type": "AWS Access Key",
                "secret_sample": "AKIA****",
                "nist_controls": ["CM-8"],
                "mitre_techniques": ["T1552"],
                "remediation": {
                    "summary": "Rotate exposed AWS key and purge from repo history.",
                    "steps": [
                        "Invalidate and rotate the AWS access key",
                        "Purge the secret from git history",
                        "Add pre-commit secret scanning",
                    ],
                    "validation": ["Secret scan reports zero findings", "New key validated in CI"],
                },
            },
        },
        {
            "id": uuid.uuid4(),
            "scanner_id": "checkov",
            "scan_type": "iac",
            "target_ref": "terraform/aws-prod",
            "status": "completed",
            "started_at": now - timedelta(hours=2, minutes=50),
            "finished_at": now - timedelta(hours=2, minutes=45),
            "summary": {
                "findings": 3,
                "severity": "medium",
                "type": "iac",
                "resource": "aws_s3_bucket.demo",
                "control_id": "CKV_AWS_20",
                "desired_state": "block public access, enable encryption",
                "nist_controls": ["CM-6"],
                "mitre_techniques": ["T1552"],
                "remediation": {
                    "summary": "Harden IaC for S3 bucket.",
                    "steps": [
                        "Set block_public_acls and block_public_policy to true",
                        "Enable default encryption (SSE)",
                        "Re-run IaC scan in CI",
                    ],
                    "validation": ["IaC scan returns zero medium/high findings"],
                },
            },
        },
    ]
    for s in scans:
        cur.execute(
            """
            INSERT INTO scans (id, tenant_id, scanner_id, scan_type, target_ref, status, created_at, updated_at, started_at, finished_at, summary)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                str(s["id"]),
                DEMO_TENANT,
                s["scanner_id"],
                s.get("scan_type", s["scanner_id"]),
                s["target_ref"],
                s["status"],
                now,
                now,
                s["started_at"],
                s["finished_at"],
                json.dumps(s["summary"]),
            ),
        )
        # Seed a default FixGroup for each scan so the UI has actionable units
        fg_type = "patch_group" if s["scanner_id"] in ("cloud", "trivy", "prowler") else "dependency_upgrade"
        fg_id = uuid.uuid4()
        has_ticket = s["scanner_id"] == "trivy"  # seed a ticket link on one row
        cur.execute(
            """
            INSERT INTO fix_groups (id, tenant_id, scan_id, type, description, priority, status, created_at, updated_at, fixed_in_target, ai_guidance, ticket_id, ticket_status)
            VALUES (%s, %s, %s, %s, %s, %s, 'open', %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                str(fg_id),
                DEMO_TENANT,
                str(s["id"]),
                fg_type,
                f"Default remediation for {s['target_ref']}",
                "P1" if s.get("summary", {}).get("severity") in ("critical", "high") else "P2",
                now,
                now,
                "base:2024.01" if fg_type == "dependency_upgrade" else None,
                json.dumps(
                    {
                        "summary": f"Apply fixes for {s['target_ref']}",
                        "steps": [
                            "Review findings in the scan report.",
                            "Apply vendor patch or upgrade dependency/base image.",
                            "Re-run the scan to verify remediation.",
                        ],
                        "validation": ["Re-run the originating scan to confirm findings are cleared."],
                    }
                ),
                "TKT-DEMO-1" if has_ticket else None,
                "open" if has_ticket else None,
            ),
        )
        # Seed asset/CVE linkage for richer UI
        cur.execute(
            """
            INSERT INTO fix_group_assets (fix_group_id, tenant_id, asset_ref, asset_type)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (fix_group_id, asset_ref) DO NOTHING
            """,
            (str(fg_id), DEMO_TENANT, s["target_ref"], s["scanner_id"]),
        )
        for cve in sample_cves[:2]:
            cur.execute(
                """
                INSERT INTO fix_group_cves (fix_group_id, tenant_id, cve_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (fix_group_id, cve_id) DO NOTHING
                """,
                (str(fg_id), DEMO_TENANT, cve),
            )
    cur.close()
    conn.close()


if __name__ == "__main__":
    seed()
