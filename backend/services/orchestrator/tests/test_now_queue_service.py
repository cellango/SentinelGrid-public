import os
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.api import dashboard as dashboard_api
from app.services.now_queue_service import NowQueueService
from sg_core.models import Incident
from sg_core.service_metrics import get_service_metrics, reset_service_metrics


class _FakeQuery:
    def __init__(self, incidents):
        self.incidents = incidents

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return list(self.incidents)


class _FakeSession:
    def __init__(self, incidents):
        self.incidents = incidents

    def query(self, model):
        model_name = getattr(model, "__name__", "")
        if model_name != "Incident":
            raise AssertionError(f"Unexpected model query: {model}")
        return _FakeQuery(self.incidents)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_list_open_incidents_returns_real_story_context():
    reset_service_metrics("orchestrator")
    tenant_uuid = uuid4()
    now = datetime.now(timezone.utc)
    incident = Incident(
        id=uuid4(),
        tenant_id=tenant_uuid,
        source="detection_service",
        title="Suspicious admin session",
        status="open",
        severity="high",
        raw_payload={
            "user_identifier": "owner@example.com",
            "host": {"hostname": "prod-admin-1"},
            "description": "Admin activity from unusual source IP",
            "ai_summary": "Escalated because the affected identity still has privileged access.",
            "ai_proposed_fixes": ["Revoke the session", "Reset the admin password"],
        },
        created_at=now,
        updated_at=now,
    )

    service = NowQueueService()
    service.db_session_factory = lambda: _FakeSession([incident])

    items = service.list_open_incidents(str(tenant_uuid))

    assert len(items) == 1
    item = items[0]
    assert item["id"] == str(incident.id)
    assert item["severity"] == "high"
    assert item["affected_count"] == 2
    assert item["description"] == "Admin activity from unusual source IP"
    assert item["ai_summary"] == "Escalated because the affected identity still has privileged access."
    assert item["ai_proposed_fixes"] == ["Revoke the session", "Reset the admin password"]
    assert "identity" in item["story_domains"]
    assert "endpoint" in item["story_domains"]
    assert item["story_summary"]["primary_entity"]["label"] == "owner@example.com"
    snapshot = get_service_metrics("orchestrator").snapshot()
    assert snapshot["gauges"]["now_queue_open_incidents_last"]["__base__"] == 1


def test_build_queue_records_backlog_metrics(monkeypatch):
    reset_service_metrics("orchestrator")
    service = NowQueueService()
    monkeypatch.setattr(
        dashboard_api,
        "_now_queue_service",
        service,
    )
    monkeypatch.setattr(
        service,
        "_incident_candidates",
        lambda tenant_id: [{"id": "incident:1", "item_type": "incident", "priority": "high", "domains": ["identity"]}],
    )
    monkeypatch.setattr(
        service,
        "_alert_candidates",
        lambda tenant_id: [{"id": "alert:1", "item_type": "alert", "priority": "medium", "domains": ["endpoint"]}],
    )
    monkeypatch.setattr(
        "app.services.now_queue_service.build_recommendations",
        lambda posture_score, people_access, onboarding_status: [
            {
                "id": "rec-1",
                "title": "Recommended fix",
                "description": "Do the thing",
                "priority": "medium",
                "actions": [{"label": "Open", "endpoint": "/dashboard"}],
            }
        ],
    )

    queue = service.build_queue("11111111-1111-1111-1111-111111111111", {}, {}, {}, limit=8)

    assert queue["summary"]["total_items"] == 3
    snapshot = get_service_metrics("orchestrator").snapshot()
    assert snapshot["counters"]["now_queue_builds_total"]["total"] == 1
    assert snapshot["gauges"]["now_queue_items_last"]["__base__"] == 3
    assert snapshot["gauges"]["now_queue_items_by_type_last"]["item_type=incident"] == 1
    assert snapshot["gauges"]["now_queue_items_by_type_last"]["item_type=alert"] == 1
    assert snapshot["gauges"]["now_queue_items_by_type_last"]["item_type=recommendation"] == 1


@pytest.mark.asyncio
async def test_dashboard_snapshot_includes_open_incidents(monkeypatch):
    open_incidents = [
        {
            "id": "incident-1",
            "title": "Open incident",
            "severity": "critical",
            "risk_level": "critical",
            "affected_count": 1,
            "description": "Critical incident",
            "created_at": "2026-04-15T12:00:00Z",
            "story_domains": ["identity"],
            "story_summary": {"headline": "Identity story", "entity_count": 1, "evidence_count": 1},
            "entities": [],
            "evidence": [],
        }
    ]

    async def _fake_context(_tenant_id):
        return ({}, {}, {})

    monkeypatch.setattr(dashboard_api, "_load_operator_context", _fake_context)
    monkeypatch.setattr(
        dashboard_api,
        "_now_queue_service",
        SimpleNamespace(list_open_incidents=lambda tenant_id: open_incidents),
    )
    monkeypatch.setattr(
        dashboard_api,
        "_ai_risk_summary_service",
        SimpleNamespace(build_summary=lambda tenant_id: {"health_status": "inactive"}),
    )
    monkeypatch.setattr(dashboard_api, "build_cloud_posture_snapshot", lambda posture_score: {})
    monkeypatch.setattr(dashboard_api, "build_dashboard_health", lambda onboarding_status, posture_score: {})
    monkeypatch.setattr(dashboard_api, "build_recommendations", lambda posture_score, people_access, onboarding_status: [])
    monkeypatch.setattr(dashboard_api, "build_first_value_section", lambda tenant_id, posture_score, people_access: {"findings": []})

    payload = await dashboard_api.get_dashboard_snapshot(str(uuid4()))

    assert payload["open_incidents"] == open_incidents
