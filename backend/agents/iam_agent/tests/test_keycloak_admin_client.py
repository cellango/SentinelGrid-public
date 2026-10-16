"""
Tests for KeycloakAdminClient - Direct REST API Integration.

This test suite validates the new KeycloakAdminClient implementation
that replaces python-keycloak for direct control and performance.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import httpx
from datetime import datetime

from app.services.keycloak_admin_client import (
    KeycloakAdminClient,
    KeycloakAPIError,
    KeycloakUserExistsError,
    KeycloakAttributePersistenceError
)


@pytest.fixture
def kc_client():
    """Create KeycloakAdminClient instance for testing."""
    return KeycloakAdminClient(
        server_url="http://localhost:8081",
        admin_user="admin",
        admin_password="admin"
    )


@pytest.fixture
def mock_token_response():
    """Mock successful token response."""
    return {
        "access_token": "mock-admin-token",
        "expires_in": 60,
        "token_type": "Bearer"
    }


@pytest.fixture
def mock_user():
    """Mock user data."""
    return {
        "id": "user-uuid-123",
        "username": "test@example.com",
        "email": "test@example.com",
        "firstName": "Test",
        "lastName": "User",
        "enabled": True,
        "emailVerified": False,
        "attributes": {
            "tenant_id": ["tenant-uuid-456"],
            "customer_id": ["customer-uuid-789"]
        }
    }


class TestAdminTokenCaching:
    """Test admin token caching mechanism."""
    
    @pytest.mark.asyncio
    async def test_get_admin_token_success(self, kc_client, mock_token_response):
        """Test successful admin token acquisition."""
        with patch.object(kc_client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = mock_token_response
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            token = await kc_client._get_admin_token()
            
            assert token == "mock-admin-token"
            assert kc_client._admin_token == "mock-admin-token"
            assert kc_client._token_expiry is not None
    
    @pytest.mark.asyncio
    async def test_token_caching(self, kc_client, mock_token_response):
        """Test that token is cached and reused."""
        with patch.object(kc_client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = mock_token_response
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            # First call - should hit API
            token1 = await kc_client._get_admin_token()
            
            # Second call - should use cache
            token2 = await kc_client._get_admin_token()
            
            assert token1 == token2
            # Verify API was only called once
            assert mock_client.post.call_count == 1


class TestUserCreation:
    """Test user creation with attribute verification."""
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, kc_client, mock_token_response):
        """Test successful user creation with attributes."""
        with patch.object(kc_client, '_make_request') as mock_request:
            # Mock successful creation response
            create_response = Mock()
            create_response.status_code = 201
            create_response.headers = {"Location": "http://keycloak/admin/realms/test/users/user-123"}
            password_response = Mock()
            password_response.status_code = 204
            mock_request.side_effect = [create_response, password_response]
            
            # Mock get_user for verification
            with patch.object(kc_client, 'get_user') as mock_get_user:
                mock_get_user.return_value = {
                    "id": "user-123",
                    "attributes": {
                        "tenant_id": ["tenant-456"],
                        "customer_id": ["customer-789"]
                    }
                }
                
                user_id = await kc_client.create_user(
                    realm="test",
                    username="test@example.com",
                    email="test@example.com",
                    first_name="Test",
                    last_name="User",
                    password="password123",
                    attributes={
                        "tenant_id": ["tenant-456"],
                        "customer_id": ["customer-789"]
                    }
                )
                
                assert user_id == "user-123"
                # Verify user was retrieved for attribute verification
                assert mock_get_user.called
    
    @pytest.mark.asyncio
    async def test_create_user_attribute_validation(self, kc_client):
        """Test that attribute format is validated (must be arrays)."""
        with pytest.raises(ValueError, match="must be a list"):
            await kc_client.create_user(
                realm="test",
                username="test@example.com",
                email="test@example.com",
                first_name="Test",
                last_name="User",
                attributes={
                    "tenant_id": "not-a-list"  # Invalid - should be ["not-a-list"]
                }
            )
    
    @pytest.mark.asyncio
    async def test_create_user_already_exists(self, kc_client):
        """Test handling of duplicate user creation."""
        with patch.object(kc_client, '_make_request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status_code = 409
            mock_response.text = "User already exists"
            mock_request.return_value = mock_response
            
            with pytest.raises(KeycloakUserExistsError):
                await kc_client.create_user(
                    realm="test",
                    username="existing@example.com",
                    email="existing@example.com",
                    first_name="Test",
                    last_name="User"
                )
    
    @pytest.mark.asyncio
    async def test_attribute_persistence_retry(self, kc_client):
        """Test attribute persistence verification with retry."""
        with patch.object(kc_client, '_make_request') as mock_request:
            # Mock successful creation
            mock_create_response = AsyncMock()
            mock_create_response.status_code = 201
            mock_create_response.headers = {"Location": "http://keycloak/admin/realms/test/users/user-123"}
            
            # Mock get_user - attributes missing on first call, present on second
            with patch.object(kc_client, 'get_user') as mock_get_user:
                mock_get_user.side_effect = [
                    {"id": "user-123", "attributes": {}},  # First check - missing
                    {"id": "user-123", "attributes": {"tenant_id": ["tenant-456"]}},  # After retry - present
                ]
                
                with patch.object(kc_client, 'update_user_attributes') as mock_update:
                    mock_update.return_value = None
                    mock_request.return_value = mock_create_response
                    
                    user_id = await kc_client.create_user(
                        realm="test",
                        username="test@example.com",
                        email="test@example.com",
                        first_name="Test",
                        last_name="User",
                        attributes={"tenant_id": ["tenant-456"]}
                    )
                    
                    assert user_id == "user-123"
                    # Verify retry was attempted
                    assert mock_update.called


class TestUserRetrieval:
    """Test user retrieval methods."""
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, kc_client, mock_user):
        """Test retrieving user by ID."""
        with patch.object(kc_client, '_make_request') as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = mock_user
            mock_response.raise_for_status = Mock()
            mock_request.return_value = mock_response
            
            user = await kc_client.get_user("test", "user-uuid-123")
            
            assert user["id"] == "user-uuid-123"
            assert user["email"] == "test@example.com"
            assert "tenant_id" in user["attributes"]
    
    @pytest.mark.asyncio
    async def test_get_user_by_username(self, kc_client, mock_user):
        """Test retrieving user by username."""
        with patch.object(kc_client, '_make_request') as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = [mock_user]
            mock_response.raise_for_status = Mock()
            mock_request.return_value = mock_response
            
            user = await kc_client.get_user_by_username("test", "test@example.com")
            
            assert user is not None
            assert user["username"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_get_user_by_username_not_found(self, kc_client):
        """Test user not found returns None."""
        with patch.object(kc_client, '_make_request') as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = []  # No users found
            mock_response.raise_for_status = Mock()
            mock_request.return_value = mock_response
            
            user = await kc_client.get_user_by_username("test", "nonexistent@example.com")
            
            assert user is None


class TestAttributeManagement:
    """Test user attribute update operations."""
    
    @pytest.mark.asyncio
    async def test_update_user_attributes_merge(self, kc_client):
        """Test updating attributes with merge."""
        with patch.object(kc_client, 'get_user') as mock_get_user:
            mock_get_user.return_value = {
                "id": "user-123",
                "attributes": {
                    "existing_attr": ["value1"]
                }
            }
            
            with patch.object(kc_client, '_make_request') as mock_request:
                mock_response = AsyncMock()
                mock_response.raise_for_status = Mock()
                mock_request.return_value = mock_response
                
                await kc_client.update_user_attributes(
                    "test",
                    "user-123",
                    {"tenant_id": ["tenant-456"]},
                    merge=True
                )
                
                # Verify merged attributes were sent
                call_args = mock_request.call_args
                assert call_args[1]["json_data"]["attributes"]["existing_attr"] == ["value1"]
                assert call_args[1]["json_data"]["attributes"]["tenant_id"] == ["tenant-456"]
    
    @pytest.mark.asyncio
    async def test_update_user_attributes_replace(self, kc_client):
        """Test updating attributes without merge (replace all)."""
        with patch.object(kc_client, '_make_request') as mock_request:
            mock_response = AsyncMock()
            mock_response.raise_for_status = Mock()
            mock_request.return_value = mock_response
            
            await kc_client.update_user_attributes(
                "test",
                "user-123",
                {"tenant_id": ["tenant-456"]},
                merge=False
            )
            
            # Verify only new attributes were sent
            call_args = mock_request.call_args
            assert call_args[1]["json_data"]["attributes"] == {"tenant_id": ["tenant-456"]}


class TestRoleManagement:
    """Test role assignment and management."""
    
    @pytest.mark.asyncio
    async def test_assign_realm_role(self, kc_client):
        """Test assigning realm role to user."""
        mock_role = {"id": "role-123", "name": "TENANT_ADMIN"}
        
        with patch.object(kc_client, 'get_realm_role') as mock_get_role:
            mock_get_role.return_value = mock_role
            
            with patch.object(kc_client, '_make_request') as mock_request:
                mock_response = AsyncMock()
                mock_response.status_code = 204
                mock_request.return_value = mock_response
                
                await kc_client.assign_realm_role("test", "user-123", "TENANT_ADMIN")
                
                # Verify role was assigned
                assert mock_request.called
    
    @pytest.mark.asyncio
    async def test_assign_nonexistent_role(self, kc_client):
        """Test assigning non-existent role raises error."""
        with patch.object(kc_client, 'get_realm_role') as mock_get_role:
            mock_get_role.return_value = None  # Role not found
            
            with pytest.raises(KeycloakAPIError, match="Role not found"):
                await kc_client.assign_realm_role("test", "user-123", "NONEXISTENT")


class TestPasswordManagement:
    """Test password setting operations."""
    
    @pytest.mark.asyncio
    async def test_set_user_password(self, kc_client):
        """Test setting user password."""
        with patch.object(kc_client, '_make_request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status_code = 204
            mock_request.return_value = mock_response
            
            await kc_client.set_user_password("test", "user-123", "newpassword", temporary=False)
            
            # Verify password was set
            assert mock_request.called
            call_args = mock_request.call_args
            assert call_args[1]["json_data"]["value"] == "newpassword"
            assert call_args[1]["json_data"]["temporary"] == False


class TestHealthCheck:
    """Test health check and connectivity."""
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, kc_client, mock_token_response):
        """Test health check when Keycloak is accessible."""
        with patch.object(kc_client, '_get_admin_token') as mock_get_token:
            mock_get_token.return_value = "mock-token"
            
            health = await kc_client.health_check()
            
            assert health["status"] == "healthy"
            assert health["admin_authenticated"] == True
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, kc_client):
        """Test health check when Keycloak is not accessible."""
        with patch.object(kc_client, '_get_admin_token') as mock_get_token:
            mock_get_token.side_effect = Exception("Connection failed")
            
            health = await kc_client.health_check()
            
            assert health["status"] == "unhealthy"
            assert health["admin_authenticated"] == False
            assert "error" in health


class TestContextManager:
    """Test async context manager protocol."""
    
    @pytest.mark.asyncio
    async def test_context_manager_creates_client(self):
        """Test context manager creates HTTP client."""
        kc_client = KeycloakAdminClient()
        
        assert kc_client._client is None
        
        async with kc_client as client:
            assert client._client is not None
        
        # Client should be closed after context
        assert kc_client._client is None
    
    @pytest.mark.asyncio
    async def test_context_manager_cleanup_on_error(self):
        """Test context manager cleans up even on error."""
        kc_client = KeycloakAdminClient()
        
        try:
            async with kc_client as client:
                assert client._client is not None
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Client should still be cleaned up
        assert kc_client._client is None


class TestPerformanceOptimizations:
    """Test performance-related features."""
    
    @pytest.mark.asyncio
    async def test_connection_pooling(self, kc_client):
        """Test that connection pool is configured correctly."""
        async with kc_client as client:
            http_client = client._client
            
            # Verify connection pool settings
            assert http_client._transport._pool._max_connections == 100
            assert http_client._transport._pool._max_keepalive_connections == 20
    
    @pytest.mark.asyncio
    async def test_token_cache_reduces_api_calls(self, kc_client, mock_token_response):
        """Test that token caching reduces API calls."""
        with patch.object(kc_client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = mock_token_response
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            # Make multiple requests
            for _ in range(5):
                await kc_client._get_admin_token()
            
            # Verify token endpoint was only called once (cached for subsequent calls)
            assert mock_client.post.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
