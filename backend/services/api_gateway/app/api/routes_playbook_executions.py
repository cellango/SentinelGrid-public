"""Playbook execution routes with traceability back to detections and playbooks."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID as UUIDType
import json
import sys
import os

# Allow importing shared models/helpers
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))

from sg_core.db import get_tenant_session
from sg_core.security import get_current_tenant
from sg_core.models import PlaybookExecution, Alert, Playbook

router = APIRouter()


def _tenant_uuid(tenant_id: str) -> UUIDType:
    """Validate and coerce tenant UUID."""
    try:
        return UUIDType(str(tenant_id))
    except Exception as exc:  # pragma: no cover - defensive guardrail
        raise HTTPException(status_code=400, detail=f"Invalid tenant_id: {tenant_id}") from exc


def _system_tenant_id() -> UUIDType:
    override = os.getenv("SYSTEM_TENANT_ID")
    if override:
        return UUIDType(str(override))
    return UUIDType("f0fbc168-b457-47c4-9f41-d4076051f963")


def _to_json(value):
    """Best-effort JSON loader for raw payloads that may be stored as strings."""
    if value is None:
        return {}
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}
    return {}


def _extract_detection_context(raw_payload: dict) -> tuple[str | None, str | None]:
    """Pull detection rule identifiers from alert payload if present."""
    if not isinstance(raw_payload, dict):
        return None, None

    sg_ctx = raw_payload.get("sg") or {}
    rule_ctx = raw_payload.get("rule") or {}

    detection_rule_id = (
        raw_payload.get("detection_rule_id")
        or sg_ctx.get("detection_rule_id")
        or sg_ctx.get("rule_id")
        or rule_ctx.get("id")
        or rule_ctx.get("rule_id")
        or raw_payload.get("rule_id")
    )
    detection_rule_version_id = (
        raw_payload.get("detection_rule_version_id")
        or sg_ctx.get("detection_rule_version_id")
        or sg_ctx.get("rule_version")
        or rule_ctx.get("version_id")
        or rule_ctx.get("version")
        or raw_payload.get("rule_version")
    )

    return (
        str(detection_rule_id) if detection_rule_id else None,
        str(detection_rule_version_id) if detection_rule_version_id else None,
    )


def _extract_detection_from_logs(logs) -> tuple[str | None, str | None]:
    """Fallback detection IDs from execution logs/result blobs."""
    candidates = []
    if isinstance(logs, dict):
        candidates.append(logs)
    elif isinstance(logs, list):
        candidates.extend([l for l in logs if isinstance(l, dict)])

    det_id = det_ver = None
    for entry in candidates:
        det_id = det_id or entry.get("detection_rule_id")
        det_ver = det_ver or entry.get("detection_rule_version_id")
        if det_id and det_ver:
            break
    return (
        str(det_id) if det_id else None,
        str(det_ver) if det_ver else None,
    )


def _normalize_logs(logs):
    """Return logs as a list for UI consumption."""
    if logs is None:
        return []
    if isinstance(logs, list):
        return logs
    return [logs]


def _serialize_execution(
    execution: PlaybookExecution,
    playbook: Playbook | None,
    alert: Alert | None,
) -> dict:
    raw_payload = _to_json(alert.raw_payload) if alert else {}
    detection_rule_id, detection_rule_version_id = _extract_detection_context(raw_payload)
    if not detection_rule_id or not detection_rule_version_id:
        det_id_logs, det_ver_logs = _extract_detection_from_logs(execution.logs)
        detection_rule_id = detection_rule_id or det_id_logs
        detection_rule_version_id = detection_rule_version_id or det_ver_logs

    return {
        "id": str(execution.id),
        "tenant_id": str(execution.tenant_id),
        "playbook_id": str(execution.playbook_id) if execution.playbook_id else None,
        "playbook_name": getattr(playbook, "name", None),
        "playbook_version_id": getattr(playbook, "version", None),
        "trigger_type": execution.target_type,
        "trigger_id": str(execution.target_id) if execution.target_id else None,
        "status": execution.status,
        "workflow_exec_id": execution.workflow_exec_id,
        "triggered_by": execution.triggered_by,
        "approval_status": execution.approval_status,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.finished_at.isoformat() if execution.finished_at else None,
        "result": execution.result_summary,
        "logs": _normalize_logs(execution.logs),
        "alert_id": str(execution.alert_id) if execution.alert_id else None,
        "detection_rule_id": detection_rule_id,
        "detection_rule_version_id": detection_rule_version_id,
        "created_at": execution.created_at.isoformat() if execution.created_at else None,
        "updated_at": execution.updated_at.isoformat() if execution.updated_at else None,
    }


@router.get("")
@router.get("/")
def list_executions(
    status: str | None = Query(default=None, description="Filter by status"),
    approval_status: str | None = Query(default=None, description="Filter by approval status"),
    alert_id: UUIDType | None = Query(default=None, description="Filter by alert"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """List playbook executions for the current tenant."""
    tenant_uuid = _tenant_uuid(tenant_id)
    query = db.query(PlaybookExecution).filter(PlaybookExecution.tenant_id == tenant_uuid)

    if status:
        query = query.filter(PlaybookExecution.status == status)
    if approval_status:
        query = query.filter(PlaybookExecution.approval_status == approval_status)
    if alert_id:
        query = query.filter(PlaybookExecution.alert_id == alert_id)

    executions = (
        query.order_by(PlaybookExecution.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    alert_ids = [exc.alert_id for exc in executions if exc.alert_id]
    playbook_ids = [exc.playbook_id for exc in executions if exc.playbook_id]

    alerts = (
        {
            a.id: a
            for a in db.query(Alert).filter(
                Alert.id.in_(alert_ids),
                Alert.tenant_id == tenant_uuid,
            ).all()
        }
        if alert_ids
        else {}
    )
    playbooks = (
        {
            p.id: p
            for p in db.query(Playbook).filter(
                Playbook.id.in_(playbook_ids),
                Playbook.tenant_id.in_([tenant_uuid, _system_tenant_id()]),
            ).all()
        }
        if playbook_ids
        else {}
    )

    return [
        _serialize_execution(exc, playbooks.get(exc.playbook_id), alerts.get(exc.alert_id))
        for exc in executions
    ]


@router.get("/{execution_id}")
@router.get("/{execution_id}/")
def get_execution(
    execution_id: UUIDType,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Get a single playbook execution with traceability context."""
    tenant_uuid = _tenant_uuid(tenant_id)
    execution = (
        db.query(PlaybookExecution)
        .filter(
            PlaybookExecution.id == execution_id,
            PlaybookExecution.tenant_id == tenant_uuid,
        )
        .first()
    )
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    playbook = (
        db.query(Playbook)
        .filter(
            Playbook.id == execution.playbook_id,
            Playbook.tenant_id.in_([tenant_uuid, _system_tenant_id()]),
        )
        .first()
    )
    alert = (
        db.query(Alert)
        .filter(Alert.id == execution.alert_id, Alert.tenant_id == tenant_uuid)
        .first()
        if execution.alert_id
        else None
    )

    return _serialize_execution(execution, playbook, alert)
