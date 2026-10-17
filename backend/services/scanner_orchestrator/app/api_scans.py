import os
import json
import boto3
from botocore.client import Config as BotoConfig
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
import uuid
from datetime import datetime, timedelta
import httpx
from fastapi import Header
import logging
import json as pyjson

from sg_core.db import SessionLocal
from sg_core.dependencies import service_tenant_dependency
get_current_tenant = service_tenant_dependency('scanner_orchestrator')
from sg_core.cloud.registry import CLOUD_RESOURCE_BASELINE_SCANNER_ID, resolve_scanner_alias

S3_ENDPOINT = os.getenv("SCAN_ARTIFACT_S3_ENDPOINT")
S3_BUCKET = os.getenv("SCAN_ARTIFACT_S3_BUCKET")
S3_ACCESS_KEY = os.getenv("SCAN_ARTIFACT_S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("SCAN_ARTIFACT_S3_SECRET_KEY")
S3_REGION = os.getenv("SCAN_ARTIFACT_S3_REGION", "us-east-1")
S3_SECURE = os.getenv("SCAN_ARTIFACT_S3_SECURE", "true").lower() in ("1", "true", "yes")
MODEL_GATEWAY_URL = os.getenv("MODEL_GATEWAY_URL", "http://model_gateway:8000")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()
UPSTREAM_TLS_VERIFY = os.getenv("UPSTREAM_TLS_VERIFY", "false").lower() in ("1", "true", "yes")
LLM_REMEDIATION_ENABLED = os.getenv("LLM_REMEDIATION_ENABLED", "true").lower() in ("1", "true", "yes")
LLM_REMEDIATION_ENDPOINT = os.getenv(
    "LLM_REMEDIATION_ENDPOINT", f"{MODEL_GATEWAY_URL}/internal/llm/triage-alert"
)

if ENVIRONMENT == "production" and UPSTREAM_TLS_VERIFY is not True:
    raise RuntimeError("UPSTREAM_TLS_VERIFY must be enabled in production")

logger = logging.getLogger(__name__)

router = APIRouter()


def _resolve_scanner_payload(payload: dict) -> tuple[str, str | None, dict]:
    requested_scanner = payload.get("scanner_id")
    resolution = resolve_scanner_alias(requested_scanner)
    scanner_id = resolution["scanner"] or requested_scanner
    target_ref = payload.get("target_ref") or resolution.get("target")
    effective_payload = dict(payload or {})
    effective_payload["scanner_id"] = scanner_id
    effective_payload["requested_scanner_id"] = resolution["requested_scanner"]
    if resolution.get("alias"):
        effective_payload["scanner_alias"] = resolution["metadata"]
    if target_ref:
        effective_payload["target_ref"] = target_ref
    return scanner_id, target_ref, effective_payload

PRIORITY_MAP = {
    "critical": "P0",
    "high": "P1",
    "medium": "P2",
    "low": "P2",
    "info": "P2",
}
SEVERITY_ORDER = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
}


def _normalize_summary(summary: dict | str | None) -> dict:
    """Ensure summary is a dict."""
    if isinstance(summary, dict):
        return summary
    if isinstance(summary, str):
        try:
            return json.loads(summary)
        except Exception:
            return {}
    return summary or {}


def _signed_url(bucket: str, key: str, expires: int = 600):
    if not (S3_ENDPOINT and S3_BUCKET and S3_ACCESS_KEY and S3_SECRET_KEY):
        return None
    session = boto3.session.Session()
    client = session.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
        use_ssl=S3_SECURE,
        config=BotoConfig(s3={"addressing_style": "path"}),
    )
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires,
    )


def _deterministic_guidance(scanner_id: str | None, target_ref: str | None, summary: dict | None) -> dict:
    """Fallback deterministic guidance so UI stays actionable without LLM."""
    summary = _normalize_summary(summary)
    sev = (summary or {}).get("severity", "medium")
    target_label = target_ref or "the target"
    scanner = (scanner_id or "scanner").lower()

    # Base steps per scanner family
    if scanner in ("cloud", "prowler"):
        steps = [
            "Review the failing controls in the scan report for this account.",
            "Apply vendor patches or configuration hardening for the flagged resources.",
            "Re-run the scan to validate the controls now pass.",
        ]
        summary_txt = f"Apply cloud hardening/patches for {target_label} (priority: {sev})."
    elif scanner in ("trivy", "zap", "semgrep", "gitleaks", "checkov", "git"):
        steps = [
            "Identify the vulnerable package/component from the report.",
            "Upgrade to the vendor-fixed version or rebuild the base image with patched deps.",
            "Run the security scan again and basic smoke tests before release.",
        ]
        summary_txt = f"Upgrade dependencies or base image for {target_label} to clear vulnerabilities (priority: {sev})."
    else:
        steps = [
            "Validate the misconfiguration described in the findings.",
            "Apply the recommended secure configuration and restart affected services.",
            "Re-run the scan or functional checks to confirm the issue is resolved.",
        ]
        summary_txt = f"Apply configuration fixes for {target_label} (priority: {sev})."

    return {
        "summary": summary_txt,
        "steps": steps,
        "validation": [
            "Re-run the originating scan to confirm findings are cleared.",
            "If applicable, run smoke/health checks on the affected service after changes.",
        ],
        "severity": sev,
        "scanner": scanner_id,
        "target": target_ref,
    }

