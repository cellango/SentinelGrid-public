"""Unreviewed HTTP surfaces cannot inherit permission from a module or prefix."""

import ast
import asyncio
from pathlib import Path
import os
import subprocess
from unittest.mock import Mock
from uuid import uuid4
import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from app.api import scim, ai_editor, policies, iam_portal, privileged_access
from app.api.auth import get_token_validator
from app.api.request_context import RequestContext, get_current_request_context
from app.core.source_admission import (
    REVIEWED_SOURCE_ROUTES,
    include_source_router,
    source_review_lifespan,
)

ROOT = Path(__file__).resolve().parents[4]


def app_with_context():
    app = FastAPI()
    app.dependency_overrides[get_current_request_context] = lambda: RequestContext(
        uuid4(), str(uuid4()), ("TENANT_ADMIN",)
    )
    return app


@pytest.mark.parametrize(
    "roles", [(), ("TENANT_ADMIN",), ("PLATFORM_ADMIN",), ("INTERNAL_SERVICE",)]
)
def test_unlisted_route_blocks_before_provider_database_and_handler(roles, monkeypatch):
    app = app_with_context()
    router = APIRouter(prefix="/api/v1/entitlements")
    observed = Mock()

    def provider():
        observed("provider")
        raise AssertionError("Provider must not initialize")

    @router.post("/new-power")
    def new_power(body: dict, service=Depends(provider)):
        observed("handler")
        return {"executed": True}

    # Reusing an admitted router identifier or environment switch cannot admit
    # a new path, method or endpoint.
    monkeypatch.setenv("IAM_ENABLE_ALL_ROUTES", "true")
    app.dependency_overrides[get_current_request_context] = lambda: RequestContext(
        uuid4(), str(uuid4()), roles
    )
    include_source_router(app, "entitlements.router", router)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/entitlements/new-power",
            json={
                "tenant_id": str(uuid4()),
                "reviewed": True,
                "approved": True,
                "roles": ["PLATFORM_ADMIN"],
            },
            headers={"X-Tenant-ID": str(uuid4())},
        )
    assert response.status_code == 501
    assert observed.mock_calls == []
    assert app.state.iam_source_routes[0]["reviewed"] is False


def test_missing_auth_and_invalid_token_do_not_reach_unlisted_handler():
    app = FastAPI()
    router = APIRouter()
    effect = Mock()

    @router.post("/legacy")
    def legacy():
        effect()
        return {"executed": True}

    include_source_router(app, "legacy.router", router)
    validator = Mock()
    validator.validate_token.return_value = {"valid": False}
    app.dependency_overrides[get_token_validator] = lambda: validator
    with TestClient(app) as client:
        assert client.post("/legacy").status_code == 401
        assert (
            client.post(
                "/legacy", headers={"Authorization": "Bearer invalid"}
            ).status_code
            == 401
        )
    effect.assert_not_called()


def test_actual_JIT_routes_are_denied_before_service_construction(monkeypatch):
    app = app_with_context()
    service = Mock(side_effect=AssertionError("No runtime DDL or grant"))
    monkeypatch.setattr(privileged_access, "PrivilegedAccessService", service)
    include_source_router(app, "privileged_access.router", privileged_access.router)
    with TestClient(app) as client:
        result = client.post(
            "/api/v1/privileged-access/request",
            json={
                "resource_type": "role",
                "resource_id": "admin",
                "reason": "synthetic privilege request",
                "duration_hours": 1,
            },
        )
    assert result.status_code == 501, result.text
    service.assert_not_called()


def test_SCIM_opaque_auth_and_custom_route_class_are_preserved():
    app = FastAPI()
    include_source_router(app, "scim.router", scim.router)
    with TestClient(app) as client:
        metadata = client.get("/api/v1/scim/v2/ServiceProviderConfig")
        missing = client.get("/api/v1/scim/v2/Users")
    assert (
        metadata.status_code == 200 and metadata.json()["patch"]["supported"] is False
    )
    assert missing.status_code == 401 and missing.headers["cache-control"] == "no-store"
    assert "scim+json" in missing.headers["content-type"]


