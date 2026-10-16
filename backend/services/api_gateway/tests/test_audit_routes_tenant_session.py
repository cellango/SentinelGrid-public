from uuid import uuid4

import pytest
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes_audit
from sg_core.db import get_tenant_session
from sg_core.security import get_current_tenant


class _QueryChain:
    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return None


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FetchResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeDB:
    def __init__(self):
        self.calls = []

    def query(self, _model):
        return _QueryChain()

    def execute(self, statement, params=None):
        self.calls.append({"statement": statement, "params": params or {}})
        if params is not None:
            return _FetchResult([])
        return _ScalarResult([])


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.text)


class FakeAsyncClient:
    def __init__(self, recorder):
        self.recorder = recorder

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    async def get(self, url, headers=None, params=None):
        self.recorder["method"] = "GET"
        self.recorder["url"] = url
        self.recorder["headers"] = headers or {}
        self.recorder["params"] = params or {}
        self.recorder["json"] = None
        return FakeResponse({"items": [], "count": 0})

    async def post(self, url, headers=None, json=None):
        self.recorder["method"] = "POST"
        self.recorder["url"] = url
        self.recorder["headers"] = headers or {}
        self.recorder["params"] = {}
        self.recorder["json"] = json
        return FakeResponse({"ok": True})


@pytest.fixture
def workflow_client():
    app = FastAPI()
    app.include_router(routes_audit.router)
    tenant_id = str(uuid4())

    def _get_tenant():
        return tenant_id

    app.dependency_overrides[get_current_tenant] = _get_tenant

    with TestClient(app) as client:
        yield client, tenant_id

    app.dependency_overrides.clear()


def test_alert_audit_route_uses_tenant_scoped_db_dependency():
    app = FastAPI()
    app.include_router(routes_audit.router)
    fake_db = _FakeDB()

    def _get_tenant_session():
        yield fake_db

    def _get_tenant():
        return "tenant-123"

    app.dependency_overrides[get_tenant_session] = _get_tenant_session
    app.dependency_overrides[get_current_tenant] = _get_tenant

    client = TestClient(app)
    response = client.get("/audit/alerts/alert-123")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}

    audit_call = next(call for call in fake_db.calls if call["params"])
    assert audit_call["params"]["tenant_id"] == "tenant-123"
    assert audit_call["params"]["resource_type"] == "alert"
    assert audit_call["params"]["resource_id"] == "alert-123"

    app.dependency_overrides.clear()


def test_get_ai_activity_forwards_authenticated_tenant(workflow_client, monkeypatch):
    client, tenant_id = workflow_client
    recorder = {}
    monkeypatch.setattr(routes_audit.httpx, "AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    response = client.get(
        "/audit/ai-activity?realm_name=acme&limit=25",
        headers={"Authorization": "Bearer token-123"},
    )

    assert response.status_code == 200
    assert recorder["url"].endswith("/api/v1/audit/ai-activity")
    assert recorder["headers"]["X-Tenant-ID"] == tenant_id
    assert recorder["headers"]["Authorization"] == "Bearer token-123"
    assert recorder["params"]["tenant_id"] == tenant_id
    assert recorder["params"]["realm_name"] == "acme"


def test_get_ai_activity_rejects_foreign_tenant_override(workflow_client, monkeypatch):
    client, _tenant_id = workflow_client
    recorder = {}
    monkeypatch.setattr(routes_audit.httpx, "AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    response = client.get(
        f"/audit/ai-activity?tenant_id={uuid4()}&realm_name=acme",
        headers={"Authorization": "Bearer token-123"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant ID mismatch. You can only access your own tenant's data."
    assert recorder == {}


def test_post_ai_activity_forwards_authenticated_tenant(workflow_client, monkeypatch):
    client, tenant_id = workflow_client
    recorder = {}
    monkeypatch.setattr(routes_audit.httpx, "AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    response = client.post(
        "/audit/ai-activity",
        headers={"Authorization": "Bearer token-123"},
        json={"realm_name": "acme", "action": "ai.query", "metadata": {"query": "hello"}},
    )

    assert response.status_code == 201
    assert recorder["url"].endswith("/api/v1/audit/ai-activity")
    assert recorder["headers"]["X-Tenant-ID"] == tenant_id
    assert recorder["headers"]["Authorization"] == "Bearer token-123"
    assert recorder["json"]["tenant_id"] == tenant_id
    assert recorder["json"]["realm_name"] == "acme"


def test_post_ai_activity_rejects_foreign_tenant_override(workflow_client, monkeypatch):
    client, _tenant_id = workflow_client
    recorder = {}
    monkeypatch.setattr(routes_audit.httpx, "AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    response = client.post(
        "/audit/ai-activity",
        headers={"Authorization": "Bearer token-123"},
        json={"tenant_id": str(uuid4()), "realm_name": "acme", "action": "ai.query"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant ID mismatch. You can only access your own tenant's data."
    assert recorder == {}