def _maybe_llm_guidance(tenant_id: str | None, scanner_id: str | None, target_ref: str | None, summary: dict | None) -> dict | None:
    """Try to fetch structured remediation guidance from model_gateway; return None on failure."""
    if not (LLM_REMEDIATION_ENABLED and MODEL_GATEWAY_URL):
        return None
    summary = _normalize_summary(summary)
    try:
        payload = {
            "scanner_id": scanner_id,
            "target_ref": target_ref,
            "severity": summary.get("severity"),
            "summary": summary,
            "tenant_id": tenant_id,
        }
        headers = {}
        if tenant_id:
            headers["X-Tenant-ID"] = str(tenant_id)
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(LLM_REMEDIATION_ENDPOINT, json=payload, headers=headers)
        if resp.status_code >= 300:
            logger.debug("LLM remediation call failed: status=%s body=%s", resp.status_code, resp.text)
            return None
        body = resp.json()
        rec = body.get("recommended_actions", {}) if isinstance(body, dict) else {}
        playbook_key = rec.get("playbook_key")
        steps_preview = rec.get("steps_preview") or []
        summary_txt = (
            f"Apply playbook {playbook_key} for {target_ref or 'target'} (severity {body.get('ai_severity','unknown')})"
            if playbook_key
            else body.get("rationale") or ""
        )
        if not summary_txt:
            summary_txt = f"Remediate findings on {target_ref or 'target'} (severity {summary.get('severity')})"
        steps = steps_preview or [
            "Review the flagged finding and confirm scope.",
            "Apply vendor fix or configuration change.",
            "Re-run the scan to validate remediation.",
        ]
        validation = [
            "Re-run the originating scan to confirm findings are cleared.",
            "Run smoke/health checks on the affected service after changes.",
        ]
        return {
            "summary": summary_txt,
            "steps": [str(s) for s in steps][:5],
            "validation": validation,
        }
    except Exception as exc:
        logger.debug("LLM remediation error: %s", exc)
        return None

def _build_ai_guidance(tenant_id: str | None, scanner_id: str | None, target_ref: str | None, summary: dict | None) -> dict:
    """
    Prefer LLM-backed remediation guidance; fall back to deterministic guidance.
    """
    base = _deterministic_guidance(scanner_id, target_ref, summary)
    llm = _maybe_llm_guidance(tenant_id, scanner_id, target_ref, summary)
    if llm:
        merged = {**base, **{k: v for k, v in llm.items() if v}}
        return merged
    return base


def _load_guidance(val):
    if isinstance(val, str):
        try:
            return pyjson.loads(val)
        except Exception:
            return val
    return val


def _ingest_fixgroup_embedding(
    tenant_id: str,
    fix_group_id: str,
    scanner_id: str | None,
    target_ref: str | None,
    description: str | None,
    guidance: dict | None,
    created_at: datetime,
):
    """
    Best-effort send FixGroup guidance to model_gateway embeddings endpoint for RAG/Q&A.
    Fails soft if model_gateway is unavailable.
    """
    def _do_post():
        try:
            text_parts = [
                f"Scanner: {scanner_id or 'unknown'}",
                f"Target: {target_ref or 'n/a'}",
                f"Description: {description or 'n/a'}",
            ]
            if guidance:
                if guidance.get("summary"):
                    text_parts.append(f"Summary: {guidance['summary']}")
                if guidance.get("steps"):
                    text_parts.append("Steps: " + " | ".join(guidance["steps"]))
                if guidance.get("validation"):
                    text_parts.append("Validation: " + " | ".join(guidance["validation"]))
            payload = {
                "summaries": [
                    {
                        "tenant_id": str(tenant_id),
                        "source": "fix_group",
                        "agent_id": scanner_id,
                        "host_id": target_ref,
                        "os_id": fix_group_id,
                        "timestamp": created_at.isoformat(),
                        "summary": " | ".join(text_parts),
                        "fields": {
                            "scanner_id": scanner_id,
                            "target_ref": target_ref,
                            "fix_group_id": fix_group_id,
                            "resource_type": "fix_group",
                        },
                    }
                ]
            }
            with httpx.Client(timeout=3.0) as client:
                client.post(f"{MODEL_GATEWAY_URL}/api/v1/embeddings/security-events", json=payload)
        except Exception:
            return

    # Fire-and-forget to avoid blocking scan flow
    import threading
    threading.Thread(target=_do_post, daemon=True).start()


def _ingest_security_embeddings(tenant_id: str, entries: list[dict]):
    """Fire-and-forget embedding ingest for arbitrary security summaries."""
    if not entries:
        return

    def _do_post():
        try:
            payload = {"summaries": entries}
            with httpx.Client(timeout=3.0) as client:
                client.post(f"{MODEL_GATEWAY_URL}/api/v1/embeddings/security-events", json=payload)
        except Exception:
            return

    import threading
    threading.Thread(target=_do_post, daemon=True).start()


