#!/usr/bin/env python3
"""
Seed script to create default admin user for SentinelGrid.

Creates:
1. Default tenant (sentinelgrid) in database
2. SentinelGrid realm in Keycloak (if not exists)
3. Admin user: admin@sentinelgrid.ai with password admin123
4. Assigns TENANT_ADMIN role

Usage:
    python backend/scripts/seed_admin_user.py
"""

import sys
import os
from pathlib import Path
from uuid import uuid4
from datetime import datetime

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError

# Configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8081")
KEYCLOAK_ADMIN_USER = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
KEYCLOAK_ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
REALM_NAME = "sentinelgrid"
DB_URL = os.getenv("DB_URL", "postgresql://sg:sg@localhost:5432/sg")

# Admin user details
ADMIN_EMAIL = "admin@sentinelgrid.ai"
ADMIN_PASSWORD = "admin123"
ADMIN_FIRST_NAME = "Admin"
ADMIN_LAST_NAME = "SentinelGrid"
TENANT_NAME = "SentinelGrid"
TENANT_SLUG = "sentinelgrid"


def create_tenant_in_db(db_session):
    """Create default tenant in database."""
    print("Creating default tenant in database...")
    
    # Check if tenant exists
    result = db_session.execute(
        text("SELECT id FROM tenants WHERE slug = :slug"),
        {"slug": TENANT_SLUG}
    ).fetchone()
    
    if result:
        tenant_id = result[0]
        print(f"  ✅ Tenant already exists: {tenant_id}")
        return tenant_id
    
    # Create tenant
    tenant_id = uuid4()
    db_session.execute(
        text("""
            INSERT INTO tenants (id, name, slug, status, created_at, updated_at)
            VALUES (:id, :name, :slug, :status, :created_at, :updated_at)
        """),
        {
            "id": str(tenant_id),
            "name": TENANT_NAME,
            "slug": TENANT_SLUG,
            "status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    )
    db_session.commit()
    print(f"  ✅ Tenant created: {tenant_id}")
    return tenant_id


def create_realm(keycloak_admin):
    """Create SentinelGrid realm in Keycloak."""
    print("Creating Keycloak realm...")
    
    try:
        # Check if realm exists
        try:
            realm = keycloak_admin.get_realm(REALM_NAME)
            print(f"  ✅ Realm '{REALM_NAME}' already exists")
            return
        except KeycloakError:
            pass  # Realm doesn't exist, create it
        
        # Create realm
        realm_data = {
            "realm": REALM_NAME,
            "enabled": True,
            "displayName": "SentinelGrid",
            "loginWithEmailAllowed": True,
            "duplicateEmailsAllowed": False,
            "resetPasswordAllowed": True,
            "editUsernameAllowed": False,
            "bruteForceProtected": True,
            "rememberMe": True,
            "verifyEmail": False,
            "accessTokenLifespan": 3600,
            "ssoSessionIdleTimeout": 1800,
        }
        
        keycloak_admin.create_realm(realm_data)
        print(f"  ✅ Realm '{REALM_NAME}' created")
        
    except KeycloakError as e:
        print(f"  ⚠️  Error creating realm: {e}")
        raise


def create_clients(keycloak_admin):
    """Create clients for SentinelGrid realm."""
    print("Creating Keycloak clients...")
    
    # Web client
    try:
        clients = keycloak_admin.get_clients(REALM_NAME)
        web_client = next((c for c in clients if c.get("clientId") == "sentinelgrid-web"), None)
        
        if web_client:
            print("  ✅ Web client already exists")
        else:
            web_client_data = {
                "clientId": "sentinelgrid-web",
                "name": "SentinelGrid Web Client",
                "enabled": True,
                "publicClient": True,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": True,
                "redirectUris": ["http://localhost:3000/*", "https://*.sentinelgrid.com/*"],
                "webOrigins": ["+"],
            }
            keycloak_admin.create_client(web_client_data, REALM_NAME)
            print("  ✅ Web client created")
    except KeycloakError as e:
        print(f"  ⚠️  Error creating web client: {e}")
    
    # API client
    try:
        clients = keycloak_admin.get_clients(REALM_NAME)
        api_client = next((c for c in clients if c.get("clientId") == "sentinelgrid-api"), None)
        
        if api_client:
            print("  ✅ API client already exists")
        else:
            api_client_data = {
                "clientId": "sentinelgrid-api",
                "name": "SentinelGrid API Client",
                "enabled": True,
                "publicClient": False,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": True,
                "redirectUris": [],
            }
            keycloak_admin.create_client(api_client_data, REALM_NAME)
            print("  ✅ API client created")
    except KeycloakError as e:
        print(f"  ⚠️  Error creating API client: {e}")


def create_roles(keycloak_admin):
    """Create roles for SentinelGrid realm."""
    print("Creating roles...")
    
    roles = ["TENANT_ADMIN", "SOC_MANAGER", "SOC_ANALYST", "VIEW_ONLY"]
    
    for role_name in roles:
        try:
            try:
                keycloak_admin.get_realm_role(role_name, REALM_NAME)
                print(f"  ✅ Role '{role_name}' already exists")
            except KeycloakError:
                role_data = {
                    "name": role_name,
                    "description": f"Role: {role_name}",
                }
                keycloak_admin.create_realm_role(role_data, REALM_NAME)
                print(f"  ✅ Role '{role_name}' created")
        except KeycloakError as e:
            print(f"  ⚠️  Error creating role {role_name}: {e}")


def create_tenant_id_mapper(keycloak_admin):
    """Create tenant_id protocol mapper for API client."""
    print("Creating tenant_id protocol mapper...")
    
    try:
        # Get API client
        clients = keycloak_admin.get_clients(REALM_NAME)
        api_client = next((c for c in clients if c.get("clientId") == "sentinelgrid-api"), None)
        
        if not api_client:
            print("  ⚠️  API client not found, skipping mapper")
            return
        
        client_id = api_client["id"]
        
        # Check if mapper exists
        mappers = keycloak_admin.get_client_protocol_mappers(client_id, REALM_NAME)
        if any(m.get("name") == "tenant-id-mapper" for m in mappers):
            print("  ✅ tenant_id mapper already exists")
            return
        
        # Create mapper
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
            }
        }
        
        keycloak_admin.create_client_protocol_mapper(client_id, mapper_data, REALM_NAME)
        print("  ✅ tenant_id mapper created")
        
    except KeycloakError as e:
        print(f"  ⚠️  Error creating mapper: {e}")


