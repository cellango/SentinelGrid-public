#!/usr/bin/env python3
"""
Create User Profile component for Keycloak 26.x
Properly handles JSON escaping and includes default attributes

This script enables unmanaged attributes in Keycloak 26.x, allowing custom
attributes like tenant_id to be set without pre-definition in User Profile.

Usage:
    python3 create-user-profile-component.py [realm-name]

Environment Variables:
    REALM: Realm name (default: agribotsai)
    KEYCLOAK_CONTAINER: Docker container name (default: sentinelgrid-keycloak-1)
"""

import json
import subprocess
import sys
import os

# Allow command-line argument or environment variable
REALM = sys.argv[1] if len(sys.argv) > 1 else os.getenv("REALM", "agribotsai")
CONTAINER = os.getenv("KEYCLOAK_CONTAINER", "sentinelgrid-keycloak-1")

print(f"Creating User Profile component for realm: {REALM}")
print("=" * 60)

# Step 1: Get realm ID
print("\n1. Getting realm ID...")
cmd = ["docker", "exec", CONTAINER, "/opt/keycloak/bin/kcadm.sh", 
       "get", f"realms/{REALM}", "--fields", "id", "--format", "csv", "--noquotes"]
result = subprocess.run(cmd, capture_output=True, text=True, check=False)
if result.returncode != 0:
    print(f"❌ Failed to get realm ID: {result.stderr}")
    sys.exit(1)

realm_id = result.stdout.strip().split('\n')[-1]
print(f"✅ Realm ID: {realm_id}")

# Step 2: Check if component already exists
print("\n2. Checking if component already exists...")
cmd = ["docker", "exec", CONTAINER, "/opt/keycloak/bin/kcadm.sh",
       "get", f"components/{REALM}"]
result = subprocess.run(cmd, capture_output=True, text=True, check=False)
if "declarative-user-profile" in result.stdout:
    print("⚠️  Component already exists!")
    sys.exit(0)

# Step 3: Create component JSON
print("\n3. Creating component JSON...")
user_profile_config = {
    "attributes": [
        {
            "name": "username",
            "displayName": "${username}",
            "validations": {},
            "permissions": {"view": ["admin", "user"], "edit": ["admin"]}
        },
        {
            "name": "email",
            "displayName": "${email}",
            "validations": {},
            "permissions": {"view": ["admin", "user"], "edit": ["admin", "user"]}
        }
    ],
    "unmanagedAttributePolicy": "ENABLED"
}

component = {
    "name": "declarative-user-profile",
    "providerId": "declarative-user-profile",
    "providerType": "org.keycloak.userprofile.UserProfileProvider",
    "parentId": realm_id,
    "config": {
        "kc.user.profile.config": [json.dumps(user_profile_config)]
    }
}

component_json = json.dumps(component, indent=2)
print("Component JSON:")
print(component_json[:200] + "...")

# Step 4: Write to file locally and copy to container
print("\n4. Writing JSON file and copying to container...")
temp_file = "/tmp/user-profile-comp.json"
with open(temp_file, 'w') as f:
    json.dump(component, f, indent=2)

# Copy file to container
cmd = ["docker", "cp", temp_file, f"{CONTAINER}:/tmp/user-profile-comp.json"]
result = subprocess.run(cmd, capture_output=True, text=True, check=False)
if result.returncode != 0:
    print(f"❌ Failed to copy JSON: {result.stderr}")
    sys.exit(1)
print("✅ JSON copied to container")

# Step 5: Create component
print("\n5. Creating component via kcadm.sh...")
cmd = ["docker", "exec", CONTAINER, "/opt/keycloak/bin/kcadm.sh",
       "create", "components", "-r", REALM, "-f", "/tmp/user-profile-comp.json", "-i"]
result = subprocess.run(cmd, capture_output=True, text=True, check=False)

if result.returncode == 0 and result.stdout.strip():
    component_id = result.stdout.strip()
    print(f"✅✅✅ Component created! ID: {component_id}")
else:
    print(f"❌ Component creation failed:")
    print(f"Exit code: {result.returncode}")
    print(f"Stdout: {result.stdout}")
    print(f"Stderr: {result.stderr}")
    sys.exit(1)

# Step 6: Verify
print("\n6. Verifying component...")
cmd = ["docker", "exec", CONTAINER, "/opt/keycloak/bin/kcadm.sh",
       "get", f"components/{REALM}"]
result = subprocess.run(cmd, capture_output=True, text=True, check=False)
if "declarative-user-profile" in result.stdout:
    print("✅✅✅ Component verified!")
    sys.exit(0)
else:
    print("⚠️  Component created but not found in list")
    sys.exit(1)

