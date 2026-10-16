#!/usr/bin/env python3
"""
Delete admin user from Keycloak before seeding.
This ensures the seeder creates a fresh user.
"""

import httpx
import sys
import os

# Try HTTPS first, fall back to HTTP
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "https://localhost:8443")
# If HTTPS fails, try HTTP (for internal Docker network)
KEYCLOAK_URL_HTTP = os.getenv("KEYCLOAK_URL_HTTP", "http://localhost:8080")
ADMIN_USER = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
REALM = os.getenv("KEYCLOAK_REALM", "sentinelgrid")
ADMIN_EMAIL = os.getenv("KEYCLOAK_ADMIN_EMAIL", "admin@sentinelgrid.ai")

if len(sys.argv) > 1:
    ADMIN_EMAIL = sys.argv[1]
if len(sys.argv) > 2:
    REALM = sys.argv[2]

print(f"Deleting admin user '{ADMIN_EMAIL}' from realm '{REALM}'...")
print(f"Keycloak URL: {KEYCLOAK_URL}")

# Step 1: Get admin token
print("\n1. Getting admin token...")
token_url = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"
token_data = {
    "client_id": "admin-cli",
    "username": ADMIN_USER,
    "password": ADMIN_PASSWORD,
    "grant_type": "password",
}

# Try HTTPS first, fall back to HTTP
admin_token = None
for url_base in [KEYCLOAK_URL, KEYCLOAK_URL_HTTP]:
    token_url = f"{url_base}/realms/master/protocol/openid-connect/token"
    try:
        with httpx.Client(timeout=10.0, verify=False) as client:
            token_response = client.post(token_url, data=token_data)
            if token_response.status_code == 200:
                admin_token = token_response.json()["access_token"]
                print(f"✅ Admin token obtained from {url_base}")
                KEYCLOAK_URL = url_base  # Use the working URL
                break
    except Exception as e:
        continue

if not admin_token:
    print(f"❌ Failed to get admin token from both {KEYCLOAK_URL} and {KEYCLOAK_URL_HTTP}")
    sys.exit(1)

# Step 2: Check if user exists
print(f"\n2. Checking if user '{ADMIN_EMAIL}' exists...")
users_url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users"
params = {"username": ADMIN_EMAIL, "exact": "true"}
headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

try:
    with httpx.Client(timeout=10.0, verify=False) as client:
        users_response = client.get(users_url, headers=headers, params=params)
        if users_response.status_code != 200:
            print(f"❌ Failed to check for user: {users_response.status_code}")
            print(users_response.text)
            sys.exit(1)
        
        users = users_response.json()
        if not users:
            print(f"ℹ️  User '{ADMIN_EMAIL}' does not exist in realm '{REALM}', nothing to delete")
            sys.exit(0)
        
        user_id = users[0]["id"]
        print(f"✅ Found user '{ADMIN_EMAIL}' (ID: {user_id})")
except Exception as e:
    print(f"❌ Error checking for user: {e}")
    sys.exit(1)

# Step 3: Delete user
print(f"\n3. Deleting user '{ADMIN_EMAIL}'...")
delete_url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}"

try:
    with httpx.Client(timeout=10.0, verify=False) as client:
        delete_response = client.delete(delete_url, headers=headers)
        if delete_response.status_code == 204:
            print(f"✅ Successfully deleted user '{ADMIN_EMAIL}' from realm '{REALM}'")
            sys.exit(0)
        else:
            print(f"❌ Failed to delete user: {delete_response.status_code}")
            print(delete_response.text[:500])
            sys.exit(1)
except Exception as e:
    print(f"❌ Error deleting user: {e}")
    sys.exit(1)

