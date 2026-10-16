#!/usr/bin/env python3
"""
Simple test script to verify Keycloak authentication flow.
Creates a test user, logs in, and deletes the user.
Uses exposed Keycloak API endpoints (no need to run inside container).
"""

import sys
import asyncio
import httpx
import json
from typing import Optional, Dict, Any

# Configuration - using exposed ports
KEYCLOAK_URL = "http://localhost:8081"  # HTTP endpoint (redirects to HTTPS)
KEYCLOAK_HTTPS_URL = "https://localhost:8443"  # HTTPS endpoint
KEYCLOAK_ADMIN_USER = "admin"
KEYCLOAK_ADMIN_PASSWORD = "admin"
REALM = "sentinelgrid"
TEST_CLIENT_ID = "sentinelgrid-web"

TEST_USER_EMAIL = "test@sentinelgrid.ai"
TEST_USER_PASSWORD = "TestPassword123!"


def get_admin_token() -> Optional[str]:
    """Get admin access token from master realm."""
    # Try HTTPS first, then HTTP
    for base_url in [KEYCLOAK_HTTPS_URL, KEYCLOAK_URL]:
        try:
            response = httpx.post(
                f"{base_url}/realms/master/protocol/openid-connect/token",
                data={
                    "grant_type": "password",
                    "client_id": "admin-cli",
                    "username": KEYCLOAK_ADMIN_USER,
                    "password": KEYCLOAK_ADMIN_PASSWORD,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
                verify=False,  # For self-signed certs in dev
                follow_redirects=True
            )
            if response.status_code == 200:
                return response.json()["access_token"]
            else:
                print(f"   ⚠️  Failed via {base_url}: {response.status_code}")
                continue
        except Exception as e:
            print(f"   ⚠️  Exception with {base_url}: {e}")
            continue
    
    print(f"   ❌ Failed to get admin token from any endpoint")
    return None


def get_client_info(admin_token: str) -> Optional[Dict[str, Any]]:
    """Get client information."""
    for base_url in [KEYCLOAK_HTTPS_URL, KEYCLOAK_URL]:
        try:
            response = httpx.get(
                f"{base_url}/admin/realms/{REALM}/clients",
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                },
                timeout=10.0,
                verify=False,
                follow_redirects=True
            )
            if response.status_code == 200:
                clients = response.json()
                print(f"   ✅ Found {len(clients)} clients")
                web_client = [c for c in clients if c.get('clientId') == TEST_CLIENT_ID]
                if web_client:
                    return web_client[0]
                else:
                    print(f"   ⚠️  Client '{TEST_CLIENT_ID}' not in list")
                    print(f"      Available clients: {[c.get('clientId') for c in clients[:5]]}")
                    continue
            else:
                print(f"   ⚠️  Failed via {base_url}: {response.status_code} - {response.text[:100]}")
                continue
        except Exception as e:
            print(f"   ⚠️  Exception with {base_url}: {e}")
            continue
    
    print(f"   ❌ Failed to get client info from any endpoint")
    return None


