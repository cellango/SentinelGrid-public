import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

SERVICE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
LIBS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../libs"))
if SERVICE_ROOT not in sys.path:
    sys.path.insert(0, SERVICE_ROOT)
if LIBS_ROOT not in sys.path:
    sys.path.insert(0, LIBS_ROOT)

from app.services.ticket_service import TicketService, TicketingHandoffConfig
from sg_core.models import Ticket


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def fetchone(self):
        return self._row


class _FakeDb:
    def __init__(self, rows):
        self._rows = list(rows)
        self._index = 0

    def execute(self, _stmt, _params=None):
        row = self._rows[self._index] if self._index < len(self._rows) else None
        self._index += 1
        return _FakeResult(row)


def test_build_auth_headers_supports_prefixed_and_raw_tokens():
    service = TicketService()

    assert service._build_auth_headers("Bearer abc123") == {"Authorization": "Bearer abc123"}
    assert service._build_auth_headers("Basic Zm9vOmJhcg==") == {"Authorization": "Basic Zm9vOmJhcg=="}
    assert service._build_auth_headers("plain-token") == {"Authorization": "Bearer plain-token"}


def test_resolve_handoff_config_prefers_onboarding_customer_managed_settings():
    service = TicketService()
    db = _FakeDb(
        [
            {
                "id": "tenant-1",
                "slug": "acme",
                "customer_id": "customer-1",
                "incident_management_mode": "saas_managed",
                "ticketing_provider": "internal",
                "ticketing_project": None,
                "services_selected": {"socManaged": True},
            },
            {
                "services_selected": {"socManaged": False, "ticketing": "jira"},
                "ticketing_config": {
                    "provider": "jira",
                    "url": "https://jira.example.com",
                    "project": "SECOPS",
                    "api_key": "Bearer abc123",
                    "issue_type": "Incident",
                    "assignment_mode": "named_owner",
                    "default_assignee": "security-lead",
                    "assignee_identifier_type": "account_id",
                    "auto_create_tickets": True,
                    "notify_slack": True,
                    "slack_channel": "#security-alerts",
                    "slack_webhook_url": "https://hooks.slack.com/services/T1/B1/C1",
                },
                "ticketing_health": {"status": "healthy"},
            },
        ]
    )

    config = service.resolve_handoff_config(db, "tenant-1", {})

    assert config.customer_managed is True
    assert config.provider == "jira"
    assert config.project == "SECOPS"
    assert config.assignment_mode == "named_owner"
    assert config.default_assignee == "security-lead"
    assert config.assignee_identifier_type == "account_id"
    assert config.notify_slack is True
    assert config.health_status == "healthy"


def test_resolve_handoff_config_falls_back_to_tenant_preferences():
    service = TicketService()
    db = _FakeDb(
        [
            {
                "id": "tenant-2",
                "slug": "beta",
                "customer_id": None,
                "incident_management_mode": "customer_managed",
                "ticketing_provider": "servicenow",
                "ticketing_project": "Security Operations",
                "services_selected": {"socManaged": False},
            },
            None,
        ]
    )

    config = service.resolve_handoff_config(db, "tenant-2", {})

    assert config.customer_managed is True
    assert config.provider == "servicenow"
    assert config.project == "Security Operations"
    assert config.issue_type == "Security Incident"
    assert config.assignee_identifier_type == "username"


def test_external_ticket_description_includes_routing_context():
    service = TicketService()
    ticket = SimpleNamespace(
        external_id="SG-acme-123",
        title="Suspicious Login",
        description="Multiple failed logins from a new location",
        severity="high",
        category="identity",
    )
    config = SimpleNamespace(
        assignment_mode="named_owner",
        default_assignee="secops-oncall",
    )

    description = service._build_external_ticket_description(
        ticket,
        {"incident_id": "inc-1", "alert_ids": ["alert-1", "alert-2"]},
        config,
    )

    assert "SG ticket ID: SG-acme-123" in description
    assert "SentinelGrid incident: inc-1" in description
    assert "Assign to secops-oncall." in description


