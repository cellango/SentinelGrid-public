from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import access_requests
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
        self.committed = False

    def query(self, _model):
        return self.query_spy

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, _obj):
        return None

    def flush(self):
        return None


def _override_db(app, fake_db):
    def _get_tenant_session_override():
        yield fake_db

    app.dependency_overrides[get_tenant_session] = _get_tenant_session_override


def _bind_values(criteria):
    values = []

    def _walk(node):
        value = getattr(node, "value", None)
        if value is not None:
            values.append(value)
        for child in getattr(node, "get_children", lambda: [])():
            _walk(child)

    for criterion in criteria:
        _walk(criterion)
    return values


def _build_access_request(request_context, **overrides):
    payload = {
        "id": uuid4(),
        "tenant_id": request_context.tenant_id,
        "requested_by": uuid4(),
        "requested_for": uuid4(),
        "resource_type": "alert",
        "resource_id": "alert-123",
        "action": "read",
        "justification": "Need access for investigation",
        "status": "pending",
        "reviewer_id": None,
        "reviewed_at": None,
        "review_comments": None,
        "expires_at": None,
        "entitlement_id": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


@pytest.fixture
def request_context():
    return RequestContext(
        tenant_id=uuid4(),
        user_id=str(uuid4()),
        roles=("SOC_ANALYST",),
    )


@pytest.fixture
def admin_request_context(request_context):
    return RequestContext(
        tenant_id=request_context.tenant_id,
        user_id=request_context.user_id,
        roles=("TENANT_ADMIN",),
    )


@pytest.fixture
def access_requests_test_app(request_context):
    app = FastAPI()
    app.include_router(access_requests.router)
    app.dependency_overrides[get_current_request_context] = lambda: request_context
    return app


@pytest.fixture
def access_requests_client(access_requests_test_app):
    return TestClient(access_requests_test_app)


def test_list_access_requests_scopes_non_admin_queries_to_authenticated_user(
    access_requests_test_app,
    access_requests_client,
    request_context,
):
    fake_db = FakeDB(QuerySpy(all_result=[]))
    _override_db(access_requests_test_app, fake_db)

    response = access_requests_client.get(
        "/api/v1/access-requests",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    bind_values = {str(value) for value in _bind_values(fake_db.query_spy.criteria)}
    assert str(request_context.user_id) in bind_values


def test_list_access_requests_rejects_foreign_requested_by_for_non_admin(
    access_requests_test_app,
    access_requests_client,
):
    fake_db = FakeDB(QuerySpy(all_result=[]))
    _override_db(access_requests_test_app, fake_db)

    response = access_requests_client.get(
        f"/api/v1/access-requests?requested_by={uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied"}


def test_get_access_request_blocks_non_owner_non_admin(
    access_requests_test_app,
    access_requests_client,
    request_context,
):
    fake_db = FakeDB(QuerySpy(first_result=_build_access_request(request_context)))
    _override_db(access_requests_test_app, fake_db)

    response = access_requests_client.get(
        f"/api/v1/access-requests/{uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied"}


def test_get_access_request_allows_request_owner(
    access_requests_test_app,
    access_requests_client,
    request_context,
):
    fake_db = FakeDB(
        QuerySpy(
            first_result=_build_access_request(
                request_context,
                requested_by=UUID(request_context.user_id),
            )
        )
    )
    _override_db(access_requests_test_app, fake_db)

    response = access_requests_client.get(
        f"/api/v1/access-requests/{uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json()["requested_by"] == request_context.user_id


def test_get_access_request_history_blocks_non_owner_non_admin(
    access_requests_test_app,
    access_requests_client,
    request_context,
):
    fake_db = FakeDB(QuerySpy(first_result=_build_access_request(request_context)))
    _override_db(access_requests_test_app, fake_db)

    response = access_requests_client.get(
        f"/api/v1/access-requests/{uuid4()}/history",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied"}


def test_review_access_request_requires_admin_role(
    access_requests_test_app,
    access_requests_client,
    request_context,
):
    fake_db = FakeDB(QuerySpy(first_result=_build_access_request(request_context)))
    _override_db(access_requests_test_app, fake_db)

    response = access_requests_client.post(
        f"/api/v1/access-requests/{uuid4()}/review",
        headers={"authorization": "Bearer test-token"},
        json={"decision": "approve"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied"}


def test_review_access_request_allows_admin_role(
    access_requests_test_app,
    access_requests_client,
    admin_request_context,
):
    access_requests_test_app.dependency_overrides[get_current_request_context] = lambda: admin_request_context
    request_to_review = _build_access_request(admin_request_context)
    fake_db = FakeDB(QuerySpy(first_result=request_to_review))
    _override_db(access_requests_test_app, fake_db)

    response = access_requests_client.post(
        f"/api/v1/access-requests/{request_to_review.id}/review",
        headers={"authorization": "Bearer test-token"},
        json={"decision": "deny", "comments": "Not justified"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "denied"
    assert response.json()["reviewer_id"] == admin_request_context.user_id
