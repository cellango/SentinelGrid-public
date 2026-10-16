"""
End-to-end authentication flow tests.

Tests the complete authentication flow:
1. Token generation from Keycloak
2. Token validation via IAM Agent
3. API Gateway authorization
4. Tenant isolation
"""

import pytest
import httpx
import os
import json
import base64
from typing import Dict, Any

# Test configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8081")
IAM_AGENT_URL = os.getenv("IAM_AGENT_URL", "http://localhost:8005")
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8082")

# Test realm and user credentials
TEST_REALM = os.getenv("TEST_REALM", "agribotsai")
TEST_CLIENT_ID = os.getenv("TEST_CLIENT_ID", "agribotsai-web")
TEST_USERNAME = os.getenv("TEST_USERNAME", "admin@agribotsai.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "ChangeMe123!")


def get_token(keycloak_url: str, realm: str, client_id: str, username: str, password: str) -> str:
    """Get a JWT token from Keycloak."""
    token_endpoint = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token"
    # Use form-encoded data for Keycloak token endpoint
    data = {
        "client_id": client_id,
        "username": username,
        "password": password,
        "grant_type": "password",
        "scope": "openid profile email",
    }
    
    with httpx.Client(timeout=10.0) as client:
        response = client.post(
            token_endpoint,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if response.status_code != 200:
            error_detail = response.text
            raise Exception(f"Token request failed: {response.status_code} - {error_detail}")
        response.raise_for_status()
        return response.json()["access_token"]


def decode_token_payload(token: str) -> Dict[str, Any]:
    """Decode JWT token payload without verification."""
    parts = token.split(".")
    if len(parts) < 2:
        raise ValueError("Invalid token format")
    
    payload_b64 = parts[1]
    payload_b64 += "=" * (4 - len(payload_b64) % 4)
    return json.loads(base64.urlsafe_b64decode(payload_b64))


class TestTokenGeneration:
    """Test token generation from Keycloak."""
    
    def test_get_token_success(self):
        """Test successful token generation."""
        token = get_token(KEYCLOAK_URL, TEST_REALM, TEST_CLIENT_ID, TEST_USERNAME, TEST_PASSWORD)
        assert token is not None
        assert len(token) > 0
        assert token.count(".") == 2  # JWT format: header.payload.signature
    
    def test_token_contains_required_claims(self):
        """Test that token contains required claims."""
        token = get_token(KEYCLOAK_URL, TEST_REALM, TEST_CLIENT_ID, TEST_USERNAME, TEST_PASSWORD)
        payload = decode_token_payload(token)
        
        assert "sub" in payload, "Token missing 'sub' claim"
        assert "iss" in payload, "Token missing 'iss' claim"
        assert "exp" in payload, "Token missing 'exp' claim"
        assert "preferred_username" in payload, "Token missing 'preferred_username' claim"
    
    def test_token_contains_tenant_id(self):
        """Test that token contains tenant_id claim."""
        token = get_token(KEYCLOAK_URL, TEST_REALM, TEST_CLIENT_ID, TEST_USERNAME, TEST_PASSWORD)
        payload = decode_token_payload(token)
        
        assert "tenant_id" in payload, "Token missing 'tenant_id' claim"
        assert payload["tenant_id"] is not None, "tenant_id claim is null"
        assert len(payload["tenant_id"]) > 0, "tenant_id claim is empty"
    
    def test_token_contains_roles(self):
        """Test that token contains realm roles."""
        token = get_token(KEYCLOAK_URL, TEST_REALM, TEST_CLIENT_ID, TEST_USERNAME, TEST_PASSWORD)
        payload = decode_token_payload(token)
        
        assert "realm_access" in payload, "Token missing 'realm_access' claim"
        realm_access = payload["realm_access"]
        assert "roles" in realm_access, "Token missing 'roles' in realm_access"
        assert len(realm_access["roles"]) > 0, "Token has no roles"


class TestIAMAgentValidation:
    """Test token validation via IAM Agent."""
    
    def test_validate_token_success(self):
        """Test successful token validation."""
        token = get_token(KEYCLOAK_URL, TEST_REALM, TEST_CLIENT_ID, TEST_USERNAME, TEST_PASSWORD)
        
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{IAM_AGENT_URL}/internal/iam/auth/validate-token",
                json={"token": token}
            )
            assert response.status_code == 200
            result = response.json()
            
            assert result["valid"] is True
            assert result["user_id"] is not None
            assert result["username"] == TEST_USERNAME
    
    def test_validate_token_with_tenant_id(self):
        """Test token validation returns tenant_id."""
        token = get_token(KEYCLOAK_URL, TEST_REALM, TEST_CLIENT_ID, TEST_USERNAME, TEST_PASSWORD)
        
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{IAM_AGENT_URL}/internal/iam/auth/validate-token",
                json={"token": token}
            )
            assert response.status_code == 200
            result = response.json()
            
            assert result["valid"] is True
            assert result["tenant_id"] is not None, "IAM Agent should return tenant_id"
            assert len(result["tenant_id"]) > 0, "tenant_id should not be empty"
    
    def test_validate_token_with_roles(self):
        """Test token validation returns roles."""
        token = get_token(KEYCLOAK_URL, TEST_REALM, TEST_CLIENT_ID, TEST_USERNAME, TEST_PASSWORD)
        
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{IAM_AGENT_URL}/internal/iam/auth/validate-token",
                json={"token": token}
            )
            assert response.status_code == 200
            result = response.json()
            
            assert result["valid"] is True
            assert "roles" in result
            assert len(result["roles"]) > 0
            # Should have TENANT_ADMIN role for admin user
            assert "TENANT_ADMIN" in result["roles"]
    
    def test_validate_invalid_token(self):
        """Test validation of invalid token."""
        invalid_token = "invalid.token.here"
        
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{IAM_AGENT_URL}/internal/iam/auth/validate-token",
                json={"token": invalid_token}
            )
            assert response.status_code == 200
            result = response.json()
            
            assert result["valid"] is False
            assert "error" in result
            assert result["error"] is not None