def _ensure_fix_group(session, tenant_id: str, scan_id: str, scanner_id: str, target_ref: str | None, summary: dict | None):
    """
    Best-effort creation of a default FixGroup so the UI has actionable units.
    If a FixGroup already exists for the scan, do nothing.
    """
    existing = session.execute(
        text("SELECT 1 FROM fix_groups WHERE scan_id = :scan_id LIMIT 1"),
        {"scan_id": scan_id},
    ).first()
    if existing:
        return

    scanner_lower = (scanner_id or "").lower()
    if scanner_lower in ("cloud", "trivy", "prowler"):
        fg_type = "patch_group"
        description = f"Apply OS/vendor patches for {target_ref or 'target'}"
    elif scanner_lower in ("zap", "semgrep", "gitleaks", "checkov", "git"):
        fg_type = "dependency_upgrade"
        description = f"Upgrade dependencies/base image for {target_ref or 'service'}"
    else:
        fg_type = "config_change"
        description = f"Review and remediate findings for {target_ref or 'target'}"

    severity = (summary or {}).get("severity")
    priority = PRIORITY_MAP.get(str(severity).lower(), "P2")
    now = datetime.utcnow()
    if priority == "P0":
        sla_due = now + timedelta(hours=72)
    elif priority == "P1":
        sla_due = now + timedelta(days=7)
    else:
        sla_due = now + timedelta(days=30)

    ai_guidance = _build_ai_guidance(tenant_id, scanner_id, target_ref, summary)
    ai_guidance_json = json.dumps(ai_guidance) if ai_guidance else None
    fg_id = uuid.uuid4()
    session.execute(
        text(
            """
            INSERT INTO fix_groups (id, tenant_id, scan_id, type, description, fixed_in_target, priority, sla_due, status, created_at, updated_at, ai_guidance)
            VALUES (:id, :tenant_id, :scan_id, :type, :description, :fixed_in_target, :priority, :sla_due, 'open', :created_at, :updated_at, :ai_guidance)
            """
        ),
        {
            "id": str(fg_id),
            "tenant_id": tenant_id,
            "scan_id": scan_id,
            "type": fg_type,
            "description": description,
            "fixed_in_target": None,
            "priority": priority,
            "sla_due": sla_due,
            "created_at": now,
            "updated_at": now,
            "ai_guidance": ai_guidance_json,
        },
    )
    session.commit()
    _ingest_fixgroup_embedding(
        tenant_id=tenant_id,
        fix_group_id=str(fg_id),
        scanner_id=scanner_id,
        target_ref=target_ref,
        description=description,
        guidance=ai_guidance,
        created_at=now,
    )


def _priority_from_severity(severity: str | None) -> str:
    sev = (severity or "medium").lower()
    return PRIORITY_MAP.get(sev, "P2")


def _extract_cve(raw_payload: dict | None, title: str | None) -> str | None:
    if not raw_payload:
        raw_payload = {}
    candidates = [
        raw_payload.get("VulnerabilityID"),
        raw_payload.get("vulnerability_id"),
        raw_payload.get("cve_id"),
        raw_payload.get("cve"),
        title,
    ]
    for c in candidates:
        if not c or not isinstance(c, str):
            continue
        if c.upper().startswith("CVE-"):
            return c.upper()
    return None


def _extract_fixed_target(raw_payload: dict | None, remediation: str | None) -> str | None:
    if not raw_payload:
        raw_payload = {}
    for key in ("FixedVersion", "fixed_version", "FixedIn", "fixed_in"):
        val = raw_payload.get(key)
        if val:
            return str(val)
    if remediation and any(ch.isdigit() for ch in remediation):
        return remediation
    return None


