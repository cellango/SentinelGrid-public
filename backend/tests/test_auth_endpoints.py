"""
Integration tests for authentication API endpoints.
Tests the IAM Agent auth endpoints with TestClient.
"""

import pytest
pytest.skip(
    "Legacy root auth suite quarantined; replaced by owner-local gateway and IAM auth tests.",
    allow_module_level=True,
)
import sys
import os
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import jwt
from datetime import datetime, timedelta

# Add IAM Agent service directory to path for relative imports
iam_agent_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'agents', 'iam_agent'))
if iam_agent_path not in sys.path:
    sys.path.insert(0, iam_agent_path)

# Add shared libs (sg_core) to path so service imports resolve
libs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'libs'))
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

from app.main import app


class FakeResult:
    """Simple result wrapper to emulate SQLAlchemy fetch methods."""
    def __init__(self, one=None, all=None):
        self._one = one
        self._all = all or []

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._all


class FakeSession:
    """Minimal session stub for signup flow."""
    def execute(self, query, params=None):
        sql = str(query)
        if "information_schema.columns" in sql:
            return FakeResult(all=[
                ("realm_name",),
                ("employee_count",),
                ("compliance_required",),
                ("signup_completed",),
                ("org_count",),
                ("region",),
                ("status",),
            ])
        if "SELECT id FROM tenants" in sql:
            return FakeResult(one=None)
        return FakeResult()

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None


@pytest.fixture(autouse=True)
def configure_settings(monkeypatch):
    """Ensure settings required by auth endpoints are present during tests."""
    from app.core import config
    monkeypatch.setattr(config.settings, "DB_URL", "sqlite:///:memory:", raising=False)
    monkeypatch.setattr(config.settings, "KEYCLOAK_URL", "http://localhost:8081", raising=False)
    yield


@pytest.fixture(autouse=True)
def stub_audit_logging(monkeypatch):
    """Prevent audit service from touching the database during tests."""
    audit_stub = Mock()
    audit_stub.log_auth_event = Mock()
    monkeypatch.setattr("app.services.audit_service.AuditService.log_auth_event", Mock(), raising=False)
    monkeypatch.setattr("app.api.auth.AuditService", audit_stub, raising=False)
    yield


def setup_auth_mocks(mock_kc_admin_cls, mock_mfa_cls=None, mock_audit_service=None, existing_user=None):
    """Configure common mocks for auth endpoints."""
    admin_instance = AsyncMock()
    admin_instance.get_user_by_username = AsyncMock(return_value=existing_user)
    admin_instance.get_user_realm_roles = AsyncMock(return_value=[{"name": "TENANT_ADMIN"}])
    admin_instance.assign_realm_role = AsyncMock(return_value=True)
    admin_instance.create_user = AsyncMock(return_value="user-123")
    admin_instance._make_request = AsyncMock(return_value=None)
    admin_instance.__aenter__ = AsyncMock(return_value=admin_instance)
    admin_instance.__aexit__ = AsyncMock(return_value=None)
    mock_kc_admin_cls.return_value = admin_instance

    if mock_mfa_cls is not None:
        mfa_instance = AsyncMock()
        mfa_instance.evaluate_mfa_requirement = AsyncMock(return_value={"mfa_required": False})
        mock_mfa_cls.return_value = mfa_instance

    if mock_audit_service is not None:
        mock_audit_service.log_auth_event = Mock()

    return admin_instance


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_keycloak_token_response():
    """Mock Keycloak token response."""
    return {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_in": 3600,
        "token_type": "Bearer"
    }


@pytest.fixture
def mock_jwt_payload():
    """Mock JWT payload."""
    return {
        "sub": "user-123",
        "email": "test@example.com",
        "tenant_id": "tenant-456",
        "realm_access": {
            "roles": ["TENANT_ADMIN"]
        },
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.utcnow().timestamp())
    }


class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login."""
    
    @patch('app.api.auth.MFAPolicyService')
    @patch('app.api.auth.KeycloakAdminClient')
    @patch('app.api.auth.httpx.AsyncClient')
    @patch('app.api.auth.jwt.decode')
    def test_login_success(
        self,
        mock_jwt_decode,
        mock_httpx_client,
        mock_kc_admin_cls,
        mock_mfa_cls,
        client,
        mock_keycloak_token_response,
        mock_jwt_payload
    ):
        """Test successful login."""
        setup_auth_mocks(mock_kc_admin_cls, mock_mfa_cls)
        # Mock httpx client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_keycloak_token_response
        
        mock_client_instance = Mock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_httpx_client.return_value = mock_client_instance
        
        # Mock JWT decode
        mock_jwt_decode.return_value = mock_jwt_payload
        
        # Make request
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123",
                "remember_me": False
            }
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "test@example.com"
        assert data["user"]["tenant_id"] == "tenant-456"
    
    @patch('app.api.auth.MFAPolicyService')
    @patch('app.api.auth.KeycloakAdminClient')
    @patch('app.api.auth.httpx.AsyncClient')
    @patch('app.api.auth.jwt.decode')
    def test_login_invalid_credentials(
        self,
        mock_jwt_decode,
        mock_httpx_client,
        mock_kc_admin_cls,
        mock_mfa_cls,
        client
    ):
        """Test login with invalid credentials."""
        setup_auth_mocks(mock_kc_admin_cls, mock_mfa_cls)
        mock_jwt_decode.return_value = {
            "iss": "http://localhost:8081/realms/sentinelgrid"
        }
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "invalid_grant"}
        mock_response.text = ""
        
        mock_client_instance = Mock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_httpx_client.return_value = mock_client_instance
        
        # Make request
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword",
                "remember_me": False
            }
        )
        
        # Verify response
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    
    def test_login_missing_fields(self, client):
        """Test login with missing fields."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com"
                # Missing password
            }
        )
        
        assert response.status_code == 422  # Validation error


