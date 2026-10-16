"""Playbook routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID, UUID as UUIDType
from pydantic import BaseModel
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))

from sg_core.db import get_tenant_session
from sg_core.security import get_current_tenant
from sg_core.models import Playbook, PlaybookExecution

router = APIRouter()
clone_router = APIRouter()
CLONE_PREFIX = "/clone"


class PlaybookCloneRequest(BaseModel):
    name: str | None = None
    key: str | None = None
    description: str | None = None

class PlaybookUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    workflow: dict | None = None


class PlaybookExecuteRequest(BaseModel):
    trigger_type: str | None = None  # alert | incident | manual | scheduled
    trigger_id: UUID | None = None
    alert_id: UUID | None = None
    parameters: dict | None = None
    detection_rule_id: str | None = None
    detection_rule_version_id: str | None = None
    triggered_by: str | None = None


def _coerce_uuid(value) -> UUID | None:
    if not value:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except Exception:
        return None


def _execution_submission_summary(pb: Playbook) -> tuple[str, str]:
    if pb.requires_approval:
        return (
            "pending",
            "Execution request recorded and awaiting approval before automation can start.",
        )
    return (
        "approved",
        "Execution request recorded and pending SOAR worker handoff.",
    )


def _system_tenant_id() -> str:
    """
    System tenant for built-ins. Prefer env override so it tracks the real sg_admin id.
    """
    override = os.getenv("SYSTEM_TENANT_ID")
    if override:
        return UUIDType(override)
    return UUIDType("f0fbc168-b457-47c4-9f41-d4076051f963")

def _starter_workflow() -> dict:
    """Local starter graph for the editor when no stored workflow is available."""
    return {
        "nodes": [
            {"id": "t1", "type": "trigger", "position": {"x": 0, "y": 0}, "data": {"label": "Alert Trigger"}},
            {"id": "a1", "type": "action", "position": {"x": 220, "y": 0}, "data": {"label": "Initial Response"}},
        ],
        "edges": [
            {"id": "e1", "source": "t1", "target": "a1", "type": "smoothstep"}
        ],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    }

def _workflow_state(pb: Playbook) -> tuple[dict | None, str, str | None]:
    """Describe whether a playbook has a real stored graph or needs a truthful editor notice."""
    workflow = getattr(pb, "workflow", None)
    if workflow and isinstance(workflow, dict) and workflow.get("nodes"):
        return workflow, "stored", None

    workflow_ref = getattr(pb, "workflow_ref", None)
    if workflow_ref:
        return (
            None,
            "external_reference",
            "This playbook is backed by an external workflow reference. The launch editor does not expose the live automation graph.",
        )

    return (
        None,
        "missing",
        "This playbook does not have a stored workflow graph yet. The editor can start from a local starter graph after you open it and save a real workflow.",
    )

def _serialize_playbook(pb: Playbook) -> dict:
    category = None
    if pb.category_filter:
        if isinstance(pb.category_filter, list) and len(pb.category_filter) > 0:
            category = pb.category_filter[0]
        elif isinstance(pb.category_filter, dict):
            cats = pb.category_filter.get("categories") or []
            category = cats[0] if cats else None

    workflow, workflow_status, workflow_message = _workflow_state(pb)

    return {
        "id": str(pb.id),
        "tenant_id": str(pb.tenant_id),
        "name": pb.name,
        "description": pb.description or "",
        "category": category,
        "version": getattr(pb, "version", "1.0") or "1.0",
        "workflow": workflow,
        "workflow_status": workflow_status,
        "workflow_message": workflow_message,
        "workflow_ref": getattr(pb, "workflow_ref", None),
        "timeout_seconds": getattr(pb, "timeout_seconds", 3600) or 3600,
        "retry_policy": getattr(pb, "retry_policy", None)
        or {
            "max_retries": 3,
            "retry_delay_seconds": 60,
            "backoff_multiplier": 2,
        },
        "on_failure": getattr(pb, "on_failure", "fail") or "fail",
        "is_template": getattr(pb, "is_builtin", False),
        "requires_approval": pb.requires_approval,
        "tags": pb.tags or (category.split(",") if category else []),
        "nist_controls": getattr(pb, "nist_controls", []),
        "soc2_criteria": getattr(pb, "soc2_criteria", []),
        "mitre_tactics": getattr(pb, "mitre_tactics", []),
        "mitre_techniques": getattr(pb, "mitre_techniques", []),
        "triggers": getattr(pb, "triggers", []),
        "playbook_key": getattr(pb, "key", None) or getattr(pb, "playbook_key", None),
        "created_at": pb.created_at.isoformat() if pb.created_at else None,
        "updated_at": pb.updated_at.isoformat() if pb.updated_at else None,
    }


@router.get("")
def list_playbooks(
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """List available playbooks - includes built-in (system) and tenant-specific."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🎭 Playbooks Query START - tenant_id: {tenant_id}")

    system_tenant_id = _system_tenant_id()

    builtin_playbooks = db.query(Playbook).filter(
        Playbook.tenant_id == system_tenant_id,
        Playbook.is_enabled == True,
    ).all()
    logger.info(f"📊 Found {len(builtin_playbooks)} builtin playbooks")

    tenant_playbooks = db.query(Playbook).filter(
        Playbook.tenant_id == tenant_id,
        Playbook.is_enabled == True,
        Playbook.is_builtin != True,
    ).all()
    logger.info(f"📊 Found {len(tenant_playbooks)} tenant-specific playbooks (non-builtin)")

    all_playbooks = [_serialize_playbook(pb) for pb in (builtin_playbooks + tenant_playbooks)]
    logger.info(f"✅ Playbooks Query COMPLETE - Returning {len(all_playbooks)} playbooks from database")
    return all_playbooks


