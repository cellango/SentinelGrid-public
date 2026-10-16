"""Incident routes."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
import logging
import sys
import os

from fastapi import APIRouter, Depends, HTTPException, Query
import httpx
from pydantic import BaseModel
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))

from sg_core.db import get_tenant_session
from sg_core.security import get_current_tenant
from sg_core.models import Incident
from sg_core.entity_model import build_story_context, build_story_summary
from sg_agent_runtime.soc_case_runtime_client import SOCCaseRuntimeClient
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class IncidentUpdateRequest(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    phase: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None
    description: Optional[str] = None
    comment: Optional[str] = None
    timeline_event: Optional[str] = None


class SOCCaseFeedbackRequest(BaseModel):
    recommendation_id: str
    feedback_type: str
    actor_id: str
    actor_role: str = "HUMAN_OWNER"
    accepted: bool
    action_id: Optional[str] = None
    playbook_id: Optional[str] = None
    playbook_key: Optional[str] = None
    playbook_name: Optional[str] = None
    notes: Optional[str] = None


def _incident_payload(incident: Incident) -> dict:
    raw_payload = getattr(incident, "raw_payload", {}) or {}
    if isinstance(raw_payload, dict):
        return dict(raw_payload)
    return {}


def _serialize_related_detections(raw_payload: dict) -> list[dict]:
    related_alert_ids = raw_payload.get("related_alert_ids") or []
    if related_alert_ids:
        return [{"id": str(alert_id)} for alert_id in related_alert_ids]

    detections = raw_payload.get("detections") or []
    if isinstance(detections, list):
        return [
            {
                "id": str(detection.get("id") if isinstance(detection, dict) else detection),
                "title": detection.get("title") if isinstance(detection, dict) else None,
                "severity": detection.get("severity") if isinstance(detection, dict) else None,
            }
            for detection in detections
        ]
    return []


def _serialize_incident_timeline(raw_payload: dict) -> list[dict]:
    entries = list(raw_payload.get("audit") or []) + list(raw_payload.get("comments") or [])
    timeline: list[dict] = []
    for entry in entries:
        timeline.append(
            {
                "ts": entry.get("ts") or entry.get("at") or entry.get("timestamp"),
                "text": entry.get("text") or entry.get("comment") or entry.get("title") or "Event",
                "actor": entry.get("actor") or entry.get("user") or "system",
                "metadata": entry.get("metadata"),
            }
        )
    return timeline


def _append_incident_audit_entry(raw_payload: dict, text: str, actor: str = "operator", metadata: Optional[dict] = None) -> dict:
    next_payload = dict(raw_payload or {})
    audit_entries = list(next_payload.get("audit") or [])
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "text": text,
        "actor": actor,
    }
    if metadata:
        entry["metadata"] = metadata
    audit_entries.append(entry)
    next_payload["audit"] = audit_entries[-50:]
    return next_payload


def _sync_linked_ticket_update(ticket_id: UUID, tenant_id: str, ticket_updates: dict) -> dict:
    url = f"{settings.TICKETING_SERVICE_URL.rstrip('/')}/api/v1/tickets/{ticket_id}"
    headers = {
        "Content-Type": "application/json",
        "X-Tenant-ID": tenant_id,
        "X-SG-SOC-Refresh-Skip": "true",
    }
    with httpx.Client(timeout=15.0) as client:
        response = client.put(url, headers=headers, json=ticket_updates)
        response.raise_for_status()
        if response.content:
            return response.json()
    return {}


def _add_linked_ticket_comment(ticket_id: UUID, tenant_id: str, comment: str) -> dict:
    url = f"{settings.TICKETING_SERVICE_URL.rstrip('/')}/api/v1/tickets/{ticket_id}/comments"
    headers = {
        "Content-Type": "application/json",
        "X-Tenant-ID": tenant_id,
        "X-SG-SOC-Refresh-Skip": "true",
    }
    with httpx.Client(timeout=15.0) as client:
        response = client.post(url, headers=headers, json={"comment": comment})
        response.raise_for_status()
        if response.content:
            return response.json()
    return {}


def _fetch_soc_case_state(incident_id: UUID, tenant_id: str) -> dict:
    url = f"{settings.AGENT_RUNTIME_URL.rstrip('/')}/agents/cases/{incident_id}"
    headers = {
        "Authorization": f"Bearer {settings.INTERNAL_SERVICE_TOKEN}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=15.0) as client:
        response = client.get(
            url,
            headers=headers,
            params={"tenant_id": tenant_id},
        )
        response.raise_for_status()
        if response.content:
            return response.json()
    return {}


def _submit_soc_case_refresh(
    incident: Incident,
    tenant_id: str,
    changed_fields: list[str],
    reason: str,
) -> dict | None:
    if not changed_fields:
        return None
    trigger_type = (
        "incident_status_changed"
        if any(field in {"status", "severity", "phase"} for field in changed_fields)
        else "analyst_action_recorded"
    )
    client = SOCCaseRuntimeClient(
        runtime_url=getattr(settings, "AGENT_RUNTIME_URL", None),
        internal_token=settings.INTERNAL_SERVICE_TOKEN,
    )
    return client.submit_case_refresh_sync(
        tenant_id=tenant_id,
        incident_id=str(incident.id),
        trigger_type=trigger_type,
        source_kind="incident_update",
        source_event_id=str(incident.id),
        changed_fields=changed_fields,
        reason=reason,
        payload={
            "status": incident.status,
            "severity": incident.severity,
            "phase": incident.phase,
        },
    )


def _submit_soc_case_feedback(
    incident_id: UUID,
    tenant_id: str,
    payload: SOCCaseFeedbackRequest,
) -> dict | None:
    client = SOCCaseRuntimeClient(
        runtime_url=getattr(settings, "AGENT_RUNTIME_URL", None),
        internal_token=settings.INTERNAL_SERVICE_TOKEN,
    )
    return client.record_feedback_sync(
        incident_id=str(incident_id),
        tenant_id=tenant_id,
        recommendation_id=payload.recommendation_id,
        feedback_type=payload.feedback_type,
        actor_id=payload.actor_id,
        actor_role=payload.actor_role,
        accepted=payload.accepted,
        action_id=payload.action_id,
        playbook_id=payload.playbook_id,
        playbook_key=payload.playbook_key,
        playbook_name=payload.playbook_name,
        notes=payload.notes,
    )


def _serialize_incident(incident: Incident) -> dict:
    """Convert Incident ORM object to API-friendly dict with framework metadata."""
    raw_payload = _incident_payload(incident)
    related_detections = _serialize_related_detections(raw_payload)
    story_context = build_story_context(
        raw_payload=raw_payload,
        asset_id=raw_payload.get("asset_id"),
        user_identifier=raw_payload.get("user_identifier"),
        detection_rule_id=raw_payload.get("detection_rule_id"),
        detection_rule_version_id=raw_payload.get("detection_rule_version_id"),
        playbook_id=raw_payload.get("playbook_id") or (raw_payload.get("sg") or {}).get("playbook_id"),
        playbook_version_id=raw_payload.get("playbook_version_id"),
        related_detections=related_detections,
        ticket_id=str(incident.ticket_id) if incident.ticket_id else None,
        external_ticket_id=incident.external_ticket_id,
        external_ticket_provider=incident.external_ticket_provider,
        cve_ids=getattr(incident, "cve_ids", None),
    )
    story_summary = build_story_summary(story_context=story_context)
    return {
        "id": str(incident.id),
        "tenant_id": str(incident.tenant_id),
        "source": incident.source,
        "external_id": incident.external_id,
        "title": incident.title,
        "status": incident.status,
        "severity": incident.severity,
        "description": incident.description,
        "phase": incident.phase,
        "assignee": incident.assigned_to,
        "assigned_to": incident.assigned_to,
        "sla": raw_payload.get("sla") or raw_payload.get("sla_minutes"),
        "due_date": incident.due_date,
        "incident_management_mode": raw_payload.get("incident_management_mode"),
        "ticket_id": str(incident.ticket_id) if incident.ticket_id else None,
        "external_ticket_id": incident.external_ticket_id,
        "external_ticket_provider": incident.external_ticket_provider,
        "related_detections": related_detections,
        "entities": story_context["entities"],
        "evidence": story_context["evidence"],
        "story_domains": story_context["story_domains"],
        "story_summary": story_summary,
        "timeline": _serialize_incident_timeline(raw_payload),
        "detection_rule_id": raw_payload.get("detection_rule_id"),
        "detection_rule_version_id": raw_payload.get("detection_rule_version_id"),
        "playbook_version_id": raw_payload.get("playbook_version_id"),
        "nist_controls": getattr(incident, "nist_controls", None),
        "mitre_tactics": getattr(incident, "mitre_tactics", None),
        "mitre_techniques": getattr(incident, "mitre_techniques", None),
        "cve_ids": getattr(incident, "cve_ids", None),
        "exploit_indicators": getattr(incident, "exploit_indicators", None),
        "raw_payload": raw_payload or None,
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
        "updated_at": incident.updated_at.isoformat() if incident.updated_at else None,
    }


@router.get("/", response_model=dict)
def list_incidents(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """List incidents."""
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        return {"items": [], "total": 0, "limit": limit, "offset": offset}

    query = db.query(Incident).filter(Incident.tenant_id == tenant_uuid)
    if status:
        query = query.filter(Incident.status == status)
    if severity:
        query = query.filter(Incident.severity == severity)

    total = query.count()
    incidents = query.order_by(Incident.created_at.desc()).offset(offset).limit(limit).all()
    items = [_serialize_incident(inc) for inc in incidents]

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/open-with-actions")
def get_open_incidents_with_actions(
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Get open incidents with AI-proposed fixes and quick actions."""
    # Fail closed to an empty list if incident enrichment is unavailable.
    # Do not backfill demo incidents into operator-facing surfaces.
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        tenant_uuid = None

    if tenant_uuid:
        try:
            open_items = db.query(Incident).filter(
                Incident.tenant_id == tenant_uuid,
                Incident.status.in_(["open", "in_progress", "investigating"])
            ).order_by(Incident.created_at.desc()).limit(10).all()

            items = []
            for inc in open_items:
                raw_payload = inc.raw_payload or {}
                related_detections = _serialize_related_detections(raw_payload)
                story_context = build_story_context(
                    raw_payload=raw_payload,
                    asset_id=raw_payload.get("asset_id"),
                    user_identifier=raw_payload.get("user_identifier"),
                    detection_rule_id=raw_payload.get("detection_rule_id"),
                    detection_rule_version_id=raw_payload.get("detection_rule_version_id"),
                    playbook_id=raw_payload.get("playbook_id") or (raw_payload.get("sg") or {}).get("playbook_id"),
                    playbook_version_id=raw_payload.get("playbook_version_id"),
                    related_detections=related_detections,
                    ticket_id=str(inc.ticket_id) if inc.ticket_id else None,
                    external_ticket_id=inc.external_ticket_id,
                    external_ticket_provider=inc.external_ticket_provider,
                    cve_ids=getattr(inc, "cve_ids", None),
                )
                story_summary = build_story_summary(story_context=story_context)
                items.append({
                    "id": str(inc.id),
                    "title": inc.title,
                    "severity": inc.severity,
                    "risk_level": inc.severity,  # placeholder until risk calc available
                    "affected_count": max(story_summary["entity_count"], 1),
                    "description": story_summary["detail"],
                    "ai_summary": raw_payload.get("ai_summary") if hasattr(inc, "raw_payload") else None,
                    "ai_proposed_fixes": raw_payload.get("ai_proposed_fixes") if hasattr(inc, "raw_payload") else [],
                    "quick_actions": [],
                    "created_at": inc.created_at.isoformat() if inc.created_at else None,
                    "story_domains": story_context["story_domains"],
                    "story_summary": story_summary,
                    "entities": story_context["entities"],
                    "evidence": story_context["evidence"],
                })
            return {"items": items}
        except Exception as e:
            logger.warning("Unable to build open incident summary for tenant %s: %s", tenant_id, e)
    return {"items": []}


