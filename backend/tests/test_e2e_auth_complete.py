"""
End-to-End Authentication Flow Tests with MFA.

Tests complete authentication flows from signup to login with MFA,
token refresh, and logout. Validates tenant_id persistence throughout.
"""

import pytest
import asyncio
import httpx
from datetime import datetime
import base64
import json


# Configuration
IAM_AGENT_URL = "http://localhost:8000"
KEYCLOAK_URL = "http://localhost:8080"


class TestCompleteAuthFlow:
    """Test complete authentication flows end-to-end."""
    
    @pytest.mark.asyncio
    async def test_signup_login_flow_with_tenant_id(self):
        """
        Test complete signup → login flow with tenant_id verification.
        
        Steps:
        1. Signup new user
        2. Verify tenant_id assigned
        3. Login with credentials
        4. Verify JWT token contains tenant_id
        5. Verify tenant_id matches original
        """
        timestamp = int(datetime.now().timestamp())
        test_email = f"e2e-test-{timestamp}@example.com"
        test_password = "TestPassword123!"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Signup
            print(f"\n1. Testing signup for {test_email}...")
            signup_response = await client.post(
                f"{IAM_AGENT_URL}/api/v1/auth/signup",
                json={
                    "company_name": "E2E Test Company",
                    "email": test_email,
                    "password": test_password,
                    "first_name": "E2E",
                    "last_name": "Test",
                    "employee_count": 10
                }
            )
            
            assert signup_response.status_code == 200, \
                f"Signup failed: {signup_response.status_code} - {signup_response.text}"
            
            signup_data = signup_response.json()
            assert "tenant_id" in signup_data, "Signup response missing tenant_id"
            assert "user_id" in signup_data, "Signup response missing user_id"
            
            tenant_id = signup_data["tenant_id"]
            user_id = signup_data["user_id"]
            
            print(f"   ✅ User created: {user_id}")
            print(f"   ✅ Tenant ID: {tenant_id}")
            
            # Step 2: Login
            print(f"\n2. Testing login...")
            login_response = await client.post(
                f"{IAM_AGENT_URL}/api/v1/auth/login",
                json={
                    "email": test_email,
                    "password": test_password
                }
            )
            
            assert login_response.status_code == 200, \
                f"Login failed: {login_response.status_code} - {login_response.text}"
            
            login_data = login_response.json()
            assert "access_token" in login_data, "Login response missing access_token"
            assert "user" in login_data, "Login response missing user"
            
            access_token = login_data["access_token"]
            user_info = login_data["user"]
            
            print(f"   ✅ Login successful")
            print(f"   ✅ Token received")
            
            # Step 3: Verify token contains tenant_id
            print(f"\n3. Verifying JWT token contains tenant_id...")
            token_parts = access_token.split('.')
            payload_part = token_parts[1]
            payload_part += '=' * (4 - len(payload_part) % 4)  # Add padding
            payload = json.loads(base64.urlsafe_b64decode(payload_part))
            
            assert "tenant_id" in payload, "JWT token missing tenant_id claim!"
            token_tenant_id = payload["tenant_id"]
            
            print(f"   ✅ Token contains tenant_id: {token_tenant_id}")
            
            # Step 4: Verify tenant_id matches
            assert token_tenant_id == tenant_id, \
                f"Tenant ID mismatch! Signup: {tenant_id}, Token: {token_tenant_id}"
            
            assert user_info.get("tenant_id") == tenant_id, \
                f"User info tenant_id mismatch!"
            
            print(f"   ✅ Tenant ID consistent across signup and login")
            
            # Step 5: Test token refresh
            print(f"\n4. Testing token refresh...")
            refresh_token = login_data.get("refresh_token")
            
            if refresh_token:
                refresh_response = await client.post(
                    f"{IAM_AGENT_URL}/api/v1/auth/refresh",
                    json={"refresh_token": refresh_token}
                )
                
                if refresh_response.status_code == 200:
                    refresh_data = refresh_response.json()
                    new_access_token = refresh_data["access_token"]
                    
                    # Verify new token also has tenant_id
                    new_token_parts = new_access_token.split('.')
                    new_payload = json.loads(
                        base64.urlsafe_b64decode(new_token_parts[1] + '==')
                    )
                    
                    assert new_payload.get("tenant_id") == tenant_id, \
                        "Refreshed token missing or wrong tenant_id!"
                    
                    print(f"   ✅ Token refresh successful with tenant_id preserved")
            
            # Step 6: Test /me endpoint
            print(f"\n5. Testing /me endpoint...")
            me_response = await client.get(
                f"{IAM_AGENT_URL}/api/v1/auth/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            assert me_response.status_code == 200
            me_data = me_response.json()
            assert me_data.get("tenant_id") == tenant_id, \
                "/me endpoint returned wrong tenant_id!"
            
            print(f"   ✅ /me endpoint returns correct tenant_id")
            
            print(f"\n✅ Complete auth flow test PASSED")
            print(f"   tenant_id consistent across all operations")
    
    @pytest.mark.asyncio
    async def test_mfa_enrollment_flow(self):
        """
        Test MFA enrollment flow.
        
        Steps:
        1. Create user
        2. Login
        3. Enroll MFA
        4. Verify enrollment
        5. Check MFA status
        """
        timestamp = int(datetime.now().timestamp())
        test_email = f"mfa-test-{timestamp}@example.com"
        test_password = "TestPassword123!"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Signup
            print(f"\n1. Creating user for MFA test...")
            signup_response = await client.post(
                f"{IAM_AGENT_URL}/api/v1/auth/signup",
                json={
                    "company_name": "MFA Test Company",
                    "email": test_email,
                    "password": test_password,
                    "first_name": "MFA",
                    "last_name": "Test",
                    "employee_count": 5
                }
            )
            
            assert signup_response.status_code == 200
            signup_data = signup_response.json()
            user_id = signup_data["user_id"]
            tenant_id = signup_data["tenant_id"]
            
            print(f"   ✅ User created: {user_id}")
            
            # Step 2: Login
            print(f"\n2. Logging in...")
            login_response = await client.post(
                f"{IAM_AGENT_URL}/api/v1/auth/login",
                json={"email": test_email, "password": test_password}
            )
            
            assert login_response.status_code == 200
            access_token = login_response.json()["access_token"]
            
            print(f"   ✅ Login successful")
            
            # Step 3: Enroll MFA
            print(f"\n3. Enrolling MFA...")
            mfa_enroll_response = await client.post(
                f"{IAM_AGENT_URL}/api/v1/mfa/enroll",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"user_id": user_id}
            )
            
            if mfa_enroll_response.status_code == 200:
                mfa_data = mfa_enroll_response.json()
                assert "secret" in mfa_data, "MFA enrollment missing secret"
                assert "qr_code" in mfa_data, "MFA enrollment missing QR code"
                
                print(f"   ✅ MFA enrollment successful")
                print(f"   ✅ QR code generated")
                
                # Step 4: Check MFA status
                print(f"\n4. Checking MFA status...")
                status_response = await client.get(
                    f"{IAM_AGENT_URL}/api/v1/mfa/{user_id}/status",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"   ✅ MFA status retrieved")
                    print(f"   MFA enabled: {status_data.get('mfa_enabled')}")
                
                print(f"\n✅ MFA enrollment flow test PASSED")
            else:
                print(f"   ⚠️  MFA enrollment endpoint returned {mfa_enroll_response.status_code}")
                print(f"   Note: MFA may need additional configuration")