@router.post("/{playbook_id}/execute")
@router.post("/{playbook_id}/execute/")
# Fallback path to handle proxies or mis-configured prefixes
@router.post("/execute/{playbook_id}")
def execute_playbook(
    playbook_id: UUID,
    payload: PlaybookExecuteRequest,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Create a truthful execution record for a requested playbook run."""
    pb = db.query(Playbook).filter(Playbook.id == playbook_id).first()
    if not pb:
        raise HTTPException(status_code=404, detail="Playbook not found")
    if pb.tenant_id not in (UUIDType(tenant_id), _system_tenant_id()):
        raise HTTPException(status_code=403, detail="Forbidden")

    now = datetime.utcnow()
    approval_status, result_summary = _execution_submission_summary(pb)
    resolved_alert_id = (
        payload.alert_id
        or (
            payload.trigger_id
            if (payload.trigger_type or "manual") == "alert"
            else None
        )
        or _coerce_uuid((payload.parameters or {}).get("alert_id"))
    )
    execution = PlaybookExecution(
        tenant_id=UUIDType(tenant_id),
        playbook_id=playbook_id,
        target_type=payload.trigger_type or "manual",
        target_id=payload.trigger_id or resolved_alert_id or payload.alert_id or playbook_id,
        status="pending",
        workflow_exec_id=None,
        triggered_by=payload.triggered_by or "ui",
        approval_status=approval_status,
        started_at=now,
        finished_at=None,
        result_summary=result_summary,
        logs={
            "parameters": payload.parameters or {},
            "detection_rule_id": payload.detection_rule_id,
            "detection_rule_version_id": payload.detection_rule_version_id,
            "requested_at": now.isoformat(),
            "requires_approval": pb.requires_approval,
            "execution_mode": "queued_request",
        },
        alert_id=resolved_alert_id,
        trigger_rule_id=None,
    )

    db.add(execution)
    db.commit()
    db.refresh(execution)

    return {
        "execution_id": str(execution.id),
        "status": execution.status,
        "approval_status": execution.approval_status,
        "workflow_exec_id": execution.workflow_exec_id,
        "trigger_type": execution.target_type,
        "trigger_id": str(execution.target_id) if execution.target_id else None,
        "alert_id": str(execution.alert_id) if execution.alert_id else None,
        "message": execution.result_summary,
    }


@router.post(CLONE_PREFIX + "/{playbook_id}")
@router.post("/{playbook_id}/clone")
def clone_playbook(
    playbook_id: UUID,
    payload: PlaybookCloneRequest,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """
    Clone a system built-in (or tenant-owned) playbook into the current tenant.
    Useful when a customer manages their own SOC and wants an editable copy.
    """
    source = (
        db.query(Playbook)
        .filter(Playbook.id == playbook_id)
        .first()
    )
    if not source:
        raise HTTPException(status_code=404, detail="Playbook not found")

    clone_key = payload.key or f"{source.key}-COPY"
    clone_name = payload.name or f"{source.name} Copy"

    new_playbook = Playbook(
        tenant_id=tenant_id,
        key=clone_key,
        name=clone_name,
        description=payload.description or source.description,
        target_type=source.target_type,
        severity_filter=source.severity_filter,
        category_filter=source.category_filter,
        workflow_ref=source.workflow_ref,
        workflow=source.workflow if isinstance(getattr(source, "workflow", None), dict) else None,
        requires_approval=source.requires_approval,
        is_enabled=True,
        is_builtin=False,
    )
    db.add(new_playbook)
    db.commit()
    db.refresh(new_playbook)
    return _serialize_playbook(new_playbook)


# Secondary router to expose clone under a distinct prefix to avoid proxy collisions
@clone_router.post("/playbook-clone/{playbook_id}")
def clone_playbook_alt(
    playbook_id: UUID,
    payload: PlaybookCloneRequest,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    return clone_playbook(playbook_id, payload, tenant_id, db)


@router.get("/{playbook_id}")
def get_playbook(
    playbook_id: UUID,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    pb = db.query(Playbook).filter(Playbook.id == playbook_id).first()
    if not pb:
        raise HTTPException(status_code=404, detail="Playbook not found")
    # Tenant can read system built-ins plus own; deny others.
    if pb.tenant_id not in (UUIDType(tenant_id), _system_tenant_id()):
        raise HTTPException(status_code=403, detail="Forbidden")
    return _serialize_playbook(pb)


@router.put("/{playbook_id}")
def update_playbook(
    playbook_id: UUID,
    payload: PlaybookUpdateRequest,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    pb = db.query(Playbook).filter(Playbook.id == playbook_id).first()
    if not pb:
        raise HTTPException(status_code=404, detail="Playbook not found")
    if pb.is_builtin and pb.tenant_id == _system_tenant_id():
        raise HTTPException(status_code=403, detail="Cannot edit built-in playbook; clone it first")
    if pb.tenant_id != UUIDType(tenant_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    if payload.name is not None:
        pb.name = payload.name
    if payload.description is not None:
        pb.description = payload.description
    if payload.workflow is not None:
        pb.workflow = payload.workflow

    db.add(pb)
    db.commit()
    db.refresh(pb)
    return _serialize_playbook(pb)


@router.post("/{playbook_id}/validate")
def validate_playbook(
    playbook_id: UUID,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    pb = db.query(Playbook).filter(Playbook.id == playbook_id).first()
    if not pb:
        raise HTTPException(status_code=404, detail="Playbook not found")
    if pb.tenant_id not in (UUIDType(tenant_id), _system_tenant_id()):
        raise HTTPException(status_code=403, detail="Forbidden")

    workflow, workflow_status, _workflow_message = _workflow_state(pb)
    if workflow_status == "external_reference":
        return {
            "valid": True,
            "errors": [],
            "warnings": [
                "This playbook is backed by an external workflow reference; the live automation graph is not exposed in the launch editor.",
            ],
        }
    if workflow_status != "stored" or workflow is None:
        return {
            "valid": False,
            "errors": [
                "Stored workflow is missing. Save a real workflow before validating this playbook.",
            ],
            "warnings": [],
        }

    nodes = workflow.get("nodes") or []
    errors = []
    if not any(n.get("type") == "trigger" for n in nodes):
        errors.append("At least one trigger node required")
    return {"valid": len(errors) == 0, "errors": errors, "warnings": []}
