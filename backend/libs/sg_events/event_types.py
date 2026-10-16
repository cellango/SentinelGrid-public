"""Event type definitions."""

import time
import uuid
from enum import Enum
from typing import Any, Dict


class EventType(str, Enum):
    """Event type enumeration."""

    # Existing event types
    ALERT_INGESTED = "alert.ingested"
    ALERT_TRIAGED = "alert.triaged"
    INCIDENT_CREATED = "incident.created"
    INCIDENT_UPDATED = "incident.updated"
    PLAYBOOK_STARTED = "playbook.started"
    PLAYBOOK_FINISHED = "playbook.finished"
    MODEL_INFERENCE = "model.inference"

    # Agent task lifecycle
    TASK_SUBMITTED = "task.submitted"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"

    # Approval workflow
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_REJECTED = "approval.rejected"

    # Agent lifecycle
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"

    # Enrichment
    ENRICHMENT_COMPLETED = "enrichment.completed"


class Event:
    """Event wrapper with metadata."""

    def __init__(
        self,
        event_type: EventType,
        tenant_id: str,
        payload: Dict[str, Any],
        source: str = "sentinelgrid",
    ):
        self.event_type = event_type
        self.tenant_id = tenant_id
        self.payload = payload
        self.source = source

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "type": self.event_type.value,
            "tenant_id": self.tenant_id,
            "payload": self.payload,
            "source": self.source,
        }


def create_event(
    event_type: EventType | str,
    tenant_id: str,
    payload: Dict[str, Any],
    source: str = "sentinelgrid",
) -> Dict[str, Any]:
    """Create a properly structured event dict ready for publishing.

    Args:
        event_type: An EventType enum member or its string value.
        tenant_id: Tenant identifier for multi-tenant isolation.
        payload: Arbitrary event payload.
        source: Originating service/agent name.

    Returns:
        A dict suitable for ``EventBus.publish()``.
    """
    if isinstance(event_type, EventType):
        type_value = event_type.value
    else:
        type_value = str(event_type)

    return {
        "id": str(uuid.uuid4()),
        "type": type_value,
        "tenant_id": tenant_id,
        "payload": payload,
        "source": source,
        "timestamp": time.time(),
    }
