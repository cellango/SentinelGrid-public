"""Contract tests for canonical onboarding status and health rechecks."""

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.api import onboarding


class _FakeResult:
    def __init__(self, row=None):
        self._row = row

    def mappings(self):
        return self

    def fetchone(self):
        return self._row

    def scalar(self):
        if isinstance(self._row, tuple):
            return self._row[0]
        return self._row


class _StatusDb:
    def __init__(self, progress_row, access_profile_ready=False, birthright_ready=False):
        self.progress_row = progress_row
        self.access_profile_ready = access_profile_ready
        self.birthright_ready = birthright_ready
        self.statements = []
        self.commits = 0
        self.rollbacks = 0

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql, params))

        if "FROM onboarding_progress" in sql and "SELECT" in sql:
            return _FakeResult(self.progress_row)
        if "FROM customer_git_providers" in sql and "SELECT metadata" in sql:
            return _FakeResult(None)
        if "FROM access_profiles" in sql:
            return _FakeResult((self.access_profile_ready,))
        if "FROM birthright_rules" in sql:
            return _FakeResult((self.birthright_ready,))
        return _FakeResult()

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class _RecheckDb:
    def __init__(self, progress_row, cloud_row=None):
        self.progress_row = progress_row
        self.cloud_row = cloud_row
        self.statements = []
        self.commits = 0

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql, params))

        if "FROM onboarding_progress" in sql and "SELECT appsec_config" in sql:
            return _FakeResult(self.progress_row)
        if "FROM customer_cloud_accounts" in sql:
            return _FakeResult(self.cloud_row)
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


