from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import access_requests, role_mappings
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

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, _limit):
        return self

    def offset(self, _offset):
        return self


class FakeDB:
    def __init__(self, query_spy):
        self.query_spy = query_spy
        self.added = []
        self.deleted = []
        self.committed = False

    def query(self, _model):
        return self.query_spy

    def add(self, obj):
        self.added.append(obj)

    def delete(self, obj):
        self.deleted.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, _obj):
        return None

    def flush(self):
        return None


@pytest.fixture
def request_context():
    return RequestContext(
        tenant_id=uuid4(),
        user_id=str(uuid4()),
    )


@pytest.fixture
def role_access_test_app(request_context):
    app = FastAPI()
    app.include_router(role_mappings.router)
    app.include_router(access_requests.router)
    app.dependency_overrides[get_current_request_context] = lambda: request_context
    return app


@pytest.fixture
def role_access_client(role_access_test_app):
    return TestClient(role_access_test_app)


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


def test_create_role_pattern_rejects_foreign_body_tenant(
    role_access_test_app,
    role_access_client,
):
    fake_db = FakeDB(QuerySpy())
    _override_db(role_access_test_app, fake_db)

    response = role_access_client.post(
        "/api/v1/role-mappings",
        headers={"authorization": "Bearer test-token"},
        json={
            "role_name": "SOC_ANALYST",
            "tenant_id": str(uuid4()),
            "entitlement_pattern": "alert:*:read",
            "auto_grant": True,
            "created_by": str(uuid4()),
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert fake_db.added == []


def test_get_role_pattern_scopes_lookup_to_authenticated_tenant(
    role_access_test_app,
    role_access_client,
    request_context,
):
    query_spy = QuerySpy(first_result=None)
    fake_db = FakeDB(query_spy)
    _override_db(role_access_test_app, fake_db)

    response = role_access_client.get(
        f"/api/v1/role-mappings/{uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Role pattern not found"}
    assert request_context.tenant_id in _tenant_filter_values(query_spy.criteria)


def test_list_access_requests_rejects_foreign_query_tenant(
    role_access_test_app,
    role_access_client,
):
    fake_db = FakeDB(QuerySpy(all_result=[]))
    _override_db(role_access_test_app, fake_db)

    response = role_access_client.get(
        f"/api/v1/access-requests?tenant_id={uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}


def test_cancel_access_request_scopes_lookup_to_authenticated_tenant(
    role_access_test_app,
    role_access_client,
    request_context,
):
    query_spy = QuerySpy(
        first_result=SimpleNamespace(
            id=uuid4(),
            requested_by=uuid4(),
            status="pending",
        )
    )
    fake_db = FakeDB(query_spy)
    _override_db(role_access_test_app, fake_db)

    response = role_access_client.post(
        f"/api/v1/access-requests/{uuid4()}/cancel",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code in {403, 404}
    assert request_context.tenant_id in _tenant_filter_values(query_spy.criteria)
