import sys
import types
from enum import Enum
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[2]
LIBS_ROOT = Path(__file__).resolve().parents[4] / "libs"

for path in (SERVICE_ROOT, LIBS_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


class _WorkflowEventType(str, Enum):
    ALERT_PROMOTED_TO_INCIDENT = "alert.promoted_to_incident"
    INCIDENT_TICKET_REQUESTED = "incident.ticket.requested"
    TICKET_CREATED = "ticket.created"
    TICKET_HANDOFF_COMPLETED = "ticket.handoff.completed"
    TICKET_HANDOFF_SKIPPED = "ticket.handoff.skipped"
    NOTIFICATION_SENT = "notification.sent"
    WORKFLOW_FAILED = "workflow.failed"


class _WorkflowStage(str, Enum):
    DETECTION = "detection"
    INCIDENT = "incident"
    TICKETING = "ticketing"
    NOTIFICATION = "notification"


def _publish_workflow_event(**kwargs):
    return kwargs


if "sg_events.workflow" not in sys.modules:
    workflow_module = types.ModuleType("sg_events.workflow")
    workflow_module.WorkflowEventType = _WorkflowEventType
    workflow_module.WorkflowStage = _WorkflowStage
    workflow_module.publish_workflow_event = _publish_workflow_event

    package_module = types.ModuleType("sg_events")
    package_module.__path__ = []  # type: ignore[attr-defined]
    package_module.workflow = workflow_module

    sys.modules["sg_events"] = package_module
    sys.modules["sg_events.workflow"] = workflow_module
