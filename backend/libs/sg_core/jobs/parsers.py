"""
Parsers for tool outputs -> normalized findings list.
"""

from typing import List, Dict, Any
from datetime import datetime, timezone


def parse_prowler_json(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings = []
    items = raw.get("findings") or raw.get("Findings") or []
    # Also allow a single record in raw
    if isinstance(raw, dict) and not items and any(k in raw for k in ("Status", "Severity", "Title")):
        items = [raw]
    for item in items:
        status = (item.get("Status") or "").upper()
        if status == "PASS":
            continue
        severity = (item.get("Severity") or "low").lower()
        findings.append(
            {
                "source_tool": "prowler",
                "severity": severity,
                "category": "cloud_misconfiguration",
                "title": item.get("Title") or item.get("ControlId") or "Prowler finding",
                "description": item.get("Description") or "",
                "remediation": item.get("Remediation") or item.get("Recommendation") or "",
                "detected_at": item.get("UpdatedAt") or item.get("CreatedAt") or datetime.now(timezone.utc).isoformat(),
                "asset_type": "cloud_account",
                "external_id": item.get("AccountId") or item.get("ResourceId"),
                "raw_payload": item,
            }
        )
    return findings


def parse_trivy_json(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings = []
    for result in raw.get("Results", []):
        target = result.get("Target")
        vulns = result.get("Vulnerabilities") or []
        for v in vulns:
            findings.append(
                {
                    "source_tool": "trivy",
                    "severity": (v.get("Severity") or "low").lower(),
                    "category": "vuln",
                    "title": v.get("VulnerabilityID") or v.get("Title") or "Trivy finding",
                    "description": v.get("Description") or "",
                    "remediation": v.get("FixedVersion") or "",
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                    "asset_type": "image",
                    "external_id": target,
                    "raw_payload": v,
                }
            )
    return findings


def parse_gitleaks_json(raw: Any) -> List[Dict[str, Any]]:
    findings = []
    if not raw:
        return findings
    items = raw if isinstance(raw, list) else raw.get("results") if isinstance(raw, dict) else []
    for item in items:
        findings.append(
            {
                "source_tool": "gitleaks",
                "severity": "high",
                "category": "secret_exposure",
                "title": item.get("Description") or "Secret found",
                "description": f"Rule: {item.get('RuleID')} File: {item.get('File')}",
                "remediation": "Rotate the secret and remove from repo.",
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "asset_type": "source_repo",
                "external_id": item.get("File"),
                "raw_payload": item,
            }
        )
    return findings


def parse_checkov_json(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings = []
    failed = raw.get("results", {}).get("failed_checks", [])
    for fc in failed:
        findings.append(
            {
                "source_tool": "checkov",
                "severity": (fc.get("severity") or "low").lower(),
                "category": "iac_misconfiguration",
                "title": fc.get("check_id") or "Checkov finding",
                "description": fc.get("check_name") or "",
                "remediation": fc.get("guideline") or "",
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "asset_type": "source_repo",
                "external_id": fc.get("file_path"),
                "raw_payload": fc,
            }
        )
    return findings


def parse_zap_json(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings = []
    sites = raw.get("site") or []
    for site in sites:
        alerts = site.get("alerts") or []
        for a in alerts:
            risk = a.get("riskdesc", "").lower()
            severity = "info"
            if "high" in risk:
                severity = "high"
            elif "medium" in risk:
                severity = "medium"
            elif "low" in risk:
                severity = "low"
            uri = None
            instances = a.get("instances") or []
            if instances:
                uri = instances[0].get("uri")
            findings.append(
                {
                    "source_tool": "zap",
                    "severity": severity,
                    "category": "dast",
                    "title": a.get("name") or "ZAP finding",
                    "description": a.get("desc") or "",
                    "remediation": a.get("solution") or "",
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                    "asset_type": "app_url",
                    "external_id": uri,
                    "raw_payload": a,
                }
            )
    return findings


def parse_semgrep_json(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings = []
    results = raw.get("results") or []
    for r in results:
        extra = r.get("extra") or {}
        sev = (extra.get("severity") or "info").lower()
        findings.append(
            {
                "source_tool": "semgrep",
                "severity": sev,
                "category": "sast",
                "title": r.get("check_id") or "Semgrep finding",
                "description": extra.get("message") or "",
                "remediation": "",
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "asset_type": "source_repo",
                "external_id": r.get("path"),
                "raw_payload": r,
            }
        )
    return findings
