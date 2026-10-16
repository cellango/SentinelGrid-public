import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.ai_risk_summary_service import AiRiskSummaryService
from sg_core.models import Alert, Incident


class _FakeQuery:
    def __init__(self, items):
        self.items = items

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return list(self.items)


class _FakeSession:
    def __init__(self, alerts, incidents):
        self.alerts = alerts
        self.incidents = incidents

    def query(self, model):
        model_name = getattr(model, "__name__", "")
        if model_name == "Alert":
            return _FakeQuery(self.alerts)
        if model_name == "Incident":
            return _FakeQuery(self.incidents)
        raise AssertionError(f"Unexpected model query: {model}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_build_summary_prioritizes_ai_incidents_and_top_apps():
    tenant_id = str(uuid4())
    tenant_uuid = uuid4()
    now = datetime.now(timezone.utc)
    alert = Alert(
        id=uuid4(),
        tenant_id=tenant_uuid,
        source="sentinelgrid_ai_shield",
        external_id="evt-1",
        title="Prompt injection attempt detected in support-assistant",
        description="AI Shield flagged a suspected prompt injection attempt.",
        raw_severity="high",
        status="open",
        detection_time=now,
        asset_id="support-assistant",
        user_identifier="owner@example.com",
        raw_payload={
            "category": "ai",
            "ai": {"app_id": "support-assistant", "user_id": "owner@example.com"},
            "finding": {"type": "prompt_injection"},
        },
        created_at=now,
        updated_at=now,
    )
    incident = Incident(
        id=uuid4(),
        tenant_id=tenant_uuid,
        source="sentinelgrid_ai_shield",
        external_id="inc-1",
        title="Secrets exposure through support-assistant",
        status="open",
        severity="critical",
        raw_payload={
            "description": "Likely secret material flowed to an external model.",
            "ai": {"app_id": "support-assistant", "user_id": "owner@example.com"},
        },
        created_at=now,
        updated_at=now,
    )

    service = AiRiskSummaryService()
    service.db_session_factory = lambda: _FakeSession([alert], [incident])

    summary = service.build_summary(tenant_id)

    assert summary["health_status"] == "critical"
    assert summary["open_alerts"] == 1
    assert summary["active_incidents"] == 1
    assert summary["affected_apps"] == 1
    assert summary["affected_users"] == 1
    assert summary["prompt_injection_alerts"] == 1
    assert summary["top_risk"]["item_type"] == "incident"
    assert summary["top_risk"]["title"] == incident.title
    assert summary["top_applications"][0]["label"] == "support-assistant"
    assert summary["top_applications"][0]["active_incidents"] == 1


def test_build_summary_returns_inactive_when_no_ai_findings():
    service = AiRiskSummaryService()
    service.db_session_factory = lambda: _FakeSession([], [])

    summary = service.build_summary(str(uuid4()))

    assert summary["health_status"] == "inactive"
    assert summary["open_alerts"] == 0
    assert summary["active_incidents"] == 0
    assert summary["top_risk"] is None