@router.get("/{incident_id}", response_model=dict)
def get_incident(
    incident_id: UUID,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Get incident details."""
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID")

    incident = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.tenant_id == tenant_uuid
    ).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    return _serialize_incident(incident)


@router.get("/{incident_id}/soc-case", response_model=dict)
def get_incident_soc_case(
    incident_id: UUID,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Get the latest SOC AI case state for an incident."""
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID")

    incident = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.tenant_id == tenant_uuid,
    ).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    try:
        return _fetch_soc_case_state(incident_id, tenant_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(status_code=404, detail="SOC case state not found") from exc
        raise HTTPException(status_code=502, detail="Failed to fetch SOC case state") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Failed to fetch SOC case state") from exc


@router.post("/{incident_id}/soc-case/feedback", response_model=dict)
def submit_incident_soc_case_feedback(
    incident_id: UUID,
    payload: SOCCaseFeedbackRequest,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Persist analyst feedback for the latest SOC case recommendation."""
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID")

    incident = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.tenant_id == tenant_uuid,
    ).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    try:
        response = _submit_soc_case_feedback(incident_id, tenant_id, payload)
        return response or {"incident_id": str(incident_id), "tenant_id": tenant_id}
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(status_code=404, detail="SOC case state not found") from exc
        raise HTTPException(status_code=502, detail="Failed to record SOC case feedback") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Failed to record SOC case feedback") from exc


@router.patch("/{incident_id}", response_model=dict)
def update_incident(
    incident_id: UUID,
    payload: IncidentUpdateRequest,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Update incident workflow fields and append audit entries."""
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID")

    incident = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.tenant_id == tenant_uuid,
    ).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _serialize_incident(incident)

    current_payload = _incident_payload(incident)
    previous_status = incident.status
    previous_phase = incident.phase
    previous_assigned_to = incident.assigned_to
    previous_due_date = incident.due_date
    previous_description = incident.description
    previous_severity = incident.severity
    ticket_updates: dict = {}
    linked_ticket_comment: Optional[str] = None

    if "status" in updates:
        next_status = (updates["status"] or "").strip()
        if not next_status:
            raise HTTPException(status_code=422, detail="status cannot be empty")
        if next_status != incident.status:
            incident.status = next_status
            ticket_updates["status"] = next_status
            current_payload = _append_incident_audit_entry(
                current_payload,
                f"Status changed to {next_status}",
                metadata={
                    "previous_status": previous_status,
                    "status": next_status,
                },
            )

    if "severity" in updates:
        next_severity = (updates["severity"] or "").strip() or None
        if next_severity != incident.severity:
            incident.severity = next_severity
            ticket_updates["severity"] = next_severity
            current_payload = _append_incident_audit_entry(
                current_payload,
                f"Severity changed to {next_severity or 'unset'}",
                metadata={
                    "previous_severity": previous_severity,
                    "severity": next_severity,
                },
            )

    if "phase" in updates:
        next_phase = updates["phase"] or None
        if next_phase:
            current_payload["phase"] = next_phase
        else:
            current_payload.pop("phase", None)
        if next_phase != previous_phase:
            current_payload = _append_incident_audit_entry(
                current_payload,
                f"Phase changed to {next_phase or 'unset'}",
                metadata={
                    "previous_phase": previous_phase,
                    "phase": next_phase,
                },
            )

    if "assigned_to" in updates:
        next_assigned_to = (updates["assigned_to"] or "").strip() or None
        if next_assigned_to:
            current_payload["assigned_to"] = next_assigned_to
            current_payload["assignee"] = next_assigned_to
        else:
            current_payload.pop("assigned_to", None)
            current_payload.pop("assignee", None)
        if next_assigned_to != previous_assigned_to:
            ticket_updates["assigned_to"] = next_assigned_to or ""
            current_payload = _append_incident_audit_entry(
                current_payload,
                f"Assigned to {next_assigned_to or 'unassigned'}",
                metadata={
                    "previous_assigned_to": previous_assigned_to,
                    "assigned_to": next_assigned_to,
                },
            )

    if "due_date" in updates:
        next_due_date = (updates["due_date"] or "").strip() or None
        if next_due_date:
            current_payload["due_date"] = next_due_date
            current_payload["sla_due_at"] = next_due_date
        else:
            current_payload.pop("due_date", None)
            current_payload.pop("sla_due_at", None)
        if next_due_date != previous_due_date:
            ticket_updates["due_date"] = next_due_date or ""
            current_payload = _append_incident_audit_entry(
                current_payload,
                f"SLA target set to {next_due_date or 'unset'}",
                metadata={
                    "previous_due_date": previous_due_date,
                    "due_date": next_due_date,
                },
            )

    if "description" in updates:
        next_description = (updates["description"] or "").strip() or None
        if next_description:
            current_payload["description"] = next_description
        else:
            current_payload.pop("description", None)
        if next_description != previous_description:
            ticket_updates["description"] = next_description or ""
            current_payload = _append_incident_audit_entry(
                current_payload,
                "Description updated",
                metadata={
                    "previous_description": previous_description,
                    "description": next_description,
                },
            )

    if "comment" in updates:
        next_comment = (updates["comment"] or "").strip()
        if not next_comment:
            raise HTTPException(status_code=422, detail="comment cannot be empty")
        current_comments = list(current_payload.get("comments") or [])
        current_comments.append(
            {
                "text": next_comment,
                "at": datetime.now(timezone.utc).isoformat(),
                "actor": "operator",
            }
        )
        current_payload["comments"] = current_comments[-50:]
        linked_ticket_comment = next_comment

    if "timeline_event" in updates:
        next_timeline_event = (updates["timeline_event"] or "").strip()
        if not next_timeline_event:
            raise HTTPException(status_code=422, detail="timeline_event cannot be empty")
        current_payload = _append_incident_audit_entry(
            current_payload,
            next_timeline_event,
            actor="operator",
            metadata={"source": "soc_ai_timeline_draft"},
        )

    incident.raw_payload = current_payload
    db.add(incident)
    db.commit()
    db.refresh(incident)

    if incident.ticket_id and ticket_updates:
        try:
            _sync_linked_ticket_update(incident.ticket_id, tenant_id, ticket_updates)
        except Exception as exc:
            logger.warning("Failed syncing linked ticket %s for incident %s: %s", incident.ticket_id, incident.id, exc)
            current_payload = _append_incident_audit_entry(
                _incident_payload(incident),
                "Linked ticket update failed",
                metadata={
                    "ticket_id": str(incident.ticket_id),
                    "updated_fields": sorted(ticket_updates.keys()),
                    "error": str(exc),
                },
            )
            incident.raw_payload = current_payload
            db.add(incident)
            db.commit()
            db.refresh(incident)

    if incident.ticket_id and linked_ticket_comment:
        try:
            _add_linked_ticket_comment(incident.ticket_id, tenant_id, linked_ticket_comment)
        except Exception as exc:
            logger.warning("Failed posting linked ticket comment %s for incident %s: %s", incident.ticket_id, incident.id, exc)
            current_payload = _append_incident_audit_entry(
                _incident_payload(incident),
                "Linked ticket comment failed",
                metadata={
                    "ticket_id": str(incident.ticket_id),
                    "error": str(exc),
                },
            )
            incident.raw_payload = current_payload
            db.add(incident)
            db.commit()
            db.refresh(incident)

    try:
        _submit_soc_case_refresh(
            incident,
            tenant_id,
            sorted(updates.keys()),
            "Incident fields were updated by an operator workflow.",
        )
    except Exception as exc:
        logger.warning("Failed submitting SOC case refresh for incident %s: %s", incident.id, exc)

    return _serialize_incident(incident)
