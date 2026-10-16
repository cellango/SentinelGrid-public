"""Focused tenant-isolation coverage for OAuth callback routing."""

from uuid import uuid4
from unittest.mock import patch

from app.api import connectors as connectors_api
from app.main import app


def test_oauth_callback_uses_resolved_tenant_scope(client, test_db):
    """OAuth callback should resolve tenant scope before opening DB access."""
    tenant_id = str(uuid4())
    calls = {"tenant": 0, "session": 0}

    def override_resolve_oauth_callback_tenant():
        calls["tenant"] += 1
        return tenant_id

    def override_get_oauth_callback_tenant_session():
        calls["session"] += 1
        yield test_db

    app.dependency_overrides[connectors_api.resolve_oauth_callback_tenant] = (
        override_resolve_oauth_callback_tenant
    )
    app.dependency_overrides[connectors_api.get_oauth_callback_tenant_session] = (
        override_get_oauth_callback_tenant_session
    )

    try:
        with patch(
            "app.services.oauth_service.OAuthService.handle_google_workspace_callback"
        ) as mock_callback:
            mock_callback.return_value = {
                "status": "connected",
                "connector_id": str(uuid4()),
                "users_synced": 12,
                "last_sync": "2025-01-28T10:00:00Z",
            }

            response = client.post(
                "/api/v1/connectors/oauth/callback",
                json={
                    "provider": "google_workspace",
                    "code": "test-auth-code",
                    "state": "state-token",
                },
            )
    finally:
        app.dependency_overrides.pop(connectors_api.resolve_oauth_callback_tenant, None)
        app.dependency_overrides.pop(
            connectors_api.get_oauth_callback_tenant_session,
            None,
        )

    assert response.status_code == 200
    assert calls == {"tenant": 1, "session": 1}
