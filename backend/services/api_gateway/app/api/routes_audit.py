"""Audit feed routes for alerts and incidents."""

from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import datetime
from typing import List, Optional
import sys
import os
import httpx
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))
from sg_core.security import get_current_tenant
from sg_core.db import get_tenant_session
from sg_core.models import Alert, Incident, Ticket
try:
    from sg_core.models import ticket_alerts
except Exception:
    ticket_alerts = None
from sqlalchemy.orm import Session
from sqlalchemy import select, text
from app.core.config import settings

router = APIRouter()


def _build_proxy_headers(auth_header: Optional[str], tenant_id: str) -> dict:
    return {
        "Authorization": auth_header,
        "X-Tenant-ID": tenant_id,
    }


def _enforce_same_tenant_override(requested_tenant_id: Optional[str], current_tenant_id: str) -> None:
    if requested_tenant_id and str(requested_tenant_id) != str(current_tenant_id):
        raise HTTPException(
            status_code=403,
            detail="Tenant ID mismatch. You can only access your own tenant's data.",
        )


def _coalesce_timeline(raw_payload) -> List[dict]:
    if not raw_payload:
        return []
    entries = list(raw_payload.get("audit") or []) + list(raw_payload.get("comments") or [])
    out = []
    for e in entries:
        out.append({
            "ts": e.get("ts") or e.get("at") or e.get("timestamp") or datetime.utcnow().isoformat(),
            "text": e.get("text") or e.get("comment") or "Comment",
            "actor": e.get("actor") or e.get("user") or "system",
        })
    return out


def _fetch_platform_audit(db: Session, tenant_id: str, resource_type: str, resource_id: str, limit: int = 100) -> List[dict]:
    """Fetch audit entries from platform_audit_logs."""
    rows = db.execute(
        text(
            """
            SELECT action, action_category, actor_user_id, actor_email, success, error_message,
                   metadata, timestamp
            FROM platform_audit_logs
            WHERE tenant_id = :tenant_id
              AND resource_type = :resource_type
              AND resource_id = :resource_id
            ORDER BY timestamp DESC
            LIMIT :limit
            """
        ),
        {"tenant_id": str(tenant_id), "resource_type": resource_type, "resource_id": resource_id, "limit": limit},
    ).fetchall()
    events = []
    for r in rows:
        meta = r.metadata if hasattr(r, "metadata") else None
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {"raw": meta}
        workflow_event = meta.get("workflow_event") if isinstance(meta, dict) else None
        events.append(
            {
                "ts": getattr(r, "timestamp", None) or datetime.utcnow().isoformat(),
                "text": (
                    workflow_event.get("title")
                    if isinstance(workflow_event, dict) and workflow_event.get("title")
                    else r.action
                ),
                "actor": r.actor_user_id or "system",
                "category": r.action_category,
                "success": r.success,
                "error": r.error_message,
                "metadata": meta,
            }
        )
    return events


