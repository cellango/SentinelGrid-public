"""Contract tests for onboarding ticketing handoff validation."""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import onboarding


class _FakeResult:
    def __init__(self, row=None):
        self._row = row

    def fetchone(self):
        return self._row

    def first(self):
        return self._row


class _FakeDb:
    def __init__(self):
        self.statements = []
        self.commits = 0

    def execute(self, statement, params=None):
        self.statements.append((str(statement), params))
        return _FakeResult()

    def commit(self):
        self.commits += 1


def _build_client(fake_db):
    app = FastAPI()
    app.include_router(onboarding.router)
    app.dependency_overrides[onboarding.get_db] = lambda: fake_db
    app.dependency_overrides[onboarding.get_tenant_session] = lambda: fake_db
    app.dependency_overrides[onboarding.get_onboarding_customer_id] = lambda: "tenant-123"
    return TestClient(app)


@pytest.fixture
def valid_jira_payload():
    return {
        "provider": "jira",
        "url": "https://example.atlassian.net",
        "project": "SECOPS",
        "api_key": "Bearer jira-token",
        "issueType": "Incident",
        "assignmentMode": "named_owner",
        "defaultAssignee": "acct-123",
        "assigneeIdentifierType": "account_id",
        "autoCreateTickets": True,
        "notifySlack": True,
        "slackChannel": "#security-alerts",
        "slackWebhookUrl": "https://hooks.slack.com/services/T1/B1/C1",
        "socManaged": False,
    }


def test_connect_ticketing_rejects_invalid_provider():
    fake_db = _FakeDb()
    client = _build_client(fake_db)

    response = client.post(
        "/api/v1/onboarding/connect-ticketing",
        headers={"X-Tenant-ID": "tenant-123"},
        json={"provider": "pagerduty"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid ticketing provider"}


@pytest.mark.parametrize(
    ("field", "value", "expected_detail"),
    [
        ("url", None, "Ticketing URL is required"),
        ("project", None, "Project or assignment group is required"),
        ("api_key", None, "API token is required"),
    ],
)
def test_connect_ticketing_requires_external_provider_fields(valid_jira_payload, field, value, expected_detail):
    fake_db = _FakeDb()
    client = _build_client(fake_db)

    payload = dict(valid_jira_payload)
    payload[field] = value

    response = client.post(
        "/api/v1/onboarding/connect-ticketing",
        headers={"X-Tenant-ID": "tenant-123"},
        json=payload,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": expected_detail}


def test_connect_ticketing_requires_default_assignee_for_named_owner(valid_jira_payload):
    fake_db = _FakeDb()
    client = _build_client(fake_db)

    payload = dict(valid_jira_payload)
    payload["defaultAssignee"] = None

    response = client.post(
        "/api/v1/onboarding/connect-ticketing",
        headers={"X-Tenant-ID": "tenant-123"},
        json=payload,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Default assignee is required for named owner routing"}


def test_connect_ticketing_rejects_invalid_servicenow_named_owner_identifier():
    fake_db = _FakeDb()
    client = _build_client(fake_db)

    response = client.post(
        "/api/v1/onboarding/connect-ticketing",
        headers={"X-Tenant-ID": "tenant-123"},
        json={
            "provider": "servicenow",
            "url": "https://example.service-now.com",
            "project": "Security Operations",
            "api_key": "Bearer servicenow-token",
            "assignmentMode": "named_owner",
            "defaultAssignee": "owner@company.com",
            "assigneeIdentifierType": "email",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "ServiceNow named owners must use username or sys_id"
    }


@pytest.mark.parametrize(
    ("field", "value", "expected_detail"),
    [
        ("slackChannel", None, "Slack channel is required when Slack notifications are enabled"),
        ("slackWebhookUrl", None, "Slack webhook URL is required when Slack notifications are enabled"),
    ],
)
def test_connect_ticketing_requires_complete_slack_configuration(
    valid_jira_payload,
    field,
    value,
    expected_detail,
):
    fake_db = _FakeDb()
    client = _build_client(fake_db)

    payload = dict(valid_jira_payload)
    payload[field] = value

    response = client.post(
        "/api/v1/onboarding/connect-ticketing",
        headers={"X-Tenant-ID": "tenant-123"},
        json=payload,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": expected_detail}


def test_connect_ticketing_persists_normalized_config_and_health(monkeypatch, valid_jira_payload):
    fake_db = _FakeDb()
    client = _build_client(fake_db)

    monkeypatch.setattr(onboarding, "_resolve_progress_key", lambda customer_id, db: customer_id)
    monkeypatch.setattr(
        onboarding,
        "_probe_ticketing",
        lambda cfg: {
            "status": "healthy",
            "checked_at": "2026-03-27T14:00:00Z",
            "provider": cfg["provider"],
            "assignment_mode": cfg["assignment_mode"],
            "assignee_identifier_type": cfg["assignee_identifier_type"],
        },
    )

    response = client.post(
        "/api/v1/onboarding/connect-ticketing",
        headers={"X-Tenant-ID": "tenant-123"},
        json=valid_jira_payload,
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "status": "healthy",
        "message": "Ticketing handoff is ready.",
        "health": {
            "status": "healthy",
            "checked_at": "2026-03-27T14:00:00Z",
            "provider": "jira",
            "assignment_mode": "named_owner",
            "assignee_identifier_type": "account_id",
        },
    }
    assert fake_db.commits == 1

    insert_sql, insert_params = fake_db.statements[0]
    assert "INSERT INTO onboarding_progress" in insert_sql
    assert insert_params["provider"] == "jira"
    assert insert_params["soc_managed"] is False

    saved_config = json.loads(insert_params["config"])
    saved_health = json.loads(insert_params["health"])

    assert saved_config["provider"] == "jira"
    assert saved_config["assignment_mode"] == "named_owner"
    assert saved_config["assignee_identifier_type"] == "account_id"
    assert saved_config["default_assignee"] == "acct-123"
    assert saved_health["status"] == "healthy"
    assert insert_params["step_ticketing_completed"] is True


def test_connect_ticketing_keeps_step_incomplete_when_health_is_degraded(monkeypatch, valid_jira_payload):
    fake_db = _FakeDb()
    client = _build_client(fake_db)

    monkeypatch.setattr(onboarding, "_resolve_progress_key", lambda customer_id, db: customer_id)
    monkeypatch.setattr(
        onboarding,
        "_probe_ticketing",
        lambda cfg: {
            "status": "degraded",
            "checked_at": "2026-03-27T14:10:00Z",
            "provider": cfg["provider"],
            "warnings": ["Named owner routing requires a default assignee."],
        },
    )

    response = client.post(
        "/api/v1/onboarding/connect-ticketing",
        headers={"X-Tenant-ID": "tenant-123"},
        json=valid_jira_payload,
    )

    assert response.status_code == 200
    assert response.json()["success"] is False
    assert response.json()["status"] == "degraded"
    assert "needs attention" in response.json()["message"].lower()

    _, insert_params = fake_db.statements[0]
    assert insert_params["step_ticketing_completed"] is False