def test_editor_custom_error_headers_and_default_off_are_preserved(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "IAM_ENABLE_AI_EDITOR", False)
    app = app_with_context()
    include_source_router(app, "ai_editor.router", ai_editor.router)
    with TestClient(app) as client:
        result = client.post(
            "/api/v1/ai/editor/generate", json={"description": "Draft a deny policy"}
        )
    assert result.status_code == 501 and result.headers["cache-control"] == "no-store"
    assert "disabled" in result.text


def test_policy_templates_are_not_shadowed_by_policy_id_and_legacy_alias():
    app = app_with_context()
    service = Mock()
    service.list_templates.return_value = []
    app.dependency_overrides[policies.get_policy_service] = lambda: service
    legacy = Mock(side_effect=AssertionError("Legacy policy owner must not initialize"))
    app.dependency_overrides[iam_portal.get_iam_service] = legacy
    include_source_router(app, "iam_policies.router", policies.router)
    include_source_router(app, "iam_portal.router", iam_portal.router)
    with TestClient(app) as client:
        response = client.get("/api/iam-portal/policies/templates")
    assert response.status_code == 200, response.text
    service.list_templates.assert_called_once_with(None)
    legacy.assert_not_called()
    aliases = [
        r
        for r in app.state.iam_source_routes
        if r["router_id"] == "iam_portal.router"
        and r["path"] == "/api/iam-portal/policies"
    ]
    assert aliases and all(not r["mounted"] for r in aliases)


def test_unreviewed_alias_cannot_add_a_method_through_overlap():
    app = FastAPI()
    effect = Mock()
    router = APIRouter()

    @router.api_route("/api/v1/scim/v2/ServiceProviderConfig", methods=["GET", "POST"])
    def alias():
        effect()
        return {"executed": True}

    include_source_router(app, "scim.router", scim.router)
    include_source_router(app, "legacy.router", router)
    with TestClient(app) as client:
        assert client.get("/api/v1/scim/v2/ServiceProviderConfig").status_code == 200
        assert client.post("/api/v1/scim/v2/ServiceProviderConfig").status_code == 405
    effect.assert_not_called()


def test_reviewed_route_cannot_silently_replace_an_earlier_legacy_mount():
    app = FastAPI()
    router = APIRouter()

    @router.get("/api/v1/scim/v2/ServiceProviderConfig")
    def alias():
        return {}

    include_source_router(app, "legacy.router", router)
    with pytest.raises(ValueError, match="precede"):
        include_source_router(app, "scim.router", scim.router)


@pytest.mark.parametrize(
    "kind", ["startup", "shutdown", "lifespan", "websocket", "nested"]
)
def test_new_startup_or_transport_surface_requires_separate_admission(kind):
    router = APIRouter()
    effect = Mock()
    if kind == "startup":
        router.on_startup.append(effect)
    elif kind == "shutdown":
        router.on_shutdown.append(effect)
    elif kind == "lifespan":
        router.lifespan_context = source_review_lifespan
    elif kind == "websocket":

        @router.websocket("/ws")
        async def websocket(websocket):
            effect()
    else:
        child = APIRouter()

        @child.get("/nested")
        def nested():
            effect()

        router.include_router(child)
    with pytest.raises(ValueError):
        include_source_router(FastAPI(), "legacy.router", router)
    effect.assert_not_called()


def test_lifespan_creates_no_tasks_and_does_not_seed_or_connect(monkeypatch):
    task = Mock(side_effect=AssertionError("No task creation"))
    monkeypatch.setattr(asyncio, "create_task", task)

    async def run():
        async with source_review_lifespan(FastAPI()):
            pass

    asyncio.run(run())
    task.assert_not_called()