def test_build_jira_assignee_field_uses_identifier_type():
    service = TicketService()

    assert service._build_jira_assignee_field("acct-123", "account_id") == {"accountId": "acct-123"}
    assert service._build_jira_assignee_field("owner@company.com", "email") == {"emailAddress": "owner@company.com"}
    assert service._build_jira_assignee_field("jira.user", "username") == {"name": "jira.user"}


def test_build_jira_update_fields_includes_assignee():
    service = TicketService()
    ticket = SimpleNamespace(
        title="Suspicious Login",
        description="Updated details",
        priority="P2",
        severity="high",
    )
    config = TicketingHandoffConfig(
        provider="jira",
        assignment_mode="named_owner",
        default_assignee="712020:abc",
        assignee_identifier_type="account_id",
    )

    fields = service._build_jira_update_fields(
        ticket,
        {"assigned_to": "712020:abc"},
        config,
    )

    assert fields["assignee"] == {"accountId": "712020:abc"}


def test_pick_jira_transition_id_matches_status_family():
    service = TicketService()

    transition_id = service._pick_jira_transition_id(
        [
            {"id": "11", "to": {"name": "Open"}},
            {"id": "12", "to": {"name": "In Progress"}},
            {"id": "13", "to": {"name": "Done"}},
        ],
        "resolved",
    )

    assert transition_id == "13"


def test_build_servicenow_update_payload_maps_status_and_severity():
    service = TicketService()
    ticket = SimpleNamespace(
        title="Critical malware",
        description="Malware detected on host",
        status="resolved",
        severity="critical",
    )

    payload = service._build_servicenow_update_payload(
        ticket,
        {"status": "resolved", "severity": "critical", "assigned_to": "secops-user"},
    )

    assert payload["state"] == "6"
    assert payload["severity"] == "1"
    assert payload["urgency"] == "1"
    assert payload["impact"] == "1"
    assert payload["assigned_to"] == "secops-user"


def test_ticket_assigned_to_property_uses_timeline_data():
    ticket = Ticket(
        id=uuid4(),
        tenant_id=uuid4(),
        source="internal",
        title="Suspicious login",
        status="open",
    )

    assert ticket.assigned_to is None

    ticket.assigned_to = "secops-oncall"

    assert ticket.assigned_to == "secops-oncall"
    assert ticket.timeline_data["assigned_to"] == "secops-oncall"


def test_ticket_due_date_property_uses_timeline_data():
    ticket = Ticket(
        id=uuid4(),
        tenant_id=uuid4(),
        source="internal",
        title="Suspicious login",
        status="open",
    )

    assert ticket.due_date is None

    ticket.due_date = "2026-03-27T12:00:00+00:00"

    assert ticket.due_date == "2026-03-27T12:00:00+00:00"
    assert ticket.timeline_data["due_date"] == "2026-03-27T12:00:00+00:00"


def test_record_ticket_mutation_events_tracks_status_and_assignment_changes():
    service = TicketService()
    ticket = Ticket(
        id=uuid4(),
        tenant_id=uuid4(),
        source="internal",
        title="Suspicious login",
        status="resolved",
        timeline_data={},
    )
    ticket.assigned_to = "secops-oncall"
    ticket.due_date = "2026-03-27T12:00:00+00:00"

    service._record_ticket_mutation_events(
        ticket,
        previous_status="open",
        previous_assignee="triage-queue",
        previous_due_date="2026-03-27T08:00:00+00:00",
        ticket_data={
            "status": "resolved",
            "assigned_to": "secops-oncall",
            "due_date": "2026-03-27T12:00:00+00:00",
        },
    )

    events = ticket.timeline_data["events"]
    assert events[0]["type"] == "status_updated"
    assert events[0]["metadata"]["previous_status"] == "open"
    assert events[1]["type"] == "assignment_updated"
    assert events[1]["metadata"]["previous_assigned_to"] == "triage-queue"
    assert events[1]["metadata"]["assigned_to"] == "secops-oncall"
    assert events[2]["type"] == "sla_updated"
    assert events[2]["metadata"]["previous_due_date"] == "2026-03-27T08:00:00+00:00"
    assert events[2]["metadata"]["due_date"] == "2026-03-27T12:00:00+00:00"


