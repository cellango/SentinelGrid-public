"""Tests for self-service API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock

from app.main import app
from app.api.self_service import get_current_user


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_user_token():
    """Mock token data for regular user."""
    return {
        "valid": True,
        "tenant_id": "test-tenant-123",
        "user_id": "user-123",
        "email": "user@example.com",
        "username": "testuser",
        "roles": ["SOC_ANALYST"]
    }


@pytest.fixture(autouse=True)
def override_current_user(mock_user_token):
    """Route self-service endpoints through a stable mocked user context."""
    app.dependency_overrides[get_current_user] = lambda: mock_user_token
    yield
    app.dependency_overrides.pop(get_current_user, None)


@patch('app.api.self_service.KeycloakAdminClient')
def test_get_profile(mock_kc_class, client, mock_user_token):
    """Test get profile endpoint."""
    mock_kc = AsyncMock()
    mock_kc.get_user = AsyncMock(return_value={
        "id": "user-123",
        "username": "testuser",
        "email": "user@example.com",
        "firstName": "Test",
        "lastName": "User",
        "emailVerified": True,
        "attributes": {}
    })
    mock_kc.__aenter__ = AsyncMock(return_value=mock_kc)
    mock_kc.__aexit__ = AsyncMock(return_value=None)
    mock_kc_class.return_value = mock_kc
    
    response = client.get(
        "/api/v1/self/profile",
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "user-123"
    assert data["email"] == "user@example.com"


@patch('app.api.self_service.KeycloakAdminClient')
def test_update_profile(mock_kc_class, client, mock_user_token):
    """Test update profile endpoint."""
    mock_kc = AsyncMock()
    mock_kc.get_user = AsyncMock(side_effect=[
        {
            "id": "user-123",
            "username": "testuser",
            "email": "user@example.com",
            "firstName": "Old",
            "lastName": "Name",
            "attributes": {}
        },
        {
            "id": "user-123",
            "username": "testuser",
            "email": "user@example.com",
            "firstName": "New",
            "lastName": "Name",
            "attributes": {
                "locale": ["en"],
                "timezone": ["America/New_York"],
            }
        },
    ])
    mock_kc._make_request = AsyncMock()
    mock_kc.__aenter__ = AsyncMock(return_value=mock_kc)
    mock_kc.__aexit__ = AsyncMock(return_value=None)
    mock_kc_class.return_value = mock_kc
    
    response = client.put(
        "/api/v1/self/profile",
        json={
            "firstName": "New",
            "lastName": "Name",
            "locale": "en",
            "timezone": "America/New_York"
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["firstName"] == "New"


@patch('app.api.self_service.KeycloakAdminClient')
def test_change_password(mock_kc_class, client, mock_user_token):
    """Test change password endpoint."""
    mock_kc = AsyncMock()
    mock_kc._make_request = AsyncMock()
    mock_kc.__aenter__ = AsyncMock(return_value=mock_kc)
    mock_kc.__aexit__ = AsyncMock(return_value=None)
    mock_kc_class.return_value = mock_kc
    
    response = client.post(
        "/api/v1/self/password/change",
        json={
            "current_password": "oldpass123",
            "new_password": "newpass123"
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@patch('app.api.self_service.KeycloakAdminClient')
def test_list_sessions(mock_kc_class, client, mock_user_token):
    """Test list sessions endpoint."""
    mock_kc = AsyncMock()
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = [
        {
            "id": "session-1",
            "username": "testuser",
            "userId": "user-123",
            "ipAddress": "192.168.1.1",
            "start": 1704067200,
            "lastAccess": 1704070800,
            "clients": {}
        }
    ]
    mock_kc._make_request = AsyncMock(return_value=mock_response)
    mock_kc.__aenter__ = AsyncMock(return_value=mock_kc)
    mock_kc.__aexit__ = AsyncMock(return_value=None)
    mock_kc_class.return_value = mock_kc
    
    response = client.get(
        "/api/v1/self/sessions",
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "session-1"


@patch('app.api.self_service.KeycloakAdminClient')
def test_logout_session_reports_global_logout(mock_kc_class, client, mock_user_token):
    """Test session logout endpoint reports the real behavior."""
    mock_kc = AsyncMock()
    mock_kc._make_request = AsyncMock()
    mock_kc.__aenter__ = AsyncMock(return_value=mock_kc)
    mock_kc.__aexit__ = AsyncMock(return_value=None)
    mock_kc_class.return_value = mock_kc

    response = client.post(
        "/api/v1/self/sessions/session-1/logout",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "message": "All active sessions signed out",
    }
