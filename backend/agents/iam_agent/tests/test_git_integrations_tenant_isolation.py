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


from app.api import git_providers, git_scanning
from app.api.request_context import (
    RequestContext,
    get_current_request_context,
    get_tenant_session,
)


class ResultStub:
    def __init__(self, *, rows=None, row=None):
        self._rows = rows or []
        self._row = row

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._row


class FakeDB:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.committed = False
        self.rolled_back = False

    def execute(self, statement, params=None):
        sql = str(statement)
        self.calls.append({"sql": sql, "params": params or {}})
        if self.responses:
            response = self.responses.pop(0)
            if callable(response):
                return response(statement, params or {})
            return response
        return ResultStub()

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


@pytest.fixture
def request_context():
    return RequestContext(
        tenant_id=uuid4(),
        user_id=str(uuid4()),
    )


@pytest.fixture
def git_test_app(request_context):
    app = FastAPI()
    app.include_router(git_providers.router)
    app.include_router(git_scanning.router)
    app.dependency_overrides[get_current_request_context] = lambda: request_context
    return app


@pytest.fixture
def git_client(git_test_app):
    return TestClient(git_test_app)


def _override_provider_db(app, fake_db):
    def _get_tenant_session_override():
        yield fake_db

    app.dependency_overrides[get_tenant_session] = _get_tenant_session_override


def _override_scanning_db(app, fake_db):
    def _get_tenant_session_override():
        yield fake_db

    app.dependency_overrides[get_tenant_session] = _get_tenant_session_override


def test_connect_git_provider_persists_authenticated_tenant(
    git_test_app,
    git_client,
    request_context,
):
    fake_db = FakeDB([ResultStub(row=(str(uuid4()),))])
    _override_provider_db(git_test_app, fake_db)

    response = git_client.post(
        "/api/v1/git-providers/connect",
        headers={"authorization": "Bearer test-token"},
        json={
            "provider": "self_hosted",
            "config": {},
            "organization": "example-org",
        },
    )

    assert response.status_code == 200
    insert_call = next(call for call in fake_db.calls if "INSERT INTO customer_git_providers" in call["sql"])
    assert insert_call["params"]["customer_id"] == str(request_context.tenant_id)


def test_list_git_providers_queries_authenticated_tenant_only(
    git_test_app,
    git_client,
    request_context,
):
    fake_db = FakeDB(
        [
            ResultStub(
                rows=[
                    (
                        uuid4(),
                        "github",
                        "example-org",
                        "connected",
                        None,
                        None,
                        None,
                    )
                ]
            )
        ]
    )
    _override_provider_db(git_test_app, fake_db)

    response = git_client.get(
        "/api/v1/git-providers",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    select_call = fake_db.calls[0]
    assert select_call["params"]["customer_id"] == str(request_context.tenant_id)


def test_recheck_git_provider_queries_authenticated_tenant_only(
    git_test_app,
    git_client,
    request_context,
):
    fake_db = FakeDB([ResultStub(row=None)])
    _override_provider_db(git_test_app, fake_db)

    response = git_client.post(
        "/api/v1/git-providers/recheck",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 404
    lookup_call = fake_db.calls[0]
    assert lookup_call["params"]["customer_id"] == str(request_context.tenant_id)


def test_list_repositories_requires_provider_owned_by_authenticated_tenant(
    git_test_app,
    git_client,
    request_context,
):
    fake_db = FakeDB([ResultStub(row=None)])
    _override_provider_db(git_test_app, fake_db)

    response = git_client.get(
        f"/api/v1/git-providers/{uuid4()}/repositories",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 404
    provider_lookup = fake_db.calls[0]
    assert provider_lookup["params"]["customer_id"] == str(request_context.tenant_id)


def test_sync_repositories_requires_provider_owned_by_authenticated_tenant(
    git_test_app,
    git_client,
    request_context,
):
    fake_db = FakeDB([ResultStub(row=None)])
    _override_provider_db(git_test_app, fake_db)

    response = git_client.post(
        f"/api/v1/git-providers/{uuid4()}/sync",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 404
    provider_lookup = fake_db.calls[0]
    assert provider_lookup["params"]["customer_id"] == str(request_context.tenant_id)


def test_scan_repository_requires_repo_owned_by_authenticated_tenant(
    git_test_app,
    git_client,
    request_context,
):
    fake_db = FakeDB([ResultStub(row=None)])
    _override_scanning_db(git_test_app, fake_db)

    response = git_client.post(
        "/api/v1/git-scanning/scan",
        headers={"authorization": "Bearer test-token"},
        json={"repo_id": str(uuid4())},
    )

    assert response.status_code == 404
    repo_lookup = fake_db.calls[0]
    assert repo_lookup["params"]["customer_id"] == str(request_context.tenant_id)


def test_list_findings_filters_by_authenticated_tenant(
    git_test_app,
    git_client,
    request_context,
):
    fake_db = FakeDB([ResultStub(row=(0,)), ResultStub(rows=[])])
    _override_scanning_db(git_test_app, fake_db)

    response = git_client.get(
        "/api/v1/git-scanning/findings",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert fake_db.calls[0]["params"]["customer_id"] == str(request_context.tenant_id)
    assert fake_db.calls[1]["params"]["customer_id"] == str(request_context.tenant_id)


def test_get_finding_requires_authenticated_tenant_scope(
    git_test_app,
    git_client,
    request_context,
):
    fake_db = FakeDB([ResultStub(row=None)])
    _override_scanning_db(git_test_app, fake_db)

    response = git_client.get(
        f"/api/v1/git-scanning/findings/{uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 404
    lookup = fake_db.calls[0]
    assert lookup["params"]["customer_id"] == str(request_context.tenant_id)


def test_update_finding_status_requires_authenticated_tenant_scope(
    git_test_app,
    git_client,
    request_context,
):
    fake_db = FakeDB([ResultStub(row=None)])
    _override_scanning_db(git_test_app, fake_db)

    response = git_client.patch(
        f"/api/v1/git-scanning/findings/{uuid4()}",
        headers={"authorization": "Bearer test-token"},
        params={"status": "resolved"},
    )

    assert response.status_code == 404
    lookup = fake_db.calls[0]
    assert lookup["params"]["customer_id"] == str(request_context.tenant_id)


def test_get_finding_filters_by_authenticated_tenant(
    git_test_app,
    git_client,
    request_context,
):
    fake_db = FakeDB([ResultStub(row=None)])
    _override_scanning_db(git_test_app, fake_db)

    response = git_client.get(
        f"/api/v1/git-scanning/findings/{uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 404
    assert fake_db.calls[0]["params"]["customer_id"] == str(request_context.tenant_id)


def test_update_finding_status_filters_by_authenticated_tenant(
    git_test_app,
    git_client,
    request_context,
):
    fake_db = FakeDB([ResultStub(row=None)])
    _override_scanning_db(git_test_app, fake_db)

    response = git_client.patch(
        f"/api/v1/git-scanning/findings/{uuid4()}?status=resolved",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 404
    assert fake_db.calls[0]["params"]["customer_id"] == str(request_context.tenant_id)
