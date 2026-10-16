"""Internal ingestion routes for SentinelGrid AI Shield telemetry."""

from __future__ import annotations

import hashlib
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))

from sg_core.db import get_tenant_session
from sg_core.entity_model import build_story_context
from sg_core.models import Alert, Incident, Tenant
from app.api.routes_incidents import _serialize_incident
from app.api.routes_siem import _serialize_alert
from app.core.config import settings
from sg_core.service_security import verify_internal_service_token

router = APIRouter(prefix="/internal/ai-shield", tags=["internal-ai-shield"])
logger = logging.getLogger(__name__)


class AiShieldEventIngestRequest(BaseModel):
    event_id: Optional[str] = None
    org_id: Optional[str] = None
    ai_app_id: Optional[str] = None
    realm: Optional[str] = None
    user_id: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    has_pii: bool = False
    has_secrets: bool = False
    prompt_injection_suspected: bool = False
    policy_decision: Optional[str] = None
    violation_reason: Optional[str] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    prompt_preview: Optional[str] = None
    response_preview: Optional[str] = None
    created_at: Optional[datetime] = None


def verify_internal_token(
    authorization: Optional[str] = Header(None),
    x_internal_service_token: Optional[str] = Header(None, alias="X-Internal-Service-Token"),
) -> bool:
    verify_internal_service_token(
        settings.INTERNAL_SERVICE_TOKEN,
        authorization=authorization,
        x_internal_service_token=x_internal_service_token,
        missing_detail="Missing authorization header",
        invalid_detail="Invalid internal service token",
    )
    return True


def _normalize_timestamp(value: Optional[datetime]) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    return datetime.now(timezone.utc)


