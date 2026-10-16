import sys
from types import ModuleType
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeRedisClient:
    def ping(self):
        return True

    def get(self, *_args, **_kwargs):
        return None

    def setex(self, *_args, **_kwargs):
        return True

    def delete(self, *_args, **_kwargs):
        return 0

    def keys(self, *_args, **_kwargs):
        return []


if "redis" not in sys.modules:
    fake_redis = ModuleType("redis")
    fake_redis.from_url = lambda *_args, **_kwargs: _FakeRedisClient()
    sys.modules["redis"] = fake_redis


from app.api import bulk_operations, entitlements
from app.api.request_context import RequestContext, get_current_request_context, get_tenant_session


class QuerySpy:
    def __init__(self, *, first_result=None, all_result=None):
        self.first_result = first_result
        self.all_result = all_result or []
        self.criteria = []

    def filter(self, *criteria):
        self.criteria.extend(criteria)
        return self

    def first(self):
        return self.first_result

    def all(self):
        return self.all_result

    def limit(self, _limit):
        return self

    def offset(self, _offset):
        return self


class FakeDB:
    def __init__(self, query_spy):
        self.query_spy = query_spy
        self.added = []
        self.committed = False

    def query(self, _model):
        return self.query_spy

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, _obj):
        return None

    def rollback(self):
        return None


@pytest.fixture
def request_context():
    return RequestContext(
        tenant_id=uuid4(),
        user_id=str(uuid4()),
    )


@pytest.fixture
def entitlement_test_app(request_context):
    app = FastAPI()
    app.include_router(bulk_operations.router)
    app.include_router(entitlements.router)
    app.dependency_overrides[get_current_request_context] = lambda: request_context
    return app


@pytest.fixture
def entitlement_client(entitlement_test_app):
    return TestClient(entitlement_test_app)


@pytest.fixture(autouse=True)
def patch_entitlement_side_effects(monkeypatch):
    monkeypatch.setattr(entitlements.cache, "get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(entitlements.cache, "invalidate_entitlement", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(bulk_operations.cache, "invalidate_tenant_entitlements", lambda *_args, **_kwargs: None)


def _override_db(app, fake_db):
    def _get_tenant_session_override():
        yield fake_db

    app.dependency_overrides[get_tenant_session] = _get_tenant_session_override


def _tenant_filter_values(criteria):
    values = []
    for criterion in criteria:
        left = getattr(criterion, "left", None)
        if getattr(left, "key", None) != "tenant_id":
            continue
        right = getattr(criterion, "right", None)
        values.append(getattr(right, "value", None))
    return values


def test_create_entitlement_rejects_foreign_body_tenant(
    entitlement_test_app,
    entitlement_client,
    request_context,
):
    fake_db = FakeDB(QuerySpy())
    _override_db(entitlement_test_app, fake_db)

    response = entitlement_client.post(
        "/api/v1/entitlements",
        headers={"authorization": "Bearer test-token"},
        json={
            "tenant_id": str(uuid4()),
            "resource_type": "device",
            "resource_id": "endpoint-123",
            "action": "read",
            "granted_to_type": "user",
            "granted_to_id": str(uuid4()),
            "granted_by": str(uuid4()),
            "metadata": {},
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert fake_db.added == []


def test_list_entitlements_rejects_foreign_query_tenant(
    entitlement_test_app,
    entitlement_client,
):
    fake_db = FakeDB(QuerySpy(all_result=[]))
    _override_db(entitlement_test_app, fake_db)

    response = entitlement_client.get(
        f"/api/v1/entitlements?tenant_id={uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}


def test_get_entitlement_scopes_lookup_to_authenticated_tenant(
    entitlement_test_app,
    entitlement_client,
    request_context,
):
    query_spy = QuerySpy(first_result=None)
    fake_db = FakeDB(query_spy)
    _override_db(entitlement_test_app, fake_db)
    entitlement_id = uuid4()

    response = entitlement_client.get(
        f"/api/v1/entitlements/{entitlement_id}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Entitlement not found"}
    assert request_context.tenant_id in _tenant_filter_values(query_spy.criteria)


def test_bulk_create_entitlements_rejects_foreign_body_tenant(
    entitlement_test_app,
    entitlement_client,
):
    fake_db = FakeDB(QuerySpy())
    _override_db(entitlement_test_app, fake_db)

    response = entitlement_client.post(
        "/api/v1/entitlements/bulk",
        headers={"authorization": "Bearer test-token"},
        json={
            "entitlements": [
                {
                    "tenant_id": str(uuid4()),
                    "resource_type": "device",
                    "resource_id": "endpoint-456",
                    "action": "read",
                    "granted_to_type": "user",
                    "granted_to_id": str(uuid4()),
                    "granted_by": str(uuid4()),
                    "metadata": {},
                }
            ]
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert fake_db.added == []


def test_bulk_delete_entitlements_scopes_lookup_to_authenticated_tenant(
    entitlement_test_app,
    entitlement_client,
    request_context,
):
    query_spy = QuerySpy(first_result=None)
    fake_db = FakeDB(query_spy)
    _override_db(entitlement_test_app, fake_db)
    entitlement_id = uuid4()

    response = entitlement_client.request(
        "DELETE",
        "/api/v1/entitlements/bulk",
        headers={"authorization": "Bearer test-token"},
        json={"entitlement_ids": [str(entitlement_id)]},
    )

    assert response.status_code == 200
    assert response.json()["failed"] == 1
    assert request_context.tenant_id in _tenant_filter_values(query_spy.criteria)
