"""Access requests use verified identity and independent reviewers."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import access_requests as api
from app.api.request_context import RequestContext, get_current_request_context, get_entitlement_session


@pytest.fixture
def route():
    caller = RequestContext(uuid4(), str(uuid4()), ("TENANT_ADMIN",))
    now = datetime.now(timezone.utc)
    row = SimpleNamespace(id=uuid4(), tenant_id=caller.tenant_id, requested_by=uuid4(),
        requested_for=None, resource_type="document", resource_id="synthetic", action="read",
        justification="Synthetic request", status="pending", reviewer_id=None, reviewed_at=None,
        review_comments=None, expires_at=None, entitlement_id=None, created_at=now, updated_at=now)
    row.requested_for = row.requested_by
    class Storage:
        def __init__(self): self.added=[]; self.commits=0; self.rollbacks=0
        def query(self, model): return self
        def filter(self, *args): return self
        def populate_existing(self): return self
        def with_for_update(self): return self
        def first(self): return row
        def add(self, value): self.added.append(value)
        def flush(self): pass
        def commit(self): self.commits += 1
        def rollback(self): self.rollbacks += 1
        def refresh(self, value): pass
    db=Storage()
    app=FastAPI();app.include_router(api.router)
    app.dependency_overrides[get_current_request_context]=lambda: caller
    app.dependency_overrides[get_entitlement_session]=lambda: db
    with TestClient(app) as client:
        yield client, caller, row, db


def payload(caller, **extra):
    return dict(tenant_id=str(caller.tenant_id), resource_type="document", resource_id="synthetic",
                action="read", justification="Synthetic request", **extra)


@pytest.mark.parametrize("roles", [(), ("TENANT_ADMIN",), ("PLATFORM_ADMIN",)])
def test_delegation_requires_future_trusted_membership_path(route, roles):
    client, caller, _, db=route
    object.__setattr__(caller,"roles",roles)
    response=client.post("/api/v1/access-requests", json=payload(caller,requested_for=str(uuid4())))
    assert response.status_code==403
    assert db.added==[] and db.commits==0


@pytest.mark.parametrize("expiry", ["2020-01-01T00:00:00Z", "2099-01-01T00:00:00", "2020-01-01T00:00:00+02:00"])
def test_expiry_must_be_aware_and_future(route, expiry):
    client, caller, _, db=route
    assert client.post("/api/v1/access-requests",json=payload(caller,expires_at=expiry)).status_code==422
    assert db.added==[]


@pytest.mark.parametrize("field", ["resource_type", "resource_id", "action"])
@pytest.mark.parametrize("value", ["", "   "])
def test_empty_targets_are_rejected(route, field, value):
    client, caller, _, db=route
    body=payload(caller);body[field]=value
    assert client.post("/api/v1/access-requests",json=body).status_code==422
    assert db.added==[]


@pytest.mark.parametrize("identity", ["requested_by", "requested_for"])
def test_requester_or_beneficiary_cannot_approve_even_as_admin(route, identity):
    client, caller, row, db=route
    setattr(row, identity, api.UUID(caller.user_id))
    response=client.post(f"/api/v1/access-requests/{row.id}/review",json={"decision":"approve"})
    assert response.status_code==403
    assert row.status=="pending" and db.added==[] and db.commits==0


def test_legacy_delegated_request_cannot_create_grant(route):
    client, _, row, db=route
    row.requested_for=uuid4()
    response=client.post(f"/api/v1/access-requests/{row.id}/review",json={"decision":"approve"})
    assert response.status_code==409 and db.commits==0 and db.added==[]


def test_expired_pending_request_cannot_create_grant(route):
    client, _, row, db=route
    row.expires_at=datetime.now(timezone.utc)-timedelta(minutes=1)
    response=client.post(f"/api/v1/access-requests/{row.id}/review",json={"decision":"approve"})
    assert response.status_code==409 and row.status=="pending" and db.commits==0


def test_legacy_null_beneficiary_is_read_as_requester(route):
    client, _, row, _=route
    row.requested_for=None
    response=client.get(f"/api/v1/access-requests/{row.id}")
    assert response.status_code==200
    assert response.json()["requested_for"]==str(row.requested_by)


def test_non_admin_cannot_review(route):
    client, caller, row, db=route
    object.__setattr__(caller,"roles",())
    assert client.post(f"/api/v1/access-requests/{row.id}/review",json={"decision":"approve"}).status_code==403
    assert db.added==[] and db.commits==0
