"""Tests for Keycloak client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from keycloak.exceptions import KeycloakError

from app.services.keycloak_client import KeycloakClient


@pytest.fixture
def keycloak_client():
    """Create Keycloak client instance."""
    with patch('app.services.keycloak_client.KeycloakAdmin') as mock_admin, \
         patch('app.services.keycloak_client.KeycloakOpenID') as mock_openid:
        mock_admin.return_value = Mock()
        mock_openid.return_value = Mock()
        client = KeycloakClient()
        return client


def test_keycloak_client_initialization(keycloak_client):
    """Test Keycloak client initialization."""
    assert keycloak_client is not None
    assert keycloak_client.server_url is not None
    assert keycloak_client.realm is not None


def test_get_public_key(keycloak_client):
    """Test getting public key URL."""
    jwks_url = keycloak_client.get_public_key()
    assert jwks_url is not None
    assert "realms" in jwks_url
    assert "certs" in jwks_url


def test_get_user_success(keycloak_client):
    """Test getting user successfully."""
    mock_user = {
        "id": "user-123",
        "username": "testuser",
        "email": "test@example.com"
    }
    keycloak_client.admin.get_user = Mock(return_value=mock_user)
    
    result = keycloak_client.get_user("user-123")
    assert result == mock_user
    keycloak_client.admin.get_user.assert_called_once_with("user-123")


def test_get_user_not_found(keycloak_client):
    """Test getting non-existent user."""
    keycloak_client.admin.get_user = Mock(side_effect=KeycloakError("User not found"))
    
    result = keycloak_client.get_user("non-existent")
    assert result is None


def test_list_users(keycloak_client):
    """Test listing users."""
    mock_users = [
        {"id": "user-1", "username": "user1"},
        {"id": "user-2", "username": "user2"}
    ]
    keycloak_client.admin.get_users = Mock(return_value=mock_users)
    
    result = keycloak_client.list_users()
    assert len(result) == 2
    assert result == mock_users


def test_create_user(keycloak_client):
    """Test creating a user."""
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "enabled": True
    }
    keycloak_client.admin.create_user = Mock(return_value="user-123")
    
    result = keycloak_client.create_user(user_data)
    assert result == "user-123"
    keycloak_client.admin.create_user.assert_called_once_with(user_data)


def test_create_user_failure(keycloak_client):
    """Test user creation failure."""
    keycloak_client.admin.create_user = Mock(side_effect=KeycloakError("User already exists"))
    
    result = keycloak_client.create_user({"username": "existing"})
    assert result is None


def test_get_realm_roles(keycloak_client):
    """Test getting realm roles."""
    mock_roles = [
        {"name": "SOC_ANALYST"},
        {"name": "SOC_MANAGER"}
    ]
    keycloak_client.admin.get_realm_roles = Mock(return_value=mock_roles)
    
    result = keycloak_client.get_realm_roles()
    assert len(result) == 2
    assert result == mock_roles


def test_assign_role(keycloak_client):
    """Test assigning role to user."""
    mock_role = {"name": "SOC_ANALYST"}
    keycloak_client.admin.get_realm_role = Mock(return_value=mock_role)
    keycloak_client.admin.assign_realm_roles = Mock(return_value=None)
    
    result = keycloak_client.assign_role("user-123", "SOC_ANALYST")
    assert result is True
    keycloak_client.admin.assign_realm_roles.assert_called_once()


def test_remove_role(keycloak_client):
    """Test removing role from user."""
    mock_role = {"name": "SOC_ANALYST"}
    keycloak_client.admin.get_realm_role = Mock(return_value=mock_role)
    keycloak_client.admin.delete_realm_roles_of_user = Mock(return_value=None)
    
    result = keycloak_client.remove_role("user-123", "SOC_ANALYST")
    assert result is True