def create_admin_user(keycloak_admin, tenant_id):
    """Create admin user in Keycloak."""
    print("Creating admin user...")
    
    try:
        # Check if user exists
        users = keycloak_admin.get_users(REALM_NAME, query={"username": ADMIN_EMAIL})
        if users:
            user_id = users[0]["id"]
            print(f"  ✅ User already exists: {user_id}")
            
            # Update user to ensure correct settings
            keycloak_admin.update_user(
                user_id,
                {
                    "email": ADMIN_EMAIL,
                    "firstName": ADMIN_FIRST_NAME,
                    "lastName": ADMIN_LAST_NAME,
                    "enabled": True,
                    "emailVerified": True,
                    "attributes": {"tenant_id": [str(tenant_id)]},
                    "requiredActions": [],
                },
                REALM_NAME
            )
            
            # Set password
            keycloak_admin.set_user_password(user_id, ADMIN_PASSWORD, temporary=False, realm_name=REALM_NAME)
            print("  ✅ User password updated")
            
        else:
            # Create user
            user_data = {
                "username": ADMIN_EMAIL,
                "email": ADMIN_EMAIL,
                "firstName": ADMIN_FIRST_NAME,
                "lastName": ADMIN_LAST_NAME,
                "enabled": True,
                "emailVerified": True,
                "attributes": {"tenant_id": [str(tenant_id)]},
                "requiredActions": [],
            }
            
            user_id = keycloak_admin.create_user(user_data, REALM_NAME)
            print(f"  ✅ User created: {user_id}")
            
            # Set password
            keycloak_admin.set_user_password(user_id, ADMIN_PASSWORD, temporary=False, realm_name=REALM_NAME)
            print("  ✅ User password set")
        
        # Assign TENANT_ADMIN role
        try:
            role = keycloak_admin.get_realm_role("TENANT_ADMIN", REALM_NAME)
            keycloak_admin.assign_realm_roles(user_id, [role], REALM_NAME)
            print("  ✅ TENANT_ADMIN role assigned")
        except KeycloakError as e:
            print(f"  ⚠️  Error assigning role: {e}")
        
        return user_id
        
    except KeycloakError as e:
        print(f"  ❌ Error creating user: {e}")
        raise


def main():
    """Main entry point."""
    print("=" * 60)
    print("SentinelGrid Admin User Seeding")
    print("=" * 60)
    print()
    
    # Connect to database
    print("Connecting to database...")
    engine = create_engine(DB_URL)
    SessionLocal = sessionmaker(bind=engine)
    db_session = SessionLocal()
    
    try:
        # Create tenant
        tenant_id = create_tenant_in_db(db_session)
        print()
        
        # Connect to Keycloak
        print("Connecting to Keycloak...")
        keycloak_admin = KeycloakAdmin(
            server_url=KEYCLOAK_URL,
            username=KEYCLOAK_ADMIN_USER,
            password=KEYCLOAK_ADMIN_PASSWORD,
            realm_name="master",  # Admin operations use master realm
            verify=True
        )
        print("  ✅ Connected to Keycloak")
        print()
        
        # Create realm
        create_realm(keycloak_admin)
        print()
        
        # Switch to sentinelgrid realm for subsequent operations
        keycloak_admin.realm_name = REALM_NAME
        
        # Create clients
        create_clients(keycloak_admin)
        print()
        
        # Create roles
        create_roles(keycloak_admin)
        print()
        
        # Create protocol mapper
        create_tenant_id_mapper(keycloak_admin)
        print()
        
        # Create admin user
        user_id = create_admin_user(keycloak_admin, tenant_id)
        print()
        
        print("=" * 60)
        print("✅ Seeding completed successfully!")
        print("=" * 60)
        print()
        print(f"Admin User: {ADMIN_EMAIL}")
        print(f"Password: {ADMIN_PASSWORD}")
        print(f"Tenant ID: {tenant_id}")
        print(f"Realm: {REALM_NAME}")
        print()
        print("You can now log in at: http://localhost:3000")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db_session.close()


if __name__ == "__main__":
    main()