def _derive_fix_groups_from_findings(session, tenant_id: str, scan_id: str, scanner_id: str | None, target_ref: str | None):
    """
    Build FixGroups from persisted findings for a scan. Groups by type + asset_ref + fixed target.
    Populates fix_group_assets and fix_group_cves for richer tickets and embeddings.
    """
    rows = (
        session.execute(
            text(
                """
                SELECT f.id, f.source_tool, f.severity, f.title, f.description, f.remediation, f.raw_payload,
                       f.asset_id, f.asset_type, a.external_id AS asset_external_id, a.name AS asset_name
                FROM findings f
                LEFT JOIN assets a ON a.id = f.asset_id
                WHERE f.scan_id = :scan_id AND f.tenant_id = :tenant_id
                """
            ),
            {"scan_id": scan_id, "tenant_id": tenant_id},
        )
        .mappings()
        .all()
    )
    if not rows:
        return

    groups: dict[str, dict] = {}

    summaries: list[dict] = []

    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}

    for r in rows:
        source = (r.get("source_tool") or "").lower()
        asset_ref = r.get("asset_external_id") or target_ref or str(r.get("asset_id"))
        severity = r.get("severity") or "medium"
        raw_payload = r.get("raw_payload") if isinstance(r.get("raw_payload"), dict) else {}
        cve_id = _extract_cve(raw_payload, r.get("title"))
        fixed_in = _extract_fixed_target(raw_payload, r.get("remediation"))

        if source in ("trivy", "zap", "semgrep", "gitleaks", "checkov", "git"):
            fg_type = "dependency_upgrade"
            desc = f"Upgrade or rebuild to address findings for {asset_ref}"
        elif source in ("prowler", "cloud"):
            fg_type = "patch_group"
            desc = f"Apply cloud/OS patches for {asset_ref}"
        else:
            fg_type = "config_change"
            desc = f"Remediate findings for {asset_ref}"

        key = "|".join([fg_type, asset_ref or "asset", fixed_in or ""])
        entry = groups.setdefault(
            key,
            {
                "type": fg_type,
                "description": desc,
                "fixed_in_target": fixed_in,
                "asset_refs": set(),
                "asset_types": set(),
                "cves": set(),
                "severities": set(),
            },
        )
        if asset_ref:
            entry["asset_refs"].add(asset_ref)
        if r.get("asset_type"):
            entry["asset_types"].add(r.get("asset_type"))
        if cve_id:
            entry["cves"].add(cve_id)
        if severity:
            entry["severities"].add(severity)

        # Prepare finding-level embedding summary for top items (later truncated)
        text_parts = [
            f"Scanner: {source or scanner_id or 'scanner'}",
            f"Severity: {severity}",
            f"Title: {r.get('title')}",
            f"Description: {r.get('description') or ''}",
        ]
        summaries.append(
            {
                "tenant_id": str(tenant_id),
                "source": "finding",
                "agent_id": scanner_id,
                "host_id": asset_ref,
                "os_id": str(r.get("id")),
                "timestamp": datetime.utcnow().isoformat(),
                "summary": " | ".join(text_parts),
                "fields": {
                    "resource_type": "finding",
                    "scan_id": scan_id,
                    "asset_ref": asset_ref,
                    "asset_type": r.get("asset_type"),
                    "severity": severity,
                    "cve_id": cve_id,
                    "title": r.get("title"),
                },
            }
        )

    for entry in groups.values():
        highest_sev = None
        if entry["severities"]:
            highest_sev = max(entry["severities"], key=lambda s: SEVERITY_ORDER.get((s or "").lower(), 0))
        priority = _priority_from_severity(highest_sev or "medium")
        now = datetime.utcnow()
        if priority == "P0":
            sla_due = now + timedelta(hours=72)
        elif priority == "P1":
            sla_due = now + timedelta(days=7)
        else:
            sla_due = now + timedelta(days=30)

        existing = session.execute(
            text(
                """
                SELECT id, status, ticket_id, ticket_status
                FROM fix_groups
                WHERE scan_id = :scan_id AND tenant_id = :tenant_id
                  AND type = :type
                  AND description = :description
                  AND COALESCE(fixed_in_target, '') = COALESCE(:fixed_in_target, '')
                LIMIT 1
                """
            ),
            {
                "scan_id": scan_id,
                "tenant_id": tenant_id,
                "type": entry["type"],
                "description": entry["description"],
                "fixed_in_target": entry["fixed_in_target"],
            },
        ).mappings().first()

        if existing:
            fg_id = existing["id"]
            session.execute(
                text(
                    """
                    UPDATE fix_groups
                    SET priority = :priority,
                        sla_due = :sla_due,
                        updated_at = :updated_at
                    WHERE id = :id AND tenant_id = :tenant_id
                    """
                ),
                {"priority": priority, "sla_due": sla_due, "updated_at": now, "id": fg_id, "tenant_id": tenant_id},
            )
        else:
            guidance = _build_ai_guidance(tenant_id, scanner_id, target_ref, {"severity": list(entry["severities"])[0] if entry["severities"] else "medium"})
            fg_id = str(uuid.uuid4())
            session.execute(
                text(
                    """
                    INSERT INTO fix_groups (id, tenant_id, scan_id, type, description, fixed_in_target, priority, sla_due, status, created_at, updated_at, ai_guidance)
                    VALUES (:id, :tenant_id, :scan_id, :type, :description, :fixed_in_target, :priority, :sla_due, 'open', :created_at, :updated_at, :ai_guidance)
                    """
                ),
                {
                    "id": fg_id,
                    "tenant_id": tenant_id,
                    "scan_id": scan_id,
                    "type": entry["type"],
                    "description": entry["description"],
                    "fixed_in_target": entry["fixed_in_target"],
                    "priority": priority,
                    "sla_due": sla_due,
                    "created_at": now,
                    "updated_at": now,
                    "ai_guidance": json.dumps(guidance),
                },
            )
            _ingest_fixgroup_embedding(
                tenant_id=tenant_id,
                fix_group_id=fg_id,
                scanner_id=scanner_id,
                target_ref=target_ref,
                description=entry["description"],
                guidance=_load_guidance(guidance),
                created_at=now,
            )

        # Refresh asset/CVE linkage for this FixGroup
        session.execute(
            text("DELETE FROM fix_group_assets WHERE fix_group_id = :fg_id AND tenant_id = :tenant_id"),
            {"fg_id": fg_id, "tenant_id": tenant_id},
        )
        session.execute(
            text("DELETE FROM fix_group_cves WHERE fix_group_id = :fg_id AND tenant_id = :tenant_id"),
            {"fg_id": fg_id, "tenant_id": tenant_id},
        )
        for asset_ref in entry["asset_refs"]:
            session.execute(
                text(
                    """
                    INSERT INTO fix_group_assets (fix_group_id, tenant_id, asset_ref, asset_type)
                    VALUES (:fg_id, :tenant_id, :asset_ref, :asset_type)
                    ON CONFLICT (fix_group_id, asset_ref) DO NOTHING
                    """
                ),
                {
                    "fg_id": fg_id,
                    "tenant_id": tenant_id,
                    "asset_ref": asset_ref,
                    "asset_type": ",".join(sorted(entry["asset_types"])) if entry["asset_types"] else None,
                },
            )
        for cve in entry["cves"]:
            session.execute(
                text(
                    """
                    INSERT INTO fix_group_cves (fix_group_id, tenant_id, cve_id)
                    VALUES (:fg_id, :tenant_id, :cve_id)
                    ON CONFLICT (fix_group_id, cve_id) DO NOTHING
                    """
                ),
                {"fg_id": fg_id, "tenant_id": tenant_id, "cve_id": cve},
            )

    session.commit()

    # Ingest a small slice of findings + a scan summary into embeddings for Q&A
    summaries_sorted = sorted(
        summaries,
        key=lambda s: severity_rank.get((s.get("fields") or {}).get("severity", "info"), 0),
        reverse=True,
    )
    top_summaries = summaries_sorted[:20]  # cap to avoid spam
    scan_summary_text = f"Scan {scan_id} results for {target_ref or 'target'} with {len(rows)} findings"
    top_summaries.append(
        {
            "tenant_id": str(tenant_id),
            "source": "scan_summary",
            "agent_id": scanner_id,
            "host_id": target_ref,
            "os_id": scan_id,
            "timestamp": datetime.utcnow().isoformat(),
            "summary": scan_summary_text,
            "fields": {
                "resource_type": "scan_summary",
                "scan_id": scan_id,
                "target_ref": target_ref,
                "severity": highest_sev or "medium" if groups else "info",
            },
        }
    )
    _ingest_security_embeddings(tenant_id, top_summaries)


