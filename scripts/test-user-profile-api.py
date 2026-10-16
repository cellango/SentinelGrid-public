#!/usr/bin/env python3
"""
Test User Profile API endpoints in Keycloak 26.x
Runs inside Keycloak container where curl/python3 are available
"""

import httpx
import json
import sys

KEYCLOAK_INTERNAL_URL = "http://localhost:8080"
REALM = "agribotsai"
ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin"

print("Testing User Profile API endpoints in Keycloak 26.x")
print("=" * 60)

# Step 1: Get admin token
print("\n1. Getting admin token...")
token_url = f"{KEYCLOAK_INTERNAL_URL}/realms/master/protocol/openid-connect/token"
token_data = {
    "client_id": "admin-cli",
    "username": ADMIN_USER,
    "password": ADMIN_PASSWORD,
    "grant_type": "password",
}

try:
    with httpx.Client(timeout=10.0) as client:
        token_response = client.post(token_url, data=token_data)
        if token_response.status_code != 200:
            print(f"❌ Failed to get admin token: {token_response.status_code}")
            print(token_response.text)
            sys.exit(1)
        
        admin_token = token_response.json()["access_token"]
        print("✅ Admin token obtained")
except Exception as e:
    print(f"❌ Error getting admin token: {e}")
    sys.exit(1)

# Step 2: Test various User Profile API endpoints
print("\n2. Testing User Profile API endpoints...")
headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

endpoints_to_try = [
    f"/admin/realms/{REALM}/users/profile",
    f"/admin/realms/{REALM}/user-profile/config",
    f"/admin/realms/{REALM}/user-profile",
    f"/admin/realms/{REALM}/user-profile/metadata",
]

for endpoint in endpoints_to_try:
    url = f"{KEYCLOAK_INTERNAL_URL}{endpoint}"
    print(f"\n  Testing: {endpoint}")
    try:
        with httpx.Client(timeout=10.0) as client:
            # Try GET first
            response = client.get(url, headers=headers)
            print(f"    GET: HTTP {response.status_code}")
            if response.status_code == 200:
                print(f"    ✅ Found working endpoint!")
                try:
                    data = response.json()
                    print(f"    Response preview: {json.dumps(data, indent=2)[:500]}")
                    print(f"\n    📝 Full response saved to /tmp/user-profile-config.json")
                    with open("/tmp/user-profile-config.json", "w") as f:
                        json.dump(data, f, indent=2)
                    break
                except:
                    print(f"    Response: {response.text[:200]}")
            elif response.status_code == 404:
                print(f"    ❌ Not found")
            else:
                print(f"    ⚠️  HTTP {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"    ❌ Error: {e}")

# Step 3: If we found the endpoint, try to add tenant_id attribute
print("\n3. If endpoint found, we'll configure tenant_id attribute...")
print("   (This requires knowing the correct API structure)")

print("\n" + "=" * 60)
print("📝 Findings:")
print("  - Check /tmp/user-profile-config.json if endpoint was found")
print("  - If no endpoint worked, User Profile may need UI configuration")
print("  - Or Keycloak version may need upgrade to 26.1.0+")

