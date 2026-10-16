#!/usr/bin/env python3
"""
Drop demo realm and tenant for clean recreation.

This script deletes:
- Demo realm from Keycloak (users, clients, roles, mappers)
- Demo tenant from database

Usage:
    python backend/scripts/drop_demo_realm.py
"""

import os
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text

# Try to import Keycloak admin
try:
    from keycloak import KeycloakAdmin
    from keycloak.exceptions import KeycloakError
    KEYCLOAK_AVAILABLE = True
except ImportError:
    KEYCLOAK_AVAILABLE = False
    KeycloakAdmin = type(None)
    KeycloakError = Exception

# Configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8081")
KEYCLOAK_ADMIN_USER = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
KEYCLOAK_ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
DB_URL = os.getenv("DB_URL", "postgresql://sg:sg@localhost:5432/sg")

REALM_NAME = os.getenv("REALM_NAME", "demo")
TENANT_SLUG = os.getenv("TENANT_SLUG", "demo")


def delete_demo_realm():
    """Delete demo realm from Keycloak."""
    if not KEYCLOAK_AVAILABLE:
        print("⚠️  Keycloak library not available, skipping realm deletion")
        return False
    
    print(f"🗑️  Deleting Keycloak realm '{REALM_NAME}'...")
    
    try:
        # Create master realm admin for realm deletion
        keycloak_admin = KeycloakAdmin(
            server_url=KEYCLOAK_URL,
            username=KEYCLOAK_ADMIN_USER,
            password=KEYCLOAK_ADMIN_PASSWORD,
            realm_name="master",
            verify=False  # Disable SSL verification for dev
        )
        
        # Check if realm exists
        try:
            realm = keycloak_admin.get_realm(REALM_NAME)
            print(f"  ✅ Realm '{REALM_NAME}' found")
        except KeycloakError:
            print(f"  ℹ️  Realm '{REALM_NAME}' does not exist, nothing to delete")
            return True
        
        # Delete realm (this deletes all associated data: users, clients, roles, mappers)
        keycloak_admin.delete_realm(REALM_NAME)
        print(f"  ✅ Realm '{REALM_NAME}' deleted successfully")
        return True
        
    except KeycloakError as e:
        print(f"  ❌ Error deleting realm: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        return False


def delete_demo_tenant():
    """Delete demo tenant from database."""
    print(f"🗑️  Deleting demo tenant from database...")
    
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            # Check if tenant exists
            result = conn.execute(
                text("SELECT id FROM tenants WHERE slug = :slug"),
                {"slug": TENANT_SLUG}
            ).first()
            
            if not result:
                print(f"  ℹ️  Tenant with slug '{TENANT_SLUG}' does not exist, nothing to delete")
                return True
            
            tenant_id = result[0]
            print(f"  ✅ Found tenant: {tenant_id}")
            
            # Delete tenant (cascade will handle related data if foreign keys are set up)
            # First, delete related data manually to be safe
            print("  🗑️  Deleting related data...")
            
            # Delete user entitlements
            conn.execute(
                text("DELETE FROM user_entitlements WHERE tenant_id = :tenant_id"),
                {"tenant_id": str(tenant_id)}
            )
            
            # Delete access requests
            conn.execute(
                text("DELETE FROM access_requests WHERE tenant_id = :tenant_id"),
                {"tenant_id": str(tenant_id)}
            )
            
            # Delete entitlements
            conn.execute(
                text("DELETE FROM entitlements WHERE tenant_id = :tenant_id"),
                {"tenant_id": str(tenant_id)}
            )
            
            # Delete apps
            conn.execute(
                text("DELETE FROM apps WHERE tenant_id = :tenant_id"),
                {"tenant_id": str(tenant_id)}
            )
            
            # Delete access profiles
            conn.execute(
                text("DELETE FROM access_profiles WHERE tenant_id = :tenant_id"),
                {"tenant_id": str(tenant_id)}
            )
            
            # Delete user_tenants
            conn.execute(
                text("DELETE FROM user_tenants WHERE tenant_id = :tenant_id"),
                {"tenant_id": str(tenant_id)}
            )
            
            # Delete assets
            conn.execute(
                text("DELETE FROM assets WHERE tenant_id = :tenant_id"),
                {"tenant_id": str(tenant_id)}
            )
            
            # Finally, delete tenant
            conn.execute(
                text("DELETE FROM tenants WHERE id = :tenant_id"),
                {"tenant_id": str(tenant_id)}
            )
            
            conn.commit()
            print(f"  ✅ Tenant '{TENANT_SLUG}' and all related data deleted successfully")
            return True
            
    except Exception as e:
        print(f"  ❌ Error deleting tenant: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function."""
    print("=" * 70)
    print("🗑️  Drop Demo Realm and Tenant")
    print("=" * 70)
    print()
    
    # Delete realm first
    realm_deleted = delete_demo_realm()
    print()
    
    # Delete tenant
    tenant_deleted = delete_demo_tenant()
    print()
    
    if realm_deleted and tenant_deleted:
        print("=" * 70)
        print("✅ Demo realm and tenant dropped successfully!")
        print("=" * 70)
        print()
        print("Next steps:")
        print("  1. Run seed script to recreate: python backend/scripts/seed_demo_data.py")
        print("  2. Users will need to log out and log back in to get new tokens with tenant_id")
        return 0
    else:
        print("=" * 70)
        print("⚠️  Some operations failed. Please check the errors above.")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())

