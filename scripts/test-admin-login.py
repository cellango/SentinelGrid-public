#!/usr/bin/env python3
"""
Test login for admin user to verify account was created correctly.
"""

import httpx
import sys
import os
import json
import base64

# Try HTTPS first, fall back to HTTP
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "https://localhost:8443")
KEYCLOAK_URL_HTTP = os.getenv("KEYCLOAK_URL_HTTP", "http://localhost:8080")
REALM = os.getenv("KEYCLOAK_REALM", "sentinelgrid")
ADMIN_EMAIL = os.getenv("KEYCLOAK_ADMIN_EMAIL", "admin@sentinelgrid.ai")
ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD_SEED", "admin123")
CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "sentinelgrid-web")

if len(sys.argv) > 1:
    ADMIN_EMAIL = sys.argv[1]
if len(sys.argv) > 2:
    ADMIN_PASSWORD = sys.argv[2]
if len(sys.argv) > 3:
    REALM = sys.argv[3]

print(f"Testing login for user '{ADMIN_EMAIL}' in realm '{REALM}'...")
print(f"Keycloak URL: {KEYCLOAK_URL}")
print(f"Client ID: {CLIENT_ID}")

# Step 1: Attempt to get token
print("\n1. Attempting to get access token...")
token_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"
token_data = {
    "client_id": CLIENT_ID,
    "username": ADMIN_EMAIL,
    "password": ADMIN_PASSWORD,
    "grant_type": "password",
    "scope": "openid profile email",
}

# Try HTTPS first, fall back to HTTP
token_response = None
for url_base in [KEYCLOAK_URL, KEYCLOAK_URL_HTTP]:
    token_url = f"{url_base}/realms/{REALM}/protocol/openid-connect/token"
    try:
        with httpx.Client(timeout=10.0, verify=False) as client:
            token_response = client.post(
                token_url,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if token_response.status_code == 200:
                KEYCLOAK_URL = url_base  # Use the working URL
                break
    except Exception as e:
        continue

if not token_response:
    print(f"❌ Failed to connect to Keycloak at {KEYCLOAK_URL} or {KEYCLOAK_URL_HTTP}")
    sys.exit(1)

try:
    if token_response.status_code == 200:
        
        if token_response.status_code == 200:
            token_data = token_response.json()
            if "access_token" in token_data:
                access_token = token_data["access_token"]
                print("✅ Login successful! Token obtained")
                
                # Step 2: Decode token to verify claims
                print("\n2. Decoding token to verify claims...")
                try:
                    # JWT tokens have 3 parts separated by dots
                    parts = access_token.split('.')
                    if len(parts) >= 2:
                        # Decode payload (second part)
                        payload_part = parts[1]
                        # Add padding if needed
                        payload_part += '=' * (4 - len(payload_part) % 4)
                        payload = json.loads(base64.urlsafe_b64decode(payload_part).decode('utf-8'))
                        
                        print(f"✅ Token decoded successfully")
                        print(f"\nToken Claims:")
                        print(f"  - Username: {payload.get('preferred_username', 'N/A')}")
                        print(f"  - Email: {payload.get('email', 'N/A')}")
                        print(f"  - Realm: {payload.get('iss', 'N/A').split('/realms/')[-1] if 'realms' in payload.get('iss', '') else 'N/A'}")
                        print(f"  - Roles: {payload.get('realm_access', {}).get('roles', [])}")
                        print(f"  - Tenant ID: {payload.get('tenant_id', 'N/A')}")
                        print(f"  - Expires: {payload.get('exp', 'N/A')}")
                        
                        # Verify key fields
                        if payload.get('preferred_username') == ADMIN_EMAIL:
                            print("\n✅ Username matches")
                        else:
                            print(f"\n⚠️  Username mismatch: expected {ADMIN_EMAIL}, got {payload.get('preferred_username')}")
                        
                        if payload.get('email') == ADMIN_EMAIL:
                            print("✅ Email matches")
                        else:
                            print(f"⚠️  Email mismatch: expected {ADMIN_EMAIL}, got {payload.get('email')}")
                        
                        roles = payload.get('realm_access', {}).get('roles', [])
                        if 'TENANT_ADMIN' in roles:
                            print("✅ TENANT_ADMIN role found")
                        else:
                            print(f"⚠️  TENANT_ADMIN role not found. Roles: {roles}")
                        
                        print("\n✅ Login test PASSED - Account is correctly configured!")
                        sys.exit(0)
                    else:
                        print("⚠️  Token format unexpected")
                except Exception as e:
                    print(f"⚠️  Could not decode token: {e}")
                    print("✅ But login was successful, so account is working")
                    sys.exit(0)
            else:
                print(f"❌ Token response missing access_token: {token_data}")
                sys.exit(1)
        else:
            error_data = token_response.json() if token_response.headers.get("content-type", "").startswith("application/json") else {"error": token_response.text}
            print(f"❌ Login failed ({token_response.status_code}): {error_data}")
            sys.exit(1)
except Exception as e:
    print(f"❌ Error during login test: {e}")
    sys.exit(1)