def test_get_onboarding_status_returns_canonical_progress_shape(monkeypatch):
    fake_db = _StatusDb(
        progress_row={
            "step_idp_completed": True,
            "step_cloud_completed": False,
            "step_endpoint_completed": False,
            "step_git_completed": True,
            "onboarding_completed": False,
            "step_appsec_completed": True,
            "step_ai_completed": False,
            "step_ticketing_completed": False,
            "services_selected": {
                "cloud": True,
                "git": True,
                "appsec": True,
                "aiShield": "hosted",
                "socManaged": False,
                "idpProvider": "google",
            },
            "appsec_health": {"status": "healthy", "checked_at": "2026-03-27T12:00:00Z"},
            "ai_health": {"status": "degraded", "checked_at": "2026-03-27T12:05:00Z"},
            "ticketing_health": {
                "status": "degraded",
                "checked_at": "2026-03-27T12:10:00Z",
                "warnings": ["Named owner routing requires a default assignee."],
            },
            "cloud_health": {"success": False, "checked_at": "2026-03-27T12:15:00Z"},
        },
        access_profile_ready=False,
        birthright_ready=True,
    )
    client = _build_client(fake_db)

    monkeypatch.setattr(onboarding, "_resolve_progress_key", lambda customer_id, db: customer_id)
    monkeypatch.setattr(
        onboarding,
        "_infer_existing_connections",
        lambda db, progress_id: {"idp": False, "cloud": False, "git": False},
    )
    monkeypatch.setattr(onboarding, "_load_latest_idp_provider", lambda progress_id, db: "google_workspace")
    monkeypatch.setattr(onboarding, "_get_primary_tenant_id", lambda customer_id, db: "tenant-123")
    monkeypatch.setattr(
        onboarding,
        "_get_endpoint_agent_health",
        lambda customer_id, db: {
            "status": "healthy",
            "checked_at": "2026-03-27T12:20:00Z",
            "message": "Endpoint agent is registered and reporting for this tenant.",
        },
    )

    response = client.get(
        "/api/v1/onboarding/status",
        headers={"X-Tenant-ID": "tenant-123"},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["idp_connected"] is True
    assert payload["idp_provider"] == "google_workspace"
    assert payload["cloud_connected"] is False
    assert payload["endpoint_deployed"] is True
    assert payload["git_connected"] is True
    assert payload["appsec_connected"] is True
    assert payload["ai_connected"] is False
    assert payload["ticketing_connected"] is False
    assert payload["next_step"] == "cloud"
    assert payload["last_incomplete_step_id"] == "cloud"
    assert payload["progress_percentage"] == 57
    assert payload["overall_complete"] is False
    assert payload["access_profile_ready"] is False
    assert payload["birthright_ready"] is True
    assert payload["status_version"]
    assert len(payload["status_version"]) == 12
    assert payload["services_selected"]["idpProvider"] == "google_workspace"
    assert [step["id"] for step in payload["steps"]] == [
        "idp",
        "cloud",
        "endpoint",
        "git",
        "appsec",
        "ai",
        "ticketing",
    ]
    assert payload["steps"][2]["health"]["status"] == "healthy"
    assert payload["announcements"][0]["id"] == "people-access-readiness"
    assert fake_db.rollbacks == 1


def test_get_onboarding_status_does_not_trust_stale_endpoint_completion_without_registered_agent(monkeypatch):
    fake_db = _StatusDb(
        progress_row={
            "step_idp_completed": True,
            "step_cloud_completed": True,
            "step_endpoint_completed": True,
            "step_git_completed": True,
            "onboarding_completed": False,
            "step_appsec_completed": False,
            "step_ai_completed": False,
            "step_ticketing_completed": False,
            "services_selected": {
                "cloud": True,
                "git": True,
                "socManaged": True,
            },
            "appsec_health": None,
            "ai_health": None,
            "ticketing_health": None,
            "cloud_health": {"success": True, "checked_at": "2026-03-27T12:15:00Z"},
        },
        access_profile_ready=False,
        birthright_ready=False,
    )
    client = _build_client(fake_db)

    monkeypatch.setattr(onboarding, "_resolve_progress_key", lambda customer_id, db: customer_id)
    monkeypatch.setattr(
        onboarding,
        "_infer_existing_connections",
        lambda db, progress_id: {"idp": False, "cloud": False, "git": False},
    )
    monkeypatch.setattr(onboarding, "_load_latest_idp_provider", lambda progress_id, db: "sentinelgrid")
    monkeypatch.setattr(onboarding, "_get_primary_tenant_id", lambda customer_id, db: "tenant-123")
    monkeypatch.setattr(
        onboarding,
        "_get_endpoint_agent_health",
        lambda customer_id, db: {
            "status": "pending",
            "checked_at": "2026-03-27T12:20:00Z",
            "message": "No endpoint agent is registered for this tenant yet. Deploy the agent and re-run validation.",
        },
    )

    response = client.get(
        "/api/v1/onboarding/status",
        headers={"X-Tenant-ID": "tenant-123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["endpoint_deployed"] is False
    assert payload["steps"][2]["done"] is False
    assert payload["steps"][2]["health"]["status"] == "pending"
    assert payload["next_step"] == "endpoint"


@pytest.mark.parametrize(
    ("target", "probe_attr", "expected_health"),
    [
        (
            "appsec",
            "_probe_appsec",
            {
                "status": "healthy",
                "checked_at": "2026-03-27T13:00:00Z",
                "message": "AppSec gateway responded",
                "details": {"url": "https://appsec.example.com"},
            },
        ),
        (
            "ai",
            "_probe_ai",
            {
                "status": "degraded",
                "checked_at": "2026-03-27T13:05:00Z",
                "message": "Gateway needs API key rotation",
                "warnings": ["Rotate the hosted gateway token."],
            },
        ),
        (
            "ticketing",
            "_probe_ticketing",
            {
                "status": "degraded",
                "checked_at": "2026-03-27T13:10:00Z",
                "provider": "jira",
                "warnings": ["Named owner routing requires a default assignee."],
            },
        ),
    ],
)
def test_recheck_health_preserves_structured_ui_payloads(monkeypatch, target, probe_attr, expected_health):
    fake_db = _RecheckDb(
        progress_row=(
            {"gateway_url": "https://appsec.example.com"},
            {"status": "unknown"},
            {"mode": "hosted"},
            {"status": "unknown"},
            {"provider": "jira", "url": "https://example.atlassian.net"},
            {"status": "unknown"},
            False,
            True,
        )
    )
    client = _build_client(fake_db)

    monkeypatch.setattr(onboarding, "_resolve_progress_key", lambda customer_id, db: customer_id)
    monkeypatch.setattr(onboarding, probe_attr, lambda cfg: expected_health)

    response = client.post(
        "/api/v1/onboarding/recheck-health",
        headers={"X-Tenant-ID": "tenant-123"},
        json={"target": target},
    )

    assert response.status_code == 200
    assert response.json() == {"success": True, "health": expected_health}
    assert fake_db.commits == 1


def test_recheck_health_preserves_structured_cloud_payload(monkeypatch):
    fake_db = _RecheckDb(
        progress_row=(
            {},
            {},
            {},
            {},
            {},
            {},
            False,
            True,
        ),
        cloud_row=(
            "arn:aws:iam::123456789012:role/SentinelGridMonitor",
            "ext-123",
            {
                "additional_log_group_arns": ["arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/main"],
                "additional_s3_log_bucket_arns": ["arn:aws:s3:::security-bucket"],
            },
        ),
    )
    client = _build_client(fake_db)

    class _FakeAwsTester:
        def test_log_access(self, **kwargs):
            assert kwargs["role_arn"].endswith("SentinelGridMonitor")
            return {
                "success": True,
                "checked_at": "2026-03-27T13:15:00Z",
                "details": {
                    "log_groups": kwargs["log_groups"],
                    "s3_buckets": kwargs["s3_buckets"],
                },
            }

    monkeypatch.setattr(onboarding, "_resolve_progress_key", lambda customer_id, db: customer_id)
    monkeypatch.setattr("app.services.aws_connection_tester.AWSConnectionTester", _FakeAwsTester)

    response = client.post(
        "/api/v1/onboarding/recheck-health",
        headers={"X-Tenant-ID": "tenant-123"},
        json={"target": "cloud"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "health": {
            "success": True,
            "checked_at": "2026-03-27T13:15:00Z",
            "details": {
                "log_groups": ["arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/main"],
                "s3_buckets": ["arn:aws:s3:::security-bucket"],
            },
        },
    }


def test_recheck_health_uses_adapter_backed_cloud_provider(monkeypatch):
    fake_db = _RecheckDb(
        progress_row=(
            {},
            {},
            {},
            {},
            {},
            {},
            False,
            True,
        ),
        cloud_row=(
            "hetzner",
            None,
            None,
            "vault/hetzner-token",
            {"server_name": "websites-prod", "target_id": "websites-prod"},
            "123456789",
            "websites-prod",
        ),
    )
    client = _build_client(fake_db)
    calls = {}

    import sg_core.cloud.onboarding as cloud_onboarding

    def fake_refresh_cloud_connection_state(provider_id, *, account_id, account_name, secret, metadata):
        calls["provider_id"] = provider_id
        calls["account_id"] = account_id
        calls["account_name"] = account_name
        calls["secret"] = secret
        calls["metadata"] = metadata
        return SimpleNamespace(
            provider="hetzner",
            metadata={"health": {"status": "healthy"}, "scope_hash": "scope-fresh"},
            health={"success": True, "status": "healthy", "scope_hash": "scope-fresh"},
        )

    monkeypatch.setattr(onboarding, "_resolve_progress_key", lambda customer_id, db: customer_id)
    monkeypatch.setattr(onboarding, "decrypt_secret", lambda encrypted: f"secret-for-{encrypted}")
    monkeypatch.setattr(cloud_onboarding, "refresh_cloud_connection_state", fake_refresh_cloud_connection_state)

    response = client.post(
        "/api/v1/onboarding/recheck-health",
        headers={"X-Tenant-ID": "tenant-123"},
        json={"target": "cloud"},
    )

    assert response.status_code == 200
    assert response.json()["health"]["status"] == "healthy"
    assert calls == {
        "provider_id": "hetzner",
        "account_id": "123456789",
        "account_name": "websites-prod",
        "secret": "secret-for-vault/hetzner-token",
        "metadata": {"server_name": "websites-prod", "target_id": "websites-prod"},
    }
    update_sql, update_params = next(
        (sql, params)
        for sql, params in fake_db.statements
        if "UPDATE customer_cloud_accounts" in sql
    )
    assert "cloud_provider = :cloud_provider" in update_sql
    assert update_params["cloud_provider"] == "hetzner"


def test_recheck_health_keeps_endpoint_incomplete_without_registered_agent(monkeypatch):
    fake_db = _RecheckDb(
        progress_row=(
            {},
            {},
            {},
            {},
            {},
            {},
            True,
            True,
        )
    )
    client = _build_client(fake_db)

    monkeypatch.setattr(onboarding, "_resolve_progress_key", lambda customer_id, db: customer_id)
    monkeypatch.setattr(
        onboarding,
        "_get_endpoint_agent_health",
        lambda customer_id, db: {
            "status": "pending",
            "checked_at": "2026-03-27T13:20:00Z",
            "message": "No endpoint agent is registered for this tenant yet. Deploy the agent and re-run validation.",
        },
    )

    response = client.post(
        "/api/v1/onboarding/recheck-health",
        headers={"X-Tenant-ID": "tenant-123"},
        json={"target": "endpoint"},
    )

    assert response.status_code == 200
    assert response.json()["health"]["status"] == "pending"
    assert fake_db.commits == 1
    assert any(
        "SET step_endpoint_completed = false" in sql
        for sql, _ in fake_db.statements
    )
