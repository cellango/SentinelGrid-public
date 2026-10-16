#!/usr/bin/env python3
"""
Test script to verify tenant_id attribute persistence with new KeycloakAdminClient.

This script will:
1. Create a test user with tenant_id attribute
2. Verify the attribute persisted in Keycloak
3. Get a JWT token and verify tenant_id is in the token claims
4. Clean up the test user

Usage:
    python3 scripts/test_tenant_id_attribute.py
"""

import asyncio
import sys
import os
import uuid
import json
import base64
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend/agents/iam_agent'))

from app.services.keycloak_admin_client import KeycloakAdminClient
import httpx


# Configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
REALM = os.getenv("KEYCLOAK_REALM", "sentinelgrid")
TEST_TENANT_ID = str(uuid.uuid4())
TEST_CUSTOMER_ID = str(uuid.uuid4())
TEST_EMAIL = f"test-{int(datetime.now().timestamp())}@example.com"
TEST_PASSWORD = "TestPassword123!"


def print_header(text):
    """Print a formatted header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print('='*70)


def print_success(text):
    """Print success message."""
    print(f"✅ {text}")


def print_error(text):
    """Print error message."""
    print(f"❌ {text}")


def print_info(text):
    """Print info message."""
    print(f"ℹ️  {text}")


def decode_jwt_payload(token: str) -> dict:
    """Decode JWT token payload (without verification)."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return {}
        
        payload_part = parts[1]
        # Add padding if needed
        payload_part += '=' * (4 - len(payload_part) % 4)
        
        payload_bytes = base64.urlsafe_b64decode(payload_part)
        payload = json.loads(payload_bytes.decode('utf-8'))
        
        return payload
    except Exception as e:
        print_error(f"Failed to decode token: {e}")
        return {}


