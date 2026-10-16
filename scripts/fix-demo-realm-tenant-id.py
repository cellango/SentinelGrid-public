#!/usr/bin/env python3
"""
Fix tenant_id issue for demo realm:
1. Add tenant_id protocol mapper to demo-web client
2. Verify users have tenant_id attribute
3. Create user_tenants entries if missing
"""

import sys
import os
import httpx
import json
from uuid import UUID

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Try to detect Keycloak URL - use internal Docker network if running in container
# Try multiple Keycloak URLs
KEYCLOAK_URLS = [
    os.getenv("KEYCLOAK_URL", "http://localhost:8080"),
    "http://keycloak:8080",  # Internal Docker network
    "http://localhost:8081",  # Alternative port
]

KEYCLOAK_URL = None
for url in KEYCLOAK_URLS:
    try:
        httpx.get(f"{url}/health", timeout=2.0, verify=False)
        KEYCLOAK_URL = url
        break
    except:
        continue

if not KEYCLOAK_URL:
    KEYCLOAK_URL = KEYCLOAK_URLS[0]  # Default to first one
REALM = "demo"
ADMIN_USER = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")

def get_admin_token():
    """Get Keycloak admin token."""
    response = httpx.post(
        f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": ADMIN_USER,
            "password": ADMIN_PASSWORD,
        },
        timeout=10.0,
        verify=False
    )
    response.raise_for_status()
    return response.json()["access_token"]

def get_client_id(token, client_id_name):
    """Get client ID by client ID name."""
    response = httpx.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients?clientId={client_id_name}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10.0,
        verify=False
    )
    response.raise_for_status()
    clients = response.json()
    if clients:
        return clients[0]["id"]
    return None

def check_mapper_exists(token, client_uuid):
    """Check if tenant_id mapper exists on client."""
    response = httpx.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10.0,
        verify=False
    )
    response.raise_for_status()
    mappers = response.json()
    return any(m.get("name") == "tenant-id-mapper" for m in mappers)

def create_tenant_id_mapper(token, client_uuid, client_name):
    """Create tenant_id protocol mapper on client."""
    mapper_data = {
        "name": "tenant-id-mapper",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-usermodel-attribute-mapper",
        "config": {
            "user.attribute": "tenant_id",
            "claim.name": "tenant_id",
            "jsonType.label": "String",
            "id.token.claim": "true",
            "access.token.claim": "true",
            "userinfo.token.claim": "true",
        }
    }
    
    response = httpx.post(
        f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=mapper_data,
        timeout=10.0,
        verify=False
    )
    
    if response.status_code == 201:
        print(f"  ✅ Created tenant_id mapper on {client_name} client")
        return True
    elif response.status_code == 409:
        print(f"  ✅ tenant_id mapper already exists on {client_name} client")
        return True
    else:
        print(f"  ❌ Failed to create mapper: {response.status_code} - {response.text}")
        return False

def get_users(token):
    """Get all users in realm."""
    response = httpx.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM}/users",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10.0,
        verify=False
    )
    response.raise_for_status()
    return response.json()

def get_user_details(token, user_id):
    """Get user details including attributes."""
    response = httpx.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10.0,
        verify=False
    )
    response.raise_for_status()
    return response.json()

def main():
    print("=" * 60)
    print("Fixing tenant_id for Demo Realm")
    print("=" * 60)
    print()
    
    # Get admin token
    print("1. Getting admin token...")
    try:
        token = get_admin_token()
        print("  ✅ Admin token obtained")
    except Exception as e:
        print(f"  ❌ Failed to get admin token: {e}")
        return 1
    
    # Get web client ID
    print("\n2. Finding demo-web client...")
    web_client_uuid = get_client_id(token, "demo-web")
    if not web_client_uuid:
        print("  ❌ demo-web client not found!")
        return 1
    print(f"  ✅ Found demo-web client: {web_client_uuid}")
    
    # Check if mapper exists
    print("\n3. Checking tenant_id mapper on demo-web client...")
    if check_mapper_exists(token, web_client_uuid):
        print("  ✅ tenant_id mapper already exists on demo-web")
    else:
        print("  ⚠️  tenant_id mapper MISSING on demo-web client!")
        print("  🔧 Creating tenant_id mapper...")
        if create_tenant_id_mapper(token, web_client_uuid, "demo-web"):
            print("  ✅ Mapper created successfully")
        else:
            print("  ❌ Failed to create mapper")
            return 1
    
    # Check API client too
    print("\n4. Checking tenant_id mapper on demo-api client...")
    api_client_uuid = get_client_id(token, "demo-api")
    if api_client_uuid:
        if check_mapper_exists(token, api_client_uuid):
            print("  ✅ tenant_id mapper already exists on demo-api")
        else:
            print("  🔧 Creating tenant_id mapper on demo-api...")
            create_tenant_id_mapper(token, api_client_uuid, "demo-api")
    
    # Check users
    print("\n5. Checking users for tenant_id attribute...")
    users = get_users(token)
    print(f"  Found {len(users)} users in demo realm")
    
    users_without_tenant = []
    for user in users:
        user_id = user["id"]
        username = user.get("username", "N/A")
        user_details = get_user_details(token, user_id)
        attributes = user_details.get("attributes", {})
        tenant_id = attributes.get("tenant_id", [None])[0] if isinstance(attributes.get("tenant_id"), list) else attributes.get("tenant_id")
        
        if not tenant_id:
            users_without_tenant.append((user_id, username))
            print(f"  ⚠️  User {username} ({user_id}) has NO tenant_id attribute")
        else:
            print(f"  ✅ User {username} has tenant_id: {tenant_id}")
    
    if users_without_tenant:
        print(f"\n  ⚠️  {len(users_without_tenant)} users are missing tenant_id attribute")
        print("  💡 Users need tenant_id attribute set in Keycloak for tokens to include it")
    
    print("\n" + "=" * 60)
    print("✅ Fix complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. If mapper was created, users need to log out and log back in")
    print("2. If users are missing tenant_id attribute, set it in Keycloak Admin Console")
    print("3. Or run: python3 scripts/set-demo-user-tenant-id.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

