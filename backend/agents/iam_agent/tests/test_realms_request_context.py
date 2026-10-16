from fastapi import FastAPI
from fastapi.testclient import TestClient
from keycloak.exceptions import KeycloakError

from app.api import realms
from app.api.request_context import RequestContext, get_current_request_context


def _request_context(*roles: str) -> RequestContext:
    return RequestContext(
        tenant_id="00000000-0000-0000-0000-000000000001",
        user_id="user-123",
        roles=tuple(roles),
    )


def test_create_realm_rejects_non_platform_admin(monkeypatch):
    app = FastAPI()
    app.include_router(realms.router)
    app.dependency_overrides[get_current_request_context] = lambda: _request_context("TENANT_ADMIN")
    client = TestClient(app)

    response = client.post(
        "/api/v1/realms",
        headers={"authorization": "Bearer test-token"},
        json={
            "realm_name": "sg-mt-us-2",
            "realm_type": "multi_tenant",
            "region": "us",
            "shard_number": 2,
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Missing required role"}


def test_create_realm_allows_platform_admin(monkeypatch):
    app = FastAPI()
    app.include_router(realms.router)
    app.dependency_overrides[get_current_request_context] = lambda: _request_context("PLATFORM_ADMIN")

    class FakeRealmCreationService:
        def __init__(self, admin):
            self.admin = admin

        def create_realm(self, **kwargs):
            assert kwargs["realm_name"] == "sg-mt-us-2"
            return {
                "realm_name": kwargs["realm_name"],
                "keycloak_realm_id": "realm-123",
                "status": "created",
                "user_profile_configured": True,
            }

    monkeypatch.setattr(realms, "get_keycloak_admin", lambda: object())
    monkeypatch.setattr(realms, "RealmCreationService", FakeRealmCreationService)

    client = TestClient(app)
    response = client.post(
        "/api/v1/realms",
        headers={"authorization": "Bearer test-token"},
        json={
            "realm_name": "sg-mt-us-2",
            "realm_type": "multi_tenant",
            "region": "us",
            "shard_number": 2,
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "realm_name": "sg-mt-us-2",
        "keycloak_realm_id": "realm-123",
        "status": "created",
        "user_profile_configured": True,
    }


def test_get_realm_status_rejects_non_platform_admin():
    app = FastAPI()
    app.include_router(realms.router)
    app.dependency_overrides[get_current_request_context] = lambda: _request_context("TENANT_ADMIN")
    client = TestClient(app)

    response = client.get(
        "/api/v1/realms/sg-mt-us-1/status",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Missing required role"}


def test_get_realm_status_allows_platform_admin(monkeypatch):
    app = FastAPI()
    app.include_router(realms.router)
    app.dependency_overrides[get_current_request_context] = lambda: _request_context("PLATFORM_ADMIN")

    class FakeAdmin:
        def get_realm(self, realm_name):
            assert realm_name == "sg-mt-us-1"
            return {"id": "realm-123"}

    import sg_core.keycloak_user_profile as keycloak_user_profile

    monkeypatch.setattr(realms, "get_keycloak_admin", lambda: FakeAdmin())
    monkeypatch.setattr(keycloak_user_profile, "verify_user_profile_configured", lambda *args, **kwargs: True)

    client = TestClient(app)
    response = client.get(
        "/api/v1/realms/sg-mt-us-1/status",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "realm_name": "sg-mt-us-1",
        "exists": True,
        "user_profile_configured": True,
        "keycloak_realm_id": "realm-123",
    }


def test_get_realm_status_reports_missing_realm(monkeypatch):
    app = FastAPI()
    app.include_router(realms.router)
    app.dependency_overrides[get_current_request_context] = lambda: _request_context("PLATFORM_ADMIN")

    class MissingRealmAdmin:
        def get_realm(self, _realm_name):
            raise KeycloakError("Realm not found")

    monkeypatch.setattr(realms, "get_keycloak_admin", lambda: MissingRealmAdmin())

    client = TestClient(app)
    response = client.get(
        "/api/v1/realms/sg-mt-us-9/status",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "realm_name": "sg-mt-us-9",
        "exists": False,
        "user_profile_configured": False,
        "keycloak_realm_id": None,
    }
