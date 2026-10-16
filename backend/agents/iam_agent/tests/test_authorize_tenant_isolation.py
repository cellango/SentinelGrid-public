import sys
from types import ModuleType, SimpleNamespace
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


from app.api import authorize as authorize_api
from app.api.request_context import RequestContext, get_current_request_context, get_tenant_session


@pytest.fixture
def request_context():
    return RequestContext(
        tenant_id=uuid4(),
        user_id=str(uuid4()),
    )


@pytest.fixture
def authorize_test_app(request_context):
    app = FastAPI()
    app.include_router(authorize_api.router)
    app.dependency_overrides[get_current_request_context] = lambda: request_context
    return app


@pytest.fixture
def authorize_client(authorize_test_app):
    return TestClient(authorize_test_app)


def _override_db(app):
    def _get_tenant_session_override():
        yield object()

    app.dependency_overrides[get_tenant_session] = _get_tenant_session_override


def test_authorize_rejects_foreign_body_tenant(authorize_test_app, authorize_client):
    _override_db(authorize_test_app)

    response = authorize_client.post(
        "/api/v1/authorize",
        headers={"authorization": "Bearer test-token"},
        json={
            "user_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "resource_type": "device",
            "resource_id": "endpoint-1",
            "action": "read",
            "context": {},
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}


def test_authorize_batch_rejects_mixed_tenant_payload(authorize_test_app, authorize_client, request_context):
    _override_db(authorize_test_app)

    response = authorize_client.post(
        "/api/v1/authorize/batch",
        headers={"authorization": "Bearer test-token"},
        json={
            "requests": [
                {
                    "user_id": str(uuid4()),
                    "tenant_id": str(request_context.tenant_id),
                    "resource_type": "device",
                    "resource_id": "endpoint-1",
                    "action": "read",
                    "context": {},
                },
                {
                    "user_id": str(uuid4()),
                    "tenant_id": str(uuid4()),
                    "resource_type": "device",
                    "resource_id": "endpoint-2",
                    "action": "write",
                    "context": {},
                },
            ]
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}


def test_get_user_entitlements_rejects_foreign_body_tenant(authorize_test_app, authorize_client):
    _override_db(authorize_test_app)

    response = authorize_client.post(
        "/api/v1/authorize/user/entitlements",
        headers={"authorization": "Bearer test-token"},
        json={
            "user_id": str(uuid4()),
            "tenant_id": str(uuid4()),
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}


def test_clear_evaluation_cache_scopes_to_authenticated_tenant(
    authorize_test_app,
    authorize_client,
    monkeypatch,
    request_context,
):
    _override_db(authorize_test_app)
    deleted_patterns = []

    monkeypatch.setattr(
        authorize_api.cache,
        "delete_pattern",
        lambda pattern: deleted_patterns.append(pattern) or 7,
    )

    response = authorize_client.delete(
        "/api/v1/authorize/cache",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "deleted_keys": 7,
        "pattern": f"evaluation:*:tenant:{request_context.tenant_id}:*",
    }
    assert deleted_patterns == [f"evaluation:*:tenant:{request_context.tenant_id}:*"]


def test_clear_evaluation_cache_rejects_foreign_tenant_query(
    authorize_test_app,
    authorize_client,
):
    _override_db(authorize_test_app)

    response = authorize_client.delete(
        f"/api/v1/authorize/cache?tenant_id={uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
