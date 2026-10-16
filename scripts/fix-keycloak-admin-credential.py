#!/usr/bin/env python3
"""
Fix Keycloak admin credential by creating a proper password hash.
This uses Keycloak's REST API to set the password.
"""

import sys
import httpx
import subprocess
import time

KEYCLOAK_URL = "http://localhost:8080"
ADMIN_USER = "admin"
NEW_PASSWORD = "admin"

def get_keycloak_token():
    """Get admin token using password grant - this won't work if credential is missing."""
    # This won't work, but let's try
    try:
        response = httpx.post(
            f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": ADMIN_USER,
                "password": NEW_PASSWORD,
            },
            timeout=10.0,
        )
        if response.status_code == 200:
            return response.json()["access_token"]
    except:
        pass
    return None

def create_admin_credential_via_cli():
    """Try to create admin credential using kcadm.sh with environment variable."""
    print("🔧 Attempting to use Keycloak's built-in admin creation...")
    print("   This requires restarting Keycloak with KEYCLOAK_ADMIN_PASSWORD set")
    print("")
    print("Since the admin user exists but has no credential, we need to:")
    print("1. Delete the admin user entirely")
    print("2. Restart Keycloak with KEYCLOAK_ADMIN_PASSWORD=admin")
    print("3. Keycloak will recreate the admin user with the password")
    print("")
    
    # Get admin user ID
    result = subprocess.run(
        [
            "docker", "exec", "sentinelgrid-keycloak_db-1",
            "psql", "-U", "keycloak", "-d", "keycloak", "-t", "-c",
            "SELECT id FROM user_entity WHERE username = 'admin' AND realm_id = (SELECT id FROM realm WHERE name = 'master') LIMIT 1;"
        ],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0 or not result.stdout.strip():
        print("❌ Could not find admin user")
        return False
    
    admin_id = result.stdout.strip()
    print(f"✅ Found admin user: {admin_id}")
    print("")
    
    print("⚠️  WARNING: This will delete the admin user and recreate it.")
    print("   All admin user settings will be lost (but realms/users remain).")
    print("")
    response = input("Continue? (yes/no): ")
    
    if response.lower() != "yes":
        print("Cancelled.")
        return False
    
    # Delete admin user
    print("🗑️  Deleting admin user...")
    result = subprocess.run(
        [
            "docker", "exec", "sentinelgrid-keycloak_db-1",
            "psql", "-U", "keycloak", "-d", "keycloak", "-c",
            f"DELETE FROM user_entity WHERE id = '{admin_id}';"
        ],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Failed to delete admin user: {result.stderr}")
        return False
    
    print("✅ Admin user deleted")
    print("")
    
    # Restart Keycloak with KEYCLOAK_ADMIN_PASSWORD
    print("🔄 Restarting Keycloak with KEYCLOAK_ADMIN_PASSWORD=admin...")
    result = subprocess.run(
        [
            "docker", "compose", "-f", "docker-compose.dev.yml", "restart", "keycloak"
        ],
        cwd=".",
        capture_output=True,
        text=True
    )
    
    print("⏳ Waiting for Keycloak to start (30 seconds)...")
    time.sleep(30)
    
    # Test authentication
    print("🔐 Testing authentication...")
    result = subprocess.run(
        [
            "docker", "exec", "sentinelgrid-keycloak-1",
            "/opt/keycloak/bin/kcadm.sh", "config", "credentials",
            "--server", "http://localhost:8080",
            "--realm", "master",
            "--user", "admin",
            "--password", "admin"
        ],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Admin password reset successful!")
        print("")
        print("Login credentials:")
        print(f"  Username: {ADMIN_USER}")
        print(f"  Password: {NEW_PASSWORD}")
        print(f"  Realm: master")
        print(f"  Admin Console: http://localhost:8080/admin")
        return True
    else:
        print("⚠️  Authentication test failed")
        print(f"   Error: {result.stderr}")
        print("")
        print("Try accessing: http://localhost:8080/admin")
        print("Or wait a bit longer and try again.")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Fix Keycloak Admin Credential")
    print("=" * 60)
    print()
    
    if not create_admin_credential_via_cli():
        sys.exit(1)