def create_test_user(admin_token: str) -> Optional[str]:
    """Create a test user."""
    try:
        # Check if user exists
        for base_url in [KEYCLOAK_HTTPS_URL, KEYCLOAK_URL]:
            try:
                response = httpx.get(
                    f"{base_url}/admin/realms/{REALM}/users",
                    params={"username": TEST_USER_EMAIL},
                    headers={
                        "Authorization": f"Bearer {admin_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0,
                    verify=False,
                    follow_redirects=True
                )
                if response.status_code == 200:
                    users = response.json()
                    if users:
                        # Delete existing user
                        user_id = users[0]["id"]
                        delete_response = httpx.delete(
                            f"{base_url}/admin/realms/{REALM}/users/{user_id}",
                            headers={"Authorization": f"Bearer {admin_token}"},
                            timeout=10.0,
                            verify=False,
                            follow_redirects=True
                        )
                        print(f"   ⚠️  Deleted existing user")
                    break
            except:
                continue
        
        # Create new user
        user_data = {
            "username": TEST_USER_EMAIL,
            "email": TEST_USER_EMAIL,
            "firstName": "Test",
            "lastName": "User",
            "enabled": True,
            "emailVerified": True,
            "requiredActions": [],
        }
        
        for base_url in [KEYCLOAK_HTTPS_URL, KEYCLOAK_URL]:
            try:
                response = httpx.post(
                    f"{base_url}/admin/realms/{REALM}/users",
                    json=user_data,
                    headers={
                        "Authorization": f"Bearer {admin_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0,
                    verify=False,
                    follow_redirects=True
                )
        
                if response.status_code == 201:
                    # Get user ID from Location header or by querying
                    location = response.headers.get("Location", "")
                    if location:
                        user_id = location.split("/")[-1]
                    else:
                        # Query for the user
                        get_response = httpx.get(
                            f"{base_url}/admin/realms/{REALM}/users",
                            params={"username": TEST_USER_EMAIL},
                            headers={"Authorization": f"Bearer {admin_token}"},
                            timeout=10.0,
                            verify=False,
                            follow_redirects=True
                        )
                        if get_response.status_code == 200:
                            users = get_response.json()
                            user_id = users[0]["id"] if users else None
                        else:
                            user_id = None
                    
                    if user_id:
                        # Set password
                        password_response = httpx.put(
                            f"{base_url}/admin/realms/{REALM}/users/{user_id}/reset-password",
                            json={
                                "type": "password",
                                "value": TEST_USER_PASSWORD,
                                "temporary": False
                            },
                            headers={
                                "Authorization": f"Bearer {admin_token}",
                                "Content-Type": "application/json"
                            },
                            timeout=10.0,
                            verify=False,
                            follow_redirects=True
                        )
                
                        if password_response.status_code in [204, 200]:
                            print(f"   ✅ User created and password set: {user_id}")
                            return user_id
                        else:
                            print(f"   ⚠️  User created but password set failed: {password_response.status_code}")
                            return user_id
                    else:
                        print(f"   ⚠️  User created but couldn't get user ID")
                        return None
                    break
                else:
                    continue
            except:
                continue
        
        print(f"   ❌ Failed to create user from any endpoint")
        return None
    except Exception as e:
        print(f"   ❌ Exception creating user: {e}")
        return None


async def test_login() -> bool:
    """Test login with the test user."""
    try:
        # Try both HTTP and HTTPS endpoints
        for base_url in [KEYCLOAK_URL, KEYCLOAK_HTTPS_URL]:
            try:
                token_url = f"{base_url}/realms/{REALM}/protocol/openid-connect/token"
                response = await httpx.AsyncClient(timeout=10.0, verify=False).post(
                    token_url,
                    data={
                        "grant_type": "password",
                        "client_id": TEST_CLIENT_ID,
                        "username": TEST_USER_EMAIL,
                        "password": TEST_USER_PASSWORD,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ Login successful via {base_url}!")
                    print(f"      - Token type: {data.get('token_type')}")
                    print(f"      - Expires in: {data.get('expires_in')}s")
                    print(f"      - Access token: {data.get('access_token', '')[:50]}...")
                    return True
                else:
                    error_data = response.json() if response.text else {}
                    print(f"   ❌ Login failed via {base_url}: {response.status_code}")
                    print(f"      - Error: {error_data.get('error')}")
                    print(f"      - Description: {error_data.get('error_description')}")
            except Exception as e:
                print(f"   ⚠️  Exception trying {base_url}: {e}")
                continue
        
        return False
    except Exception as e:
        print(f"   ❌ Login test failed with exception: {e}")
        return False


def delete_test_user(admin_token: str, user_id: Optional[str]):
    """Delete the test user."""
    if not user_id:
        # Try to find the user
        for base_url in [KEYCLOAK_HTTPS_URL, KEYCLOAK_URL]:
            try:
                response = httpx.get(
                    f"{base_url}/admin/realms/{REALM}/users",
                    params={"username": TEST_USER_EMAIL},
                    headers={"Authorization": f"Bearer {admin_token}"},
                    timeout=10.0,
                    verify=False,
                    follow_redirects=True
                )
                if response.status_code == 200:
                    users = response.json()
                    if users:
                        user_id = users[0]["id"]
                        break
            except:
                continue
    
    if user_id:
        for base_url in [KEYCLOAK_HTTPS_URL, KEYCLOAK_URL]:
            try:
                response = httpx.delete(
                    f"{base_url}/admin/realms/{REALM}/users/{user_id}",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    timeout=10.0,
                    verify=False,
                    follow_redirects=True
                )
                if response.status_code == 204:
                    print(f"   ✅ User deleted")
                    break
            except:
                continue


async def main():
    """Run the complete test."""
    print("=" * 60)
    print("Keycloak Authentication Test")
    print("=" * 60)
    
    # Step 1: Get admin token
    print("\n1. Getting admin token...")
    admin_token = get_admin_token()
    if not admin_token:
        print("   ❌ Cannot proceed without admin token")
        return False
    print("   ✅ Admin token obtained")
    
    # Step 2: Check client
    print(f"\n2. Checking if client '{TEST_CLIENT_ID}' exists...")
    client = get_client_info(admin_token)
    if not client:
        print(f"   ⚠️  Client '{TEST_CLIENT_ID}' not found! Creating it...")
        # Create the client
        client_data = {
            "clientId": TEST_CLIENT_ID,
            "name": "SentinelGrid Web Client",
            "enabled": True,
            "publicClient": True,
            "standardFlowEnabled": True,
            "directAccessGrantsEnabled": True,
            "redirectUris": [
                "http://localhost:3000/*",
                "http://localhost:3001/*",
                "https://localhost:3443/*",
                "https://*.sentinelgrid.com/*"
            ],
            "webOrigins": ["+"]
        }
        
        for base_url in [KEYCLOAK_HTTPS_URL, KEYCLOAK_URL]:
            try:
                response = httpx.post(
                    f"{base_url}/admin/realms/{REALM}/clients",
                    json=client_data,
                    headers={
                        "Authorization": f"Bearer {admin_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0,
                    verify=False,
                    follow_redirects=True
                )
                if response.status_code == 201:
                    print(f"   ✅ Client created successfully!")
                    # Get the created client
                    client = get_client_info(admin_token)
                    if not client:
                        print(f"   ❌ Client created but couldn't retrieve it")
                        return False
                    break
                else:
                    print(f"   ⚠️  Failed to create client via {base_url}: {response.status_code} - {response.text[:200]}")
                    continue
            except Exception as e:
                print(f"   ⚠️  Exception creating client via {base_url}: {e}")
                continue
        
        if not client:
            print(f"   ❌ Failed to create client")
            return False
    
    print(f"   ✅ Client found: {client['id']}")
    print(f"      - Enabled: {client.get('enabled')}")
    print(f"      - Public Client: {client.get('publicClient')}")
    print(f"      - Direct Access Grants: {client.get('directAccessGrantsEnabled')}")
    print(f"      - Standard Flow: {client.get('standardFlowEnabled')}")
    
    # Step 3: Create test user
    print(f"\n3. Creating test user '{TEST_USER_EMAIL}'...")
    user_id = create_test_user(admin_token)
    if not user_id:
        print("   ❌ Cannot proceed without test user")
        return False
    
    # Wait a moment
    await asyncio.sleep(1)
    
    # Step 4: Test login
    print(f"\n4. Testing login with '{TEST_USER_EMAIL}'...")
    login_success = await test_login()
    
    # Step 5: Cleanup
    print(f"\n5. Cleaning up: Deleting test user...")
    delete_test_user(admin_token, user_id)
    
    # Summary
    print("\n" + "=" * 60)
    if login_success:
        print("✅ TEST PASSED: Authentication flow works correctly")
    else:
        print("❌ TEST FAILED: Authentication flow has issues")
    print("=" * 60)
    
    return login_success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
