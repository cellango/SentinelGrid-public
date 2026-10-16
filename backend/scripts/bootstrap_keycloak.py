#!/usr/bin/env python3
"""
Bootstrap script to reset and seed Keycloak for SentinelGrid.

This script:
1. Resets the Keycloak database (drops and recreates)
2. Creates the SentinelGrid realm
3. Creates clients (web, api, iam-agent)
4. Creates roles (TENANT_ADMIN, SOC_MANAGER, SOC_ANALYST, VIEW_ONLY)
5. Creates protocol mappers
6. Creates admin user: admin@sentinelgrid.ai
7. Creates default tenant in PostgreSQL

Usage:
    python backend/scripts/bootstrap_keycloak.py [--reset-db]
    
Environment Variables:
    KEYCLOAK_URL - Keycloak server URL (default: http://localhost:8081)
    KEYCLOAK_ADMIN_USER - Admin username (default: admin)
    KEYCLOAK_ADMIN_PASSWORD - Admin password (default: admin)
    DB_URL - PostgreSQL database URL (default: postgresql://sg:sg@localhost:5432/sg)
    KEYCLOAK_DB_URL - Keycloak database URL (default: postgresql://keycloak:keycloak@localhost:5432/keycloak)
"""

import sys
import os
import argparse
from pathlib import Path
from uuid import uuid4
from datetime import datetime
import json

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
KEYCLOAK_DB_URL = os.getenv("KEYCLOAK_DB_URL", "postgresql://keycloak:keycloak@localhost:5432/keycloak")

# Admin user details
ADMIN_EMAIL = "admin@sentinelgrid.ai"
ADMIN_PASSWORD = "admin123"
ADMIN_FIRST_NAME = "Admin"
ADMIN_LAST_NAME = "SentinelGrid"
TENANT_NAME = "SentinelGrid"
TENANT_SLUG = "sentinelgrid"


def reset_keycloak_database():
    """Reset Keycloak database by dropping and recreating it."""
    print("=" * 60)
    print("Resetting Keycloak Database")
    print("=" * 60)
    print()
    
    try:
        # Connect to postgres database (not keycloak database)
        db_url_parts = KEYCLOAK_DB_URL.rsplit("/", 1)
        postgres_url = db_url_parts[0] + "/postgres"
        engine = create_engine(postgres_url)
        
        with engine.connect() as conn:
            # Terminate existing connections
            conn.execute(text("""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = 'keycloak'
                AND pid <> pg_backend_pid();
            """))
            conn.commit()
            
            # Drop database
            conn.execute(text("DROP DATABASE IF EXISTS keycloak;"))
            conn.commit()
            print("  ✅ Dropped existing Keycloak database")
            
            # Create database
            conn.execute(text("CREATE DATABASE keycloak;"))
            conn.commit()
            print("  ✅ Created new Keycloak database")
            
        print()
        print("⚠️  Keycloak container needs to restart to initialize the new database")
        print("   Run: docker-compose restart keycloak")
        print()
        
    except Exception as e:
        print(f"  ❌ Error resetting database: {e}")
        raise


def wait_for_keycloak(max_retries=30, delay=2):
    """Wait for Keycloak to be ready."""
    import time
    import requests
    
    print("Waiting for Keycloak to be ready...")
    for i in range(max_retries):
        try:
            response = requests.get(f"{KEYCLOAK_URL}/health/ready", timeout=2)
            if response.status_code == 200:
                print("  ✅ Keycloak is ready")
                return True
        except:
            pass
        
        if i < max_retries - 1:
            print(f"  ⏳ Waiting... ({i+1}/{max_retries})")
            time.sleep(delay)
    
    print("  ⚠️  Keycloak may not be fully ready, continuing anyway...")
    return False


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


def seed_app_catalog(db_session):
    """Seed app_catalog table with default entries (BYO OIDC + GitLab SAML) if missing."""
    print("Seeding app_catalog...")
    rows = db_session.execute(text("SELECT COUNT(1) FROM app_catalog")).scalar()
    if rows and rows > 0:
        print("  ✅ app_catalog already populated")
        return
    defaults = [
        {
            "id": str(uuid4()),
            "name": "custom_byo_proxy",
            "display_name": "Bring Your Own App (Auth Proxy)",
            "description": "Front any homegrown app with an auth proxy (OIDC) and inject headers (X-User/X-Roles).",
            "app_type": "Custom",
            "protocol": "OIDC",
            "icon_url": None,
            "category": "Custom",
            "required_fields": json.dumps(["redirect_uri"]),
            "optional_fields": json.dumps(["entitlements", "assign_groups", "assign_users"]),
            "default_config": json.dumps({
                "entitlements": "admin, user",
                "activation_mode": "draft",
                "redirect_uris": "https://app.example.com/oauth2/callback",
            }),
            "setup_guide": "Use oauth2-proxy or nginx auth_request in front of your app. Configure issuer/client_id/secret from this entry, and trust X-User/X-Email/X-Roles headers.",
            "is_active": True,
        },
        {
            "id": str(uuid4()),
            "name": "gitlab",
            "display_name": "GitLab",
            "description": "Connect GitLab for SSO (SAML).",
            "app_type": "SaaS",
            "protocol": "SAML",
            "icon_url": None,
            "category": "Development",
            "required_fields": json.dumps(["redirect_uri", "entity_id"]),
            "optional_fields": json.dumps(["name_id_format"]),
            "default_config": json.dumps({}),
            "setup_guide": "GitLab SAML: configure ACS/Entity ID; map email as NameID.",
            "is_active": True,
        },
    ]
    for item in defaults:
        db_session.execute(
            text(
                """
                INSERT INTO app_catalog (id, name, display_name, description, app_type, protocol, icon_url, category,
                                         required_fields, optional_fields, default_config, setup_guide, is_active)
                VALUES (:id, :name, :display_name, :description, :app_type, :protocol, :icon_url, :category,
                        :required_fields::jsonb, :optional_fields::jsonb, :default_config::jsonb, :setup_guide, :is_active)
                ON CONFLICT (name) DO NOTHING
                """
            ),
            item,
        )
    db_session.commit()
    print("  ✅ Seeded app_catalog with defaults")


