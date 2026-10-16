"""
Tests for API Gateway Authentication Middleware
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException

from app.api import routes_alerts


class TestAuthenticationMiddleware:
    """Test suite for authentication middleware."""
    
    def test_health_check_no_auth_required(self, client):
        """Test that health check endpoint doesn't require authentication."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "api-gateway"
    
    def test_root_endpoint_no_auth_required(self, client):
        """Test that root endpoint doesn't require authentication."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    def test_protected_endpoint_requires_tenant(self, auth_client):
        """Protected endpoints should reject requests with no Authorization token."""
        response = auth_client.get("/api/v1/alerts/")

        assert response.status_code == 401
        assert response.json() == {"detail": "Missing Authorization token"}

    def test_get_current_tenant_with_valid_token(self, auth_client, mock_db_session, token_payload_factory):
        """Valid tokens should allow the protected route to resolve tenant scope."""
        with patch("sg_core.security.verify_token", return_value=token_payload_factory()) as mock_verify, patch.object(
            routes_alerts,
            "AlertService",
        ) as mock_service_class:
            mock_service = Mock()
            mock_service.list_alerts.return_value = ([], 0)
            mock_service_class.return_value = mock_service

            response = auth_client.get(
                "/api/v1/alerts/",
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == 200
        mock_verify.assert_called_once_with("valid-token")
        mock_service_class.assert_called_once_with(mock_db_session, "tenant-123")

    def test_get_current_tenant_with_invalid_token(self, auth_client):
        """Invalid tokens should be rejected before the protected handler runs."""
        with patch(
            "sg_core.security.verify_token",
            side_effect=HTTPException(status_code=401, detail="Invalid token"),
        ):
            response = auth_client.get(
                "/api/v1/alerts/",
                headers={"Authorization": "Bearer invalid-token"},
            )

        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid token"}

    def test_get_current_tenant_missing_tenant_id(self, auth_client, token_payload_factory):
        """Tokens without tenant_id should fail with a tenant-scoped auth error."""
        with patch(
            "sg_core.security.verify_token",
            return_value=token_payload_factory(tenant_id=None),
        ):
            response = auth_client.get(
                "/api/v1/alerts/",
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == 403
        assert response.json()["detail"] == "No tenant_id in token. User must be assigned to a tenant."

    def test_cookie_backed_session_is_resolved_when_authorization_header_is_missing(
        self,
        auth_client,
        mock_db_session,
        token_payload_factory,
    ):
        with patch("sg_core.security.verify_token", return_value=token_payload_factory()) as mock_verify, patch.object(
            routes_alerts,
            "AlertService",
        ) as mock_service_class:
            mock_service = Mock()
            mock_service.list_alerts.return_value = ([], 0)
            mock_service_class.return_value = mock_service

            response = auth_client.get(
                "/api/v1/alerts/",
                cookies={"access_token": "cookie-backed-token"},
            )

        assert response.status_code == 200
        mock_verify.assert_called_once_with("cookie-backed-token")
        mock_service_class.assert_called_once_with(mock_db_session, "tenant-123")

    def test_cookie_backed_session_replaces_frontend_session_marker_header(
        self,
        auth_client,
        mock_db_session,
        token_payload_factory,
    ):
        with patch("sg_core.security.verify_token", return_value=token_payload_factory()) as mock_verify, patch.object(
            routes_alerts,
            "AlertService",
        ) as mock_service_class:
            mock_service = Mock()
            mock_service.list_alerts.return_value = ([], 0)
            mock_service_class.return_value = mock_service

            response = auth_client.get(
                "/api/v1/alerts/",
                headers={"Authorization": "Bearer session-cookie"},
                cookies={"access_token": "cookie-backed-token"},
            )

        assert response.status_code == 200
        mock_verify.assert_called_once_with("cookie-backed-token")
        mock_service_class.assert_called_once_with(mock_db_session, "tenant-123")


class TestTenantContext:
    """Test suite for tenant context management."""
    
    def test_tenant_id_passed_to_service(self, client, mock_db_session):
        """Test that tenant_id is passed to service layer."""
        with patch.object(routes_alerts, "AlertService") as mock_service_class:
            mock_service = Mock()
            mock_service.list_alerts.return_value = ([], 0)
            mock_service_class.return_value = mock_service

            response = client.get("/api/v1/alerts/")

        assert response.status_code == 200
        mock_service_class.assert_called_once_with(mock_db_session, "tenant-123")

    def test_tenant_isolation_in_alerts(self, client, mock_db_session):
        """Test that tenants only see their own alerts."""
        with patch.object(routes_alerts, "AlertService") as mock_service_class:
            mock_service = Mock()
            mock_service.list_alerts.return_value = ([], 0)
            mock_service_class.return_value = mock_service

            response = client.get(
                "/api/v1/alerts/",
                headers={"x-tenant-id": "tenant-foreign"},
            )

        assert response.status_code == 200
        mock_service_class.assert_called_once_with(mock_db_session, "tenant-123")
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are configured."""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code in [200, 204]
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert response.headers.get("access-control-allow-credentials") == "true"
    
    def test_cors_allows_configured_origins(self, client):
        """Test CORS allows configured origins."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_cors_does_not_reflect_unconfigured_origin(self, client):
        """Test that non-allowlisted origins do not receive CORS access headers."""
        response = client.get(
            "/health",
            headers={"Origin": "https://evil.example"}
        )

        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") is None
