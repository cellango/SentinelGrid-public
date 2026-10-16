#!/usr/bin/env python3
"""
Configure User Profile attribute via Realm Component Provider API.
Keycloak 26.x stores User Profile configuration in realm components.

This script:
1. Gets realm component providers
2. Updates the declarative-user-profile provider config
3. Adds tenant_id attribute to User Profile
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
print("=" * 60)

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

headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

# Step 2: Get realm components
print(f"\n2. Getting realm components...")
components_url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/components"

try:
    with httpx.Client(timeout=10.0, verify=False) as client:
        components_response = client.get(components_url, headers=headers)
        if components_response.status_code != 200:
            print(f"❌ Failed to get components: {components_response.status_code}")
            print(components_response.text[:500])
            sys.exit(1)
        
        components = components_response.json()
        print(f"✅ Found {len(components)} components")
        
        # Find User Profile provider
        user_profile_provider = None
        for comp in components:
            if comp.get("providerId") == "declarative-user-profile" or comp.get("providerType") == "org.keycloak.userprofile.UserProfileProvider":
                user_profile_provider = comp
                break
        
        if not user_profile_provider:
            print("⚠️  User Profile provider not found. May need to be created.")
            print("   Creating User Profile provider...")
            # Create new provider
            new_provider = {
                "name": "declarative-user-profile",
                "providerId": "declarative-user-profile",
                "providerType": "org.keycloak.userprofile.UserProfileProvider",
                "parentId": REALM,
                "config": {
                    "kc.user.profile.config": ["{}"]
                }
            }
            create_response = client.post(components_url, headers=headers, json=new_provider)
            if create_response.status_code in [200, 201]:
                print("✅ Created User Profile provider")
                user_profile_provider = create_response.json() if create_response.content else new_provider
            else:
                print(f"❌ Failed to create provider: {create_response.status_code}")
                print(create_response.text[:500])
                sys.exit(1)
        else:
            print(f"✅ Found User Profile provider (ID: {user_profile_provider['id']})")
        
except Exception as e:
    print(f"❌ Error accessing components API: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 3: Parse and update User Profile configuration
print(f"\n3. Updating User Profile configuration...")

try:
    # Get current config
    current_config_str = user_profile_provider.get("config", {}).get("kc.user.profile.config", ["{}"])[0]
    current_config = json.loads(current_config_str) if current_config_str else {}
    
    print(f"Current attributes: {list(current_config.get('attributes', []))}")
    
    # Build attribute definition
    tenant_id_attribute = {
        "name": ATTRIBUTE_NAME,
        "displayName": "Tenant ID",
        "validations": {"length": {"max": 255}},
        "permissions": {"view": ["admin", "user"], "edit": ["admin"]},
        "multivalued": False
    }
    
    # Update config
    if "attributes" not in current_config:
        current_config["attributes"] = []
    
    # Check if attribute already exists
    existing_idx = None
    for idx, attr in enumerate(current_config["attributes"]):
        if attr.get("name") == ATTRIBUTE_NAME:
            existing_idx = idx
            break
    
    if existing_idx is not None:
        print(f"⚠️  Attribute '{ATTRIBUTE_NAME}' already exists, updating...")
        current_config["attributes"][existing_idx] = tenant_id_attribute
    else:
        print(f"✅ Adding new attribute '{ATTRIBUTE_NAME}'...")
        current_config["attributes"].append(tenant_id_attribute)
    
    # Ensure unmanagedAttributePolicy is set
    if "unmanagedAttributePolicy" not in current_config:
        current_config["unmanagedAttributePolicy"] = "ENABLED"
        print("✅ Enabled unmanaged attribute policy")
    
    # Update provider component
    updated_provider = {
        "name": user_profile_provider["name"],
        "providerId": user_profile_provider["providerId"],
        "providerType": user_profile_provider["providerType"],
        "parentId": user_profile_provider["parentId"],
        "config": {
            "kc.user.profile.config": [json.dumps(current_config)]
        }
    }
    
    # Update component
    update_url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/components/{user_profile_provider['id']}"
    
    with httpx.Client(timeout=10.0, verify=False) as client:
        update_response = client.put(update_url, headers=headers, json=updated_provider)
        if update_response.status_code in [200, 204]:
            print("✅✅✅ User Profile configured successfully!")
            print(f"   Attribute '{ATTRIBUTE_NAME}' is now available in User Profile")
            sys.exit(0)
        else:
            print(f"❌ Failed to update User Profile: {update_response.status_code}")
            print(update_response.text[:500])
            sys.exit(1)
            
except json.JSONDecodeError as e:
    print(f"❌ Error parsing User Profile config JSON: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error updating User Profile: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

