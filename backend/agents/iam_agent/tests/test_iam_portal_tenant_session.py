from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import iam_portal
from app.api.request_context import get_tenant_session
from app.models.iam_portal import App, UserInfo


class FakePortalService:
    last_init = None

    def __init__(self, db, tenant_id, realm_name):
        type(self).last_init = {
            "db": db,
            "tenant_id": tenant_id,
            "realm_name": realm_name,
        }
        self.db = db
        self.tenant_id = tenant_id
        self.realm_name = realm_name

    def list_apps(self):
        now = datetime.now(timezone.utc)
        return [
            App(
                id=uuid4(),
                tenant_id=self.tenant_id,
                name="sentinel-mail",
                display_name="Sentinel Mail",
                description="Mail security app",
                app_type="saas",
                icon_url=None,
                is_active=True,
                config={},
                created_at=now,
                updated_at=now,
            )
        ]

    async def list_users(self, department_filter=None, team_filter=None, privileged_filter=None):
        return [
            UserInfo(
                user_id="user-1",
                username="analyst",
                email="analyst@example.com",
                tenant_id=self.tenant_id,
                entitlements=[],
            )
        ]

    def create_user(self, user_data, actor_id):
        return UserInfo(
            user_id="user-2",
            username=user_data.username,
            email=user_data.email,
            tenant_id=user_data.tenant_id,
            entitlements=[],
        )


@pytest.fixture
def tenant_id():
    return uuid4()


@pytest.fixture
def portal_user_info(tenant_id):
    return {
        "user_id": "portal-user",
        "tenant_id": str(tenant_id),
        "realm_name": "demo",
        "email": "portal-user@example.com",
        "username": "portal-user",
    }


@pytest.fixture
def portal_test_app(monkeypatch, portal_user_info):
    app = FastAPI()
    app.include_router(iam_portal.router)

    fake_db = object()

    def _get_tenant_session_override():
        yield fake_db

    app.dependency_overrides[iam_portal.get_current_user_info] = lambda: portal_user_info
    app.dependency_overrides[iam_portal.get_current_user_id] = lambda: portal_user_info["user_id"]
    app.dependency_overrides[get_tenant_session] = _get_tenant_session_override
    monkeypatch.setattr(iam_portal, "IAMPortalService", FakePortalService)

    return app, fake_db


@pytest.fixture
def portal_client(portal_test_app):
    app, _ = portal_test_app
    return TestClient(app)


def test_list_apps_uses_tenant_scoped_session(portal_test_app, portal_client, tenant_id):
    _, fake_db = portal_test_app

    response = portal_client.get("/api/iam-portal/apps")

    assert response.status_code == 200
    assert response.json()[0]["tenant_id"] == str(tenant_id)
    assert FakePortalService.last_init == {
        "db": fake_db,
        "tenant_id": tenant_id,
        "realm_name": "demo",
    }


def test_list_users_uses_tenant_scoped_session(portal_test_app, portal_client, tenant_id):
    _, fake_db = portal_test_app

    response = portal_client.get("/api/iam-portal/users")

    assert response.status_code == 200
    assert response.json()[0]["tenant_id"] == str(tenant_id)
    assert FakePortalService.last_init == {
        "db": fake_db,
        "tenant_id": tenant_id,
        "realm_name": "demo",
    }


def test_create_user_rejects_foreign_body_tenant(portal_client):
    response = portal_client.post(
        "/api/iam-portal/users",
        json={
            "username": "new-user",
            "email": "new-user@example.com",
            "tenant_id": str(uuid4()),
            "first_name": "New",
            "last_name": "User",
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "tenant_id does not match current context"}
