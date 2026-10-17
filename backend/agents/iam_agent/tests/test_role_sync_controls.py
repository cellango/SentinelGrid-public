"""Role authority and shared definition admission regressions."""

from uuid import uuid4
from unittest.mock import Mock
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app.api import role_mappings as api
from app.api.request_context import (
    RequestContext,
    get_current_request_context,
    get_entitlement_session,
)
from app.services.policy_service import PolicyService
from app.services.iam_portal_service import IAMPortalService


@pytest.fixture
def route():
    caller = RequestContext(uuid4(), str(uuid4()), ())
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = None
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[get_current_request_context] = lambda: caller
    app.dependency_overrides[get_entitlement_session] = lambda: db
    with TestClient(app) as client:
        yield client, caller, db


def body(caller):
    return dict(
        role_name="reader",
        tenant_id=str(caller.tenant_id),
        entitlement_pattern="document:*:read",
        created_by=str(uuid4()),
    )


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", ""),
        ("get", ""),
        ("get", "/{id}"),
        ("put", "/{id}"),
        ("delete", "/{id}"),
        ("post", "/sync/user"),
        ("post", "/sync/role"),
    ],
)
def test_role_mutation_and_inventory_require_admin(route, method, path):
    client, caller, db = route
    payload = body(caller)
    if path == "/sync/user":
        payload = dict(
            user_id=str(uuid4()),
            tenant_id=str(caller.tenant_id),
            granted_by=str(uuid4()),
        )
    elif path == "/sync/role":
        payload = dict(
            role_name="reader", tenant_id=str(caller.tenant_id), granted_by=str(uuid4())
        )
    kwargs = {"json": payload} if method in {"post", "put"} else {}
    assert (
        getattr(client, method)(
            "/api/v1/role-mappings" + path.format(id=uuid4()), **kwargs
        ).status_code
        == 403
    )
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize(
    "value",
    [
        "document:bad*:read",
        "document:read",
        "document::read",
        "document:{tenant_id}:read",
    ],
)
def test_pattern_language_is_bounded_and_explicit(route, value):
    client, caller, db = route
    payload = body(caller)
    payload["entitlement_pattern"] = value
    assert client.post("/api/v1/role-mappings", json=payload).status_code == 422
    db.add.assert_not_called()


@pytest.mark.parametrize(
    "service,method",
    [
        (PolicyService, "list_seed_policies"),
        (PolicyService, "clone_seed_policy"),
        (IAMPortalService, "list_policy_bundles"),
        (IAMPortalService, "clone_policy_bundle"),
    ],
)
def test_cross_tenant_seed_paths_are_explicitly_blocked_without_sql(service, method):
    instance = service.__new__(service)
    instance.db = Mock()
    instance.tenant_id = uuid4()
    instance.sg_admin_tenant_id = uuid4()
    with pytest.raises(HTTPException) as error:
        getattr(instance, method)(
            uuid4(), str(uuid4())
        ) if "clone" in method else getattr(instance, method)()
    assert error.value.status_code == 503
    instance.db.execute.assert_not_called()