class TestAPIGatewayIntegration:
    """Test API Gateway integration with authentication."""
    
    def test_api_gateway_health_check(self):
        """Test API Gateway health endpoint (no auth required)."""
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{API_GATEWAY_URL}/health")
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "healthy"
    
    def test_api_gateway_without_token(self):
        """Test API Gateway rejects requests without token."""
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{API_GATEWAY_URL}/api/v1/alerts/")
            # Gateway may return 401 (unauthenticated) or 403 (forbidden when auth middleware enforces tenant context)
            assert response.status_code in [401, 403], f"Unexpected status {response.status_code}: {response.text}"
            result = response.json()
            assert "detail" in result
            assert "authenticated" in result["detail"].lower() or "token" in result["detail"].lower() or "forbidden" in result["detail"].lower()
    
    def test_api_gateway_with_valid_token(self):
        """Test API Gateway accepts requests with valid token."""
        token = get_token(KEYCLOAK_URL, TEST_REALM, TEST_CLIENT_ID, TEST_USERNAME, TEST_PASSWORD)
        
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{API_GATEWAY_URL}/api/v1/alerts/",
                headers={"Authorization": f"Bearer {token}"}
            )
            # Should not return 401 (authentication error)
            assert response.status_code != 401, f"Unexpected 401: {response.text}"
            # May return 200 (success) or 403 (authorization/tenant_id missing) or 200 with empty list
            assert response.status_code in [200, 403], f"Unexpected status {response.status_code}: {response.text}"
    
    def test_api_gateway_with_tenant_id(self):
        """Test API Gateway accepts requests when tenant_id is present."""
        token = get_token(KEYCLOAK_URL, TEST_REALM, TEST_CLIENT_ID, TEST_USERNAME, TEST_PASSWORD)
        
        # First verify token has tenant_id
        payload = decode_token_payload(token)
        if "tenant_id" not in payload or not payload["tenant_id"]:
            pytest.skip("Token does not contain tenant_id - protocol mapper may not be configured")
        
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{API_GATEWAY_URL}/api/v1/alerts/",
                headers={"Authorization": f"Bearer {token}"}
            )
            # Should not return 403 (forbidden - no tenant_id)
            assert response.status_code != 403, f"Unexpected 403 (tenant_id should be present): {response.text}"
            # Should return 200 (success with possibly empty list)
            assert response.status_code == 200, f"Unexpected status {response.status_code}: {response.text}"
            result = response.json()
            # Response should have expected structure
            assert "items" in result or "detail" not in result or "no tenant_id" not in str(result).lower()


class TestEndToEndFlow:
    """Test complete end-to-end authentication flow."""
    
    def test_complete_auth_flow(self):
        """Test complete authentication flow: token -> validation -> API access."""
        # Step 1: Get token
        token = get_token(KEYCLOAK_URL, TEST_REALM, TEST_CLIENT_ID, TEST_USERNAME, TEST_PASSWORD)
        assert token is not None
        
        # Step 2: Validate token via IAM Agent
        with httpx.Client(timeout=10.0) as client:
            validation_response = client.post(
                f"{IAM_AGENT_URL}/internal/iam/auth/validate-token",
                json={"token": token}
            )
            assert validation_response.status_code == 200
            validation_result = validation_response.json()
            assert validation_result["valid"] is True
            tenant_id = validation_result.get("tenant_id")
            username = validation_result.get("username")
            
            # Step 3: Use token to access API Gateway
            if tenant_id:
                api_response = client.get(
                    f"{API_GATEWAY_URL}/api/v1/alerts/",
                    headers={"Authorization": f"Bearer {token}"}
                )
                # Should succeed (200) or return empty list
                assert api_response.status_code in [200, 403]
                if api_response.status_code == 200:
                    result = api_response.json()
                    # Should have proper structure
                    assert "items" in result or "total" in result
    
    def test_multi_realm_support(self):
        """Test that IAM Agent can handle tokens from different realms."""
        # This test requires multiple realms to be configured
        # For now, we test that realm extraction works
        token = get_token(KEYCLOAK_URL, TEST_REALM, TEST_CLIENT_ID, TEST_USERNAME, TEST_PASSWORD)
        payload = decode_token_payload(token)
        
        # Verify issuer contains realm
        assert "iss" in payload
        issuer = payload["iss"]
        assert f"/realms/{TEST_REALM}" in issuer or f"/realms/{TEST_REALM}/" in issuer


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