@router.post("/scans")
async def enqueue_scan(
    payload: dict,
    current_tenant=Depends(get_current_tenant),
):
    """
    Enqueue a scan for the current tenant. Stores a scan row with status=queued.
    Expected payload fields: scanner_id (required), target_ref (optional), summary/raw payload optional.
    """
    requested_scanner_id = payload.get("scanner_id")
    scanner_id, target_ref, effective_payload = _resolve_scanner_payload(payload)
    summary = _normalize_summary(payload.get("summary"))
    if not requested_scanner_id:
        raise HTTPException(status_code=400, detail="scanner_id is required")

    session = SessionLocal()
    try:
        scan_id = uuid.uuid4()
        now = datetime.utcnow()
        initial_status = "queued"
        session.execute(
            text(
                """
                INSERT INTO scans (id, tenant_id, scanner_id, target_ref, status, created_at, updated_at, summary)
                VALUES (:id, :tenant_id, :scanner_id, :target_ref, :status, :created_at, :updated_at, :summary)
                """
            ),
            {
                "id": str(scan_id),
                "tenant_id": str(current_tenant),
                "scanner_id": scanner_id,
                "target_ref": target_ref,
                "status": initial_status,
                "created_at": now,
                "updated_at": now,
                "summary": json.dumps(
                    {
                        **summary,
                        "requested_scanner_id": requested_scanner_id,
                    }
                ),
            },
        )
        if scanner_id == CLOUD_RESOURCE_BASELINE_SCANNER_ID:
            from sg_core.jobs import handlers

            session.execute(
                text("UPDATE scans SET status='running', started_at=:ts, updated_at=:ts WHERE id=:id"),
                {"id": str(scan_id), "ts": now},
            )
            result = handlers.handle_cloud_resource_baseline_scan(
                session,
                {
                    "id": str(scan_id),
                    "tenant_id": str(current_tenant),
                    "job_type": "cloud_resource_baseline_scan",
                    "payload": effective_payload,
                },
                scan_id=str(scan_id),
                scanner_id=scanner_id,
            )
            finished = datetime.utcnow()
            session.execute(
                text(
                    """
                    UPDATE scans
                    SET status='completed', finished_at=:finished, updated_at=:finished, summary=CAST(:summary AS jsonb)
                    WHERE id=:id
                    """
                ),
                {"id": str(scan_id), "finished": finished, "summary": json.dumps(result)},
            )
            session.commit()
            return {"scan_id": str(scan_id), "status": "completed", "summary": result}
        session.commit()
        return {"scan_id": str(scan_id), "status": "queued"}
    finally:
        session.close()