def create_realm(keycloak_admin):
    """Create SentinelGrid realm in Keycloak."""
    print("Creating Keycloak realm...")
    
    try:
        # Check if realm exists
        try:
            realm = keycloak_admin.get_realm(REALM_NAME)
            print(f"  ⚠️  Realm '{REALM_NAME}' already exists, deleting...")
            keycloak_admin.delete_realm(REALM_NAME)
            print(f"  ✅ Deleted existing realm")
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
        print(f"  ❌ Error creating realm: {e}")
        raise


def create_clients(keycloak_admin):
    """Create clients for SentinelGrid realm."""
    print("Creating Keycloak clients...")
    
    # Web client (public)
    try:
        web_client_data = {
            "clientId": "sentinelgrid-web",
            "name": "SentinelGrid Web Client",
            "enabled": True,
            "publicClient": True,
            "standardFlowEnabled": True,
            "directAccessGrantsEnabled": True,
            "redirectUris": [
                "http://localhost:3000/*",
                "http://localhost:3001/*",
                "https://*.sentinelgrid.com/*"
            ],
            "webOrigins": ["+"],
        }
        keycloak_admin.create_client(web_client_data, REALM_NAME)
        print("  ✅ Web client created")
    except KeycloakError as e:
        print(f"  ⚠️  Error creating web client: {e}")
    
    # Frontend client (public)
    try:
        frontend_client_data = {
            "clientId": "sentinelgrid-frontend",
            "name": "SentinelGrid Frontend Client",
            "enabled": True,
            "publicClient": True,
            "standardFlowEnabled": True,
            "directAccessGrantsEnabled": True,
            "redirectUris": [
                "http://localhost:3000/*",
                "http://localhost:3001/*",
            ],
            "webOrigins": ["+"],
        }
        keycloak_admin.create_client(frontend_client_data, REALM_NAME)
        print("  ✅ Frontend client created")
    except KeycloakError as e:
        print(f"  ⚠️  Error creating frontend client: {e}")
    
    # API client (confidential)
    try:
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
    
    # IAM Agent client (service account)
    try:
        iam_client_data = {
            "clientId": "sentinelgrid-iam-agent",
            "name": "SentinelGrid IAM Agent",
            "enabled": True,
            "publicClient": False,
            "serviceAccountsEnabled": True,
            "standardFlowEnabled": False,
            "directAccessGrantsEnabled": False,
            "redirectUris": [],
        }
        keycloak_admin.create_client(iam_client_data, REALM_NAME)
        print("  ✅ IAM Agent client created")
    except KeycloakError as e:
        print(f"  ⚠️  Error creating IAM Agent client: {e}")


def create_roles(keycloak_admin):
    """Create roles for SentinelGrid realm."""
    print("Creating roles...")
    
    roles = [
        {"name": "TENANT_ADMIN", "description": "Full control over tenant"},
        {"name": "SOC_MANAGER", "description": "Manage incidents, playbooks, team"},
        {"name": "SOC_ANALYST", "description": "View and triage alerts, manage incidents"},
        {"name": "VIEW_ONLY", "description": "Read-only access"},
    ]
    
    for role_data in roles:
        try:
            try:
                keycloak_admin.get_realm_role(role_data["name"], REALM_NAME)
                print(f"  ⚠️  Role '{role_data['name']}' already exists, skipping")
            except KeycloakError:
                keycloak_admin.create_realm_role(role_data, REALM_NAME)
                print(f"  ✅ Role '{role_data['name']}' created")
        except KeycloakError as e:
            print(f"  ⚠️  Error creating role {role_data['name']}: {e}")


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
            print("  ⚠️  tenant_id mapper already exists, skipping")
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
            print(f"  ⚠️  User already exists: {user_id}, updating...")
            keycloak_admin.delete_user(user_id, REALM_NAME)
            print("  ✅ Deleted existing user")
        
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
    parser = argparse.ArgumentParser(description="Bootstrap Keycloak for SentinelGrid")
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Reset Keycloak database (drops and recreates)"
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for Keycloak to be ready before proceeding"
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("SentinelGrid Keycloak Bootstrap")
    print("=" * 60)
    print()
    
    # Reset database if requested
    if args.reset_db:
        reset_keycloak_database()
        if args.wait:
            wait_for_keycloak()
        else:
            print("⚠️  Please restart Keycloak container before continuing:")
            print("   docker-compose restart keycloak")
            print()
            response = input("Has Keycloak been restarted? (y/n): ")
            if response.lower() != 'y':
                print("Exiting. Please restart Keycloak and run again.")
                sys.exit(1)
            wait_for_keycloak()
    
    # Connect to database
    print("Connecting to database...")
    engine = create_engine(DB_URL)
    SessionLocal = sessionmaker(bind=engine)
    db_session = SessionLocal()
    
    try:
        # Create tenant
        tenant_id = create_tenant_in_db(db_session)
        try:
            seed_app_catalog(db_session)
        except Exception as e:
            print(f"  ⚠️ Skipping app_catalog seed: {e}")
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
        print("✅ Bootstrap completed successfully!")
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
