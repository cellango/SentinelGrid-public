#!/usr/bin/env python3
"""
Debug script for tenant_id attribute persistence.
This script makes direct REST API calls and logs everything.
"""

import asyncio
import httpx
import json
import uuid
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend/agents/iam_agent'))

KEYCLOAK_URL = "http://localhost:8080"
REALM = "sentinelgrid"
ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin"


async def main():
    print("\n" + "="*70)
    print("  DEBUG: Keycloak Attribute Persistence")
    print("="*70)
    
    # Step 1: Get admin token
    print("\n1. Getting admin token...")
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        response = await client.post(
            f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": ADMIN_USER,
                "password": ADMIN_PASSWORD
            }
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to get token: {response.status_code}")
            print(response.text)
            return
        
        token_data = response.json()
        admin_token = token_data["access_token"]
        print(f"✅ Admin token acquired")
    
    # Step 2: Create user with attributes
    print("\n2. Creating user with tenant_id attribute...")
    
    tenant_id = str(uuid.uuid4())
    customer_id = str(uuid.uuid4())
    test_email = f"debug-{int(asyncio.get_event_loop().time())}@example.com"
    
    print(f"   Email: {test_email}")
    print(f"   tenant_id: {tenant_id}")
    print(f"   customer_id: {customer_id}")
    
    user_payload = {
        "username": test_email,
        "email": test_email,
        "firstName": "Debug",
        "lastName": "User",
        "enabled": True,
        "emailVerified": True,
        "attributes": {
            "tenant_id": [tenant_id],
            "customer_id": [customer_id]
        }
    }
    
    print("\n   Payload being sent:")
    print(json.dumps(user_payload, indent=2))
    
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        response = await client.post(
            f"{KEYCLOAK_URL}/admin/realms/{REALM}/users",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            },
            json=user_payload
        )
        
        print(f"\n   Response status: {response.status_code}")
        print(f"   Response headers: {dict(response.headers)}")
        
        if response.status_code == 201:
            location = response.headers.get("Location", "")
            user_id = location.split("/")[-1]
            print(f"✅ User created: {user_id}")
        else:
            print(f"❌ Failed to create user: {response.status_code}")
            print(response.text)
            return
    
    # Step 3: Immediately read back the user
    print("\n3. Reading user back (immediate)...")
    
    await asyncio.sleep(0.1)  # Brief delay
    
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        response = await client.get(
            f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if response.status_code == 200:
            user_data = response.json()
            attributes = user_data.get("attributes", {})
            
            print(f"✅ User retrieved")
            print(f"\n   User attributes:")
            print(json.dumps(attributes, indent=2))
            
            # Check if tenant_id persisted
            if "tenant_id" in attributes:
                if attributes["tenant_id"] == [tenant_id]:
                    print(f"\n✅✅✅ SUCCESS! tenant_id PERSISTED!")
                    print(f"   Expected: {[tenant_id]}")
                    print(f"   Got:      {attributes['tenant_id']}")
                else:
                    print(f"\n❌ tenant_id value mismatch")
                    print(f"   Expected: {[tenant_id]}")
                    print(f"   Got:      {attributes['tenant_id']}")
            else:
                print(f"\n❌ tenant_id attribute NOT found")
                print(f"   Available attributes: {list(attributes.keys())}")
                print(f"\n🔍 This confirms the Keycloak v25.0 attribute persistence issue")
        else:
            print(f"❌ Failed to get user: {response.status_code}")
    
    # Step 4: Try update method
    print("\n4. Trying to UPDATE user attributes...")
    
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        # Get full user first
        response = await client.get(
            f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if response.status_code == 200:
            user_data = response.json()
            
            # Update with attributes
            user_data["attributes"] = {
                "tenant_id": [tenant_id],
                "customer_id": [customer_id],
                "test_attr": ["test_value"]
            }
            
            # Remove read-only fields
            for field in ["access", "createdTimestamp", "notBefore", "disableableCredentialTypes", "requiredActions"]:
                user_data.pop(field, None)
            
            print(f"   Updating user with attributes...")
            
            response = await client.put(
                f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}",
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                },
                json=user_data
            )
            
            print(f"   Update response: {response.status_code}")
            
            if response.status_code in [200, 204]:
                print(f"✅ Update successful")
                
                # Wait and verify
                await asyncio.sleep(1.0)
                
                response = await client.get(
                    f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    attributes = user_data.get("attributes", {})
                    
                    print(f"\n   Attributes after update:")
                    print(json.dumps(attributes, indent=2))
                    
                    if "tenant_id" in attributes:
                        print(f"\n✅✅✅ SUCCESS! tenant_id PERSISTED after UPDATE!")
                    else:
                        print(f"\n❌ tenant_id still NOT persisted after update")
            else:
                print(f"❌ Update failed: {response.text}")
    
    # Cleanup
    print("\n5. Cleaning up...")
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        response = await client.delete(
            f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code == 204:
            print(f"✅ Test user deleted")
    
    print("\n" + "="*70)
    print("  Debug session complete")
    print("  Check Keycloak logs for detailed information:")
    print("  docker-compose -f docker-compose.dev.yml logs keycloak | grep -i attribute")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