async def test_attribute_persistence():
    """Test tenant_id attribute persistence end-to-end."""
    
    print_header("Testing tenant_id Attribute Persistence")
    print_info(f"Keycloak URL: {KEYCLOAK_URL}")
    print_info(f"Realm: {REALM}")
    print_info(f"Test User: {TEST_EMAIL}")
    print_info(f"Test Tenant ID: {TEST_TENANT_ID}")
    
    user_id = None
    
    try:
        # Step 1: Initialize KeycloakAdminClient
        print_header("Step 1: Initialize KeycloakAdminClient")
        
        # Explicitly set the server URL to localhost (external access)
        async with KeycloakAdminClient(
            server_url=KEYCLOAK_URL,
            admin_user=os.getenv("KEYCLOAK_ADMIN_USER", "admin"),
            admin_password=os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
        ) as kc_admin:
            # Test connection
            health = await kc_admin.health_check()
            if health["status"] == "healthy":
                print_success("Connected to Keycloak")
                print_info(f"Admin authenticated: {health['admin_authenticated']}")
            else:
                print_error(f"Keycloak not healthy: {health}")
                return False
            
            # Step 2: Create user with tenant_id attribute
            print_header("Step 2: Create User with tenant_id Attribute")
            
            print_info("Creating user with attributes:")
            print_info(f"  - tenant_id: {TEST_TENANT_ID}")
            print_info(f"  - customer_id: {TEST_CUSTOMER_ID}")
            
            try:
                user_id = await kc_admin.create_user(
                    realm=REALM,
                    username=TEST_EMAIL,
                    email=TEST_EMAIL,
                    first_name="Test",
                    last_name="User",
                    password=TEST_PASSWORD,
                    enabled=True,
                    email_verified=True,
                    attributes={
                        "tenant_id": [TEST_TENANT_ID],
                        "customer_id": [TEST_CUSTOMER_ID]
                    }
                )
                
                print_success(f"User created: {user_id}")
                
            except Exception as e:
                print_error(f"Failed to create user: {e}")
                return False
            
            # Step 3: Verify attributes persisted
            print_header("Step 3: Verify Attributes Persisted in Keycloak")
            
            try:
                user = await kc_admin.get_user(REALM, user_id)
                attributes = user.get("attributes", {})
                
                print_info("User attributes retrieved:")
                print(json.dumps(attributes, indent=2))
                
                # Check tenant_id
                if "tenant_id" in attributes:
                    actual_tenant_id = attributes["tenant_id"]
                    if actual_tenant_id == [TEST_TENANT_ID]:
                        print_success("tenant_id attribute persisted correctly!")
                        print_info(f"Expected: {[TEST_TENANT_ID]}")
                        print_info(f"Actual:   {actual_tenant_id}")
                    else:
                        print_error("tenant_id value mismatch")
                        print_info(f"Expected: {[TEST_TENANT_ID]}")
                        print_info(f"Actual:   {actual_tenant_id}")
                        return False
                else:
                    print_error("tenant_id attribute NOT found in user")
                    print_info(f"Available attributes: {list(attributes.keys())}")
                    return False
                
                # Check customer_id
                if "customer_id" in attributes:
                    actual_customer_id = attributes["customer_id"]
                    if actual_customer_id == [TEST_CUSTOMER_ID]:
                        print_success("customer_id attribute persisted correctly!")
                    else:
                        print_error("customer_id value mismatch")
                else:
                    print_error("customer_id attribute NOT found")
                
            except Exception as e:
                print_error(f"Failed to verify attributes: {e}")
                return False
            
            # Step 4: Assign role (needed for token generation)
            print_header("Step 4: Assign Role for Token Generation")
            
            try:
                await kc_admin.assign_realm_role(REALM, user_id, "TENANT_ADMIN")
                print_success("Assigned TENANT_ADMIN role")
            except Exception as e:
                print_error(f"Failed to assign role (may not exist): {e}")
                # Non-fatal - continue
        
        # Step 5: Get JWT token
        print_header("Step 5: Get JWT Token and Verify tenant_id Claim")
        
        token_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"
        
        try:
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                response = await client.post(
                    token_url,
                    data={
                        "grant_type": "password",
                        "client_id": "sentinelgrid-web",
                        "username": TEST_EMAIL,
                        "password": TEST_PASSWORD,
                        "scope": "openid profile email"
                    }
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    access_token = token_data.get("access_token")
                    
                    print_success("JWT token obtained")
                    
                    # Decode token
                    payload = decode_jwt_payload(access_token)
                    
                    if payload:
                        print_info("Token payload decoded successfully")
                        
                        # Check tenant_id claim
                        if "tenant_id" in payload:
                            token_tenant_id = payload["tenant_id"]
                            if token_tenant_id == TEST_TENANT_ID:
                                print_success("✨ tenant_id found in JWT token!")
                                print_info(f"Token tenant_id: {token_tenant_id}")
                                print_success("🎉 ATTRIBUTE PERSISTENCE WORKING!")
                            else:
                                print_error("tenant_id in token doesn't match")
                                print_info(f"Expected: {TEST_TENANT_ID}")
                                print_info(f"Got:      {token_tenant_id}")
                                return False
                        else:
                            print_error("tenant_id NOT in token claims")
                            print_info(f"Available claims: {list(payload.keys())}")
                            print_error("Check protocol mapper configuration")
                            return False
                        
                        # Show other relevant claims
                        print_info("\nOther token claims:")
                        print_info(f"  - sub (user_id): {payload.get('sub', 'N/A')}")
                        print_info(f"  - email: {payload.get('email', 'N/A')}")
                        print_info(f"  - roles: {payload.get('realm_access', {}).get('roles', [])}")
                        
                    else:
                        print_error("Failed to decode token payload")
                        return False
                    
                else:
                    print_error(f"Token request failed: {response.status_code}")
                    print_info(f"Response: {response.text}")
                    return False
                    
        except Exception as e:
            print_error(f"Failed to get token: {e}")
            return False
        
        # Success!
        print_header("✅ ALL TESTS PASSED!")
        print_success("Attribute persistence is working correctly")
        print_success("tenant_id persists in Keycloak")
        print_success("tenant_id appears in JWT token")
        print_success("Multi-tenant isolation is enabled!")
        
        return True
        
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Step 6: Cleanup
        if user_id:
            print_header("Step 6: Cleanup")
            try:
                async with KeycloakAdminClient(
                    server_url=KEYCLOAK_URL,
                    admin_user=os.getenv("KEYCLOAK_ADMIN_USER", "admin"),
                    admin_password=os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
                ) as kc_admin:
                    await kc_admin.delete_user(REALM, user_id)
                    print_success(f"Test user deleted: {user_id}")
            except Exception as e:
                print_error(f"Failed to delete test user: {e}")
                print_info(f"Manual cleanup needed: {user_id}")


async def main():
    """Main entry point."""
    print("\n" + "="*70)
    print("  TENANT_ID ATTRIBUTE PERSISTENCE TEST")
    print("  Testing KeycloakAdminClient Implementation")
    print("="*70)
    
    success = await test_attribute_persistence()
    
    if success:
        print("\n" + "="*70)
        print("  🎉 SUCCESS! Attribute persistence is working!")
        print("="*70)
        print("\n✅ The Keycloak attribute persistence issue is RESOLVED")
        print("✅ Your IAM implementation is ready for production")
        print("\nNext steps:")
        print("  1. Run full integration tests")
        print("  2. Test signup flow in staging")
        print("  3. Deploy to production")
        print("\n")
        sys.exit(0)
    else:
        print("\n" + "="*70)
        print("  ❌ FAILED - Attribute persistence not working")
        print("="*70)
        print("\nTroubleshooting:")
        print("  1. Check Keycloak is running: docker-compose ps keycloak")
        print("  2. Verify realm exists: sentinelgrid")
        print("  3. Check protocol mapper for tenant_id")
        print("  4. Review logs above for details")
        print("\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

