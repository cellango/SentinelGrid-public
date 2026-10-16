#!/usr/bin/env python3
"""
Set tenant_id user attribute using Keycloak Admin REST API.
This script runs on the host and uses the exposed Keycloak port.
"""

import httpx
import json
import sys
import os

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8081")
ADMIN_USER = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
REALM = os.getenv("REALM", "agribotsai")
USERNAME = os.getenv("USERNAME", "admin@agribotsai.com")
TENANT_ID = os.getenv("TENANT_ID", "")

if len(sys.argv) > 1:
    TENANT_ID = sys.argv[1]
if len(sys.argv) > 2:
    USERNAME = sys.argv[2]
if len(sys.argv) > 3:
    REALM = sys.argv[3]

if not TENANT_ID:
    print("Usage: python3 set-tenant-id-attribute.py <tenant_id> [username] [realm]")
    sys.exit(1)

print(f"Setting tenant_id={TENANT_ID} for user {USERNAME} in realm {REALM}")

# Step 1: Get admin token
print("\n1. Getting admin token...")
token_url = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"
token_data = {
    "client_id": "admin-cli",
    "username": ADMIN_USER,
    "password": ADMIN_PASSWORD,
    "grant_type": "password",
}

try:
    with httpx.Client(timeout=10.0, verify=False) as client:
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

# Step 2: Get user ID
print(f"\n2. Finding user {USERNAME}...")
headers = {"Authorization": f"Bearer {admin_token}"}
users_url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users"

try:
    with httpx.Client(timeout=10.0, verify=False) as client:
        users_response = client.get(users_url, headers=headers, params={"username": USERNAME})
        if users_response.status_code != 200:
            print(f"❌ Failed to get users: {users_response.status_code}")
            print(users_response.text)
            sys.exit(1)
        
        users = users_response.json()
        if not users:
            print(f"❌ User {USERNAME} not found")
            sys.exit(1)
        
        user_id = users[0]["id"]
        print(f"✅ Found user ID: {user_id}")
except Exception as e:
    print(f"❌ Error finding user: {e}")
    sys.exit(1)

# Step 3: Get current user data
print(f"\n3. Getting current user data...")
user_url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}"

try:
    with httpx.Client(timeout=10.0, verify=False) as client:
        user_response = client.get(user_url, headers=headers)
        if user_response.status_code != 200:
            print(f"❌ Failed to get user data: {user_response.status_code}")
            print(user_response.text)
            sys.exit(1)
        
        user_data = user_response.json()
        current_attrs = user_data.get("attributes", {})
        print(f"Current attributes: {json.dumps(current_attrs) if current_attrs else '{} (empty)'}")
except Exception as e:
    print(f"❌ Error getting user data: {e}")
    sys.exit(1)

# Step 4: Update user with tenant_id
print(f"\n4. Setting tenant_id attribute...")
user_data["attributes"] = user_data.get("attributes", {})
user_data["attributes"]["tenant_id"] = [TENANT_ID]

# Remove read-only fields that might cause issues
readonly_fields = ["access", "self", "createdTimestamp"]
for field in readonly_fields:
    user_data.pop(field, None)

try:
    with httpx.Client(timeout=10.0, verify=False) as client:
        update_headers = {
            **headers,
            "Content-Type": "application/json"
        }
        update_response = client.put(
            user_url,
            headers=update_headers,
            json=user_data
        )
        
        if update_response.status_code not in [200, 204]:
            print(f"❌ Failed to update user: {update_response.status_code}")
            print(update_response.text)
            sys.exit(1)
        
        print(f"✅ User updated (HTTP {update_response.status_code})")
except Exception as e:
    print(f"❌ Error updating user: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 5: Verify
print(f"\n5. Verifying tenant_id was set...")
try:
    with httpx.Client(timeout=10.0, verify=False) as client:
        verify_response = client.get(user_url, headers=headers)
        if verify_response.status_code == 200:
            verify_data = verify_response.json()
            verify_attrs = verify_data.get("attributes", {})
            tenant_id_value = verify_attrs.get("tenant_id", [None])[0] if verify_attrs.get("tenant_id") else None
            
            if tenant_id_value == TENANT_ID:
                print(f"✅✅✅ SUCCESS! tenant_id={tenant_id_value} is set correctly")
                print("\n✅ Attribute persistence issue RESOLVED!")
            else:
                print(f"⚠️  tenant_id in user: {tenant_id_value}, expected: {TENANT_ID}")
                print(f"Full attributes: {json.dumps(verify_attrs)}")
                sys.exit(1)
        else:
            print(f"⚠️  Could not verify: {verify_response.status_code}")
except Exception as e:
    print(f"⚠️  Error verifying: {e}")
    sys.exit(1)

print("\n✅ Done! Generate a new token to see tenant_id in claims.")

