from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.request_identity import require_gateway_identity
from sg_core.db import get_tenant_session
from sg_core.models import Incident, Ticket
from sg_core.security import get_current_tenant


@pytest.fixture
def incident_client(mock_db_session):
    tenant_id = str(uuid4())

    def _get_db():
        yield mock_db_session

    def _get_tenant():
        return tenant_id

    app.dependency_overrides[get_tenant_session] = _get_db
    app.dependency_overrides[get_current_tenant] = _get_tenant
    # Route-unit fixture; real gateway admission has its own no-override suite.
    app.dependency_overrides[require_gateway_identity] = lambda: None

    with TestClient(app) as client:
        yield client, mock_db_session, tenant_id

    app.dependency_overrides.clear()


def test_patch_incident_updates_workflow_fields_and_audit(incident_client):
    client, mock_db_session, tenant_id = incident_client
    tenant_uuid = UUID(tenant_id)
    incident = Incident(
        id=uuid4(),
        tenant_id=tenant_uuid,
        source="detection_service",
        title="Credential misuse",
        status="open",
        severity="high",
        raw_payload={
            "description": "Initial description",
            "phase": "New",
            "assigned_to": "analyst-1",
            "audit": [],
        },
    )

    mock_db_session.query.return_value.filter.return_value.first.return_value = incident

    response = client.patch(
        f"/api/v1/incidents/{incident.id}",
        json={
            "status": "resolved",
            "phase": "Closed",
            "assigned_to": "analyst-2",
            "due_date": "2026-03-27T12:00:00+00:00",
            "description": "Updated response summary",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resolved"
    assert data["phase"] == "Closed"
    assert data["assigned_to"] == "analyst-2"
    assert data["due_date"] == "2026-03-27T12:00:00+00:00"
    assert data["description"] == "Updated response summary"
    timeline_text = [entry["text"] for entry in data["timeline"]]
    assert "Status changed to resolved" in timeline_text
    assert "Phase changed to Closed" in timeline_text
    assert "Assigned to analyst-2" in timeline_text
    assert "SLA target set to 2026-03-27T12:00:00+00:00" in timeline_text
    assert "Description updated" in timeline_text
    assert incident.raw_payload["assigned_to"] == "analyst-2"
    assert incident.raw_payload["phase"] == "Closed"
    assert incident.raw_payload["due_date"] == "2026-03-27T12:00:00+00:00"
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(incident)


def test_patch_incident_adds_timeline_event_to_audit(incident_client):
    client, mock_db_session, tenant_id = incident_client
    tenant_uuid = UUID(tenant_id)
    incident = Incident(
        id=uuid4(),
        tenant_id=tenant_uuid,
        source="detection_service",
        title="Credential misuse",
        status="open",
        severity="high",
        raw_payload={"audit": []},
    )

    mock_db_session.query.return_value.filter.return_value.first.return_value = incident

    response = client.patch(
        f"/api/v1/incidents/{incident.id}",
        json={"timeline_event": "SOC AI timeline: analyst confirmed suspicious session escalation."},
    )

    assert response.status_code == 200
    timeline_text = [entry["text"] for entry in response.json()["timeline"]]
    assert "SOC AI timeline: analyst confirmed suspicious session escalation." in timeline_text
    assert incident.raw_payload["audit"][-1]["metadata"]["source"] == "soc_ai_timeline_draft"


def test_incident_audit_includes_linked_ticket_timeline(incident_client):
    client, mock_db_session, tenant_id = incident_client
    tenant_uuid = UUID(tenant_id)
    incident = Incident(
        id=uuid4(),
        tenant_id=tenant_uuid,
        source="detection_service",
        title="Privilege escalation",
        status="open",
        severity="critical",
        raw_payload={
            "audit": [
                {
                    "ts": "2026-03-26T10:00:00Z",
                    "text": "Incident created from alert",
                    "actor": "system",
                }
            ]
        },
    )
    incident.ticket = Ticket(
        id=uuid4(),
        tenant_id=tenant_uuid,
        title="Linked case",
        status="in_progress",
        source="jira",
        timeline_data={
            "events": [
                {
                    "ts": "2026-03-26T10:05:00Z",
                    "title": "Linked ticket status updated",
                    "actor": "system",
                }
            ]
        },
    )

    mock_db_session.query.return_value.filter.return_value.first.return_value = incident
    mock_db_session.execute.return_value.fetchall.return_value = []

    response = client.get(f"/api/v1/audit/incidents/{incident.id}")

    assert response.status_code == 200
    items = response.json()["items"]
    texts = [item["text"] for item in items]
    assert "Incident created from alert" in texts
    assert "Linked ticket status updated" in texts


def test_patch_incident_syncs_linked_ticket_update(incident_client, mocker):
    client, mock_db_session, tenant_id = incident_client
    tenant_uuid = UUID(tenant_id)
    ticket_id = uuid4()
    incident = Incident(
        id=uuid4(),
        tenant_id=tenant_uuid,
        source="detection_service",
        title="Cloud admin change",
        status="open",
        severity="high",
        ticket_id=ticket_id,
        raw_payload={"audit": []},
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = incident
    sync_mock = mocker.patch("app.api.routes_incidents._sync_linked_ticket_update", return_value={})
    refresh_mock = mocker.patch("app.api.routes_incidents._submit_soc_case_refresh", return_value={})

    response = client.patch(
        f"/api/v1/incidents/{incident.id}",
        json={"status": "resolved", "assigned_to": "secops-owner"},
    )

    assert response.status_code == 200
    sync_mock.assert_called_once_with(
        ticket_id,
        tenant_id,
        {"status": "resolved", "assigned_to": "secops-owner"},
    )
    refresh_mock.assert_called_once_with(
        incident,
        tenant_id,
        ["assigned_to", "status"],
        "Incident fields were updated by an operator workflow.",
    )


def test_patch_incident_records_ticket_sync_failure_and_returns_success(incident_client, mocker):
    client, mock_db_session, tenant_id = incident_client
    tenant_uuid = UUID(tenant_id)
    incident = Incident(
        id=uuid4(),
        tenant_id=tenant_uuid,
        source="detection_service",
        title="Identity lockout",
        status="open",
        severity="medium",
        ticket_id=uuid4(),
        raw_payload={"audit": []},
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = incident
    mocker.patch(
        "app.api.routes_incidents._sync_linked_ticket_update",
        side_effect=RuntimeError("ticketing unavailable"),
    )

    response = client.patch(
        f"/api/v1/incidents/{incident.id}",
        json={"status": "resolved"},
    )

    assert response.status_code == 200
    timeline_text = [entry["text"] for entry in response.json()["timeline"]]
    assert "Linked ticket update failed" in timeline_text


def test_patch_incident_syncs_linked_ticket_comment(incident_client, mocker):
    client, mock_db_session, tenant_id = incident_client
    tenant_uuid = UUID(tenant_id)
    ticket_id = uuid4()
    incident = Incident(
        id=uuid4(),
        tenant_id=tenant_uuid,
        source="detection_service",
        title="Malicious OAuth grant",
        status="open",
        severity="high",
        ticket_id=ticket_id,
        raw_payload={"audit": [], "comments": []},
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = incident
    comment_mock = mocker.patch("app.api.routes_incidents._add_linked_ticket_comment", return_value={})

    response = client.patch(
        f"/api/v1/incidents/{incident.id}",
        json={"comment": "Escalated to customer on-call."},
    )

    assert response.status_code == 200
    comment_mock.assert_called_once_with(ticket_id, tenant_id, "Escalated to customer on-call.")
    texts = [entry["text"] for entry in response.json()["timeline"]]
    assert "Escalated to customer on-call." in texts


def test_patch_incident_ignores_spoofed_tenant_header(incident_client, mocker):
    client, mock_db_session, tenant_id = incident_client
    tenant_uuid = UUID(tenant_id)
    ticket_id = uuid4()
    incident = Incident(
        id=uuid4(),
        tenant_id=tenant_uuid,
        source="detection_service",
        title="Tenant boundary check",
        status="open",
        severity="medium",
        ticket_id=ticket_id,
        raw_payload={"audit": []},
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = incident
    sync_mock = mocker.patch("app.api.routes_incidents._sync_linked_ticket_update", return_value={})

    response = client.patch(
        f"/api/v1/incidents/{incident.id}",
        json={"status": "resolved"},
        headers={"x-tenant-id": str(uuid4())},
    )

    assert response.status_code == 200
    sync_mock.assert_called_once_with(ticket_id, tenant_id, {"status": "resolved"})


def test_get_incident_includes_story_context(incident_client):
    client, mock_db_session, tenant_id = incident_client
    tenant_uuid = UUID(tenant_id)
    incident = Incident(
        id=uuid4(),
        tenant_id=tenant_uuid,
        source="detection_service",
        title="Prompt injection investigation",
        status="open",
        severity="high",
        ticket_id=uuid4(),
        external_ticket_id="INC0012345",
        external_ticket_provider="servicenow",
        raw_payload={
            "description": "Blocked prompt injection attempt",
            "asset_id": "agent-1",
            "user_identifier": "analyst@example.com",
            "phase": "Analyzing",
            "related_alert_ids": ["alert-123"],
            "detection_rule_id": "SG-AI-001",
            "playbook_id": "AI-PROMPT-INJECTION",
            "ai": {
                "app_id": "research-assist",
                "provider": "anthropic",
                "model": "claude-3",
                "user_id": "analyst@example.com",
            },
        },
    )

    mock_db_session.query.return_value.filter.return_value.first.return_value = incident

    response = client.get(f"/api/v1/incidents/{incident.id}")

    assert response.status_code == 200
    data = response.json()
    assert {entity["type"] for entity in data["entities"]} >= {"identity", "device", "ai_app"}
    assert any(item["type"] == "alert" and item["id"] == "alert-123" for item in data["evidence"])
    assert any(item["type"] == "detection_rule" and item["id"] == "SG-AI-001" for item in data["evidence"])
    assert any(item["type"] == "playbook" and item["id"] == "AI-PROMPT-INJECTION" for item in data["evidence"])
    assert any(item["type"] == "ticket" for item in data["evidence"])
    assert "ai" in data["story_domains"]
    assert data["story_summary"]["headline"] == "AI + Endpoint + Identity story"
    assert data["story_summary"]["evidence_count"] >= 4
    assert data["story_summary"]["primary_entity"]["label"] == "analyst@example.com"


def test_open_incidents_with_actions_includes_story_summary(incident_client):
    client, mock_db_session, tenant_id = incident_client
    tenant_uuid = UUID(tenant_id)
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
            "audit": [],
        },
    )

    mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [incident]

    response = client.get("/api/v1/incidents/open-with-actions")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["affected_count"] == 2
    assert item["story_summary"]["primary_entity"]["label"] == "owner@example.com"
    assert "identity" in item["story_domains"]
    assert "endpoint" in item["story_domains"]


def test_get_incident_soc_case_proxies_runtime_state(incident_client, mocker):
    client, mock_db_session, tenant_id = incident_client
    tenant_uuid = UUID(tenant_id)
    incident = Incident(
        id=uuid4(),
        tenant_id=tenant_uuid,
        source="detection_service",
        title="SOC case state check",
        status="open",
        severity="high",
        raw_payload={"audit": []},
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = incident
    fetch_mock = mocker.patch(
        "app.api.routes_incidents._fetch_soc_case_state",
        return_value={
            "incident_id": str(incident.id),
            "tenant_id": tenant_id,
            "latest_recommendation": {
                "response_pack_id": "account_takeover",
                "response_pack_label": "Account takeover containment",
            },
            "recent_tasks": [],
        },
    )

    response = client.get(f"/api/v1/incidents/{incident.id}/soc-case")

    assert response.status_code == 200
    assert response.json()["latest_recommendation"]["response_pack_id"] == "account_takeover"
    fetch_mock.assert_called_once_with(incident.id, tenant_id)


def test_post_incident_soc_case_feedback_proxies_runtime_update(incident_client, mocker):
    client, mock_db_session, tenant_id = incident_client
    tenant_uuid = UUID(tenant_id)
    incident = Incident(
        id=uuid4(),
        tenant_id=tenant_uuid,
        source="detection_service",
        title="SOC case feedback check",
        status="open",
        severity="high",
        raw_payload={"audit": []},
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = incident
    feedback_mock = mocker.patch(
        "app.api.routes_incidents._submit_soc_case_feedback",
        return_value={
            "incident_id": str(incident.id),
            "tenant_id": tenant_id,
            "latest_recommendation": {
                "recommendation_id": "rec-1",
                "recommended_actions": [
                    {"action_id": "action-1", "status": "accepted"},
                ],
                "recommended_playbooks": [
                    {"playbook_id": "playbook-1", "status": "accepted"},
                ],
            },
            "recent_tasks": [],
        },
    )

    response = client.post(
        f"/api/v1/incidents/{incident.id}/soc-case/feedback",
        json={
            "recommendation_id": "rec-1",
            "feedback_type": "accepted_recommendation",
            "actor_id": "analyst@example.com",
            "actor_role": "HUMAN_OWNER",
            "accepted": True,
            "action_id": "action-1",
            "playbook_id": "playbook-1",
        },
    )

    assert response.status_code == 200
    assert response.json()["latest_recommendation"]["recommended_actions"][0]["status"] == "accepted"
    feedback_mock.assert_called_once()
    proxied_payload = feedback_mock.call_args.args[2]
    assert proxied_payload.recommendation_id == "rec-1"
    assert proxied_payload.action_id == "action-1"
