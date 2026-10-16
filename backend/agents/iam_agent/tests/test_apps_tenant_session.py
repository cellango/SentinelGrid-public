from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import apps


class _FakeResult:
    def __init__(self, *, rows=None, row=None):
        self._rows = rows or []
        self._row = row

    def fetchall(self):
        return self._rows

    def first(self):
        return self._row


class FakeDB:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id
        self.executed = []

    def execute(self, statement, params=None):
        sql = str(statement)
        params = params or {}
        self.executed.append((sql, params))

        if "FROM apps" in sql and "ORDER BY created_at DESC" in sql:
            return _FakeResult(
                rows=[
                    SimpleNamespace(
                        id=uuid4(),
                        tenant_id=self.tenant_id,
                        name="sentinel-mail",
                        display_name="Sentinel Mail",
                        description="Mail security",
                        app_type="Custom",
                        icon_url=None,
                        is_active=True,
                        config={"client_id": "sentinel-mail", "protocol": "oidc", "realm": "demo"},
                    )
                ]
            )

        if "FROM apps" in sql and "WHERE id = :id AND tenant_id = :tenant_id" in sql:
            return _FakeResult(
                row=SimpleNamespace(
                    id=params["id"],
                    tenant_id=self.tenant_id,
                    name="sentinel-mail",
                    display_name="Sentinel Mail",
                    description="Mail security",
                    app_type="Custom",
                    icon_url=None,
                    is_active=True,
                    config={"client_id": "sentinel-mail", "protocol": "oidc", "realm": "demo"},
                )
            )

        return _FakeResult()


@pytest.fixture
def tenant_id():
    return str(uuid4())


@pytest.fixture
def fake_db(tenant_id):
    return FakeDB(tenant_id)


@pytest.fixture
def apps_client(monkeypatch, fake_db, tenant_id):
    app = FastAPI()
    app.include_router(apps.router)

    def _get_tenant_session_override():
        yield fake_db

    async def _get_token_data(_authorization):
        return {
            "tenant_id": tenant_id,
            "realm_name": "demo",
        }

    app.dependency_overrides[apps.get_tenant_session] = _get_tenant_session_override
    monkeypatch.setattr(apps, "get_token_data", _get_token_data)
    return TestClient(app)


def test_list_apps_uses_tenant_scoped_session(apps_client, fake_db, tenant_id):
    response = apps_client.get(
        "/api/iam-portal/apps",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json()[0]["name"] == "sentinel-mail"
    assert any(
        params.get("tenant_id") == tenant_id
        for _sql, params in fake_db.executed
    )


def test_get_app_uses_tenant_scoped_session(apps_client, fake_db, tenant_id):
    app_id = str(uuid4())

    response = apps_client.get(
        f"/api/iam-portal/apps/{app_id}",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == app_id
    assert any(
        params.get("tenant_id") == tenant_id and params.get("id") == app_id
        for _sql, params in fake_db.executed
    )
