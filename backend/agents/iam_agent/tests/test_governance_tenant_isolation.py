from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import governance
from app.api.request_context import (
    RequestContext,
    get_current_request_context,
    get_entitlement_session as get_tenant_session,
)


class QuerySpy:
    def __init__(self, *, first_result=None, all_result=None):
        self.first_result = first_result
        self.all_result = all_result or []
        self.criteria = []
        self.joins = []

    def join(self, *args, **kwargs):
        self.joins.append((args, kwargs))
        return self

    def filter(self, *criteria):
        self.criteria.extend(criteria)
        return self

    def populate_existing(self):
        return self

    def with_for_update(self, **kwargs):
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

    def rollback(self):
        return None

    def commit(self):
        self.committed = True

    def refresh(self, _obj):
        return None


@pytest.fixture
def request_context():
    return RequestContext(
        tenant_id=uuid4(),
        user_id=str(uuid4()),
        roles=("TENANT_ADMIN",),
    )


@pytest.fixture
def governance_test_app(request_context):
    app = FastAPI()
    app.include_router(governance.router)
    app.dependency_overrides[get_current_request_context] = lambda: request_context
    return app


@pytest.fixture
def governance_client(governance_test_app):
    return TestClient(governance_test_app)


def _override_db(app, fake_db):
    def _get_db_override():
        yield fake_db

    app.dependency_overrides[get_tenant_session] = _get_db_override


def _tenant_filter_values(criteria):
    values = []
    for criterion in criteria:
        left = getattr(criterion, "left", None)
        if getattr(left, "key", None) != "tenant_id":
            continue
        right = getattr(criterion, "right", None)
        values.append(getattr(right, "value", None))
    return values


def test_create_campaign_rejects_foreign_body_tenant(
    governance_test_app,
    governance_client,
):
    fake_db = FakeDB(QuerySpy())
    _override_db(governance_test_app, fake_db)

    response = governance_client.post(
        "/api/v1/governance/campaigns",
        headers={"authorization": "Bearer test-token"},
        json={
            "tenant_id": str(uuid4()),
            "name": "Q2 Review",
            "start_date": "2026-04-01T00:00:00Z",
            "end_date": "2026-04-15T00:00:00Z",
            "reviewer_type": "admin",
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert fake_db.added == []


def test_get_campaign_scopes_lookup_to_authenticated_tenant(
    governance_test_app,
    governance_client,
    request_context,
):
    query_spy = QuerySpy(first_result=None)
    fake_db = FakeDB(query_spy)
    _override_db(governance_test_app, fake_db)

    response = governance_client.get(
        f"/api/v1/governance/campaigns/{uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Campaign not found"}
    assert request_context.tenant_id in _tenant_filter_values(query_spy.criteria)


def test_pending_certifications_query_is_joined_and_tenant_scoped(
    governance_test_app,
    governance_client,
    request_context,
):
    query_spy = QuerySpy(all_result=[])
    fake_db = FakeDB(query_spy)
    _override_db(governance_test_app, fake_db)

    response = governance_client.get(
        "/api/v1/governance/certifications/pending",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json() == []
    assert query_spy.joins
    assert request_context.tenant_id in _tenant_filter_values(query_spy.criteria)


def test_certify_entitlement_scopes_lookup_to_authenticated_tenant(
    governance_test_app,
    governance_client,
    request_context,
):
    query_spy = QuerySpy(first_result=None)
    fake_db = FakeDB(query_spy)
    _override_db(governance_test_app, fake_db)

    response = governance_client.post(
        f"/api/v1/governance/certifications/{uuid4()}/certify",
        headers={"authorization": "Bearer test-token"},
        json={"decision": "approved"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Certification not found"}
    assert query_spy.joins
    assert request_context.tenant_id in _tenant_filter_values(query_spy.criteria)


def test_bulk_certify_is_joined_and_tenant_scoped(
    governance_test_app,
    governance_client,
    request_context,
):
    query_spy = QuerySpy(all_result=[])
    fake_db = FakeDB(query_spy)
    _override_db(governance_test_app, fake_db)

    response = governance_client.post(
        "/api/v1/governance/certifications/bulk-certify",
        headers={"authorization": "Bearer test-token"},
        json={
            "certification_ids": [str(uuid4())],
            "decision": "approved",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Some certifications not found or already completed"
    }
    assert query_spy.joins
    assert request_context.tenant_id in _tenant_filter_values(query_spy.criteria)