@router.get("/scans/status")
async def list_scan_status(
    limit: int = 50,
    offset: int = 0,
    scanner: str | None = Query(None, description="Comma-separated scanner_ids (e.g., trivy,zap)"),
    status: str | None = Query(None, description="Comma-separated statuses (queued,running,completed,failed)"),
    q: str | None = Query(None, description="Search within target_ref"),
    with_ticket: bool | None = Query(None, description="Only scans that have tickets via fix_groups"),
    with_fix: bool | None = Query(None, description="Only scans that have fix_groups"),
    current_tenant=Depends(get_current_tenant),
):
    """List recent scans for the current tenant with status and artifact URL (presigned if available)."""
    session = SessionLocal()
    try:
        try:
            conditions = ["tenant_id = :tenant_id"]
            params: dict[str, object] = {"tenant_id": str(current_tenant), "limit": limit, "offset": offset}

            # Scanner filter (comma-separated)
            scanner_ids = [s.strip() for s in scanner.split(",") if s.strip()] if scanner else []
            if scanner_ids:
                scanner_placeholders = ", ".join([f":scanner_{i}" for i in range(len(scanner_ids))])
                conditions.append(f"scanner_id IN ({scanner_placeholders})")
                for i, s in enumerate(scanner_ids):
                    params[f"scanner_{i}"] = s

            # Status filter (comma-separated)
            statuses = [s.strip() for s in status.split(",") if s.strip()] if status else []
            if statuses:
                status_placeholders = ", ".join([f":status_{i}" for i in range(len(statuses))])
                conditions.append(f"status IN ({status_placeholders})")
                for i, s in enumerate(statuses):
                    params[f"status_{i}"] = s

            # Search by target_ref
            if q:
                conditions.append("target_ref ILIKE :search_term")
                params["search_term"] = f"%{q}%"

            if with_ticket:
                conditions.append(
                    "EXISTS (SELECT 1 FROM fix_groups fg WHERE fg.scan_id = scans.id AND fg.tenant_id = :tenant_id AND fg.ticket_id IS NOT NULL)"
                )
            if with_fix:
                conditions.append("EXISTS (SELECT 1 FROM fix_groups fg2 WHERE fg2.scan_id = scans.id AND fg2.tenant_id = :tenant_id)")

            where_clause = " AND ".join(conditions)

            rows = session.execute(
                text(
                    f"""
                    SELECT id, tenant_id, scanner_id, scan_type, target_ref, status, created_at, updated_at,
                           started_at, finished_at, summary, raw_artifact_url
                    FROM scans
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                params,
            ).mappings().all()

            # If no scans are present (fresh DB / missing seeds), return a small baked-in sample
            if not rows:
                now = datetime.utcnow()
                rows = [
                    {
                        "id": "11111111-1111-1111-1111-111111111111",
                        "tenant_id": str(current_tenant),
                        "scanner_id": "cloud",
                        "scan_type": None,
                        "target_ref": "aws-demo",
                        "status": "completed",
                        "created_at": now,
                        "updated_at": now,
                        "started_at": now - timedelta(minutes=30),
                        "finished_at": now - timedelta(minutes=25),
                        "summary": {"findings": 2, "severity": "high"},
                        "raw_artifact_url": None,
                    },
                    {
                        "id": "22222222-2222-2222-2222-222222222222",
                        "tenant_id": str(current_tenant),
                        "scanner_id": "trivy",
                        "scan_type": None,
                        "target_ref": "device-demo-01",
                        "status": "completed",
                        "created_at": now,
                        "updated_at": now,
                        "started_at": now - timedelta(minutes=75),
                        "finished_at": now - timedelta(minutes=70),
                        "summary": {"findings": 5, "severity": "critical", "type": "vulnerability", "target_kind": "device"},
                        "raw_artifact_url": None,
                    },
                    {
                        "id": "33333333-3333-3333-3333-333333333333",
                        "tenant_id": str(current_tenant),
                        "scanner_id": "git",
                        "scan_type": None,
                        "target_ref": "github/demo/repo",
                        "status": "completed",
                        "created_at": now,
                        "updated_at": now,
                        "started_at": now - timedelta(hours=2),
                        "finished_at": now - timedelta(minutes=110),
                        "summary": {"findings": 0, "severity": "low"},
                        "raw_artifact_url": None,
                    },
                    {
                        "id": "44444444-4444-4444-4444-444444444444",
                        "tenant_id": str(current_tenant),
                        "scanner_id": "zap",
                        "scan_type": None,
                        "target_ref": "https://demo.app/login",
                        "status": "completed",
                        "created_at": now,
                        "updated_at": now,
                        "started_at": now - timedelta(hours=3),
                        "finished_at": now - timedelta(minutes=175),
                        "summary": {"findings": 3, "severity": "medium", "type": "vulnerability", "target_kind": "app"},
                        "raw_artifact_url": None,
                    },
                ]
        except Exception as exc:
            # If the scans table isn't present yet (fresh env), fail soft with empty list
            import logging
            logging.getLogger(__name__).warning("scans table unavailable, returning empty list: %s", exc)
            return []

        results = []
        for r in rows:
            artifact_signed = None
            if r["raw_artifact_url"]:
                key_part = r["raw_artifact_url"].split(f"s3://{S3_BUCKET}/")[-1]
                artifact_signed = _signed_url(S3_BUCKET, key_part)
            # Fetch a single ticket linkage if present (first fix_group with ticket)
            ticket_row = session.execute(
                text(
                    """
                    SELECT ticket_id, ticket_status
                    FROM fix_groups
                    WHERE scan_id = :scan_id AND tenant_id = :tenant_id AND ticket_id IS NOT NULL
                    LIMIT 1
                    """
                ),
                {"scan_id": r["id"], "tenant_id": str(current_tenant)},
            ).first()
            results.append(
                {
                    "id": str(r["id"]),
                    "scanner_id": r["scanner_id"],
                    "scan_type": r["scan_type"] or r["scanner_id"],
                    "target_ref": r["target_ref"],
                    "status": r["status"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                    "started_at": r["started_at"],
                    "finished_at": r["finished_at"],
                    "summary": r["summary"],
                    "artifact_url": artifact_signed,
                    "has_fix_groups": bool(
                        session.execute(
                            text("SELECT 1 FROM fix_groups WHERE scan_id = :scan_id LIMIT 1"),
                            {"scan_id": r["id"]},
                        ).first()
                    ),
                    "ticket_id": ticket_row[0] if ticket_row else None,
                    "ticket_status": ticket_row[1] if ticket_row else None,
                }
            )
        return results
    finally:
        session.close()


@router.get("/scans/{scan_id}")
async def get_scan(scan_id: str, current_tenant=Depends(get_current_tenant)):
    session = SessionLocal()
    try:
        row = (
            session.execute(
                text(
                    """
                    SELECT id, tenant_id, scanner_id, scan_type, target_ref, status, created_at, updated_at, started_at, finished_at, summary, raw_artifact_url
                    FROM scans
                    WHERE id = :id AND tenant_id = :tenant_id
                    """
                ),
                {"id": scan_id, "tenant_id": str(current_tenant)},
            )
            .mappings()
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail="Scan not found")
        artifact_signed = None
        if row["raw_artifact_url"]:
            try:
                key_part = row["raw_artifact_url"].split(f"s3://{S3_BUCKET}/")[-1]
                artifact_signed = _signed_url(S3_BUCKET, key_part)
            except Exception:
                artifact_signed = None
        scan_payload = {
            "id": str(row["id"]),
            "scanner_id": row["scanner_id"],
            "scan_type": row["scan_type"] or row["scanner_id"],
            "target_ref": row["target_ref"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "summary": row["summary"],
            "artifact_url": artifact_signed,
            "raw_artifact_url": row["raw_artifact_url"],
        }
        # Attach FixGroups inline for convenience
        fg_rows = (
            session.execute(
                text(
                    """
                    SELECT id, type, description, fixed_in_target, priority, sla_due, status, owning_team_id, ai_guidance, created_at, updated_at,
                           ticket_id, ticket_status
                    FROM fix_groups
                    WHERE scan_id = :scan_id AND tenant_id = :tenant_id
                    ORDER BY created_at DESC
                    """
                ),
                {"scan_id": scan_id, "tenant_id": str(current_tenant)},
            )
            .mappings()
            .all()
        )
        fix_groups = []
        for r in fg_rows:
            guidance = r.get("ai_guidance")
            guidance = _load_guidance(guidance)
            if not guidance:
                # Backfill best-effort guidance for older rows without ai_guidance
                guidance = _build_ai_guidance(str(current_tenant), row["scanner_id"], row["target_ref"], row["summary"])
            fix_groups.append(
                {
                    "id": str(r["id"]),
                    "type": r["type"],
                    "description": r["description"],
                    "fixed_in_target": r["fixed_in_target"],
                    "priority": r["priority"],
                    "sla_due": r["sla_due"],
                    "status": r["status"],
                    "owning_team_id": r["owning_team_id"],
                    "ai_guidance": guidance,
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                    "ticket_id": r.get("ticket_id"),
                    "ticket_status": r.get("ticket_status"),
                }
            )
        scan_payload["fix_groups"] = fix_groups
        return scan_payload
    finally:
        session.close()


@router.get("/scans/{scan_id}/fix-groups")
async def list_fix_groups(scan_id: str, current_tenant=Depends(get_current_tenant)):
    """List FixGroups for a scan (tenant-scoped)."""
    session = SessionLocal()
    try:
        rows = (
            session.execute(
                text(
                    """
                    SELECT id, type, description, fixed_in_target, priority, sla_due, status, owning_team_id, ai_guidance, created_at, updated_at
                    FROM fix_groups
                    WHERE scan_id = :scan_id AND tenant_id = :tenant_id
                    ORDER BY created_at DESC
                    """
                ),
                {"scan_id": scan_id, "tenant_id": str(current_tenant)},
            )
            .mappings()
            .all()
        )
        result = []
        for r in rows:
            result.append(
                {
                    "id": str(r["id"]),
                    "type": r["type"],
                    "description": r["description"],
                    "fixed_in_target": r["fixed_in_target"],
                    "priority": r["priority"],
                    "sla_due": r["sla_due"],
                    "status": r["status"],
                    "owning_team_id": r["owning_team_id"],
                    "ai_guidance": r["ai_guidance"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                }
            )
        return result
    finally:
        session.close()


@router.post("/scans/{scan_id}/tickets")
async def create_ticket_for_scan(
    scan_id: str,
    payload: dict,
    current_tenant=Depends(get_current_tenant),
    authorization: str | None = Header(None, alias="Authorization"),
    tenant_id_query: str | None = Query(None, alias="tenant_id"),
):
    """
    Create a ticket by forwarding to ticketing_service. Requires fix_group_id.
    """
    if not payload.get("fix_group_id"):
        raise HTTPException(status_code=400, detail="fix_group_id is required")
    ticketing_url = os.getenv("TICKETING_SERVICE_URL", "http://ticketing_service:8000")
    # Fetch FixGroup context for sensible defaults and SLA/due date
    session = SessionLocal()
    try:
        fg_row = (
            session.execute(
                text(
                    """
                    SELECT fg.id, fg.type, fg.description, fg.fixed_in_target, fg.priority, fg.sla_due, fg.ai_guidance,
                           fg.ticket_id, fg.ticket_status,
                           s.target_ref, s.scanner_id
                    FROM fix_groups fg
                    JOIN scans s ON s.id = fg.scan_id
                    WHERE fg.id = :fg_id AND fg.scan_id = :scan_id AND fg.tenant_id = :tenant_id
                    """
                ),
                {"fg_id": payload.get("fix_group_id"), "scan_id": scan_id, "tenant_id": str(current_tenant)},
            )
            .mappings()
            .first()
        )
        if not fg_row:
            raise HTTPException(status_code=404, detail="FixGroup not found for scan/tenant")
        if fg_row.get("ticket_id"):
            # Enforce one-ticket-per-FixGroup: return existing linkage
            return {
                "id": fg_row.get("ticket_id"),
                "status": fg_row.get("ticket_status") or "open",
                "fix_group_id": payload.get("fix_group_id"),
                "existing": True,
            }
        guidance = _load_guidance(fg_row.get("ai_guidance"))
        cves = (
            session.execute(
                text(
                    """
                    SELECT cve_id FROM fix_group_cves
                    WHERE fix_group_id = :fg_id
                    """
                ),
                {"fg_id": payload.get("fix_group_id")},
            )
            .scalars()
            .all()
        )
        assets = (
            session.execute(
                text(
                    """
                    SELECT asset_ref, asset_type
                    FROM fix_group_assets
                    WHERE fix_group_id = :fg_id AND tenant_id = :tenant_id
                    """
                ),
                {"fg_id": payload.get("fix_group_id"), "tenant_id": str(current_tenant)},
            )
            .mappings()
            .all()
        )
    finally:
        try:
            session.close()
        except Exception:
            pass

    headers = {
        "Content-Type": "application/json",
        "X-Tenant-ID": str(current_tenant),
    }
    if authorization:
        headers["Authorization"] = authorization
    # Accept tenant from query if provided (ticketing may require it)
    tenant_for_ticket = tenant_id_query or str(current_tenant)

    def _build_description():
        if payload.get("description"):
            return payload["description"]
        parts = []
        parts.append(f"FixGroup: {fg_row['description']}")
        if fg_row.get("target_ref"):
            parts.append(f"Target: {fg_row['target_ref']}")
        if fg_row.get("scanner_id"):
            parts.append(f"Scanner: {fg_row['scanner_id']}")
        if fg_row.get("fixed_in_target"):
            parts.append(f"Fixed in: {fg_row['fixed_in_target']}")
        if assets:
            parts.append(
                "Assets: "
                + ", ".join(
                    f"{a['asset_ref']}" + (f" ({a['asset_type']})" if a.get("asset_type") else "")
                    for a in assets
                )
            )
        if guidance:
            if guidance.get("summary"):
                parts.append(f"AI summary: {guidance['summary']}")
            if guidance.get("steps"):
                parts.append("Steps: " + " | ".join(guidance["steps"]))
            if guidance.get("validation"):
                parts.append("Validation: " + " | ".join(guidance["validation"]))
        if cves:
            parts.append("CVEs: " + ", ".join(cves[:20]))
        return "\n".join(parts)

    title_default = f"[{fg_row.get('priority') or 'P2'}] {fg_row.get('description')}"
    payload_out = {
        "title": payload.get("title") or title_default,
        "description": _build_description(),
        "priority": payload.get("priority") or fg_row.get("priority"),
        "category": "vulnerability",
        "cve_ids": payload.get("cve_ids") or cves or [],
        "assets": [a["asset_ref"] for a in assets] if assets else [],
        "fix_group_id": payload.get("fix_group_id"),
        "scan_id": scan_id,
        "tenant_id": str(current_tenant),
        "due_date": fg_row.get("sla_due"),
    }
    async with httpx.AsyncClient(timeout=20.0, verify=UPSTREAM_TLS_VERIFY) as client:
        resp = await client.post(
            f"{ticketing_url}/api/v1/tickets",
            json=payload_out,
            headers=headers,
            params={"tenant_id": tenant_for_ticket},
        )
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail)
    ticket = resp.json()

    # Best-effort: persist ticket linkage on the FixGroup
    try:
        session = SessionLocal()
        session.execute(
            text(
                """
                UPDATE fix_groups
                SET ticket_id = :ticket_id, ticket_status = :ticket_status, updated_at = now()
                WHERE id = :fix_group_id AND tenant_id = :tenant_id
                """
            ),
            {
                "ticket_id": ticket.get("id") or ticket.get("external_id"),
                "ticket_status": ticket.get("status"),
                "fix_group_id": payload.get("fix_group_id"),
                "tenant_id": str(current_tenant),
            },
        )
        session.commit()
    except Exception:
        # Fail soft; ticket still created
        pass
    finally:
        try:
            session.close()
        except Exception:
            pass
    return ticket


@router.post("/scans/{scan_id}/fix-groups/{fix_group_id}/verify")
async def start_fix_group_verification(
    scan_id: str,
    fix_group_id: str,
    payload: dict | None = None,
    current_tenant=Depends(get_current_tenant),
):
    """
    Begin a verification loop for a FixGroup:
    - Marks the FixGroup as pending_verify.
    - Creates a follow-up scan row (status=queued) using the same scanner/target.
    """
    session = SessionLocal()
    try:
        row = (
            session.execute(
                text(
                    """
                    SELECT fg.id as fg_id, fg.status as fg_status, s.scanner_id, s.target_ref
                    FROM fix_groups fg
                    JOIN scans s ON s.id = fg.scan_id
                    WHERE fg.id = :fg_id AND fg.scan_id = :scan_id AND fg.tenant_id = :tenant_id
                    """
                ),
                {"fg_id": fix_group_id, "scan_id": scan_id, "tenant_id": str(current_tenant)},
            )
            .mappings()
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail="FixGroup not found for scan/tenant")

        verification_scan_id = uuid.uuid4()
        now = datetime.utcnow()
        session.execute(
            text(
                """
                INSERT INTO scans (id, tenant_id, scanner_id, target_ref, status, created_at, updated_at, summary)
                VALUES (:id, :tenant_id, :scanner_id, :target_ref, 'queued', :created_at, :updated_at, :summary)
                """
            ),
            {
                "id": str(verification_scan_id),
                "tenant_id": str(current_tenant),
                "scanner_id": row["scanner_id"],
                "target_ref": row["target_ref"],
                "created_at": now,
                "updated_at": now,
                "summary": json.dumps(
                    {
                        "reason": "verification",
                        "fix_group_id": fix_group_id,
                        "parent_scan_id": scan_id,
                    }
                ),
            },
        )
        session.execute(
            text(
                """
                UPDATE fix_groups
                SET status = 'pending_verify', updated_at = now()
                WHERE id = :fg_id AND tenant_id = :tenant_id
                """
            ),
            {"fg_id": fix_group_id, "tenant_id": str(current_tenant)},
        )
        session.commit()
        return {
            "fix_group_id": fix_group_id,
            "status": "pending_verify",
            "verification_scan_id": str(verification_scan_id),
        }
    finally:
        session.close()
