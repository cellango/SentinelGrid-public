"""Secondary catalog writers and legacy scheduling cannot bypass IAM admission."""

import asyncio
import inspect
from unittest.mock import Mock
from uuid import uuid4
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app.api import iam_portal
from app.api.request_context import (
    RequestContext,
    get_current_request_context,
    get_tenant_session,
)
from app.core.config import settings, Settings
from app.services.iam_portal_service import IAMPortalService
from app.services import lifecycle_scheduler
from app.services.connector_framework import SyncJob, SyncDirection, SyncStatus
from app.services.sync_job_manager import SyncJobManager

CATALOG_WRITERS = [
    "grant_entitlement",
    "revoke_entitlement",
    "_assign_access_profile_to_user",
    "create_access_request",
    "approve_access_request",
    "deny_access_request",
    "reapply_birthrights",
    "offboard_user",
    "bulk_update_users",
    "set_lifecycle_schedule",
    "apply_lifecycle_schedules",
]


@pytest.mark.parametrize("name", CATALOG_WRITERS)
def test_direct_catalog_writer_stops_before_sql_or_provider(name):
    service = IAMPortalService.__new__(IAMPortalService)
    service.db, service.keycloak = Mock(), Mock()
    service.tenant_id = uuid4()
    method = getattr(service, name)
    kwargs = {
        n: None
        for n, p in inspect.signature(method).parameters.items()
        if p.default is inspect.Parameter.empty
    }
    with pytest.raises(HTTPException) as error:
        result = method(**kwargs)
        if inspect.isawaitable(result):
            asyncio.run(result)
    assert error.value.status_code == 501
    assert service.db.mock_calls == [] and service.keycloak.mock_calls == []


CATALOG_ROUTES = [
    (
        "POST",
        "/users/synthetic/entitlements",
        {"user_id": "foreign", "entitlement_id": str(uuid4())},
    ),
    ("DELETE", "/users/synthetic/entitlements/" + str(uuid4()), None),
    ("POST", "/users/synthetic/birthrights/reapply", None),
    ("POST", "/users/synthetic/offboard", None),
    ("POST", "/users/bulk/actions", {"action": "offboard", "user_ids": ["synthetic"]}),
    ("POST", "/users/synthetic/lifecycle", {"deactivate_at": "2028-01-01T00:00:00Z"}),
    ("POST", "/users/lifecycle/run", None),
    (
        "POST",
        "/access-requests",
        {"entitlement_id": str(uuid4()), "reason": "synthetic"},
    ),
    ("POST", "/access-requests/" + str(uuid4()) + "/approve", None),
    ("POST", "/access-requests/" + str(uuid4()) + "/deny", None),
]


@pytest.mark.parametrize("method,path,body", CATALOG_ROUTES)
@pytest.mark.parametrize("roles,status", [(("TENANT_ADMIN",), 501), ((), 403)])
def test_catalog_routes_reject_before_legacy_database_or_provider(
    method, path, body, roles, status, monkeypatch
):
    from app.middleware.admin_audit import AdminAuditMiddleware
    from app.services import keycloak_client

    provider = Mock(side_effect=AssertionError("Unexpected provider constructor"))
    monkeypatch.setattr(keycloak_client, "KeycloakClient", provider)
    app = FastAPI()
    app.include_router(iam_portal.router)
    app.add_middleware(AdminAuditMiddleware)
    context = RequestContext(uuid4(), str(uuid4()), roles)
    app.dependency_overrides[get_current_request_context] = lambda: context
    forbidden = Mock(
        side_effect=AssertionError("Legacy service/database must not initialize")
    )
    app.dependency_overrides[iam_portal.get_iam_service] = forbidden
    app.dependency_overrides[get_tenant_session] = forbidden
    with TestClient(app) as client:
        response = client.request(
            method,
            "/api/iam-portal" + path,
            **({"json": body} if body is not None else {}),
        )
    assert response.status_code == status, response.text
    assert forbidden.mock_calls == [] and provider.mock_calls == []


def test_catalog_internal_service_and_body_do_not_invent_user_authority():
    app = FastAPI()
    app.include_router(iam_portal.router)
    app.dependency_overrides[get_current_request_context] = lambda: RequestContext(
        uuid4(), None, ("INTERNAL_SERVICE",)
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/iam-portal/users/lifecycle/run",
            json={"approved": True, "roles": ["PLATFORM_ADMIN"]},
        )
    assert response.status_code == 401


@pytest.mark.parametrize("kind", ["users", "groups", "full"])
def test_direct_sync_job_cannot_execute_preloaded_connector(kind):
    connector = Mock()
    job = SyncJob("synthetic", connector, kind, SyncDirection.IMPORT)
    with pytest.raises(HTTPException) as error:
        job.execute()
    assert error.value.status_code == 501 and connector.mock_calls == []
    assert job.status == SyncStatus.PENDING and job.started_at is None
    assert job.result is None and job.completed_at is None


def test_sync_manager_cannot_run_or_mutate_preloaded_state():
    integration = Mock()
    manager = SyncJobManager(integration)
    job = Mock()
    manager.jobs["preloaded"] = job
    manager.schedules["preloaded"] = {"tenant_id": str(uuid4()), "enabled": True}
    for name, method in inspect.getmembers(manager, inspect.ismethod):
        if name == "__init__":
            continue
        kwargs = {
            n: None
            for n, p in inspect.signature(method).parameters.items()
            if p.default is inspect.Parameter.empty
        }
        with pytest.raises(HTTPException) as error:
            method(**kwargs)
        assert error.value.status_code == 501
    assert integration.mock_calls == [] and job.mock_calls == []
    assert (
        manager.jobs["preloaded"] is job
        and manager.schedules["preloaded"]["enabled"] is True
    )


@pytest.mark.parametrize("flag", [False, True])
def test_lifecycle_flag_cannot_reenable_unqualified_background_effects(
    monkeypatch, flag
):
    monkeypatch.setattr(settings, "LIFECYCLE_JOB_ENABLED", flag)
    db = Mock(side_effect=AssertionError("No database access"))
    task = Mock(side_effect=AssertionError("No background task"))
    monkeypatch.setattr(lifecycle_scheduler, "SessionLocal", db)
    monkeypatch.setattr(lifecycle_scheduler.asyncio, "create_task", task)
    lifecycle_scheduler.start_scheduler()
    for method in [
        lifecycle_scheduler.run_lifecycle_once,
        lifecycle_scheduler._lifecycle_loop,
    ]:
        with pytest.raises(HTTPException) as error:
            asyncio.run(method())
        assert error.value.status_code == 501
    assert db.mock_calls == [] and task.mock_calls == []


def test_legacy_scheduler_defaults_off(monkeypatch):
    monkeypatch.delenv("LIFECYCLE_JOB_ENABLED", raising=False)
    assert Settings(_env_file=None).LIFECYCLE_JOB_ENABLED is False