@pytest.mark.parametrize("mode", ["auto", "flyway", "docker", "psql", "unknown"])
def test_legacy_migration_launcher_refuses_every_mode_without_executing_tools(
    tmp_path, mode
):
    marker = tmp_path / "invoked"
    fake = tmp_path / "bin"
    fake.mkdir()
    for name in ["flyway", "docker", "psql", "cat"]:
        path = fake / name
        path.write_text("#!/bin/sh\n/bin/echo invoked >> " + str(marker) + "\n")
        path.chmod(0o700)
    env = {
        **os.environ,
        "PATH": str(fake),
        "SCHEMA_MIGRATION_MODE": mode,
        "DB_URL": "postgresql://synthetic:do-not-print@invalid/synthetic",
        "JDBC_URL": "do-not-print",
    }
    result = subprocess.run(
        ["/bin/bash", str(ROOT / "scripts/flyway_schema_only.sh")],
        env=env,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2 and not marker.exists()
    assert "do-not-print" not in result.stdout + result.stderr
    assert "unavailable" in result.stderr


def test_main_mounts_all_source_routers_through_the_admission_helper():
    main = ROOT / "backend/agents/iam_agent/app/main.py"
    tree = ast.parse(main.read_text())
    mounts = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = ast.unparse(node.func)
            assert name != "app.include_router"
            if name == "include_source_router":
                mounts.append(ast.literal_eval(node.args[1]))
            assert name not in {
                "KeycloakSeeder",
                "start_scheduler",
                "asyncio.create_task",
                "Base.metadata.create_all",
            }
    assert len(mounts) == 57 and len(set(mounts)) == 57
    assert "privileged_access.router" in mounts and "onboarding.router" in mounts
    assert "AdminAuditMiddleware" not in main.read_text()
    assert len(REVIEWED_SOURCE_ROUTES) == 86


def test_canonical_template_provider_failure_is_unavailable_not_empty():
    from fastapi import HTTPException

    app = FastAPI()
    service = Mock()
    service.list_templates.side_effect = HTTPException(
        503, "Policy templates could not be loaded"
    )
    app.dependency_overrides[policies.get_policy_service] = lambda: service
    include_source_router(app, "iam_policies.router", policies.router)
    with TestClient(app) as client:
        response = client.get("/api/iam-portal/policies/templates")
    assert (
        response.status_code == 503 and response.json() != {} and response.json() != []
    )


def test_template_service_storage_error_is_not_an_empty_inventory():
    from app.services.policy_service import PolicyService
    from fastapi import HTTPException

    db = Mock()
    db.execute.side_effect = RuntimeError(
        "synthetic provider credentials must not appear"
    )
    with pytest.raises(HTTPException) as error:
        PolicyService(db, uuid4(), "synthetic").list_templates()
    assert error.value.status_code == 503
    assert "credentials" not in error.value.detail


def test_actual_portal_user_creation_cannot_delete_recreate_or_promote():
    app = app_with_context()
    forbidden = Mock(side_effect=AssertionError("No user/profile/provider operations"))
    app.dependency_overrides[iam_portal.get_iam_service] = forbidden
    include_source_router(app, "iam_portal.router", iam_portal.router)
    with TestClient(app) as client:
        result = client.post(
            "/api/iam-portal/users",
            json={
                "username": "synthetic",
                "email": "user@example.test",
                "tenant_id": str(uuid4()),
                "make_admin": True,
            },
        )
    assert result.status_code == 501, result.text
    forbidden.assert_not_called()


def test_retired_public_reset_stays_410_while_signup_cannot_initialize_provider(
    monkeypatch,
):
    from app.api import auth

    app = app_with_context()
    provider = Mock(side_effect=AssertionError("No signup provider mutation"))
    monkeypatch.setattr(auth, "KeycloakClient", provider)
    include_source_router(app, "auth.public_router", auth.public_router)
    with TestClient(app) as client:
        assert client.post("/api/v1/auth/reset-password-direct").status_code == 410
        signup = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "user@example.test",
                "password": "synthetic-unusable-password",
                "make_admin": True,
            },
        )
    assert signup.status_code == 501, signup.text
    provider.assert_not_called()


def test_verification_dependencies_do_not_initialize_administrator_clients(monkeypatch):
    from app.api import auth
    forbidden=Mock(side_effect=AssertionError('No administrator setup for JWT verification'))
    monkeypatch.setattr(auth,'KeycloakClient',forbidden)
    monkeypatch.setattr(policies,'KeycloakClient',forbidden)
    assert auth.get_token_validator().keycloak_client is None
    assert policies.get_token_validator().keycloak_client is None
    forbidden.assert_not_called()