class TestSignupEndpoint:
    """Tests for POST /api/v1/auth/signup."""
    
    @patch('app.middleware.security.RateLimitMiddleware._check_rate_limit')
    @patch('app.api.auth.KeycloakAdminClient')
    @patch('sqlalchemy.create_engine')
    @patch('sqlalchemy.orm.sessionmaker')
    def test_signup_success(
        self,
        mock_sessionmaker,
        mock_create_engine,
        mock_kc_admin_cls,
        mock_rate_limit,
        client
    ):
        """Test successful signup."""
        # Mock rate limit to allow the request (decorators applied bottom-to-top)
        mock_rate_limit.return_value = True
        mock_create_engine.return_value = Mock()
        mock_sessionmaker.return_value = FakeSession

        admin_instance = setup_auth_mocks(mock_kc_admin_cls, existing_user=None)
        
        # Make request
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "company_name": "Test Company",
                "email": "test@test.com",
                "password": "SecurePass123!",
                "first_name": "Test",
                "last_name": "User",
                "pricing_tier": "starter",
                "employee_count": 10
            }
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "tenant_id" in data
        assert "realm" in data
        assert "user_id" in data
    
    @patch('app.middleware.security.RateLimitMiddleware._check_rate_limit')
    @patch('app.api.auth.KeycloakAdminClient')
    def test_signup_duplicate_email(self, mock_kc_admin_cls, mock_rate_limit, client):
        """Test signup with duplicate email."""
        # Mock rate limit to allow the request
        mock_rate_limit.return_value = True
        
        # Mock Keycloak admin - user already exists
        setup_auth_mocks(mock_kc_admin_cls, existing_user={"id": "existing-user"})
        
        # Make request
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "company_name": "Test Company",
                "email": "existing@test.com",
                "password": "SecurePass123!",
                "first_name": "Test",
                "last_name": "User",
                "employee_count": 5
            }
        )
        
        # Verify response
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]
    
    @patch('app.middleware.security.RateLimitMiddleware._check_rate_limit')
    def test_signup_weak_password(self, mock_rate_limit, client):
        """Test signup with weak password."""
        # Mock rate limit to allow the request
        mock_rate_limit.return_value = True
        
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "company_name": "Test Company",
                "email": "test@test.com",
                "password": "weak",  # Too weak
                "first_name": "Test",
                "last_name": "User"
            }
        )
        
        assert response.status_code == 422  # Validation error


class TestLogoutEndpoint:
    """Tests for POST /api/v1/auth/logout."""
    
    @patch('app.api.auth.httpx.AsyncClient')
    @patch('app.api.auth.jwt.decode')
    def test_logout_success(
        self,
        mock_jwt_decode,
        mock_httpx_client,
        client,
        mock_jwt_payload
    ):
        """Test successful logout."""
        # Mock JWT decode
        mock_jwt_decode.return_value = {
            **mock_jwt_payload,
            "iss": "http://localhost:8081/realms/sentinelgrid"
        }
        
        # Mock httpx client
        mock_response = Mock()
        mock_response.status_code = 200
        
        mock_client_instance = Mock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_httpx_client.return_value = mock_client_instance
        
        # Make request
        response = client.post(
            "/api/v1/auth/logout",
            params={"refresh_token": "test_refresh_token"}
        )
        
        # Verify response
        assert response.status_code == 200
        assert response.json()["success"] is True


class TestRefreshTokenEndpoint:
    """Tests for POST /api/v1/auth/refresh."""
    
    @patch('app.api.auth.httpx.AsyncClient')
    @patch('app.api.auth.jwt.decode')
    def test_refresh_token_success(
        self,
        mock_jwt_decode,
        mock_httpx_client,
        client,
        mock_keycloak_token_response,
        mock_jwt_payload
    ):
        """Test successful token refresh."""
        # Mock JWT decode
        mock_jwt_decode.return_value = {
            **mock_jwt_payload,
            "iss": "http://localhost:8081/realms/sentinelgrid"
        }
        
        # Mock httpx client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_keycloak_token_response
        
        mock_client_instance = Mock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_httpx_client.return_value = mock_client_instance
        
        # Make request
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "test_refresh_token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data


class TestGetCurrentUserEndpoint:
    """Tests for GET /api/v1/auth/me."""
    
    @patch('app.api.auth.jwt.decode')
    def test_get_current_user_success(self, mock_jwt_decode, client, mock_jwt_payload):
        """Test successful get current user."""
        # Mock JWT decode
        mock_jwt_decode.return_value = {
            **mock_jwt_payload,
            "iss": "http://localhost:8081/realms/sentinelgrid"
        }
        
        # Make request
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer test_access_token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["tenant_id"] == "tenant-456"
        assert "TENANT_ADMIN" in data["roles"]
    
    def test_get_current_user_missing_token(self, client):
        """Test get current user without token."""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
