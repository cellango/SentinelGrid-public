"""Focused tenant-session coverage for ticketing service routes."""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import tickets as tickets_api
from app.main import app
from app.services import tenant_context


TENANT_ID = UUID("00000000-0000-0000-0000-000000000111")


class FakeDB:
    """Minimal DB stub for tenant-session route tests."""


def _make_ticket(ticket_id: UUID | None = None, *, title: str = "Suspicious Login"):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=ticket_id or uuid4(),
        tenant_id=TENANT_ID,
        title=title,
        description="Multiple failed logins from a new location",
        status="open",
        severity="high",
        priority="P2",
        category="identity",
        assigned_to="secops-oncall",
        due_date="2026-03-30T12:00:00+00:00",
        source="internal",
        external_id="SG-123",
        created_at=now,
        updated_at=now,
        iam_data={"actors": ["user@example.com"]},
        vm_data={"fix_group_id": "fg-1"},
        cmdb_data={"asset_id": "asset-1"},
        network_data={"src_ip": "10.0.0.5"},
        timeline_data={"events": ["created"]},
        external_vendor_id=None,
    )


@pytest.fixture
def tenant_scoped_client(monkeypatch):
    """Create a client that forces ticket routes through get_tenant_session."""
    fake_db = FakeDB()
    base_ticket = _make_ticket()
    observed = {}

    def override_get_current_tenant():
        return TENANT_ID

    def unexpected_get_db():
        raise AssertionError("Ticket route used get_db instead of get_tenant_session")
        yield  # pragma: no cover

    def override_get_tenant_session():
        yield fake_db

    def resolve_handoff_config(db, tenant_uuid, ticket_data):
        assert db is fake_db
        observed["resolved_tenant"] = tenant_uuid
        observed["resolved_ticket_data"] = dict(ticket_data)
        return SimpleNamespace(customer_managed=False)

    async def create_ticket(db, tenant_uuid, ticket_data, handoff_config=None):
        assert db is fake_db
        assert tenant_uuid == TENANT_ID
        assert handoff_config.customer_managed is False
        observed["created_ticket_data"] = dict(ticket_data)
        return base_ticket

    def get_ticket(db, ticket_id, tenant_uuid):
        assert db is fake_db
        assert tenant_uuid == TENANT_ID
        observed.setdefault("ticket_lookups", []).append(str(ticket_id))
        return base_ticket

    async def update_ticket(db, ticket_id, tenant_uuid, ticket_data):
        assert db is fake_db
        assert tenant_uuid == TENANT_ID
        observed["updated_ticket_id"] = str(ticket_id)
        observed["updated_payload"] = dict(ticket_data)
        return _make_ticket(base_ticket.id, title=ticket_data.get("title", base_ticket.title))

    async def add_comment(db, ticket_id, tenant_uuid, comment):
        assert db is fake_db
        assert tenant_uuid == TENANT_ID
        observed["comment_ticket_id"] = str(ticket_id)
        observed["comment_text"] = comment
        ticket = _make_ticket(base_ticket.id)
        ticket.timeline_data = {"events": ["created"], "latest_comment": comment}
        return ticket

    def search_tickets(db, tenant_id, status=None, severity=None, category=None, limit=50, offset=0):
        assert db is fake_db
        assert tenant_id == TENANT_ID
        observed["search"] = {
            "status": status,
            "severity": severity,
            "category": category,
            "limit": limit,
            "offset": offset,
        }
        return [base_ticket]

    app.dependency_overrides[tickets_api.get_current_tenant] = override_get_current_tenant
    app.dependency_overrides[tickets_api.get_db] = unexpected_get_db
    app.dependency_overrides[tickets_api.get_tenant_session] = override_get_tenant_session

    monkeypatch.setattr(tenant_context, "get_tenant_slug_for_id", lambda db, tenant_uuid: "acme")
    monkeypatch.setattr(tickets_api.ticket_service, "resolve_handoff_config", resolve_handoff_config)
    monkeypatch.setattr(tickets_api.ticket_service, "create_ticket", create_ticket)
    monkeypatch.setattr(tickets_api.ticket_service, "get_ticket", get_ticket)
    monkeypatch.setattr(tickets_api.ticket_service, "update_ticket", update_ticket)
    monkeypatch.setattr(tickets_api.ticket_service, "add_comment", add_comment)
    monkeypatch.setattr(tickets_api.ticket_service, "search_tickets", search_tickets)
    monkeypatch.setattr(tickets_api.thehive_integration, "base_url", None)
    monkeypatch.setattr(tickets_api, "_find_linked_incident_id", lambda db, tenant_id, ticket_id: "inc-123")
    monkeypatch.setattr(
        tickets_api,
        "_submit_soc_case_refresh",
        lambda tenant_id, incident_id, source_event_id, changed_fields, reason: observed.setdefault(
            "soc_refresh_calls",
            [],
        ).append(
            {
                "tenant_id": str(tenant_id),
                "incident_id": incident_id,
                "source_event_id": source_event_id,
                "changed_fields": list(changed_fields),
                "reason": reason,
            }
        ),
    )

    try:
        with TestClient(app) as test_client:
            yield test_client, observed, base_ticket
    finally:
        app.dependency_overrides.clear()


def test_ticket_routes_use_tenant_session(tenant_scoped_client):
    """Ticket CRUD and tab routes should never fall back to plain get_db."""
    test_client, observed, ticket = tenant_scoped_client

    create_response = test_client.post(
        "/api/v1/tickets",
        json={
            "title": ticket.title,
            "description": ticket.description,
            "severity": ticket.severity,
            "priority": ticket.priority,
        },
    )
    assert create_response.status_code == 200
    assert create_response.json()["tenant_id"] == str(TENANT_ID)
    assert observed["resolved_tenant"] == TENANT_ID
    assert observed["created_ticket_data"]["tenant_slug"] == "acme"

    get_response = test_client.get(f"/api/v1/tickets/{ticket.id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == str(ticket.id)

    update_response = test_client.put(
        f"/api/v1/tickets/{ticket.id}",
        json={"title": "Updated Ticket"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated Ticket"
    assert observed["updated_ticket_id"] == str(ticket.id)
    assert observed["soc_refresh_calls"][0] == {
        "tenant_id": str(TENANT_ID),
        "incident_id": "inc-123",
        "source_event_id": str(ticket.id),
        "changed_fields": ["title"],
        "reason": "Ticket fields were updated for a linked incident.",
    }

    comment_response = test_client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={"comment": "Investigating"},
    )
    assert comment_response.status_code == 200
    assert comment_response.json()["id"] == str(ticket.id)
    assert observed["comment_ticket_id"] == str(ticket.id)
    assert observed["soc_refresh_calls"][1] == {
        "tenant_id": str(TENANT_ID),
        "incident_id": "inc-123",
        "source_event_id": str(ticket.id),
        "changed_fields": ["comment"],
        "reason": "A linked ticket comment was added by an operator.",
    }

    search_response = test_client.get(
        "/api/v1/tickets",
        params={
            "status": "open",
            "severity": "high",
            "category": "identity",
            "limit": 10,
            "offset": 5,
        },
    )
    assert search_response.status_code == 200
    assert [item["id"] for item in search_response.json()] == [str(ticket.id)]
    assert observed["search"] == {
        "status": "open",
        "severity": "high",
        "category": "identity",
        "limit": 10,
        "offset": 5,
    }

    tab_response = test_client.get(f"/api/v1/tickets/{ticket.id}/tabs/timeline")
    assert tab_response.status_code == 200
    assert tab_response.json() == {
        "tab": "timeline",
        "data": {"events": ["created"]},
    }
