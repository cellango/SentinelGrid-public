#!/usr/bin/env python3
"""
Configure User Profile attribute in Keycloak 26.x via Admin REST API.

Keycloak 26.x requires attributes to be configured in User Profile before
they can be set on users. This script configures the tenant_id attribute.
"""

import httpx
import json
import sys
import os

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8081")
ADMIN_USER = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
REALM = os.getenv("REALM", "agribotsai")
ATTRIBUTE_NAME = os.getenv("ATTRIBUTE_NAME", "tenant_id")

print(f"Configuring User Profile attribute '{ATTRIBUTE_NAME}' in realm '{REALM}'")

# Step 1: Get admin token (from host, using exposed port)
# Note: Admin API may require HTTPS, so this might not work from outside container
print("\n1. Getting admin token...")
token_url = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"
token_data = {
    "client_id": "admin-cli",
    "username": ADMIN_USER,
    "password": ADMIN_PASSWORD,
    "grant_type": "password",
}

try:
    # Try with verify=False for HTTP
    with httpx.Client(timeout=10.0, verify=False) as client:
        token_response = client.post(token_url, data=token_data)
        if token_response.status_code != 200:
            print(f"❌ Failed to get admin token: {token_response.status_code}")
            print(token_response.text)
            print("\n⚠️  Note: Admin API may require HTTPS or internal network access")
            sys.exit(1)
        
        admin_token = token_response.json()["access_token"]
        print("✅ Admin token obtained")
except Exception as e:
    print(f"❌ Error getting admin token: {e}")
    print("\n⚠️  Admin API may require HTTPS. This script may need to run inside Keycloak container.")
    sys.exit(1)

# Step 2: Get current User Profile configuration
print(f"\n2. Getting current User Profile configuration...")
headers = {"Authorization": f"Bearer {admin_token}"}
profile_url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/profile"

try:
    with httpx.Client(timeout=10.0, verify=False) as client:
        profile_response = client.get(profile_url, headers=headers)
        if profile_response.status_code == 200:
            profile_config = profile_response.json()
            print(f"✅ Got User Profile config")
            print(f"Current attributes: {list(profile_config.get('attributes', {}).keys())}")
        elif profile_response.status_code == 404:
            print("⚠️  User Profile API endpoint not found (may be different in v26)")
            print(f"Response: {profile_response.text[:200]}")
        else:
            print(f"❌ Failed to get User Profile: {profile_response.status_code}")
            print(profile_response.text[:500])
except Exception as e:
    print(f"❌ Error accessing User Profile API: {e}")

# Step 3: Try alternative endpoints
print(f"\n3. Trying alternative User Profile endpoints...")

endpoints_to_try = [
    f"/admin/realms/{REALM}/users/profile",
    f"/admin/realms/{REALM}/user-profile/config",
    f"/admin/realms/{REALM}/user-profile",
]

for endpoint in endpoints_to_try:
    try:
        url = f"{KEYCLOAK_URL}{endpoint}"
        with httpx.Client(timeout=10.0, verify=False) as client:
            response = client.get(url, headers=headers)
            print(f"  {endpoint}: HTTP {response.status_code}")
            if response.status_code == 200:
                print(f"  ✅ Found working endpoint!")
                print(f"  Response: {response.text[:200]}")
                break
    except Exception as e:
        print(f"  {endpoint}: Error - {e}")

print("\n⚠️  User Profile API may require:")
print("  1. HTTPS connection")
print("  2. Internal Docker network access")
print("  3. Different authentication method")
print("  4. Admin Console UI configuration")

print("\n📝 Next Steps:")
print("  1. Access Admin Console: http://localhost:8081/admin")
print("  2. Navigate to: Realm Settings → User Profile")
print("  3. Add 'tenant_id' attribute")
print("  4. Set as 'unmanaged' or configure validation")
print("  5. Save and test attribute setting via API")

