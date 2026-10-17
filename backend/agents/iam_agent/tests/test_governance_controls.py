"""Governance admission must precede database mutation."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api import governance as api
from app.api.request_context import (
    RequestContext,
    get_current_request_context,
    get_entitlement_session,
)


@pytest.fixture
def route():
    caller = RequestContext(uuid4(), str(uuid4()), ())

    class Storage:
        def __init__(self):
            self.added = []
            self.criteria = []

        def query(self, *args):
            return self

        def join(self, *args):
            return self

        def filter(self, *args):
            self.criteria.extend(args)
            return self

        def order_by(self, *args):
            return self

        def offset(self, *args):
            return self

        def limit(self, *args):
            return self

        def populate_existing(self):
            return self

        def with_for_update(self, *args, **kwargs):
            return self

        def all(self):
            return []

        def first(self):
            return None

        def add(self, value):
            self.added.append(value)

        def rollback(self):
            pass

    db = Storage()
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[get_current_request_context] = lambda: caller
    app.dependency_overrides[get_entitlement_session] = lambda: db
    with TestClient(app) as client:
        yield client, caller, db


def payload(caller):
    now = datetime.now(timezone.utc)
    return dict(
        tenant_id=str(caller.tenant_id),
        name="Synthetic review",
        start_date=now.isoformat(),
        end_date=(now + timedelta(days=1)).isoformat(),
        reviewer_type="self",
    )


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/campaigns"),
        ("get", "/campaigns"),
        ("get", "/campaigns/{id}"),
        ("put", "/campaigns/{id}"),
        ("post", "/campaigns/{id}/start"),
        ("post", "/campaigns/{id}/complete"),
    ],
)
def test_campaigns_require_current_admin_role(route, method, path):
    client, caller, db = route
    args = (
        {"json": payload(caller)} if path == "/campaigns" and method == "post" else {}
    )
    if method == "put":
        args = {"json": {"name": "Changed name"}}
    response = getattr(client, method)(
        "/api/v1/governance" + path.format(id=uuid4()), **args
    )
    assert response.status_code == 403
    assert db.added == []


@pytest.mark.parametrize(
    "change",
    [
        {"name": "   "},
        {"start_date": "2026-01-01T00:00:00"},
        {"end_date": "2020-01-01T00:00:00Z"},
        {"entitlement_patterns": ["document:bad*id:read"]},
        {"entitlement_patterns": ["document:read"]},
    ],
)
def test_invalid_campaign_contract_is_rejected(route, change):
    client, caller, db = route
    body = payload(caller)
    body.update(change)
    assert client.post("/api/v1/governance/campaigns", json=body).status_code == 422
    assert db.added == []


@pytest.mark.parametrize(
    "body",
    [
        {"status": "completed"},
        {"status": "in_progress"},
        {"name": None},
        {"start_date": None},
        {"reviewer_type": None},
    ],
)
def test_put_cannot_bypass_lifecycle_or_clear_required_fields(route, body):
    client, _, db = route
    assert (
        client.put(f"/api/v1/governance/campaigns/{uuid4()}", json=body).status_code
        == 422
    )
    assert db.added == []


@pytest.mark.parametrize("ids", [[], ["same", "same"]])
def test_bulk_requires_nonempty_distinct_ids(route, ids):
    client, _, db = route
    value = str(uuid4())
    ids = [value for _ in ids]
    assert (
        client.post(
            "/api/v1/governance/certifications/bulk-certify",
            json={"certification_ids": ids, "decision": "approved"},
        ).status_code
        == 422
    )
    assert db.added == []


def test_pending_reviewer_filter_does_not_delegate_visibility(route):
    client, _, _ = route
    assert (
        client.get(
            f"/api/v1/governance/certifications/pending?user_id={uuid4()}"
        ).status_code
        == 403
    )


def test_non_admin_list_is_participant_scoped(route):
    client, caller, db = route
    assert client.get("/api/v1/governance/certifications").status_code == 200

    def values(node):
        return [getattr(node, "value", None)] + [
            v
            for child in getattr(node, "get_children", lambda: [])()
            for v in values(child)
        ]

    assert caller.user_id in {
        str(v) for criterion in db.criteria for v in values(criterion)
    }