@router.get("/audit/alerts/{alert_id}")
def get_alert_audit(
    alert_id: str,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Return audit feed for an alert (pull from raw_payload and linked ticket timelines)."""
    events: List[dict] = []
    alert = db.query(Alert).filter(Alert.id == alert_id, Alert.tenant_id == tenant_id).first()
    if alert and getattr(alert, "raw_payload", None):
        events.extend(_coalesce_timeline(alert.raw_payload))

    # Add audit entries for suppression/dedup
    if alert and alert.raw_payload:
        if alert.raw_payload.get("dedup_key"):
            events.append({
                "ts": alert.raw_payload.get("dedup_at") or alert.created_at.isoformat(),
                "text": f"Deduplicated with key {alert.raw_payload.get('dedup_key')}",
                "actor": "system"
            })
        if alert.raw_payload.get("suppression_reason"):
            events.append({
                "ts": alert.created_at.isoformat(),
                "text": f"Suppressed: {alert.raw_payload.get('suppression_reason')}",
                "actor": "system"
            })

    # Pull timelines from linked tickets (if any)
    if ticket_alerts is not None:
        stmt = select(Ticket).join(ticket_alerts, Ticket.id == ticket_alerts.c.ticket_id).where(
            ticket_alerts.c.alert_id == alert_id,
            Ticket.tenant_id == tenant_id,
        )
        for ticket in db.execute(stmt).scalars().all():
            timeline_data = getattr(ticket, "timeline_data", None) or {}
            ticket_events = timeline_data.get("events") if isinstance(timeline_data, dict) else timeline_data
            if ticket_events:
                for t in ticket_events or []:
                    events.append({
                        "ts": t.get("ts") or t.get("timestamp") or datetime.utcnow().isoformat(),
                        "text": t.get("text") or t.get("title") or "Ticket update",
                        "actor": t.get("actor") or "system",
                    })

    events = sorted(events, key=lambda e: e.get("ts", ""))
    # Append platform audit logs
    events.extend(_fetch_platform_audit(db, tenant_id, "alert", alert_id))
    events = sorted(events, key=lambda e: e.get("ts", ""))
    return {"items": events, "total": len(events)}


@router.get("/audit/incidents/{incident_id}")
def get_incident_audit(
    incident_id: str,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Return audit feed for an incident (raw_payload audit)."""
    events: List[dict] = []
    incident = db.query(Incident).filter(Incident.id == incident_id, Incident.tenant_id == tenant_id).first()
    if incident and getattr(incident, "raw_payload", None):
        events.extend(_coalesce_timeline(incident.raw_payload))
        if incident.raw_payload.get("suppression_reason"):
            events.append({
                "ts": incident.created_at.isoformat(),
                "text": f"Suppressed: {incident.raw_payload.get('suppression_reason')}",
                "actor": "system"
            })
        linked_ticket = getattr(incident, "ticket", None)
        if linked_ticket and getattr(linked_ticket, "timeline_data", None):
            timeline_data = linked_ticket.timeline_data or {}
            ticket_events = timeline_data.get("events") if isinstance(timeline_data, dict) else timeline_data
            for t in ticket_events or []:
                events.append({
                    "ts": t.get("ts") or t.get("timestamp") or datetime.utcnow().isoformat(),
                    "text": t.get("text") or t.get("title") or "Linked ticket update",
                    "actor": t.get("actor") or "system",
                })

    # Append platform audit logs
    events.extend(_fetch_platform_audit(db, tenant_id, "incident", incident_id))
    events = sorted(events, key=lambda e: e.get("ts", ""))
    return {"items": events, "total": len(events)}


@router.get("/audit/ai-activity")
async def get_ai_activity(
    request: Request,
    tenant_id: str = Depends(get_current_tenant),
):
    """Proxy AI activity feed from audit_service."""
    auth_header = request.headers.get("Authorization")
    url = f"{settings.AUDIT_SERVICE_URL}/api/v1/audit/ai-activity"
    params = dict(request.query_params)
    _enforce_same_tenant_override(params.get("tenant_id"), tenant_id)
    params["tenant_id"] = tenant_id
    headers = _build_proxy_headers(auth_header, tenant_id)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers, params=params)
        if resp.status_code == 404:
            return {"items": [], "total": 0}
        resp.raise_for_status()
        return resp.json()


@router.post("/audit/ai-activity", status_code=201)
async def post_ai_activity(
    request: Request,
    tenant_id: str = Depends(get_current_tenant),
):
    """Proxy AI activity writes to audit_service."""
    auth_header = request.headers.get("Authorization")
    url = f"{settings.AUDIT_SERVICE_URL}/api/v1/audit/ai-activity"
    body = await request.json()
    if isinstance(body, dict):
        _enforce_same_tenant_override(body.get("tenant_id"), tenant_id)
        body = dict(body)
        body["tenant_id"] = tenant_id
    headers = _build_proxy_headers(auth_header, tenant_id)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        return resp.json()
