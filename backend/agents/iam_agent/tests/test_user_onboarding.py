"""Focused tenant-session tests for user onboarding routes."""

import asyncio
import io
import sys
import types
from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile

python_multipart_stub = types.ModuleType("python_multipart")
python_multipart_stub.__version__ = "0.0.20"
sys.modules.setdefault("python_multipart", python_multipart_stub)

from app.api import user_onboarding


def _request_context():
    return {
        "tenant_id": "test-tenant-123",
        "realm_name": "sg-mt-us-1",
        "user_id": "user-123",
        "email": "admin@example.com",
    }


def _build_client(fake_db=None):
    app = FastAPI()
    app.include_router(user_onboarding.router)
    app.dependency_overrides[user_onboarding.get_current_request_context] = _request_context

    if fake_db is not None:
        def _override_session():
            yield fake_db

        app.dependency_overrides[user_onboarding.get_tenant_session] = _override_session

    client = TestClient(app)
    return client, app


def test_invite_user_no_token():
    """The route still requires bearer auth when no dependency override is present."""
    app = FastAPI()
    app.include_router(user_onboarding.router)
    client = TestClient(app)

    response = client.post(
        "/api/v1/users/invite",
        json={
            "email": "user@example.com",
            "firstName": "Test",
            "lastName": "User",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_invite_user_success_uses_tenant_session(monkeypatch):
    """Invitations should resolve through the tenant-scoped DB dependency."""
    fake_db = object()
    client, app = _build_client(fake_db=fake_db)

    mock_service = Mock()
    mock_service.create_invitation = AsyncMock(
        return_value={
            "invitation_id": "inv-123",
            "email": "user@example.com",
            "invitation_token": "token-123",
            "expires_at": "2025-02-01T00:00:00",
            "status": "pending",
            "user_id": "kc-user-123",
        }
    )
    apply_default_access_profile = Mock()

    monkeypatch.setattr(user_onboarding, "InvitationService", lambda: mock_service)
    monkeypatch.setattr(
        user_onboarding.BirthrightService,
        "apply_default_access_profile",
        apply_default_access_profile,
    )

    response = client.post(
        "/api/v1/users/invite",
        json={
            "email": "user@example.com",
            "firstName": "Test",
            "lastName": "User",
            "send_email": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["invitation_id"] == "inv-123"
    assert data["email"] == "user@example.com"
    apply_default_access_profile.assert_called_once_with(
        fake_db,
        tenant_id="test-tenant-123",
        user_id="kc-user-123",
        granted_by="user-123",
    )
    app.dependency_overrides.clear()


def test_bulk_upload_users_uses_tenant_session(monkeypatch):
    """Bulk upload should be wired to the tenant-scoped DB dependency."""
    app = FastAPI()
    app.include_router(user_onboarding.router)

    bulk_upload_route = next(
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path == "/api/v1/users/bulk-upload"
    )
    dependency_calls = {dependency.call for dependency in bulk_upload_route.dependant.dependencies}

    assert user_onboarding.get_tenant_session in dependency_calls


def test_bulk_upload_users_applies_birthright_with_tenant_session(monkeypatch):
    """Bulk upload should pass the tenant-scoped DB handle into birthright writes."""
    fake_db = object()

    mock_service = Mock()
    mock_service.import_users = AsyncMock(
        return_value={
            "total_rows": 2,
            "successful": 2,
            "failed": 0,
            "errors": [],
            "created_users": [
                {"user_id": "user-a"},
                {"user_id": "user-b"},
            ],
        }
    )
    apply_default_access_profile = Mock()

    monkeypatch.setattr(user_onboarding, "BulkImportService", lambda: mock_service)
    monkeypatch.setattr(
        user_onboarding.BirthrightService,
        "apply_default_access_profile",
        apply_default_access_profile,
    )

    csv_content = (
        "email,firstName,lastName,role\n"
        "user1@example.com,John,Doe,SOC_ANALYST\n"
        "user2@example.com,Jane,Smith,SOC_MANAGER\n"
    )
    upload_file = UploadFile(
        filename="users.csv",
        file=io.BytesIO(csv_content.encode("utf-8")),
        headers={"content-type": "text/csv"},
    )

    response = asyncio.run(
        user_onboarding.bulk_upload_users(
            file=upload_file,
            ctx=_request_context(),
            db=fake_db,
        )
    )

    assert response.total_rows == 2
    assert response.successful == 2
    assert response.failed == 0
    assert apply_default_access_profile.call_count == 2
    apply_default_access_profile.assert_any_call(
        fake_db,
        tenant_id="test-tenant-123",
        user_id="user-a",
        granted_by="user-123",
    )
    apply_default_access_profile.assert_any_call(
        fake_db,
        tenant_id="test-tenant-123",
        user_id="user-b",
        granted_by="user-123",
    )


def test_list_invitations(monkeypatch):
    """Invitation listing should continue to use the authenticated tenant context."""
    client, app = _build_client()

    mock_service = Mock()
    mock_service.list_invitations = AsyncMock(
        return_value={
            "items": [
                {
                    "invitation_id": "inv-1",
                    "email": "user1@example.com",
                    "invitation_token": "token-1",
                    "expires_at": "2025-02-01T00:00:00",
                    "status": "pending",
                }
            ],
            "total": 1,
        }
    )
    monkeypatch.setattr(user_onboarding, "InvitationService", lambda: mock_service)

    response = client.get("/api/v1/users/invitations")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["total"] == 1
    app.dependency_overrides.clear()