def _resolve_tenant_uuid(tenant_id: str, event: AiShieldEventIngestRequest) -> UUID:
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid X-Tenant-ID format") from exc

    if event.org_id:
        try:
            org_uuid = UUID(event.org_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid org_id format") from exc
        if org_uuid != tenant_uuid:
            raise HTTPException(
                status_code=403,
                detail="Tenant ID mismatch. You can only access your own tenant's data.",
            )

    return tenant_uuid


def _stable_external_id(event: AiShieldEventIngestRequest) -> str:
    if event.event_id:
        return event.event_id
    digest = hashlib.sha256(
        "|".join(
            [
                event.org_id or "",
                event.ai_app_id or "",
                event.user_id or "",
                event.provider or "",
                event.model or "",
                event.policy_decision or "",
                event.violation_reason or "",
                str(event.has_pii),
                str(event.has_secrets),
                str(event.prompt_injection_suspected),
                _normalize_timestamp(event.created_at).isoformat(),
            ]
        ).encode("utf-8")
    ).hexdigest()
    return f"ai-shield:{digest[:24]}"


def _classify_event(event: AiShieldEventIngestRequest) -> Optional[dict]:
    decision = (event.policy_decision or "").lower()
    provider = event.provider or "model provider"
    app_label = event.ai_app_id or "AI app"

    if event.has_secrets and decision != "blocked":
        return {
            "severity": "critical",
            "title": f"Secrets exposure through {app_label}",
            "description": (
                f"AI Shield detected likely secret material flowing to {provider} from {app_label}. "
                "This path should be treated as an active data-exposure incident."
            ),
            "finding_type": "sensitive_data_exposure",
            "detection_rule_id": "SG-AI-001",
            "playbook_id": "AI-DATA-LEAK",
            "tags": ["ai", "data-leak", "secrets", "external-llm"],
            "mitre_tactics": ["Collection", "Exfiltration"],
        }

    if event.has_pii and decision != "blocked":
        return {
            "severity": "high",
            "title": f"Sensitive AI data exposure in {app_label}",
            "description": (
                f"AI Shield detected likely sensitive data flowing to {provider} from {app_label}. "
                "Review the prompt path and decide whether containment or policy changes are required."
            ),
            "finding_type": "sensitive_data_exposure",
            "detection_rule_id": "SG-AI-001",
            "playbook_id": "AI-DATA-LEAK",
            "tags": ["ai", "data-leak", "pii", "external-llm"],
            "mitre_tactics": ["Collection", "Exfiltration"],
        }

    if event.prompt_injection_suspected:
        return {
            "severity": "high",
            "title": f"Prompt injection attempt detected in {app_label}",
            "description": (
                f"AI Shield flagged a suspected prompt injection or jailbreak attempt against {app_label}. "
                "Review the request path, user context, and downstream tool exposure."
            ),
            "finding_type": "prompt_injection",
            "detection_rule_id": "SG-AI-002",
            "playbook_id": "AI-PROMPT-INJECTION",
            "tags": ["ai", "prompt-injection", "jailbreak", "guardrail"],
            "mitre_tactics": ["Initial Access", "Execution"],
        }

    if decision == "blocked" or event.violation_reason:
        return {
            "severity": "medium",
            "title": f"AI policy violation in {app_label}",
            "description": (
                f"AI Shield blocked or flagged a policy violation for {app_label}. "
                "Review the offending path and decide whether the app configuration or owner workflow needs adjustment."
            ),
            "finding_type": "policy_violation",
            "detection_rule_id": "SG-AI-003",
            "playbook_id": "AI-POLICY-VIOLATION",
            "tags": ["ai", "policy-violation", "guardrail"],
            "mitre_tactics": ["Defense Evasion"],
        }

    return None


def _build_raw_payload(event: AiShieldEventIngestRequest, classification: dict, external_id: str, detected_at: datetime) -> dict:
    raw_payload = {
        "category": "ai",
        "summary": classification["description"],
        "source_label": "AI Shield",
        "ai_event_id": external_id,
        "ai": {
            "app_id": event.ai_app_id,
            "provider": event.provider,
            "model": event.model,
            "user_id": event.user_id,
            "policy_decision": event.policy_decision,
            "violation_reason": event.violation_reason,
            "tokens_in": event.tokens_in,
            "tokens_out": event.tokens_out,
            "prompt_injection_suspected": event.prompt_injection_suspected,
            "has_pii": event.has_pii,
            "has_secrets": event.has_secrets,
            "detected_at": detected_at.isoformat(),
            "realm": event.realm,
        },
        "finding": {
            "type": classification["finding_type"],
            "severity": classification["severity"],
            "title": classification["title"],
        },
        "recommended_playbook": classification["playbook_id"],
        "sg": {
            "category": "ai",
            "detection_rule_id": classification["detection_rule_id"],
            "playbook_id": classification["playbook_id"],
            "source_label": "AI Shield",
        },
        "labels": classification["tags"],
    }

    if event.prompt_preview:
        raw_payload["ai"]["prompt_preview"] = event.prompt_preview
    if event.response_preview:
        raw_payload["ai"]["response_preview"] = event.response_preview

    return raw_payload


def _create_incident_for_alert(
    db: Session,
    *,
    tenant_uuid: UUID,
    alert: Alert,
    classification: dict,
) -> Incident:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_uuid).first()
    incident_raw = dict(alert.raw_payload or {})
    incident_raw["description"] = alert.description
    incident_raw["asset_id"] = alert.asset_id
    incident_raw["user_identifier"] = alert.user_identifier
    incident_raw["incident_management_mode"] = (
        tenant.incident_management_mode if tenant and tenant.incident_management_mode else "saas_managed"
    )
    incident_raw["related_alert_ids"] = [str(alert.id)]
    audit_entries = list(incident_raw.get("audit") or [])
    audit_entries.append(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "text": "Incident created from AI Shield alert",
            "actor": "system",
        }
    )
    incident_raw["audit"] = audit_entries
    incident_raw.update(
        build_story_context(
            raw_payload=incident_raw,
            asset_id=alert.asset_id,
            user_identifier=alert.user_identifier,
            detection_rule_id=(incident_raw.get("sg") or {}).get("detection_rule_id") or incident_raw.get("detection_rule_id"),
            playbook_id=incident_raw.get("recommended_playbook") or (incident_raw.get("sg") or {}).get("playbook_id"),
            related_detections=[
                {
                    "id": str(alert.id),
                    "title": alert.title,
                    "severity": alert.raw_severity,
                }
            ],
            cve_ids=alert.cve_ids,
        )
    )

    incident = Incident(
        id=uuid4(),
        tenant_id=tenant_uuid,
        source="sentinelgrid_ai_shield",
        external_id=f"sg-ai-inc:{alert.external_id}",
        title=alert.title,
        status="open",
        severity=classification["severity"],
        raw_payload=incident_raw,
        mitre_tactics=classification.get("mitre_tactics"),
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    alert_payload = dict(alert.raw_payload or {})
    alert_payload["incident_id"] = str(incident.id)
    alert_payload["incidents"] = [
        {
            "id": str(incident.id),
            "title": incident.title,
            "severity": incident.severity,
        }
    ]
    alert.raw_payload = alert_payload
    db.add(alert)
    db.commit()
    db.refresh(alert)

    return incident


@router.post("/events")
def ingest_ai_shield_event(
    event: AiShieldEventIngestRequest,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    _verified: bool = Depends(verify_internal_token),
    db: Session = Depends(get_tenant_session),
):
    tenant_uuid = _resolve_tenant_uuid(tenant_id, event)

    classification = _classify_event(event)
    if not classification:
        return {
            "status": "skipped",
            "reason": "Telemetry did not meet the platform alert threshold",
        }

    detected_at = _normalize_timestamp(event.created_at)
    external_id = _stable_external_id(event)

    existing_alert = (
        db.query(Alert)
        .filter(
            Alert.tenant_id == tenant_uuid,
            Alert.source == "sentinelgrid_ai_shield",
            Alert.external_id == external_id,
        )
        .first()
    )
    if existing_alert:
        incident = None
        incident_id = (existing_alert.raw_payload or {}).get("incident_id")
        if incident_id:
            try:
                incident = (
                    db.query(Incident)
                    .filter(Incident.id == UUID(str(incident_id)), Incident.tenant_id == tenant_uuid)
                    .first()
                )
            except Exception:
                logger.warning("Existing AI Shield alert %s had an invalid incident reference", existing_alert.id)
        return {
            "status": "duplicate",
            "alert": _serialize_alert(existing_alert),
            "incident": _serialize_incident(incident) if incident else None,
        }

    raw_payload = _build_raw_payload(event, classification, external_id, detected_at)
    alert = Alert(
        id=uuid4(),
        tenant_id=tenant_uuid,
        source="sentinelgrid_ai_shield",
        external_id=external_id,
        title=classification["title"],
        description=classification["description"],
        raw_severity=classification["severity"],
        status="open",
        detection_time=detected_at,
        asset_id=event.ai_app_id,
        user_identifier=event.user_id,
        raw_payload=raw_payload,
        mitre_tactics=classification.get("mitre_tactics"),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    incident = None
    if classification["severity"] in {"high", "critical"}:
        incident = _create_incident_for_alert(
            db,
            tenant_uuid=tenant_uuid,
            alert=alert,
            classification=classification,
        )

    return {
        "status": "created",
        "alert": _serialize_alert(alert),
        "incident": _serialize_incident(incident) if incident else None,
    }
