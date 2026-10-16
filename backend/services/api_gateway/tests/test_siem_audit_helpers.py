"""Unit tests for SIEM alert audit helper behavior."""

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import Mock

from app.api.routes_audit import _coalesce_timeline, _fetch_platform_audit
from app.api.routes_siem import _append_alert_audit_entry, _serialize_alert
from sg_core.models import Alert


def test_append_alert_audit_entry_preserves_payload_and_appends_event():
    raw_payload = {
        "assigned_to": "triage-queue",
        "comments": [{"text": "Analyst note", "at": "2026-03-25T10:00:00"}],
    }

    next_payload = _append_alert_audit_entry(
        raw_payload,
        "Assigned to secops-oncall",
        metadata={"previous_assigned_to": "triage-queue", "assigned_to": "secops-oncall"},
    )

    assert next_payload["comments"] == raw_payload["comments"]
    assert next_payload["audit"][-1]["text"] == "Assigned to secops-oncall"
    assert next_payload["audit"][-1]["metadata"]["assigned_to"] == "secops-oncall"


def test_coalesce_timeline_merges_audit_and_comments():
    entries = _coalesce_timeline(
        {
            "audit": [
                {"ts": "2026-03-25T10:01:00", "text": "Assigned to secops-oncall", "actor": "operator"}
            ],
            "comments": [
                {"at": "2026-03-25T10:02:00", "text": "Analyst note", "actor": "analyst@example.com"}
            ],
        }
    )

    texts = [entry["text"] for entry in entries]

    assert "Assigned to secops-oncall" in texts
    assert "Analyst note" in texts


def test_serialize_alert_includes_story_context():
    alert = Alert(
        id=uuid4(),
        tenant_id=uuid4(),
        source="wazuh",
        external_id="alert-123",
        title="Suspicious AI prompt injection",
        description="Prompt injection attempt blocked",
        raw_severity="high",
        status="open",
        detection_time=datetime.utcnow(),
        asset_id="endpoint-22",
        user_identifier="analyst@example.com",
        raw_payload={
            "incident_ids": ["inc-123"],
            "detection_rule_id": "SG-AI-001",
            "playbook_id": "AI-PROMPT-INJECTION",
            "assigned_to": "triage-queue",
            "due_date": "2026-03-27T15:00:00+00:00",
            "ai": {
                "app_id": "research-assist",
                "provider": "anthropic",
                "model": "claude-3",
                "user_id": "analyst@example.com",
            },
        },
        cve_ids=["CVE-2026-0001"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    data = _serialize_alert(alert)

    assert {entity["type"] for entity in data["entities"]} >= {"identity", "device", "ai_app"}
    assert any(item["type"] == "incident" and item["id"] == "inc-123" for item in data["evidence"])
    assert any(item["type"] == "detection_rule" and item["id"] == "SG-AI-001" for item in data["evidence"])
    assert any(item["type"] == "playbook" and item["id"] == "AI-PROMPT-INJECTION" for item in data["evidence"])
    assert any(item["type"] == "cve" and item["id"] == "CVE-2026-0001" for item in data["evidence"])
    assert "ai" in data["story_domains"]
    assert data["assigned_to"] == "triage-queue"
    assert data["due_date"] == "2026-03-27T15:00:00+00:00"
    assert data["story_summary"]["headline"] == "AI + Endpoint + Identity story"
    assert data["story_summary"]["primary_entity"]["label"] == "analyst@example.com"
    assert data["story_summary"]["evidence_count"] >= 4


def test_fetch_platform_audit_prefers_workflow_event_title():
    db = Mock()
    db.execute.return_value.fetchall.return_value = [
        SimpleNamespace(
            action="ticket_handoff_completed",
            action_category="security",
            actor_user_id="system",
            actor_email=None,
            success=True,
            error_message=None,
            metadata='{"workflow_event":{"title":"TheHive handoff created","event_type":"ticket.handoff.completed"}}',
            timestamp="2026-03-27T12:00:00Z",
        )
    ]

    events = _fetch_platform_audit(
        db,
        tenant_id="tenant-123",
        resource_type="incident",
        resource_id="inc-123",
    )

    assert events[0]["text"] == "TheHive handoff created"
    assert events[0]["metadata"]["workflow_event"]["event_type"] == "ticket.handoff.completed"
