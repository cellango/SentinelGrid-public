"""Shared workflow event schema and publication helpers."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sg_core.audit_logger import AuditAction, AuditLogger
from sg_events.bus import event_bus


WORKFLOW_EVENTS_TOPIC = "workflow.events"


class WorkflowEventType(str, Enum):
    """Canonical workflow event names for operator hand-offs."""

    ALERT_PROMOTED_TO_INCIDENT = "alert.promoted_to_incident"
    INCIDENT_TICKET_REQUESTED = "incident.ticket.requested"
    TICKET_CREATED = "ticket.created"
    TICKET_HANDOFF_COMPLETED = "ticket.handoff.completed"
    TICKET_HANDOFF_SKIPPED = "ticket.handoff.skipped"
    NOTIFICATION_SENT = "notification.sent"
    WORKFLOW_FAILED = "workflow.failed"


class WorkflowStage(str, Enum):
    """High-level stages in the alert -> incident -> ticket -> notification chain."""

    DETECTION = "detection"
    INCIDENT = "incident"
    TICKETING = "ticketing"
    NOTIFICATION = "notification"


_AUDIT_ACTIONS: Dict[WorkflowEventType, AuditAction] = {
    WorkflowEventType.ALERT_PROMOTED_TO_INCIDENT: AuditAction.INCIDENT_CREATED,
    WorkflowEventType.INCIDENT_TICKET_REQUESTED: AuditAction.INCIDENT_TICKET_REQUESTED,
    WorkflowEventType.TICKET_CREATED: AuditAction.TICKET_CREATED,
    WorkflowEventType.TICKET_HANDOFF_COMPLETED: AuditAction.TICKET_HANDOFF_COMPLETED,
    WorkflowEventType.TICKET_HANDOFF_SKIPPED: AuditAction.TICKET_HANDOFF_SKIPPED,
    WorkflowEventType.NOTIFICATION_SENT: AuditAction.NOTIFICATION_SENT,
    WorkflowEventType.WORKFLOW_FAILED: AuditAction.WORKFLOW_FAILED,
}


def _stringify(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def build_workflow_event(
    *,
    event_type: WorkflowEventType,
    stage: WorkflowStage,
    tenant_id: UUID | str,
    workflow_id: UUID | str,
    source_service: str,
    title: str,
    resource_type: str,
    resource_id: UUID | str,
    resource_name: Optional[str] = None,
    related_resources: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    success: bool = True,
    error_message: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a standard workflow event envelope."""

    return {
        "event_id": str(uuid4()),
        "event_type": event_type.value,
        "stage": stage.value,
        "workflow_id": _stringify(workflow_id),
        "tenant_id": _stringify(tenant_id),
        "source_service": source_service,
        "title": title,
        "resource": {
            "type": resource_type,
            "id": _stringify(resource_id),
            "name": resource_name,
        },
        "related_resources": related_resources or [],
        "metadata": metadata or {},
        "success": success,
        "error_message": error_message,
        "occurred_at": datetime.utcnow().isoformat(),
    }


def publish_workflow_event(
    *,
    event_type: WorkflowEventType,
    stage: WorkflowStage,
    tenant_id: UUID | str,
    workflow_id: UUID | str,
    source_service: str,
    title: str,
    resource_type: str,
    resource_id: UUID | str,
    resource_name: Optional[str] = None,
    related_resources: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    db_session=None,
    realm_name: str = "sentinelgrid",
    actor_user_id: str = "system",
    actor_email: Optional[str] = None,
    actor_roles: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Publish a workflow event to the bus and persist it via audit logging when possible."""

    envelope = build_workflow_event(
        event_type=event_type,
        stage=stage,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        source_service=source_service,
        title=title,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        related_resources=related_resources,
        metadata=metadata,
        success=success,
        error_message=error_message,
    )

    tenant_key = _stringify(tenant_id)
    event_bus.publish(WORKFLOW_EVENTS_TOPIC, envelope)
    event_bus.publish(f"{WORKFLOW_EVENTS_TOPIC}.{tenant_key}", envelope)

    if db_session is not None:
        AuditLogger(db_session).log(
            action=_AUDIT_ACTIONS[event_type],
            tenant_id=UUID(tenant_key) if not isinstance(tenant_id, UUID) else tenant_id,
            realm_name=realm_name,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            actor_roles=actor_roles or ["system"],
            resource_type=resource_type,
            resource_id=_stringify(resource_id),
            resource_name=resource_name,
            success=success,
            error_message=error_message,
            metadata={
                "workflow_event": envelope,
                **(metadata or {}),
            },
        )

    return envelope
