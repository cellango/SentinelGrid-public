"""Tests for OAuth API endpoints."""

from importlib import import_module
import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.api import connectors as connectors_api
from app.models.connector import ConnectorConfig


class TestOAuthAPI:
    """Test suite for OAuth endpoints."""
    
    @patch('app.services.oauth_service.OAuthService.init_google_workspace_oauth')
    def test_init_oauth_google_workspace(self, mock_init, client, test_db):
        """Test initializing Google Workspace OAuth flow."""
        tenant_id = str(uuid4())
        
        mock_init.return_value = {
            "oauth_url": "https://accounts.google.com/o/oauth2/auth?state=test",
            "state_token": "test-state-token"
        }
        
        response = client.post(
            "/api/v1/connectors/oauth/init",
            json={
                "provider": "google_workspace",
                "tenant_id": tenant_id,
                "redirect_uri": "http://localhost:3000/onboarding/oauth/callback"
            },
            headers={"X-Tenant-ID": tenant_id},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "oauth_url" in data
        assert "state_token" in data
        assert data["oauth_url"].startswith("https://accounts.google.com")
    
    def test_init_oauth_unsupported_provider(self, client):
        """Test initializing OAuth with unsupported provider."""
        tenant_id = str(uuid4())
        response = client.post(
            "/api/v1/connectors/oauth/init",
            json={
                "provider": "unsupported_provider",
                "tenant_id": tenant_id,
                "redirect_uri": "http://localhost:3000/callback"
            },
            headers={"X-Tenant-ID": tenant_id},
        )
        
        assert response.status_code == 400
        assert "Unsupported provider" in response.json()["detail"]
    
    @patch('app.services.oauth_service.OAuthService.handle_google_workspace_callback')
    def test_oauth_callback_success(self, mock_callback, client, test_db):
        """Test OAuth callback handling."""
        tenant_id = str(uuid4())

        def override_resolve_oauth_callback_tenant():
            return tenant_id

        def override_get_oauth_callback_tenant_session():
            yield test_db

        app.dependency_overrides[connectors_api.resolve_oauth_callback_tenant] = (
            override_resolve_oauth_callback_tenant
        )
        app.dependency_overrides[connectors_api.get_oauth_callback_tenant_session] = (
            override_get_oauth_callback_tenant_session
        )

        mock_callback.return_value = {
            "status": "connected",
            "connector_id": str(uuid4()),
            "users_synced": 45,
            "last_sync": "2025-01-28T10:00:00Z"
        }

        try:
            response = client.post(
                "/api/v1/connectors/oauth/callback",
                json={
                    "provider": "google_workspace",
                    "code": "test-auth-code",
                    "state": "test-state-token"
                }
            )
        finally:
            app.dependency_overrides.pop(connectors_api.resolve_oauth_callback_tenant, None)
            app.dependency_overrides.pop(connectors_api.get_oauth_callback_tenant_session, None)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected"
        assert "connector_id" in data

    @patch('app.services.oauth_service.OAuthService.handle_google_workspace_callback')
    def test_oauth_callback_uses_resolved_tenant_scope(self, mock_callback, client, test_db):
        """Test OAuth callback resolves tenant scope before DB work."""
        tenant_id = str(uuid4())
        calls = {"tenant": 0, "session": 0}

        def override_resolve_oauth_callback_tenant():
            calls["tenant"] += 1
            return tenant_id

        def override_get_oauth_callback_tenant_session():
            calls["session"] += 1
            yield test_db

        app.dependency_overrides[connectors_api.resolve_oauth_callback_tenant] = override_resolve_oauth_callback_tenant
        app.dependency_overrides[connectors_api.get_oauth_callback_tenant_session] = override_get_oauth_callback_tenant_session

        mock_callback.return_value = {
            "status": "connected",
            "connector_id": str(uuid4()),
            "users_synced": 12,
            "last_sync": "2025-01-28T10:00:00Z",
        }

        try:
            response = client.post(
                "/api/v1/connectors/oauth/callback",
                json={
                    "provider": "google_workspace",
                    "code": "test-auth-code",
                    "state": "state-token",
                }
            )
        finally:
            app.dependency_overrides.pop(connectors_api.resolve_oauth_callback_tenant, None)
            app.dependency_overrides.pop(connectors_api.get_oauth_callback_tenant_session, None)

        assert response.status_code == 200
        assert calls == {"tenant": 1, "session": 1}
    
    def test_oauth_callback_invalid_provider(self, client):
        """Test OAuth callback with invalid provider."""
        response = client.post(
            "/api/v1/connectors/oauth/callback",
            json={
                "provider": "invalid_provider",
                "code": "test-code",
                "state": "test-state"
            }
        )
        
        assert response.status_code == 400
    
    @patch('app.services.oauth_service.OAuthService._oauth_states', {})
    def test_oauth_callback_invalid_state(self, client):
        """Test OAuth callback with invalid state token."""
        response = client.post(
            "/api/v1/connectors/oauth/callback",
            json={
                "provider": "google_workspace",
                "code": "test-code",
                "state": "invalid-state-token"
            }
        )
        
        # Should fail because state token doesn't exist
        assert response.status_code in [400, 500]


class TestConnectorTestEndpoint:
    """Test suite for connector test endpoint."""
    
    def test_test_connector_not_found(self, client, test_db):
        """Test testing non-existent connector."""
        connector_id = str(uuid4())
        
        response = client.post(
            f"/api/v1/connectors/{connector_id}/test",
            headers={"X-Tenant-ID": str(uuid4())},
        )
        
        assert response.status_code == 404
    
    def test_test_connector_google_workspace(self, client, test_db):
        """Test testing Google Workspace connector."""
        from uuid import UUID
        
        tenant_id = str(uuid4())
        connector = ConnectorConfig(
            tenant_id=UUID(tenant_id),
            type="google_workspace",
            name="Google Workspace",
            credentials={"token": "test"},
            status="active",
        )
        test_db.add(connector)
        test_db.commit()
        test_db.refresh(connector)
        
        # Mock connector instance
        google_workspace_module = import_module("app.connectors.google_workspace")
        mock_connector = Mock()
        mock_connector.test_connection.return_value = True
        mock_connector.fetch_users.return_value = [
            {"id": "1", "email": "user@test.com"}
        ]

        with patch.object(
            google_workspace_module,
            "GoogleWorkspaceConnector",
            return_value=mock_connector,
        ):
            response = client.post(
                f"/api/v1/connectors/{connector.id}/test",
                headers={"X-Tenant-ID": tenant_id},
            )
        
        assert response.status_code == 200
