"""Legacy sync routes cannot create a connector or fabricate successful status."""

from unittest.mock import Mock
from uuid import uuid4
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api import sync_jobs
from app.api.request_context import RequestContext, get_current_request_context
from app.api.auth import get_keycloak_client

ROUTES = [
    ("post", "/", {"integration_id": "synthetic", "sync_type": "full"}),
    ("post", "/job/execute", None),
    ("get", "/", None),
    ("get", "/job", None),
    (
        "post",
        "/schedules",
        {"integration_id": "synthetic", "schedule_type": "daily", "sync_type": "users"},
    ),
    ("get", "/schedules", None),
    ("get", "/schedules/synthetic", None),
    ("put", "/schedules/synthetic", {"enabled": True}),
    ("delete", "/schedules/synthetic", None),
    ("get", "/statistics", None),
    ("post", "/job/retry", None),
]


@pytest.mark.parametrize("method,path,body", ROUTES)
@pytest.mark.parametrize("roles,status", [(("TENANT_ADMIN",), 501), ((), 403)])
def test_sync_routes_have_no_job_or_provider_dependency(
    method, path, body, roles, status
):
    app = FastAPI()
    app.include_router(sync_jobs.router)
    app.dependency_overrides[get_current_request_context] = lambda: RequestContext(
        uuid4(), str(uuid4()), roles
    )
    forbidden = Mock(
        side_effect=AssertionError(
            "Unavailable paths cannot construct provider/job dependencies"
        )
    )
    app.dependency_overrides[get_keycloak_client] = forbidden
    app.dependency_overrides[sync_jobs.get_sync_job_manager] = forbidden
    with TestClient(app) as client:
        response = client.request(
            method,
            "/internal/iam/sync-jobs" + path,
            **({"json": body} if body is not None else {}),
        )
    assert response.status_code == status, response.text
    assert forbidden.mock_calls == []


@pytest.mark.parametrize(
    "method,path,body",
    [
        (
            "post",
            "/",
            {
                "integration_id": "synthetic",
                "sync_type": "users",
                "tenant_id": str(uuid4()),
            },
        ),
        ("get", "/?tenant_id=" + str(uuid4()), None),
    ],
)
def test_foreign_tenant_input_is_rejected_before_unavailable_outcome(
    method, path, body
):
    app = FastAPI()
    app.include_router(sync_jobs.router)
    app.dependency_overrides[get_current_request_context] = lambda: RequestContext(
        uuid4(), str(uuid4()), ("TENANT_ADMIN",)
    )
    with TestClient(app) as client:
        response = client.request(
            method,
            "/internal/iam/sync-jobs" + path,
            **({"json": body} if body is not None else {}),
        )
    assert response.status_code == 403
    assert "Tenant mismatch" in response.text
