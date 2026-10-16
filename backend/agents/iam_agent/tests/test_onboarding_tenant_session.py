"""Focused tenant-session proofs for onboarding route families."""

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import onboarding


class _FakeResult:
    def __init__(self, row=None):
        self._row = row

    def mappings(self):
        return self

    def fetchone(self):
        return self._row

    def first(self):
        return self._row


class _FakeDb:
    def __init__(self):
        self.statements = []
        self.commits = 0

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql, params))

        if "FROM onboarding_progress" in sql and "SELECT" in sql:
            return _FakeResult(
                {
                    "step_idp_completed": False,
                    "step_cloud_completed": False,
                    "step_endpoint_completed": False,
                    "step_git_completed": False,
                    "onboarding_completed": False,
                    "step_appsec_completed": False,
                    "step_ai_completed": False,
                    "step_ticketing_completed": False,
                    "services_selected": {},
                    "appsec_health": None,
                    "ai_health": None,
                    "ticketing_health": None,
                    "cloud_health": None,
                }
            )
        if "FROM tenants t" in sql and "JOIN organizations o" in sql:
            return _FakeResult(("demo",))
        return _FakeResult()

    def commit(self):
        self.commits += 1

    def rollback(self):
        return None


def _build_client(fake_db):
    app = FastAPI()
    app.include_router(onboarding.router)
    app.include_router(onboarding.portal_router)
    app.dependency_overrides[onboarding.get_tenant_session] = lambda: fake_db
    app.dependency_overrides[onboarding.get_onboarding_customer_id] = lambda: "tenant-123"
    return TestClient(app)


def test_onboarding_status_uses_tenant_session_override(monkeypatch):
    fake_db = _FakeDb()
    client = _build_client(fake_db)

    monkeypatch.setattr(onboarding, "_resolve_progress_key", lambda customer_id, db: customer_id)
    monkeypatch.setattr(onboarding, "_infer_existing_connections", lambda db, progress_id: {"idp": False, "cloud": False, "git": False})
    monkeypatch.setattr(onboarding, "_load_latest_idp_provider", lambda progress_id, db: None)
    monkeypatch.setattr(onboarding, "_get_primary_tenant_id", lambda customer_id, db: "tenant-123")
    monkeypatch.setattr(
        onboarding,
        "_get_endpoint_agent_health",
        lambda customer_id, db: {
            "status": "pending",
            "checked_at": "2026-03-29T00:00:00Z",
            "message": "No endpoint agent is registered for this tenant yet. Deploy the agent and re-run validation.",
        },
    )

    response = client.get("/api/v1/onboarding/status", headers={"X-Tenant-ID": "tenant-123"})

    assert response.status_code == 200
    assert any("FROM onboarding_progress" in sql for sql, _ in fake_db.statements)


def test_save_trust_profile_uses_tenant_session_override(monkeypatch):
    fake_db = _FakeDb()
    client = _build_client(fake_db)

    monkeypatch.setattr(onboarding, "_resolve_progress_key", lambda customer_id, db: customer_id)

    response = client.post(
        "/api/v1/onboarding/trust-profile",
        headers={"X-Tenant-ID": "tenant-123"},
        json={
            "enabled": True,
            "frameworks": ["soc2"],
            "primaryDriver": "customer_security_review",
            "targetTimeline": "90_days",
            "needsQuestionnaireSupport": False,
            "needsEvidenceExports": True,
        },
    )

    assert response.status_code == 200
    assert fake_db.commits == 1
    _, params = fake_db.statements[0]
    saved = json.loads(params["services_selected"])
    assert saved["trustProfile"]["enabled"] is True


def test_portal_artifact_access_uses_tenant_session_override():
    fake_db = _FakeDb()
    client = _build_client(fake_db)

    response = client.get("/api/iam-portal/onboarding/artifacts", headers={"X-Tenant-ID": "tenant-123"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant_namespace"] == onboarding._tenant_namespace_from_slug("demo")
    assert any("FROM tenants t" in sql for sql, _ in fake_db.statements)


def test_connect_ai_marks_step_complete_only_when_health_is_healthy(monkeypatch):
    fake_db = _FakeDb()
    client = _build_client(fake_db)

    monkeypatch.setattr(onboarding, "_resolve_progress_key", lambda customer_id, db: customer_id)
    monkeypatch.setattr(
        onboarding,
        "_probe_ai",
        lambda cfg: {
            "status": "healthy",
            "checked_at": "2026-04-15T12:00:00Z",
            "message": "AI gateway healthy",
        },
    )

    response = client.post(
        "/api/v1/onboarding/connect-ai",
        headers={"X-Tenant-ID": "tenant-123"},
        json={
            "mode": "hosted",
            "endpoint_url": "https://ai-shield.example.com",
            "api_key": "secret-token",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["status"] == "healthy"

    _, params = fake_db.statements[0]
    assert params["step_ai_completed"] is True


def test_connect_ai_keeps_step_incomplete_when_health_is_degraded(monkeypatch):
    fake_db = _FakeDb()
    client = _build_client(fake_db)

    monkeypatch.setattr(onboarding, "_resolve_progress_key", lambda customer_id, db: customer_id)
    monkeypatch.setattr(
        onboarding,
        "_probe_ai",
        lambda cfg: {
            "status": "degraded",
            "checked_at": "2026-04-15T12:05:00Z",
            "message": "Hosted gateway token is invalid",
        },
    )

    response = client.post(
        "/api/v1/onboarding/connect-ai",
        headers={"X-Tenant-ID": "tenant-123"},
        json={
            "mode": "hosted",
            "endpoint_url": "https://ai-shield.example.com",
            "api_key": "bad-token",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["status"] == "degraded"
    assert "saved" in payload["message"].lower()

    _, params = fake_db.statements[0]
    assert params["step_ai_completed"] is False


def test_connect_appsec_marks_step_complete_only_when_health_is_healthy(monkeypatch):
    fake_db = _FakeDb()
    client = _build_client(fake_db)

    monkeypatch.setattr(onboarding, "_resolve_progress_key", lambda customer_id, db: customer_id)
    monkeypatch.setattr(
        onboarding,
        "_probe_appsec",
        lambda cfg: {
            "status": "healthy",
            "checked_at": "2026-04-18T14:00:00Z",
            "message": "AppSec gateway healthy",
        },
    )

    response = client.post(
        "/api/v1/onboarding/connect-appsec",
        headers={"X-Tenant-ID": "tenant-123"},
        json={
            "gateway_url": "https://appsec.example.com",
            "api_key": "secret-token",
            "app_id": "customer-portal",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["status"] == "healthy"

    _, params = fake_db.statements[0]
    assert params["step_appsec_completed"] is True


def test_connect_appsec_keeps_step_incomplete_when_health_is_degraded(monkeypatch):
    fake_db = _FakeDb()
    client = _build_client(fake_db)

    monkeypatch.setattr(onboarding, "_resolve_progress_key", lambda customer_id, db: customer_id)
    monkeypatch.setattr(
        onboarding,
        "_probe_appsec",
        lambda cfg: {
            "status": "degraded",
            "checked_at": "2026-04-18T14:05:00Z",
            "message": "Gateway token is invalid",
        },
    )

    response = client.post(
        "/api/v1/onboarding/connect-appsec",
        headers={"X-Tenant-ID": "tenant-123"},
        json={
            "gateway_url": "https://appsec.example.com",
            "api_key": "bad-token",
            "app_id": "customer-portal",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["status"] == "degraded"
    assert "saved" in payload["message"].lower()

    _, params = fake_db.statements[0]
    assert params["step_appsec_completed"] is False
