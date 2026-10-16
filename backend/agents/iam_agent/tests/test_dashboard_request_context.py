from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import dashboard
from app.api.request_context import RequestContext, get_current_request_context
import app.services.anomaly_detection as anomaly_detection_module


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeKeycloakAdminClient:
    def __init__(self):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def _make_request(self, method, path):
        self.calls.append((method, path))
        if path.endswith("/users"):
            return _FakeResponse(
                [
                    {
                        "id": "user-1",
                        "enabled": True,
                        "attributes": {"tenant_id": ["11111111-1111-1111-1111-111111111111"]},
                    },
                    {
                        "id": "user-2",
                        "enabled": False,
                        "attributes": {"tenant_id": ["11111111-1111-1111-1111-111111111111"]},
                    },
                    {
                        "id": "user-3",
                        "enabled": True,
                        "attributes": {"tenant_id": ["22222222-2222-2222-2222-222222222222"]},
                    },
                ]
            )
        if path.endswith("/users/user-1/role-mappings/realm"):
            return _FakeResponse([{"name": "tenant_admin"}])
        if path.endswith("/users/user-2/role-mappings/realm"):
            return _FakeResponse([{"name": "viewer"}])
        if path.endswith("/users/user-1/credentials"):
            return _FakeResponse([{"type": "otp"}])
        if path.endswith("/users/user-2/credentials"):
            return _FakeResponse([])
        raise AssertionError(f"Unexpected Keycloak path: {path}")


class _FakeAnomalyDetectionService:
    def __init__(self):
        self.calls = []

    async def detect_anomalies(self, tenant_id, time_window_hours=24):
        self.calls.append((tenant_id, time_window_hours))
        return [
            {"severity": "critical"},
            {"severity": "medium"},
        ]
def test_dashboard_snapshot_requires_authenticated_request_context():
    app = FastAPI()
    app.include_router(dashboard.router)
    client = TestClient(app)

    response = client.get("/dashboard-snapshot")

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing or invalid authorization header"}


def test_dashboard_snapshot_uses_authenticated_tenant_not_header_override(monkeypatch):
    app = FastAPI()
    app.include_router(dashboard.router)
    request_context = RequestContext(
        tenant_id="11111111-1111-1111-1111-111111111111",
        user_id="user-123",
        roles=("TENANT_ADMIN",),
    )
    app.dependency_overrides[get_current_request_context] = lambda: request_context

    fake_kc = _FakeKeycloakAdminClient()
    fake_anomalies = _FakeAnomalyDetectionService()
    monkeypatch.setattr(dashboard, "KeycloakAdminClient", lambda: fake_kc)
    monkeypatch.setattr(anomaly_detection_module, "AnomalyDetectionService", lambda: fake_anomalies)

    client = TestClient(app)
    response = client.get(
        "/dashboard-snapshot",
        headers={
            "Authorization": "Bearer test-token",
            "X-Tenant-ID": "22222222-2222-2222-2222-222222222222",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "users_total": 2,
        "users_active": 1,
        "users_inactive": 1,
        "users_admins": 1,
        "mfa_coverage_percent": 50.0,
        "mfa_missing_count": 1,
        "dormant_accounts_count": 0,
        "failed_logins_24h": 0,
        "anomalies_count": 2,
        "anomalies_critical": 1,
        "devices_total": 0,
        "devices_trusted": 0,
        "devices_untrusted": 0,
        "fast_win": {
            "title": "Enforce MFA for 1 admin account(s)",
            "description": "1 admin account(s) are missing MFA. This is a quick security win.",
            "action": "enforce_mfa",
        },
    }
    assert fake_anomalies.calls == [("11111111-1111-1111-1111-111111111111", 24)]
