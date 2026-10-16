#!/usr/bin/env python3
"""
Seed Realms Script - Initialize SentinelGrid realm architecture.

This script:
1. Creates sg-admin realm (platform admin)
2. Creates initial multi-tenant realms (sg-mt-us-1, sg-mt-eu-1)
3. Seeds realms table in database
4. Configures clients, roles, and protocol mappers

Usage:
    python seed_realms.py [--keycloak-url URL] [--admin-user USER] [--admin-password PASS]
"""

import argparse
import logging
import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
# Also add shared libs (sg_core, etc.)
sys.path.insert(0, str(Path(__file__).parent.parent / "libs"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from keycloak_api_client import KeycloakAdminAPIClient, KeycloakAPIError
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError

# Import realm creation service
sys.path.insert(0, str(Path(__file__).parent.parent / "agents" / "iam_agent"))
from app.services.realm_creation_service import RealmCreationService, RealmType, RealmCreationError, RealmNamingError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_vault_secret(path: str, field: str = "value") -> str:
    """
    Fetch a secret from Vault using docker exec (secure - no env vars).
    
    Args:
        path: Vault secret path (e.g., "sentinelgrid/keycloak/platform-admin-password")
        field: Field name to retrieve (default: "value")
    
    Returns:
        Secret value as string, or empty string if not found
    """
    try:
        vault_addr = os.getenv("VAULT_ADDR", "http://127.0.0.1:8200")
        vault_token = os.getenv("VAULT_TOKEN", "sentinelgrid-dev-root-token")
        
        cmd = [
            "docker", "exec",
            "-e", f"VAULT_ADDR={vault_addr}",
            "-e", f"VAULT_TOKEN={vault_token}",
            "vault",
            "vault", "kv", "get", "-field", field, path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            logger.warning(f"Failed to fetch secret from Vault: {path} - {result.stderr}")
            return ""
    except Exception as e:
        logger.warning(f"Error fetching secret from Vault: {e}")
        return ""


def get_keycloak_client(url: str, admin_user: str, admin_password: str) -> KeycloakAdminAPIClient:
    """
    Create KeycloakAdminAPIClient instance.
    
    Args:
        url: Keycloak URL
        admin_user: Admin username
        admin_password: Admin password
    
    Returns:
        KeycloakAdminAPIClient instance
    """
    return KeycloakAdminAPIClient(
        server_url=url,
        admin_user=admin_user,
        admin_password=admin_password,
        verify=False  # Disable SSL verification for self-signed certificates
    )


def create_platform_admin_realm(keycloak_admin: KeycloakAdmin, client: KeycloakAdminAPIClient) -> bool:
    """
    Create sg-admin realm for platform administrators.
    
    CRITICAL: Uses RealmCreationService to ensure User Profile is configured.
    
    Args:
        keycloak_admin: KeycloakAdmin instance (authenticated against master realm)
        client: KeycloakAdminAPIClient instance (for user creation and other operations)
    
    Returns:
        True if successful
    """
    realm_name = "sg-admin"
    
    try:
        # Use centralized realm creation service
        service = RealmCreationService(keycloak_admin)
        result = service.create_realm(
            realm_name=realm_name,
            realm_type=RealmType.PLATFORM_ADMIN,
            display_name="SentinelGrid Platform Admin"
        )
        
        if not result["user_profile_configured"]:
            logger.error(f"⚠️  CRITICAL: User Profile not configured for {realm_name}")
            return False
        
        logger.info(f"✅ Platform admin realm '{realm_name}' ready (status: {result['status']})")
        
        # Create additional platform-specific clients and roles using KeycloakAdminAPIClient
        # (RealmCreationService creates standard clients, but platform admin needs additional ones)
        try:
            # Additional platform admin clients
            additional_clients = [
                {
                    "clientId": "sentinelgrid-web",
                    "name": "SentinelGrid Web Client (Legacy/Compatibility)",
                    "enabled": True,
                    "publicClient": True,
                    "standardFlowEnabled": True,
                    "directAccessGrantsEnabled": True,
                    "redirectUris": ["http://localhost:3000/*", "https://*.sentinelgrid.com/*"],
                    "webOrigins": ["+"],
                },
                {
                    "clientId": "sentinelgrid-platform-api",
                    "name": "SentinelGrid Platform API Service Account",
                    "enabled": True,
                    "publicClient": False,
                    "serviceAccountsEnabled": True,
                    "authorizationServicesEnabled": True,
                    "standardFlowEnabled": False,
                    "directAccessGrantsEnabled": False,
                    "description": "Service account for platform API operations"
                }
            ]
            
            for client_data in additional_clients:
                try:
                    client_uuid = client.create_client(realm_name, client_data)
                    logger.info(f"✅ Created additional client '{client_data['clientId']}' in {realm_name}")
                except KeycloakAPIError as e:
                    if "already exists" in str(e).lower() or "409" in str(e):
                        logger.info(f"⏭️  Client '{client_data['clientId']}' already exists")
                    else:
                        raise
            
            # Additional platform admin roles
            additional_roles = [
                {"name": "PLATFORM_ADMIN", "description": "Full platform administration"},
                {"name": "SUPPORT_ENGINEER", "description": "Customer support access"},
                {"name": "SOC_OPERATOR", "description": "SOC operations"},
            ]
            
            for role in additional_roles:
                try:
                    client.create_realm_role(realm_name, role)
                    logger.info(f"✅ Created role {role['name']} in {realm_name}")
                except KeycloakAPIError as e:
                    if "already exists" in str(e).lower() or "409" in str(e):
                        logger.info(f"⏭️  Role {role['name']} already exists")
                    else:
                        raise
        except Exception as e:
            logger.warning(f"Failed to create additional platform admin resources: {e}")
        
        # Create platform admin user
        logger.info(f"Creating platform admin user in {realm_name}...")
        
        # Get platform admin password from Vault (secure - no env vars) or use default
        platform_admin_password = get_vault_secret("sentinelgrid/keycloak/platform-admin-password")
        if not platform_admin_password:
            platform_admin_password = "Admin123!@#SentinelGrid"
            logger.warning("⚠️  Could not fetch password from Vault, using default (meets policy)")
        else:
            logger.info("✅ Retrieved platform admin password from Vault")
        
        # Check if user already exists
        try:
            users = client.get_users(realm_name, {"username": "admin@sentinelgrid.ai", "exact": "true"})
            if users:
                logger.info(f"⏭️  Platform admin user already exists, updating password from Vault...")
                platform_admin_id = users[0]["id"]
                client.set_user_password(realm_name, platform_admin_id, platform_admin_password, temporary=False)
                logger.info(f"✅ Updated platform admin user password from Vault")
            else:
                # Create user
                user_data = {
                    "username": "admin@sentinelgrid.ai",
                    "email": "admin@sentinelgrid.ai",
                    "firstName": "Platform",
                    "lastName": "Admin",
                    "enabled": True,
                    "emailVerified": True,
                }
                
                platform_admin_id = client.create_user(realm_name, user_data)
                time.sleep(0.5)  # Brief delay for Keycloak to fully process user creation
                client.set_user_password(realm_name, platform_admin_id, platform_admin_password, temporary=False)
                logger.info(f"✅ Created platform admin user: admin@sentinelgrid.ai")
            
            # Assign PLATFORM_ADMIN role
            try:
                client.assign_realm_role(realm_name, platform_admin_id, "PLATFORM_ADMIN")
                logger.info(f"✅ Assigned PLATFORM_ADMIN role to admin@sentinelgrid.ai")
            except Exception as e:
                logger.warning(f"Could not assign PLATFORM_ADMIN role: {e}")
                
        except Exception as e:
            logger.error(f"Failed to create platform admin user: {e}")
            raise
        
        return True
        
    except (RealmCreationError, RealmNamingError) as e:
        logger.error(f"❌ Failed to create platform admin realm: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"❌ Failed to create platform admin realm: {e}", exc_info=True)
        return False
        
        # Create admin clients
        clients_data = [
            {
                "clientId": f"{realm_name}-admin",
                "name": "Platform Admin Client",
                "enabled": True,
                "publicClient": False,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": True,
                "serviceAccountsEnabled": True,
                "authorizationServicesEnabled": True,
                "redirectUris": ["https://*.sentinelgrid.com/*"],
                "webOrigins": ["+"],
            },
            {
                "clientId": "sentinelgrid-web",
                "name": "SentinelGrid Web Client (Legacy/Compatibility)",
                "enabled": True,
                "publicClient": True,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": True,
                "redirectUris": ["http://localhost:3000/*", "https://*.sentinelgrid.com/*"],
                "webOrigins": ["+"],
            },
            {
                "clientId": "sentinelgrid-platform-api",
                "name": "SentinelGrid Platform API Service Account",
                "enabled": True,
                "publicClient": False,
                "serviceAccountsEnabled": True,
                "authorizationServicesEnabled": True,
                "standardFlowEnabled": False,
                "directAccessGrantsEnabled": False,
                "description": "Service account for platform API operations"
            },
            {
                "clientId": "sentinelgrid-iam-agent",
                "name": "SentinelGrid IAM Agent Client",
                "enabled": True,
                "publicClient": False,
                "serviceAccountsEnabled": True,
                "authorizationServicesEnabled": True,
                "directAccessGrantsEnabled": True,
                "redirectUris": [],
            }
        ]
        
        for client_data in clients_data:
            try:
                client_uuid = client.create_client(realm_name, client_data)
                logger.info(f"✅ Created client '{client_data['clientId']}' in {realm_name}")
                
                # Credentials stay in Keycloak; seeding must never retrieve or log them.
                
            except KeycloakAPIError as e:
                if "already exists" in str(e).lower() or "409" in str(e):
                    logger.info(f"⏭️  Client '{client_data['clientId']}' already exists")
                else:
                    raise
        
        # Create admin roles
        roles = [
            {"name": "PLATFORM_ADMIN", "description": "Full platform administration"},
            {"name": "SUPPORT_ENGINEER", "description": "Customer support access"},
            {"name": "SOC_OPERATOR", "description": "SOC operations"},
        ]
        
        for role in roles:
            try:
                client.create_realm_role(realm_name, role)
                logger.info(f"✅ Created role {role['name']} in {realm_name}")
            except KeycloakAPIError as e:
                if "already exists" in str(e).lower() or "409" in str(e):
                    logger.info(f"⏭️  Role {role['name']} already exists")
                else:
                    raise
        
        # Create platform admin user
        logger.info(f"Creating platform admin user in {realm_name}...")
        
        # Get platform admin password from Vault (secure - no env vars) or use default
        # Default password must meet policy: length(12) + digits + lowerCase + upperCase + specialChars
        platform_admin_password = get_vault_secret("sentinelgrid/keycloak/platform-admin-password")
        if not platform_admin_password:
            platform_admin_password = "Admin123!@#SentinelGrid"
            logger.warning("⚠️  Could not fetch password from Vault, using default (meets policy)")
        else:
            logger.info("✅ Retrieved platform admin password from Vault")
        
        # Check if user already exists
        try:
            users = client.get_users(realm_name, {"username": "admin@sentinelgrid.ai", "exact": "true"})
            if users:
                logger.info(f"⏭️  Platform admin user already exists, updating password from Vault...")
                platform_admin_id = users[0]["id"]
                # Update password to match Vault (important for security and consistency)
                client.set_user_password(realm_name, platform_admin_id, platform_admin_password, temporary=False)
                logger.info(f"✅ Updated platform admin user password from Vault")
            else:
                # Create user
                user_data = {
                    "username": "admin@sentinelgrid.ai",
                    "email": "admin@sentinelgrid.ai",
                    "firstName": "Platform",
                    "lastName": "Admin",
                    "enabled": True,
                    "emailVerified": True,
                }
                
                platform_admin_id = client.create_user(realm_name, user_data)
                # Set password separately (with small delay to ensure user is fully created)
                time.sleep(0.5)  # Brief delay for Keycloak to fully process user creation
                client.set_user_password(realm_name, platform_admin_id, platform_admin_password, temporary=False)
                logger.info(f"✅ Created platform admin user: admin@sentinelgrid.ai")
            
            # Assign PLATFORM_ADMIN role
            try:
                client.assign_realm_role(realm_name, platform_admin_id, "PLATFORM_ADMIN")
                logger.info(f"✅ Assigned PLATFORM_ADMIN role to admin@sentinelgrid.ai")
            except Exception as e:
                logger.warning(f"Could not assign PLATFORM_ADMIN role: {e}")
                
        except Exception as e:
            logger.error(f"Failed to create platform admin user: {e}")
            raise
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create platform admin realm: {e}", exc_info=True)
        return False


def create_multi_tenant_realm(
    keycloak_admin: KeycloakAdmin,
    client: KeycloakAdminAPIClient,
    realm_name: str,
    region: str,
    shard_number: int
) -> bool:
    """
    Create a multi-tenant realm.
    
    CRITICAL: Uses RealmCreationService to ensure User Profile is configured.
    
    Args:
        keycloak_admin: KeycloakAdmin instance (authenticated against master realm)
        client: KeycloakAdminAPIClient instance (for client scope creation)
        realm_name: Realm name (e.g., "sg-mt-us-1")
        region: Region code
        shard_number: Shard number
    
    Returns:
        True if successful
    """
    try:
        # Use centralized realm creation service
        service = RealmCreationService(keycloak_admin)
        result = service.create_realm(
            realm_name=realm_name,
            realm_type=RealmType.MULTI_TENANT,
            display_name=f"SentinelGrid Multi-Tenant ({region.upper()} Shard {shard_number})",
            region=region,
            shard_number=shard_number
        )
        
        if not result["user_profile_configured"]:
            logger.error(f"⚠️  CRITICAL: User Profile not configured for {realm_name}")
            return False
        
        logger.info(f"✅ Multi-tenant realm '{realm_name}' ready (status: {result['status']})")
        
        # Create sentinelgrid-tenant client scope with sg.* mappers
        # (This is not handled by RealmCreationService, so we do it here)
        create_tenant_client_scope(client, realm_name)
        
        return True
        
    except (RealmCreationError, RealmNamingError) as e:
        logger.error(f"❌ Failed to create multi-tenant realm {realm_name}: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"❌ Failed to create multi-tenant realm {realm_name}: {e}", exc_info=True)
        return False


def create_tenant_client_scope(client: KeycloakAdminAPIClient, realm_name: str):
    """
    Create sentinelgrid-tenant client scope with sg.* protocol mappers.
    
    Args:
        client: KeycloakAdminAPIClient instance
        realm_name: Realm name
    """
    try:
        # Check if scope exists
        scopes = client.get_client_scopes(realm_name)
        scope_id = None
        for scope in scopes:
            if scope.get("name") == "sentinelgrid-tenant":
                logger.info(f"⏭️  Client scope 'sentinelgrid-tenant' already exists")
                scope_id = scope.get("id")
                break
        
        if not scope_id:
            # Create scope
            scope_data = {
                "name": "sentinelgrid-tenant",
                "description": "SentinelGrid tenant information claims",
                "protocol": "openid-connect",
                "attributes": {
                    "include.in.token.scope": "true",
                    "display.on.consent.screen": "false"
                }
            }
            
            scope_id = client.create_client_scope(realm_name, scope_data)
            logger.info(f"✅ Created client scope 'sentinelgrid-tenant'")
        
        # Add mappers
        mappers = [
            {
                "name": "sg-tenant-id-mapper",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-attribute-mapper",
                "config": {
                    "user.attribute": "tenant_id",
                    "claim.name": "sg.tenant_id",
                    "jsonType.label": "String",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "userinfo.token.claim": "true"
                }
            },
            {
                "name": "sg-tenant-slug-mapper",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-attribute-mapper",
                "config": {
                    "user.attribute": "tenant_slug",
                    "claim.name": "sg.tenant_slug",
                    "jsonType.label": "String",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "userinfo.token.claim": "true"
                }
            },
            {
                "name": "sg-org-id-mapper",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-attribute-mapper",
                "config": {
                    "user.attribute": "org_id",
                    "claim.name": "sg.org_id",
                    "jsonType.label": "String",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "userinfo.token.claim": "true"
                }
            },
            {
                "name": "sg-customer-id-mapper",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-attribute-mapper",
                "config": {
                    "user.attribute": "customer_id",
                    "claim.name": "sg.customer_id",
                    "jsonType.label": "String",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "userinfo.token.claim": "true"
                }
            }
        ]
        
        # Get existing mappers
        existing_mappers = client.get_mappers_from_client_scope(realm_name, scope_id)
        existing_names = {m.get("name") for m in existing_mappers}
        
        for mapper in mappers:
            if mapper["name"] not in existing_names:
                client.add_mapper_to_client_scope(realm_name, scope_id, mapper)
                logger.info(f"✅ Added mapper {mapper['name']}")
            else:
                logger.info(f"⏭️  Mapper {mapper['name']} already exists")
        
        # Attach to all clients
        clients_list = client.get_clients(realm_name)
        for client_obj in clients_list:
            client_id = client_obj.get("id")
            client_name = client_obj.get("clientId")
            try:
                default_scopes = client.get_default_client_scopes(realm_name, client_id)
                if any(s.get("name") == "sentinelgrid-tenant" for s in default_scopes):
                    continue
                
                client.add_default_client_scope(realm_name, client_id, scope_id)
                logger.info(f"✅ Attached scope to client {client_name}")
            except Exception as e:
                logger.warning(f"Could not attach scope to {client_name}: {e}")
        
    except Exception as e:
        logger.error(f"❌ Failed to create tenant client scope: {e}")
        raise


def create_test_customer_user(client: KeycloakAdminAPIClient) -> bool:
    """
    Create a test customer user in sg-mt-us-1 for testing.
    
    Creates:
    - Email: test@example.com
    - Password: Test1234 (meets password policy)
    - Role: TENANT_ADMIN
    - Attributes: tenant_id, tenant_slug, customer_id (test values)
    
    Args:
        client: KeycloakAdminAPIClient instance
    
    Returns:
        True if successful
    """
    realm_name = "sg-mt-us-1"
    
    try:
        # Check if user exists
        users = client.get_users(realm_name, {"username": "test@example.com", "exact": "true"})
        if users:
            logger.info(f"⏭️  Test customer user already exists")
            return True
        
        # Create test user
        user_data = {
            "username": "test@example.com",
            "email": "test@example.com",
            "firstName": "Test",
            "lastName": "Customer",
            "enabled": True,
            "emailVerified": True,
            "attributes": {
                "tenant_id": ["test-tenant-id"],
                "tenant_slug": ["test-customer"],
                "customer_id": ["test-customer-id"]
            }
        }
        
        user_id = client.create_user(realm_name, user_data)
        # Set password separately (with small delay to ensure user is fully created)
        time.sleep(0.5)  # Brief delay for Keycloak to fully process user creation
        # Password must meet policy: length(8) + digits + lowerCase + upperCase
        test_password = "Test1234"  # Meets policy: 8 chars, has digit, lowercase, uppercase
        client.set_user_password(realm_name, user_id, test_password, temporary=False)
        logger.info(f"✅ Created test customer user: test@example.com")
        
        # Assign TENANT_ADMIN role
        try:
            client.assign_realm_role(realm_name, user_id, "TENANT_ADMIN")
            logger.info(f"✅ Assigned TENANT_ADMIN role to test user")
        except Exception as e:
            logger.warning(f"Could not assign role: {e}")
        
        return True
            
    except Exception as e:
        logger.error(f"❌ Failed to create test customer user: {e}")
        return False


def seed_database_realms(db_url: str):
    """
    Seed realms table in database.
    
    Args:
        db_url: Database connection URL
    """
    try:
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Insert platform admin realm
        session.execute(
            text("""
                INSERT INTO realms (realm_name, realm_type, region, shard_number, max_tenants, status)
                VALUES ('sg-admin', 'platform_admin', 'us', NULL, NULL, 'active')
                ON CONFLICT (realm_name) DO UPDATE
                SET updated_at = now()
            """)
        )
        logger.info("✅ Seeded sg-admin realm in database")
        
        # Insert multi-tenant realms
        realms = [
            ("sg-mt-us-1", "us", 1, 1000),
            ("sg-mt-eu-1", "eu", 1, 1000),
        ]
        
        for realm_name, region, shard, max_tenants in realms:
            session.execute(
                text("""
                    INSERT INTO realms (realm_name, realm_type, region, shard_number, max_tenants, status)
                    VALUES (:realm_name, 'multi_tenant', :region, :shard, :max_tenants, 'active')
                    ON CONFLICT (realm_name) DO UPDATE
                    SET max_tenants = :max_tenants,
                        updated_at = now()
                """),
                {
                    "realm_name": realm_name,
                    "region": region,
                    "shard": shard,
                    "max_tenants": max_tenants
                }
            )
            logger.info(f"✅ Seeded {realm_name} realm in database")
        
        session.commit()
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Failed to seed database: {e}", exc_info=True)
        raise


def change_master_admin_password(client: KeycloakAdminAPIClient, new_password: str) -> bool:
    """
    Change the Keycloak master realm admin password.
    
    WARNING: This should ONLY be called in production environments.
    In dev, we keep the default 'admin' password.
    
    Args:
        client: KeycloakAdminAPIClient instance
        new_password: New admin password
    
    Returns:
        True if successful
    """
    try:
        # Get admin user from master realm
        users = client.get_users("master", {"username": "admin", "exact": "true"})
        if not users:
            logger.error("Admin user not found in master realm")
            return False
        
        admin_user_id = users[0]["id"]
        
        # Set new password
        client.set_user_password("master", admin_user_id, new_password, temporary=False)
        logger.info(f"✅ Changed master realm admin password")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to change master admin password: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Seed SentinelGrid realms")
    parser.add_argument(
        "--keycloak-url",
        default=os.getenv("KEYCLOAK_URL", "https://localhost:8443"),
        help="Keycloak URL"
    )
    parser.add_argument(
        "--admin-user",
        default=os.getenv("KEYCLOAK_ADMIN_USER", "admin"),
        help="Keycloak admin username"
    )
    parser.add_argument(
        "--admin-password",
        default=os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin"),
        help="Keycloak admin password (use KEYCLOAK_ADMIN_PASSWORD env var to avoid shell escaping issues)"
    )
    parser.add_argument(
        "--new-admin-password",
        default=os.getenv("KEYCLOAK_NEW_ADMIN_PASSWORD"),
        help="New admin password for master realm (recommended for production)"
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv("DB_URL", "postgresql://sg:sg@localhost:5432/sg"),
        help="Database URL"
    )
    
    args = parser.parse_args()
    
    # Get passwords from Vault (secure) or arguments
    # Fetch from Vault directly - no environment variables for security
    admin_password = get_vault_secret("sentinelgrid/keycloak/master-admin-password") or args.admin_password
    new_admin_password = get_vault_secret("sentinelgrid/keycloak/master-admin-password") or args.new_admin_password
    
    if admin_password:
        logger.info("✅ Retrieved master admin password from Vault")
    else:
        logger.warning("⚠️  Could not fetch master admin password from Vault, using provided/default")
    
    logger.info("🚀 Starting realm seeding process...")
    
    try:
        # Connect to Keycloak - try provided password first, fallback to default
        logger.info(f"Connecting to Keycloak at {args.keycloak_url}...")
        client = None
        auth_success = False
        
        # Try with provided password (from Vault/env)
        if admin_password:
            try:
                client = get_keycloak_client(args.keycloak_url, args.admin_user, admin_password)
                # Test authentication by trying to get a token
                token = client._get_admin_token()
                auth_success = True
                logger.info("✅ Authenticated with provided password")
            except Exception as e:
                logger.warning(f"⚠️  Authentication with provided password failed: {e}")
        
        # Try with default password as fallback if provided password failed
        if not auth_success:
            logger.info("Trying default password (admin) as fallback...")
            try:
                client = get_keycloak_client(args.keycloak_url, args.admin_user, "admin")
                token = client._get_admin_token()
                auth_success = True
                logger.info("✅ Authenticated with default password")
                # CRITICAL: Do NOT change master admin password in dev environments
                # Only change password in production when explicitly requested
                environment = os.getenv("ENVIRONMENT", "development").lower()
                is_production = environment == "production" or os.getenv("PRODUCTION", "false").lower() == "true"
                
                if is_production and new_admin_password and new_admin_password != "admin":
                    logger.info("Updating password to Vault password (PRODUCTION MODE)...")
                    if change_master_admin_password(client, new_admin_password):
                        logger.info(f"✅ Master admin password updated to Vault password")
                        # Recreate client with new password
                        client.close()
                        client = get_keycloak_client(args.keycloak_url, args.admin_user, new_admin_password)
                    else:
                        logger.warning("⚠️  Failed to update password, continuing with default")
                elif not is_production:
                    logger.info("⏭️  Skipping master admin password change (dev environment - keeping default 'admin' password)")
            except Exception as e2:
                logger.error(f"❌ Authentication failed with both provided and default passwords: {e2}")
                raise
        
        if not auth_success or not client:
            raise Exception("Failed to authenticate with Keycloak")
        
        try:
            # CRITICAL: Do NOT change master admin password in dev environments
            # Only change password in production when explicitly requested
            # In dev, we keep the default 'admin' password until production deployment
            environment = os.getenv("ENVIRONMENT", "development").lower()
            is_production = environment == "production" or os.getenv("PRODUCTION", "false").lower() == "true"
            
            if is_production and new_admin_password and new_admin_password != admin_password:
                logger.info("Changing master realm admin password (PRODUCTION MODE)...")
                if change_master_admin_password(client, new_admin_password):
                    logger.info(f"✅ Master admin password changed to secure value")
                    # Recreate client with new password
                    client.close()
                    client = get_keycloak_client(args.keycloak_url, args.admin_user, new_admin_password)
                else:
                    logger.warning("⚠️  Failed to change master admin password")
            elif new_admin_password and new_admin_password == admin_password:
                logger.info("⏭️  Master admin password already matches (no change needed)")
            elif not is_production:
                logger.info("⏭️  Skipping master admin password change (dev environment - keeping default 'admin' password)")
            
            # Create KeycloakAdmin instance for realm creation service
            # (RealmCreationService uses KeycloakAdmin, not KeycloakAdminAPIClient)
            keycloak_admin = KeycloakAdmin(
                server_url=args.keycloak_url,
                username=args.admin_user,
                password=admin_password if auth_success else "admin",
                realm_name="master",  # Admin operations use master realm
                verify=False  # Disable SSL verification for dev
            )
            
            # Create platform admin realm
            logger.info("Creating platform admin realm...")
            if not create_platform_admin_realm(keycloak_admin, client):
                logger.error("Failed to create platform admin realm")
                sys.exit(1)
            
            # Create multi-tenant realms
            logger.info("Creating multi-tenant realms...")
            realms = [
                ("sg-mt-us-1", "us", 1),
                ("sg-mt-eu-1", "eu", 1),
            ]
            
            for realm_name, region, shard in realms:
                if not create_multi_tenant_realm(keycloak_admin, client, realm_name, region, shard):
                    logger.error(f"Failed to create realm {realm_name}")
                    sys.exit(1)
            
            # Seed database
            logger.info("Seeding database...")
            seed_database_realms(args.db_url)
            
            # Create test customer user in sg-mt-us-1 for testing
            logger.info("Creating test customer user in sg-mt-us-1...")
            if not create_test_customer_user(client):
                logger.warning("⚠️  Failed to create test customer user (non-fatal)")
            
            logger.info("✅ Realm seeding completed successfully!")
            
            # Write credentials file
            write_credentials_file(args.db_url)
        
        finally:
            # Close client connection
            client.close()
        
    except Exception as e:
        logger.error(f"❌ Realm seeding failed: {e}", exc_info=True)
        sys.exit(1)


def write_credentials_file(db_url: str):
    """Write credentials to file for reference."""
    try:
        creds_file = Path(__file__).parent / "SEEDED_CREDENTIALS.txt"
        
        with open(creds_file, "w") as f:
            f.write("=" * 70 + "\n")
            f.write("SentinelGrid Seeded Credentials\n")
            f.write("=" * 70 + "\n\n")
            
            f.write("IMPORTANT: These are default credentials for development.\n")
            f.write("DO NOT use these in production!\n\n")
            
            f.write("-" * 70 + "\n")
            f.write("KEYCLOAK MASTER ADMIN\n")
            f.write("-" * 70 + "\n")
            f.write("URL:      http://localhost:8080/admin\n")
            f.write("Username: admin\n")
            f.write("Password: admin (CHANGE THIS IN PRODUCTION!)\n\n")
            
            f.write("-" * 70 + "\n")
            f.write("PLATFORM ADMIN USER (sg-admin realm)\n")
            f.write("-" * 70 + "\n")
            f.write("Realm:    sg-admin\n")
            f.write("Email:    admin@sentinelgrid.ai\n")
            f.write("Password: Admin123!@#SentinelGrid (or from PLATFORM_ADMIN_PASSWORD env var)\n")
            f.write("Role:     PLATFORM_ADMIN\n")
            f.write("Purpose:  SentinelGrid platform administration\n\n")
            
            f.write("-" * 70 + "\n")
            f.write("TEST CUSTOMER USER (sg-mt-us-1 realm)\n")
            f.write("-" * 70 + "\n")
            f.write("Realm:    sg-mt-us-1\n")
            f.write("Email:    test@example.com\n")
            f.write("Password: Test1234\n")
            f.write("Role:     TENANT_ADMIN\n")
            f.write("Purpose:  Testing customer flows\n\n")
            
            f.write("-" * 70 + "\n")
            f.write("SERVICE ACCOUNTS\n")
            f.write("-" * 70 + "\n")
            f.write("Client ID: sentinelgrid-platform-api\n")
            f.write("Realm:     sg-admin\n")
            f.write("Purpose:   Platform API operations\n")
            f.write("Note:      Retrieve secret from Keycloak Admin Console\n\n")
            
            f.write("Client ID: sentinelgrid-iam-agent\n")
            f.write("Realm:     sg-admin, sg-mt-us-1, sg-mt-eu-1\n")
            f.write("Purpose:   IAM Agent operations\n")
            f.write("Note:      Retrieve secret from Keycloak Admin Console\n\n")
            
            f.write("-" * 70 + "\n")
            f.write("REALMS CREATED\n")
            f.write("-" * 70 + "\n")
            f.write("sg-admin    - Platform admin realm\n")
            f.write("sg-mt-us-1  - US multi-tenant realm (capacity: 1000)\n")
            f.write("sg-mt-eu-1  - EU multi-tenant realm (capacity: 1000)\n\n")
            
            f.write("-" * 70 + "\n")
            f.write("TOKEN ENDPOINTS\n")
            f.write("-" * 70 + "\n")
            f.write("Platform Admin:\n")
            f.write("  https://localhost:8443/realms/sg-admin/protocol/openid-connect/token\n\n")
            f.write("US Customers:\n")
            f.write("  https://localhost:8443/realms/sg-mt-us-1/protocol/openid-connect/token\n\n")
            f.write("EU Customers:\n")
            f.write("  https://localhost:8443/realms/sg-mt-eu-1/protocol/openid-connect/token\n\n")
            
            f.write("=" * 70 + "\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("=" * 70 + "\n")
        
        logger.info(f"✅ Credentials written to: {creds_file}")
        logger.info(f"   View with: cat {creds_file}")
        
    except Exception as e:
        logger.warning(f"Could not write credentials file: {e}")


if __name__ == "__main__":
    main()
