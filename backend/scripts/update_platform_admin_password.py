#!/usr/bin/env python3
"""
Quick script to update Keycloak platform admin password from Vault.

This is useful when Vault password changes but Keycloak still has the old one.
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
    print("🔄 Updating Keycloak platform admin password from Vault...")
    print()
    
    # Get password from Vault
    print("📥 Retrieving password from Vault...")
    password = get_vault_secret("sentinelgrid/keycloak/platform-admin-password")
    
    if not password:
        print("❌ Failed to retrieve password from Vault")
        print("   Make sure Vault is running and initialized")
        print("   Run: backend/scripts/init_vault.sh")
        sys.exit(1)
    
    print("✅ Retrieved password from Vault")
    print()
    
    # Get Keycloak master admin credentials from Vault (secure - no env vars)
    # In dev mode, Keycloak typically uses default "admin"/"admin"
    # Try default first, then Vault if default doesn't work
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
        keycloak_admin_password = get_vault_secret("sentinelgrid/keycloak/master-admin-password")
        if keycloak_admin_password:
            print("✅ Retrieved Keycloak master admin password from Vault")
            try:
                client = KeycloakAdminAPIClient(keycloak_url, admin_user, keycloak_admin_password)
                print("✅ Connected using Vault password")
            except Exception as e2:
                print(f"❌ Vault password also failed: {e2}")
                print(f"❌ Failed to connect to Keycloak")
                print("   Make sure Keycloak is running and password is correct")
                sys.exit(1)
        else:
            print(f"❌ Failed to connect to Keycloak")
            print("   Default password failed and no Vault password available")
            sys.exit(1)
    
    print()
    
    # Update password
    realm_name = "sg-admin"
    username = "admin@sentinelgrid.ai"
    
    print(f"🔐 Updating password for {username} in realm {realm_name}...")
    
    try:
        # Get user ID
        users = client.get_users(realm_name, {"username": username, "exact": "true"})
        if not users:
            print(f"❌ User {username} not found in realm {realm_name}")
            print("   The platform admin realm may need to be created first")
            print("   Run: python backend/scripts/seed_realms.py")
            sys.exit(1)
        
        user_id = users[0]["id"]
        
        # Update password
        client.set_user_password(realm_name, user_id, password, temporary=False)
        
        print("✅ Password updated successfully!")
        print()
        print(f"Login credentials:")
        print(f"  Email: {username}")
        print(f"  Realm: {realm_name}")
        print(f"  Password: (stored in Vault)")
        
    except Exception as e:
        print(f"❌ Failed to update password: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

