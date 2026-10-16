"""Tests for token validator service."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from jose import jwt
import time

from app.services.token_validator import TokenValidator
from app.services.keycloak_client import KeycloakClient
from app.core.config import settings


@pytest.fixture
def mock_keycloak_client():
    """Mock Keycloak client."""
    return Mock(spec=KeycloakClient)


@pytest.fixture
def token_validator(mock_keycloak_client):
    """Create token validator instance."""
    return TokenValidator(mock_keycloak_client)


@pytest.fixture
def sample_jwt_token():
    """Create a sample JWT token for testing."""
    # This is a mock token - in real tests, we'd get this from Keycloak
    payload = {
        "sub": "user-123",
        "tenant_id": "tenant-456",
        "email": "test@example.com",
        "preferred_username": "testuser",
        "realm_access": {
            "roles": ["SOC_ANALYST", "VIEW_ONLY"]
        },
        "exp": int(time.time()) + 3600,  # Expires in 1 hour
        "iat": int(time.time()),
        "aud": settings.KEYCLOAK_CLIENT_ID,
        "iss": f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
    }
    # Note: This won't have a valid signature, but we can test the validation logic
    return jwt.encode(payload, "secret", algorithm="HS256")


@pytest.mark.asyncio
async def test_token_validator_initialization(token_validator):
    """Test token validator initialization."""
    assert token_validator is not None
    assert token_validator.keycloak_client is not None
    assert token_validator.realm == settings.KEYCLOAK_REALM


@patch('app.services.token_validator.httpx')
def test_get_jwks_caching(mock_httpx, token_validator):
    """Test JWKS caching."""
    # Mock JWKS response
    mock_response = Mock()
    mock_response.json.return_value = {
        "keys": [{"kid": "test-key", "kty": "RSA"}]
    }
    mock_httpx.Client.return_value.__enter__.return_value.get.return_value = mock_response
    mock_httpx.Client.return_value.__enter__.return_value.get.return_value.raise_for_status = Mock()
    
    # First call - should fetch
    jwks1 = token_validator._get_jwks()
    assert jwks1 is not None
    assert mock_httpx.Client.return_value.__enter__.return_value.get.call_count == 1
    
    # Second call - should use cache
    jwks2 = token_validator._get_jwks()
    assert jwks2 is not None
    # Should still be 1 call due to caching
    assert mock_httpx.Client.return_value.__enter__.return_value.get.call_count == 1


def test_get_signing_key_no_kid(token_validator):
    """Test getting signing key when token has no kid."""
    token = "invalid.token.here"
    jwks = {"keys": []}
    
    key = token_validator._get_signing_key(token, jwks)
    assert key is None


def test_validate_token_no_token(token_validator):
    """Test validation with empty token."""
    result = token_validator.validate_token("")
    assert result["valid"] is False
    assert "error" in result


def test_validate_token_invalid_format(token_validator):
    """Test validation with invalid token format."""
    result = token_validator.validate_token("not-a-valid-token")
    assert result["valid"] is False
    assert "error" in result


def test_introspect_token_fallback(token_validator):
    """Test token introspection with fallback."""
    # Mock introspection to return None (not active)
    token_validator.keycloak_client.introspect_token = Mock(return_value=None)
    
    # Should fall back to JWT validation
    result = token_validator.introspect_token("test-token")
    assert "active" in result
    # Should be False since token is invalid
    assert result["active"] is False


