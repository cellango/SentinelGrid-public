from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import stats


class _FakeAdmin:
    def __init__(self):
        self.role_calls = []
        self.group_calls = []

    def get_users(self):
        return [
            {
                "id": "user-1",
                "enabled": True,
                "attributes": {"tenant_id": ["tenant-a"]},
            },
            {
                "id": "user-2",
                "enabled": False,
                "attributes": {"tenant_id": ["tenant-a"]},
            },
            {
                "id": "user-3",
                "enabled": True,
                "attributes": {"tenant_id": ["tenant-b"]},
            },
        ]

    def get_realm_roles_of_user(self, user_id):
        self.role_calls.append(user_id)
        if user_id == "user-1":
            return [{"name": "viewer"}, {"name": "admin"}]
        if user_id == "user-2":
            return [{"name": "viewer"}]
        return [{"name": "foreign"}]

    def get_user_groups(self, user_id):
        self.group_calls.append(user_id)
        if user_id == "user-1":
            return [{"id": "group-1"}]
        if user_id == "user-2":
            return [{"id": "group-1"}, {"id": "group-2"}]
        return [{"id": "group-foreign"}]


class _FakeKeycloakClient:
    def __init__(self):
        self.admin = _FakeAdmin()


def _build_client(monkeypatch):
    app = FastAPI()
    app.include_router(stats.router)
    monkeypatch.setattr(stats.settings, "INTERNAL_SERVICE_TOKEN", "internal-token")
    fake_client = _FakeKeycloakClient()
    app.dependency_overrides[stats.get_keycloak_client] = lambda: fake_client
    return TestClient(app), fake_client


def test_identity_stats_requires_internal_token(monkeypatch):
    client, _fake_client = _build_client(monkeypatch)

    response = client.get("/internal/iam/stats/tenant-a")

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing authorization header"}


def test_identity_stats_are_scoped_to_requested_tenant(monkeypatch):
    client, fake_client = _build_client(monkeypatch)

    response = client.get(
        "/internal/iam/stats/tenant-a",
        headers={"Authorization": "Bearer internal-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "users_count": 2,
        "active_users_count": 1,
        "roles_count": 2,
        "groups_count": 2,
        "last_sync_at": None,
    }
    assert fake_client.admin.role_calls == ["user-1", "user-2"]
    assert fake_client.admin.group_calls == ["user-1", "user-2"]