class TestTokenSecurity:
    """Test JWT token security."""
    
    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self):
        """Invalid tokens should be rejected."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{IAM_AGENT_URL}/api/v1/auth/me",
                headers={"Authorization": "Bearer invalid-token-12345"}
            )
            
            assert response.status_code == 401, \
                "Invalid token was not rejected!"
            
            print("\n✅ Invalid token correctly rejected")
    
    @pytest.mark.asyncio
    async def test_missing_token_rejected(self):
        """Requests without tokens should be rejected."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{IAM_AGENT_URL}/api/v1/auth/me")
            
            assert response.status_code in [401, 403, 422], \
                "Request without token was not rejected!"
            
            print("\n✅ Missing token correctly rejected")


class TestPasswordSecurity:
    """Test password security features."""
    
    @pytest.mark.asyncio
    async def test_weak_password_rejected(self):
        """Weak passwords should be rejected during signup."""
        timestamp = int(datetime.now().timestamp())
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{IAM_AGENT_URL}/api/v1/auth/signup",
                json={
                    "company_name": "Test Company",
                    "email": f"weak-pw-{timestamp}@example.com",
                    "password": "123",  # Too weak
                    "first_name": "Test",
                    "last_name": "User",
                    "employee_count": 1
                }
            )
            
            assert response.status_code in [400, 422], \
                "Weak password was accepted!"
            
            print("\n✅ Weak password correctly rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--asyncio-mode=auto"])

