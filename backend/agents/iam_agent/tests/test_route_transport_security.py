from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.external_idp as external_idp
import app.api.iam_orgs as iam_orgs
import app.api.onboarding as onboarding
import app.api.realms as realms
from app.api.request_context import RequestContext, get_current_request_context


def _request_context(*roles: str) -> RequestContext:
    return RequestContext(
        tenant_id="00000000-0000-0000-0000-000000000001",
        user_id="user-123",
        roles=tuple(roles),
    )


class _FakeResponse:
    def __init__(self, *, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.elapsed = SimpleNamespace(total_seconds=lambda: 0.01)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self):
        return self._json_data


def test_onboarding_health_checks_use_upstream_tls_verification(monkeypatch):
    recorded = {}

    def fake_request(method, url, **kwargs):
        recorded.update({"method": method, "url": url, **kwargs})
        return _FakeResponse(status_code=200)

    monkeypatch.setattr(onboarding.httpx, "request", fake_request)
    monkeypatch.setattr(onboarding.settings, "UPSTREAM_TLS_VERIFY", True)

    result = onboarding._check_url_health("https://ticketing.example.com/health")

    assert result["status"] == "healthy"
    assert recorded["verify"] is True


def test_external_idp_diagnostics_use_upstream_tls_verification(monkeypatch):
    app = FastAPI()
    app.include_router(external_idp.router)
    app.dependency_overrides[get_current_request_context] = lambda: _request_context("TENANT_ADMIN")
    captured = {}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            captured["kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, _url):
            return _FakeResponse(
                json_data={
                    "issuer": "https://idp.example",
                    "authorization_endpoint": "https://idp.example/auth",
                    "token_endpoint": "https://idp.example/token",
                }
            )

        async def post(self, _url, data=None, headers=None):
            return _FakeResponse(status_code=200, json_data={"access_token": "token"})

    monkeypatch.setattr(external_idp.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(external_idp.settings, "UPSTREAM_TLS_VERIFY", True)
    client = TestClient(app)

    response = client.post(
        "/api/v1/idp/test/oidc",
        headers={"authorization": "Bearer test-token"},
        json={
            "discovery_url": "https://idp.example/.well-known/openid-configuration",
            "client_id": "client-id",
            "client_secret": "client-secret",
        },
    )

    assert response.status_code == 200
    assert captured["kwargs"]["verify"] is True


def test_realms_admin_client_uses_keycloak_tls_verification(monkeypatch):
    previous_admin = realms._keycloak_admin
    realms._keycloak_admin = None
    sentinel_admin = object()
    try:
        factory_mock = Mock(return_value=sentinel_admin)
        with patch("app.api.realms.build_keycloak_admin", factory_mock):
            monkeypatch.setattr(realms.settings, "KEYCLOAK_VERIFY_TLS", True)
            result = realms.get_keycloak_admin()
    finally:
        realms._keycloak_admin = previous_admin

    assert result is sentinel_admin
    factory_mock.assert_called_once_with(realm_name="master")


def test_iam_org_realm_manager_uses_keycloak_tls_verification(monkeypatch):
    db = Mock()
    sentinel_admin = object()

    with (
        patch("app.api.iam_orgs.build_keycloak_admin", Mock(return_value=sentinel_admin)) as factory_mock,
        patch("app.api.iam_orgs.MultiTenantRealmManager") as mock_manager,
    ):
        monkeypatch.setattr(iam_orgs.settings, "KEYCLOAK_VERIFY_TLS", True)
        result = iam_orgs._get_realm_manager(db)

    assert result is mock_manager.return_value
    factory_mock.assert_called_once_with(realm_name="master")
    mock_manager.assert_called_once_with(sentinel_admin, db)


def test_phase1_transport_files_do_not_hardcode_verify_false():
    repo_root = Path(__file__).resolve().parents[4]
    files = [
        "backend/agents/iam_agent/app/api/auth.py",
        "backend/agents/iam_agent/app/api/external_idp.py",
        "backend/agents/iam_agent/app/api/iam_orgs.py",
        "backend/agents/iam_agent/app/api/onboarding.py",
        "backend/agents/iam_agent/app/api/payment.py",
        "backend/agents/iam_agent/app/api/realms.py",
        "backend/agents/iam_agent/app/services/keycloak_seeder.py",
    ]

    for relative_path in files:
        content = (repo_root / relative_path).read_text()
        assert "verify=False" not in content
