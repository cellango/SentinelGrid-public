#!/usr/bin/env python3
"""
Quick script to update Keycloak master admin password from Vault.

This is useful when Vault password changes but Keycloak still has the old one.
No environment variables for passwords - all from Vault.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from keycloak_api_client import KeycloakAdminAPIClient, KeycloakAPIError
import subprocess
import os

def get_vault_secret(path: str, field: str = "value") -> str:
    """Fetch a secret from Vault using docker exec."""
    try:
        vault_addr = os.getenv("VAULT_ADDR", "http://127.0.0.1:8200")
        vault_token = os.getenv("VAULT_TOKEN", "sentinelgrid-dev-root-token")
        
        result = subprocess.run(
            [
                "docker", "exec",
                "-e", f"VAULT_ADDR={vault_addr}",
                "-e", f"VAULT_TOKEN={vault_token}",
                "vault",
                "vault", "kv", "get", "-field", field, path
            ],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"Error retrieving from Vault: {e}")
        return ""

def main():
    print("🔄 Updating Keycloak master admin password from Vault...")
    print()
    
    # Get master admin password from Vault
    print("📥 Retrieving master admin password from Vault...")
    new_password = get_vault_secret("sentinelgrid/keycloak/master-admin-password")
    
    if not new_password:
        print("❌ Failed to retrieve password from Vault")
        print("   Make sure Vault is running and initialized")
        print("   Run: backend/scripts/init_vault.sh")
        sys.exit(1)
    
    print("✅ Retrieved password from Vault")
    print()
    
    # Initialize Keycloak client
    keycloak_url = os.getenv("KEYCLOAK_URL", "https://localhost:8443")
    admin_user = "admin"  # Master realm admin username
    
    print("🔌 Connecting to Keycloak...")
    print("   Trying default dev password first (admin/admin)...")
    
    # Try default password first (most common in dev mode)
    client = None
    try:
        client = KeycloakAdminAPIClient(keycloak_url, admin_user, "admin")
        print("✅ Connected using default dev password")
    except Exception:
        # Default failed, try Vault password
        print("   Default password failed, trying Vault password...")
        try:
            client = KeycloakAdminAPIClient(keycloak_url, admin_user, new_password)
            print("✅ Connected using Vault password (password already updated)")
            print()
            print("✅ Master admin password is already synced from Vault!")
            print(f"   Username: {admin_user}")
            print(f"   Realm: master")
            print(f"   Password: (stored in Vault)")
            return
        except Exception as e2:
            print(f"❌ Vault password also failed: {e2}")
            print(f"❌ Failed to connect to Keycloak")
            print("   Make sure Keycloak is running")
            sys.exit(1)
    
    print()
    
    # Update master admin password
    realm_name = "master"
    username = "admin"
    
    print(f"🔐 Updating master admin password in realm {realm_name}...")
    
    try:
        # Get user ID
        users = client.get_users(realm_name, {"username": username, "exact": "true"})
        if not users:
            print(f"❌ User {username} not found in realm {realm_name}")
            print("   This should never happen - admin user should exist in master realm")
            sys.exit(1)
        
        user_id = users[0]["id"]
        
        # Update password
        client.set_user_password(realm_name, user_id, new_password, temporary=False)
        
        print("✅ Password updated successfully!")
        print()
        print(f"Login credentials:")
        print(f"  Username: {username}")
        print(f"  Realm: {realm_name}")
        print(f"  Password: (stored in Vault)")
        print()
        print("⚠️  Note: You may need to reconnect with the new password for future operations")
        
    except Exception as e:
        print(f"❌ Failed to update password: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