def test_append_comment_event_records_comment_text():
    service = TicketService()

    timeline = service._append_comment_event({}, "Containment started", actor="analyst@example.com")

    event = timeline["events"][0]
    assert event["type"] == "comment"
    assert event["text"] == "Containment started"
    assert event["actor"] == "analyst@example.com"


@pytest.mark.asyncio
async def test_update_ticket_dispatches_customer_managed_sync():
    service = TicketService()
    ticket = SimpleNamespace(
        id="ticket-1",
        tenant_id="tenant-1",
        title="Suspicious login",
        description="Initial description",
        status="open",
        severity="high",
        priority="P2",
        category="identity",
        source="internal",
        external_id="SG-acme-123",
        external_vendor_id="SECOPS-101",
        timeline_data={"external_ticket_provider": "jira"},
        updated_at=None,
    )

    class FakeDb:
        def __init__(self):
            self.commits = 0

        def commit(self):
            self.commits += 1

        def refresh(self, _obj):
            return None

    db = FakeDb()
    service._lookup_ticket = lambda *_args, **_kwargs: ticket  # type: ignore[method-assign]
    service.resolve_handoff_config = lambda *_args, **_kwargs: TicketingHandoffConfig(  # type: ignore[method-assign]
        customer_managed=True,
        provider="jira",
        url="https://jira.example.com",
        api_key="Bearer abc123",
        project="SECOPS",
    )
    service._sync_customer_managed_external_ticket_update = AsyncMock(  # type: ignore[method-assign]
        return_value={"provider": "jira", "updated_fields": ["status"], "transition_id": "31"}
    )

    updated_ticket = await service.update_ticket(
        db,
        "ticket-1",
        "tenant-1",
        {"status": "resolved"},
    )

    assert updated_ticket.status == "resolved"
    assert service._sync_customer_managed_external_ticket_update.await_count == 1
    assert (updated_ticket.timeline_data or {}).get("events")


@pytest.mark.asyncio
async def test_add_comment_dispatches_customer_managed_comment_sync():
    service = TicketService()
    ticket = SimpleNamespace(
        id="ticket-1",
        tenant_id="tenant-1",
        title="Suspicious login",
        description="Initial description",
        status="open",
        severity="high",
        priority="P2",
        category="identity",
        source="internal",
        external_id="SG-acme-123",
        external_vendor_id="SECOPS-101",
        timeline_data={"external_ticket_provider": "jira"},
        updated_at=None,
    )

    class FakeDb:
        def __init__(self):
            self.commits = 0

        def commit(self):
            self.commits += 1

        def refresh(self, _obj):
            return None

    db = FakeDb()
    service._lookup_ticket = lambda *_args, **_kwargs: ticket  # type: ignore[method-assign]
    service.resolve_handoff_config = lambda *_args, **_kwargs: TicketingHandoffConfig(  # type: ignore[method-assign]
        customer_managed=True,
        provider="jira",
        url="https://jira.example.com",
        api_key="Bearer abc123",
        project="SECOPS",
    )
    service._sync_external_ticket_comment = AsyncMock(  # type: ignore[method-assign]
        return_value={"provider": "jira", "comment_id": "10001"}
    )

    updated_ticket = await service.add_comment(
        db,
        "ticket-1",
        "tenant-1",
        "Containment started",
    )

    assert service._sync_external_ticket_comment.await_count == 1
    assert db.commits >= 1
    events = (updated_ticket.timeline_data or {}).get("events") or []
    assert any(event["type"] == "comment" for event in events)
    assert any(event["type"] == "external_comment_synced" for event in events)
