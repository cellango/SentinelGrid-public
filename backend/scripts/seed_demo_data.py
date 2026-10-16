#!/usr/bin/env python3
"""
Comprehensive Demo Data Seeding Script for SentinelGrid.

Creates a complete demo environment for customer demonstrations including:
- Isolated demo tenant and Keycloak realm
- Demo users with simple shareable password
- IAM portal data (apps, entitlements, access profiles, access requests)
- Security alerts with AI analysis for SIEM demos

Usage:
    python backend/scripts/seed_demo_data.py

Environment Variables:
    TENANT_NAME - Demo tenant name (default: "Demo Company")
    TENANT_SLUG - Demo tenant slug (default: "demo")
    REALM_NAME - Keycloak realm name (default: "demo")
    KEYCLOAK_URL - Keycloak URL (default: "http://localhost:8081")
    KEYCLOAK_ADMIN_USER - Keycloak admin user (default: "admin")
    KEYCLOAK_ADMIN_PASSWORD - Keycloak admin password (default: "admin")
    DB_URL - Database URL (default: "postgresql://sg:sg@localhost:5432/sg")
    SKIP_KEYCLOAK - Skip Keycloak setup (default: false)
"""

import os
import sys
from pathlib import Path
from uuid import uuid4, UUID
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
import random
import json
import httpx
import yaml

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
# Add shared libs (sg_core, etc.)
sys.path.insert(0, str(Path(__file__).parent.parent / "libs"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

# Try to import Keycloak admin, but allow script to work without it
try:
    from keycloak import KeycloakAdmin
    from keycloak.exceptions import KeycloakError
    KEYCLOAK_AVAILABLE = True
except ImportError:
    KEYCLOAK_AVAILABLE = False
    # Create dummy types for type hints when Keycloak is not available
    KeycloakAdmin = type(None)  # Dummy type
    KeycloakError = Exception

# Configuration
_script_path = Path(__file__).resolve()
_repo_root_override = os.getenv("REPO_ROOT")
if _repo_root_override:
    REPO_ROOT = Path(_repo_root_override).resolve()
else:
    candidate_repo_root = _script_path.parents[2]
    if not (candidate_repo_root / "cfg").exists():
        parent_repo_root = _script_path.parents[1]
        if (parent_repo_root / "cfg").exists():
            candidate_repo_root = parent_repo_root
    REPO_ROOT = candidate_repo_root
DEFAULT_KEYCLOAK_CERT = REPO_ROOT / "infra" / "nginx" / "certs" / "keycloak.crt"

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "https://localhost:8443")
KEYCLOAK_ADMIN_USER = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
KEYCLOAK_ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
DB_URL = os.getenv("DB_URL", "postgresql://sg:sg@localhost:5432/sg")
KEYCLOAK_VERIFY_ENV = os.getenv("KEYCLOAK_VERIFY", "true").lower()
if KEYCLOAK_VERIFY_ENV in ["false", "0", "no"]:
    KEYCLOAK_VERIFY = False
elif KEYCLOAK_VERIFY_ENV in ["true", "1", "yes"]:
    KEYCLOAK_VERIFY = str(DEFAULT_KEYCLOAK_CERT) if DEFAULT_KEYCLOAK_CERT.exists() else True
else:
    KEYCLOAK_VERIFY = KEYCLOAK_VERIFY_ENV

# Demo configuration
TENANT_NAME = os.getenv("TENANT_NAME", "Demo Company")
TENANT_SLUG = os.getenv("TENANT_SLUG", "demo")
REALM_NAME = os.getenv("REALM_NAME", "demo")
SKIP_KEYCLOAK = os.getenv("SKIP_KEYCLOAK", "false").lower() == "true"

# Demo password - simple and shareable (NOT from Vault)
DEMO_PASSWORD = "DemoPassword123!"

# Demo users configuration
DEMO_USERS = [
    {
        "username": "admin@demo.sentinelgrid.ai",
        "email": "admin@demo.sentinelgrid.ai",
        "first_name": "Demo",
        "last_name": "Admin",
        "role": "TENANT_ADMIN",
    },
    {
        "username": "soc.manager@demo.sentinelgrid.ai",
        "email": "soc.manager@demo.sentinelgrid.ai",
        "first_name": "SOC",
        "last_name": "Manager",
        "role": "SOC_MANAGER",
    },
    {
        "username": "analyst1@demo.sentinelgrid.ai",
        "email": "analyst1@demo.sentinelgrid.ai",
        "first_name": "Analyst",
        "last_name": "One",
        "role": "SOC_ANALYST",
    },
    {
        "username": "analyst2@demo.sentinelgrid.ai",
        "email": "analyst2@demo.sentinelgrid.ai",
        "first_name": "Analyst",
        "last_name": "Two",
        "role": "SOC_ANALYST",
    },
    {
        "username": "viewer@demo.sentinelgrid.ai",
        "email": "viewer@demo.sentinelgrid.ai",
        "first_name": "View",
        "last_name": "Only",
        "role": "VIEW_ONLY",
    },
    {
        "username": "developer1@demo.sentinelgrid.ai",
        "email": "developer1@demo.sentinelgrid.ai",
        "first_name": "Developer",
        "last_name": "One",
        "role": "SOC_ANALYST",  # Use existing role, can be customized later
    },
    {
        "username": "contractor1@demo.sentinelgrid.ai",
        "email": "contractor1@demo.sentinelgrid.ai",
        "first_name": "Contractor",
        "last_name": "One",
        "role": "VIEW_ONLY",  # Use existing role, can be customized later
    },
]

# NimbusEdge Technologies demo dataset
NIMBUSEDGE_EMPLOYEES = [
    {
        "name": "Ava Thompson",
        "email": "ava.thompson@demo.sentinelgrid.ai",  # Using @demo.sentinelgrid.ai for consistency
        "first_name": "Ava",
        "last_name": "Thompson",
        "role": "CEO / Founder",
        "department": "Executive",
        "apps": ["Google Workspace", "Slack", "Notion", "Zoom"],
        "keycloak_role": "TENANT_ADMIN",  # CEO gets admin access
    },
    {
        "name": "Leo Martinez",
        "email": "leo.martinez@demo.sentinelgrid.ai",
        "first_name": "Leo",
        "last_name": "Martinez",
        "role": "CTO",
        "department": "Engineering",
        "apps": ["Google Workspace", "Slack", "Notion", "GitHub", "Jira", "Zoom"],
        "keycloak_role": "SOC_MANAGER",
    },
    {
        "name": "Priya Shah",
        "email": "priya.shah@demo.sentinelgrid.ai",
        "first_name": "Priya",
        "last_name": "Shah",
        "role": "Lead Software Engineer",
        "department": "Engineering",
        "apps": ["Google Workspace", "Slack", "Notion", "GitHub", "Jira"],
        "keycloak_role": "SOC_ANALYST",
    },
    {
        "name": "Marcus Reed",
        "email": "marcus.reed@demo.sentinelgrid.ai",
        "first_name": "Marcus",
        "last_name": "Reed",
        "role": "Product Manager",
        "department": "Product",
        "apps": ["Google Workspace", "Slack", "Notion", "Jira", "GitHub (read-only)", "Zoom"],
        "keycloak_role": "SOC_ANALYST",
    },
    {
        "name": "Sara Delgado",
        "email": "sara.delgado@demo.sentinelgrid.ai",
        "first_name": "Sara",
        "last_name": "Delgado",
        "role": "Operations & HR",
        "department": "Operations",
        "apps": ["Google Workspace", "Slack", "Notion", "Zoom"],
        "keycloak_role": "SOC_ANALYST",
    },
]

NIMBUSEDGE_DEVICES = [
    {
        "employee_email": "ava.thompson@demo.sentinelgrid.ai",
        "device_type": "workstation",  # Laptop maps to workstation
        "make_model": "MacBook Pro 14\" (M3 Pro)",
        "os": "macOS",
        "serial_number": "MBP14-A001",
        "primary": True,
    },
    {
        "employee_email": "ava.thompson@demo.sentinelgrid.ai",
        "device_type": "mobile",  # Phone maps to mobile
        "make_model": "iPhone 15 Pro",
        "os": "iOS",
        "serial_number": "IP15P-A001",
        "primary": True,
    },
    {
        "employee_email": "leo.martinez@demo.sentinelgrid.ai",
        "device_type": "workstation",
        "make_model": "MacBook Pro 16\" (M3 Max)",
        "os": "macOS",
        "serial_number": "MBP16-L001",
        "primary": True,
    },
    {
        "employee_email": "leo.martinez@demo.sentinelgrid.ai",
        "device_type": "mobile",
        "make_model": "Pixel 8 Pro",
        "os": "Android",
        "serial_number": "PIX8P-L001",
        "primary": True,
    },
    {
        "employee_email": "priya.shah@demo.sentinelgrid.ai",
        "device_type": "workstation",
        "make_model": "MacBook Air 15\" (M3)",
        "os": "macOS",
        "serial_number": "MBA15-P001",
        "primary": True,
    },
    {
        "employee_email": "priya.shah@demo.sentinelgrid.ai",
        "device_type": "mobile",
        "make_model": "iPhone 14",
        "os": "iOS",
        "serial_number": "IP14-P001",
        "primary": True,
    },
    {
        "employee_email": "marcus.reed@demo.sentinelgrid.ai",
        "device_type": "workstation",
        "make_model": "MacBook Air 13\" (M2)",
        "os": "macOS",
        "serial_number": "MBA13-M001",
        "primary": True,
    },
    {
        "employee_email": "marcus.reed@demo.sentinelgrid.ai",
        "device_type": "mobile",
        "make_model": "Samsung Galaxy S23",
        "os": "Android",
        "serial_number": "SG23-M001",
        "primary": True,
    },
    {
        "employee_email": "sara.delgado@demo.sentinelgrid.ai",
        "device_type": "workstation",
        "make_model": "Surface Laptop 5",
        "os": "Windows 11",
        "serial_number": "SL5-S001",
        "primary": True,
    },
    {
        "employee_email": "sara.delgado@demo.sentinelgrid.ai",
        "device_type": "mobile",
        "make_model": "iPhone 13",
        "os": "iOS",
        "serial_number": "IP13-S001",
        "primary": True,
    },
]


# ============================================================================
# Tenant Creation
# ============================================================================

def create_demo_tenant(db: Session) -> UUID:
    """Create demo tenant in database."""
    print("📋 Creating demo tenant...")
    
    # Check if tenant exists
    result = db.execute(
        text("SELECT id FROM tenants WHERE slug = :slug"),
        {"slug": TENANT_SLUG}
    ).first()
    
    if result:
        tenant_id = result[0]
        print(f"  ✅ Tenant '{TENANT_NAME}' already exists: {tenant_id}")
        return tenant_id
    
    # Create tenant
    tenant_id = uuid4()
    db.execute(
        text("""
            INSERT INTO tenants (id, name, slug, status, created_at, updated_at)
            VALUES (:id, :name, :slug, :status, now(), now())
        """),
        {
            "id": str(tenant_id),
            "name": TENANT_NAME,
            "slug": TENANT_SLUG,
            "status": "active",
        }
    )
    db.commit()
    print(f"  ✅ Tenant '{TENANT_NAME}' created: {tenant_id}")
    return tenant_id


def seed_onboarding_preferences(db: Session, tenant_id: UUID) -> None:
    """
    Ensure onboarding_progress has service selections so the full wizard shows.
    We want demo to include ticketing (socManaged=false) and appsec/AI steps.
    """
    services = {
        "cloud": True,
        "git": True,
        "appsec": True,
        "aiShield": "hosted",
        "socManaged": False,  # customer-managed SOC -> require ticketing config
    }
    db.execute(
        text(
            """
            INSERT INTO onboarding_progress (customer_id, services_selected, updated_at)
            VALUES (:cid, :svc::jsonb, NOW())
            ON CONFLICT (customer_id) DO UPDATE
              SET services_selected = EXCLUDED.services_selected,
                  updated_at = NOW()
            """
        ),
        {"cid": str(tenant_id), "svc": json.dumps(services)},
    )
    db.commit()
    print("  ✅ Onboarding preferences updated (appsec + AI + ticketing required)")


def ensure_sg_admin_tenant(db: Session) -> UUID:
    """Ensure sg_admin tenant exists for shared content (detections/playbooks/templates/logs)."""
    print("📋 Ensuring sg_admin tenant exists...")
    result = db.execute(
        text("SELECT id FROM tenants WHERE slug = 'sg_admin'")
    ).first()
    if result:
        tid = result[0]
        print(f"  ✅ sg_admin tenant already exists: {tid}")
        return UUID(str(tid))
    tenant_id = uuid4()
    db.execute(
        text("""
            INSERT INTO tenants (id, name, slug, status, created_at, updated_at)
            VALUES (:id, 'SentinelGrid Admin', 'sg_admin', 'active', now(), now())
        """),
        {"id": str(tenant_id)}
    )
    db.commit()
    print(f"  ✅ Created sg_admin tenant: {tenant_id}")
    return tenant_id


# ============================================================================
# Keycloak Integration Functions
# ============================================================================

def create_demo_realm(keycloak_admin) -> None:
    """
    Create isolated demo realm in Keycloak.
    
    CRITICAL: Uses RealmCreationService to ensure User Profile is configured.
    """
    print(f"🔐 Creating Keycloak realm '{REALM_NAME}'...")
    
    try:
        # Import realm creation service
        import sys
        from pathlib import Path
        backend_agents_path = Path(__file__).parent.parent / "agents" / "iam_agent"
        if str(backend_agents_path) not in sys.path:
            sys.path.insert(0, str(backend_agents_path))
        from app.services.realm_creation_service import RealmCreationService, RealmType
        
        # Use centralized realm creation service
        service = RealmCreationService(keycloak_admin)
        result = service.create_realm(
            realm_name=REALM_NAME,
            realm_type=RealmType.DEMO,
            display_name=TENANT_NAME,
            sslRequired="external"  # Additional realm config
        )
        
        if not result["user_profile_configured"]:
            print(f"  ⚠️  CRITICAL WARNING: User Profile not configured for '{REALM_NAME}'")
            print(f"  ⚠️  Custom attributes (tenant_id) will NOT persist without User Profile configuration")
        else:
            print(f"  ✅ Realm '{REALM_NAME}' created with User Profile configured (status: {result['status']})")
        
    except Exception as e:
        print(f"  ⚠️  Error creating realm: {e}")
        import traceback
        traceback.print_exc()
        raise


def create_demo_clients(keycloak_admin) -> Dict[str, str]:
    """Create clients for demo realm.
    
    Args:
        keycloak_admin: KeycloakAdmin instance initialized for the demo realm
    """
    print("  Creating Keycloak clients...")
    
    clients = {}
    
    # Web client
    try:
        # get_clients() doesn't accept realm_name parameter - uses realm from KeycloakAdmin initialization
        existing_clients = keycloak_admin.get_clients()
        web_client = next((c for c in existing_clients if c.get("clientId") == f"{REALM_NAME}-web"), None)
        
        if web_client:
            print(f"    ✅ Web client already exists")
            clients["web"] = web_client["id"]
        else:
            web_client_data = {
                "clientId": f"{REALM_NAME}-web",
                "name": f"{TENANT_NAME} Web Client",
                "enabled": True,
                "publicClient": True,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": True,
                "redirectUris": ["http://localhost:3000/*", "https://localhost:3443/*", "https://*.sentinelgrid.com/*"],
                "webOrigins": ["+"],
            }
            # create_client() accepts realm_name as optional parameter, but since admin is for demo realm, we can omit it
            client_id = keycloak_admin.create_client(web_client_data)
            clients["web"] = client_id
            print(f"    ✅ Web client created")
    except KeycloakError as e:
        print(f"    ⚠️  Error creating web client: {e}")
    
    # API client
    try:
        # get_clients() doesn't accept realm_name parameter - uses realm from KeycloakAdmin initialization
        existing_clients = keycloak_admin.get_clients()
        api_client = next((c for c in existing_clients if c.get("clientId") == f"{REALM_NAME}-api"), None)
        
        if api_client:
            print(f"    ✅ API client already exists")
            clients["api"] = api_client["id"]
        else:
            api_client_data = {
                "clientId": f"{REALM_NAME}-api",
                "name": f"{TENANT_NAME} API Client",
                "enabled": True,
                "publicClient": False,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": True,
                "redirectUris": [],
            }
            # create_client() accepts realm_name as optional parameter, but since admin is for demo realm, we can omit it
            client_id = keycloak_admin.create_client(api_client_data)
            clients["api"] = client_id
            print(f"    ✅ API client created")
    except KeycloakError as e:
        print(f"    ⚠️  Error creating API client: {e}")
    
    return clients


def create_demo_roles(keycloak_admin) -> None:
    """Create roles for demo realm.
    
    Args:
        keycloak_admin: KeycloakAdmin instance initialized for the demo realm
    """
    print("  Creating roles...")
    
    roles = ["TENANT_ADMIN", "SOC_MANAGER", "SOC_ANALYST", "VIEW_ONLY"]
    
    for role_name in roles:
        try:
            try:
                # get_realm_role() uses realm from KeycloakAdmin initialization
                keycloak_admin.get_realm_role(role_name)
                print(f"    ✅ Role '{role_name}' already exists")
            except KeycloakError:
                role_data = {
                    "name": role_name,
                    "description": f"Demo role: {role_name}",
                }
                # create_realm_role() uses realm from KeycloakAdmin initialization
                keycloak_admin.create_realm_role(role_data)
                print(f"    ✅ Role '{role_name}' created")
        except KeycloakError as e:
            print(f"    ⚠️  Error creating role {role_name}: {e}")


def set_user_tenant_id_via_rest_api(user_id: str, tenant_id: UUID, realm_name: str) -> bool:
    """
    Set tenant_id attribute on user using REST API (more reliable than python-keycloak).
    
    Args:
        user_id: Keycloak user ID
        tenant_id: Tenant UUID to set
        realm_name: Keycloak realm name
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Use internal Docker network URL for Keycloak
        # KEYCLOAK_URL might be localhost:8081, but we need keycloak:8080 from within container
        keycloak_url = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
        if "localhost" in keycloak_url:
            # Replace localhost with keycloak for internal network access
            keycloak_url = keycloak_url.replace("localhost:8081", "keycloak:8080").replace("localhost:8080", "keycloak:8080")
        
        # Get admin token
        token_url = f"{keycloak_url}/realms/master/protocol/openid-connect/token"
        token_data = {
            "client_id": "admin-cli",
            "username": KEYCLOAK_ADMIN_USER,
            "password": KEYCLOAK_ADMIN_PASSWORD,
            "grant_type": "password",
        }
        
        with httpx.Client(timeout=10.0, verify=False) as client:
            token_response = client.post(token_url, data=token_data)
            if token_response.status_code != 200:
                print(f"    ⚠️  Failed to get admin token: {token_response.status_code}")
                return False
            
            admin_token = token_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Get current user data
            user_url = f"{keycloak_url}/admin/realms/{realm_name}/users/{user_id}"
            user_response = client.get(user_url, headers=headers)
            if user_response.status_code != 200:
                print(f"    ⚠️  Failed to get user data: {user_response.status_code}")
                return False
            
            user_data = user_response.json()
            
            # Update with tenant_id attribute
            # Keycloak may not return "attributes" field if empty, so always set it
            if "attributes" not in user_data:
                user_data["attributes"] = {}
            user_data["attributes"]["tenant_id"] = [str(tenant_id)]
            
            # Remove read-only fields that might cause issues
            for field in ["access", "self", "createdTimestamp"]:
                user_data.pop(field, None)
            
            # Update user
            update_response = client.put(
                user_url,
                headers={**headers, "Content-Type": "application/json"},
                json=user_data
            )
            
            if update_response.status_code in [200, 204]:
                return True
            else:
                print(f"    ⚠️  Failed to update user: {update_response.status_code} - {update_response.text[:200]}")
                return False
    except Exception as e:
        print(f"    ⚠️  Error setting tenant_id via REST API: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_tenant_id_mapper(keycloak_admin, client_id: str, client_name: str = "client") -> None:
    """Create tenant_id protocol mapper for a client (web or API).
    
    CRITICAL: This mapper must be on BOTH web and API clients because:
    - Web client is used for user login (frontend)
    - API client is used for service-to-service auth
    - tenant_id must be in tokens from both clients for multi-tenant isolation
    
    Args:
        keycloak_admin: KeycloakAdmin instance initialized for the demo realm
        client_id: Keycloak client ID
        client_name: Human-readable client name for logging
    """
    try:
        # Check if mapper exists
        # get_mappers_from_client() uses realm from KeycloakAdmin initialization
        mappers = keycloak_admin.get_mappers_from_client(client_id)
        if any(m.get("name") == "tenant-id-mapper" for m in mappers):
            print(f"    ✅ tenant_id mapper already exists on {client_name} client")
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
                "userinfo.token.claim": "true",  # Also add to userinfo endpoint
            }
        }
        
        # add_mapper_to_client() uses realm from KeycloakAdmin initialization
        keycloak_admin.add_mapper_to_client(client_id, mapper_data)
        print(f"    ✅ tenant_id mapper created on {client_name} client")
        
    except KeycloakError as e:
        print(f"    ⚠️  Error creating tenant_id mapper on {client_name} client: {e}")


def create_demo_users(keycloak_admin, tenant_id: UUID) -> Dict[str, str]:
    """Create demo users in Keycloak.
    
    Args:
        keycloak_admin: KeycloakAdmin instance initialized for the demo realm
        tenant_id: UUID of the demo tenant
    """
    print(f"  Creating demo users...")
    
    user_ids = {}
    
    for user_data in DEMO_USERS:
        username = user_data["username"]
        try:
            # Check if user exists
            # get_users() uses realm from KeycloakAdmin initialization
            users = keycloak_admin.get_users(query={"username": username})
            if users:
                user_id = users[0]["id"]
                # Update existing user to ensure tenant_id attribute is set
                try:
                    # get_user() uses realm from KeycloakAdmin initialization
                    user_details = keycloak_admin.get_user(user_id)
                    current_attrs = user_details.get("attributes", {})
                    current_tenant_id = current_attrs.get("tenant_id", [None])[0] if isinstance(current_attrs.get("tenant_id"), list) else current_attrs.get("tenant_id")

                    # Ensure core profile fields are populated so ROPC doesn't fail with "Account is not fully set up"
                    profile_update = {}
                    if not user_details.get("firstName"):
                        profile_update["firstName"] = user_data["first_name"]
                    if not user_details.get("lastName"):
                        profile_update["lastName"] = user_data["last_name"]
                    if not user_details.get("email"):
                        profile_update["email"] = user_data["email"]
                    # Always keep email verified for demo users
                    profile_update["emailVerified"] = True

                    if profile_update:
                        keycloak_admin.update_user(user_id, profile_update)

                    # Always reset password to demo default and clear required actions (so no forced reset)
                    try:
                        keycloak_admin.set_user_password(user_id, DEMO_PASSWORD, temporary=False)
                        keycloak_admin.update_user(user_id, {"requiredActions": []})
                        print(f"    🔄 Refreshed password/requiredActions for '{username}'")
                    except Exception as e:
                        print(f"    ⚠️  Failed to refresh password for '{username}': {e}")

                    if current_tenant_id != str(tenant_id):
                        # Try python-keycloak first
                        try:
                            update_data = {
                                "attributes": {
                                    **current_attrs,
                                    "tenant_id": [str(tenant_id)]
                                }
                            }
                            keycloak_admin.update_user(user_id, update_data)
                        except Exception as e:
                            print(f"    ⚠️  python-keycloak update failed: {e}")
                        
                        # Also try REST API (more reliable)
                        if set_user_tenant_id_via_rest_api(user_id, tenant_id, REALM_NAME):
                            print(f"    ✅ User '{username}' already exists - updated tenant_id attribute via REST API")
                        else:
                            print(f"    ⚠️  User '{username}' exists but failed to update tenant_id attribute")
                    else:
                        print(f"    ✅ User '{username}' already exists with correct tenant_id")
                except KeycloakError as e:
                        print(f"    ⚠️  User '{username}' exists but failed to update tenant_id: {e}")
                
                user_ids[username] = user_id
                continue
            
            # Create user
            kc_user_data = {
                "username": username,
                "email": user_data["email"],
                "firstName": user_data["first_name"],
                "lastName": user_data["last_name"],
                "enabled": True,
                "emailVerified": True,
                "attributes": {"tenant_id": [str(tenant_id)]},
                "requiredActions": [],
            }
            
            # create_user() uses realm from KeycloakAdmin initialization
            user_id = keycloak_admin.create_user(kc_user_data)
            
            # Set password (non-temporary, simple shareable password)
            # set_user_password() uses realm from KeycloakAdmin initialization
            keycloak_admin.set_user_password(user_id, DEMO_PASSWORD, temporary=False)
            
            # Clear required actions
            # update_user() uses realm from KeycloakAdmin initialization
            keycloak_admin.update_user(user_id, {"requiredActions": []})
            
            # CRITICAL: Ensure tenant_id attribute is set via REST API (more reliable)
            # python-keycloak may not persist attributes correctly during creation
            if not set_user_tenant_id_via_rest_api(user_id, tenant_id, REALM_NAME):
                print(f"    ⚠️  Warning: Failed to set tenant_id attribute via REST API for {username}")
            
            # Assign role
            try:
                # get_realm_role() uses realm from KeycloakAdmin initialization
                role = keycloak_admin.get_realm_role(user_data["role"])
                # assign_realm_roles() uses realm from KeycloakAdmin initialization
                keycloak_admin.assign_realm_roles(user_id, [role])
            except KeycloakError as e:
                print(f"    ⚠️  Error assigning role to {username}: {e}")
            
            user_ids[username] = user_id
            print(f"    ✅ User '{username}' created with role {user_data['role']}")
            
        except KeycloakError as e:
            print(f"    ⚠️  Error creating user {username}: {e}")
    
    return user_ids


# ============================================================================
# IAM Portal Data Seeding Functions
# ============================================================================

# Note: Access profiles seeding logic is included below (reused from seed_access_profiles.py pattern)

def seed_demo_apps(tenant_id: UUID, db: Session) -> Dict[str, UUID]:
    """Seed demo apps for IAM portal."""
    print("📱 Seeding demo apps...")
    
    apps_data = [
        {"name": "sentinelgrid", "display_name": "SentinelGrid", "description": "SentinelGrid security platform", "app_type": "sentinelgrid"},
        {"name": "github", "display_name": "GitHub", "description": "Code repository and version control", "app_type": "github"},
        {"name": "aws_console", "display_name": "AWS Console", "description": "Amazon Web Services management console", "app_type": "aws"},
        {"name": "jira", "display_name": "Jira", "description": "Project management and issue tracking", "app_type": "jira"},
        {"name": "slack", "display_name": "Slack", "description": "Team communication and collaboration", "app_type": "slack"},
        {"name": "microsoft_365", "display_name": "Microsoft 365", "description": "Office productivity suite and email", "app_type": "microsoft_365"},
        {"name": "salesforce", "display_name": "Salesforce", "description": "Customer relationship management platform", "app_type": "salesforce"},
        {"name": "confluence", "display_name": "Confluence", "description": "Team workspace and documentation", "app_type": "confluence"},
        {"name": "google_workspace", "display_name": "Google Workspace", "description": "Email, Drive, Docs, Meet", "app_type": "google_workspace"},
        {"name": "notion", "display_name": "Notion", "description": "Internal wiki & documents", "app_type": "notion"},
        {"name": "zoom", "display_name": "Zoom", "description": "Video calls", "app_type": "zoom"},
    ]
    
    app_ids = {}
    created = 0
    
    for app_data in apps_data:
        # Check if app exists
        result = db.execute(
            text("SELECT id FROM apps WHERE tenant_id = :tenant_id AND name = :name"),
            {"tenant_id": str(tenant_id), "name": app_data["name"]}
        ).first()
        
        if result:
            app_ids[app_data["name"]] = result[0]
            print(f"  ⏭️  App '{app_data['display_name']}' already exists")
            continue
        
        # Create app
        app_id = uuid4()
        db.execute(
            text("""
                INSERT INTO apps (id, tenant_id, name, display_name, description, app_type, is_active, created_at, updated_at)
                VALUES (:id, :tenant_id, :name, :display_name, :description, :app_type, true, now(), now())
            """),
            {
                "id": str(app_id),
                "tenant_id": str(tenant_id),
                "name": app_data["name"],
                "display_name": app_data["display_name"],
                "description": app_data["description"],
                "app_type": app_data["app_type"],
            }
        )
        app_ids[app_data["name"]] = app_id
        created += 1
        print(f"  ✅ Created app '{app_data['display_name']}'")
    
    db.commit()
    print(f"  📊 Created {created} new apps")
    return app_ids

def seed_demo_access_profiles(tenant_id: UUID, db: Session) -> int:
    """Seed demo access profiles."""
    print("👥 Seeding access profiles...")
    
    profiles = [
        {"name": "standard_employee", "display_name": "Standard Employee", "description": "Default access profile for standard employees.", "is_default": True},
        {"name": "developer", "display_name": "Developer", "description": "Access profile for software developers.", "is_default": False},
        {"name": "manager", "display_name": "Manager", "description": "Access profile for managers.", "is_default": False},
        {"name": "executive", "display_name": "Executive", "description": "Access profile for executives.", "is_default": False},
        {"name": "contractor", "display_name": "Contractor", "description": "Access profile for contractors.", "is_default": False},
    ]
    
    created = 0
    for profile_data in profiles:
        existing = db.execute(
            text("SELECT id FROM access_profiles WHERE tenant_id = :tenant_id AND name = :name"),
            {"tenant_id": str(tenant_id), "name": profile_data["name"]}
        ).first()
        
        if existing:
            print(f"  ⏭️  Profile '{profile_data['display_name']}' already exists")
            continue
        
        profile_id = uuid4()
        db.execute(
            text("""
                INSERT INTO access_profiles 
                (id, tenant_id, name, display_name, description, is_default, is_system, created_at, updated_at)
                VALUES (:id, :tenant_id, :name, :display_name, :description, :is_default, false, now(), now())
            """),
            {
                "id": str(profile_id),
                "tenant_id": str(tenant_id),
                "name": profile_data["name"],
                "display_name": profile_data["display_name"],
                "description": profile_data["description"],
                "is_default": profile_data["is_default"],
            }
        )
        created += 1
        print(f"  ✅ Created '{profile_data['display_name']}'")
    
    db.commit()
    return created


def seed_policy_templates(db: Session) -> int:
    """
    Seed a small library of policy templates for the drag-and-drop builder.
    These are intentionally simple and valid against the PolicyDSL so they render and import cleanly.
    """
    print("📚 Seeding policy templates...")
    templates = [
        {
            "name": "access_geo_deny_non_us",
            "display_name": "Deny Access Outside US/CA",
            "description": "Block access when user is outside the US or Canada.",
            "policy_type": "access",
            "category": "geo",
            "template_data": {
                "id": "tpl-geo-deny",
                "type": "access",
                "scope": "tenant",
                "rules": [
                    {
                        "id": "rule-geo",
                        "name": "Block non-US/CA",
                        "description": "Deny when country is not US or CA.",
                        "conditions": [
                            {"type": "country", "op": "not_in", "value": ["US", "CA"]}
                        ],
                        "actions": [{"type": "deny"}],
                        "priority": 100,
                    }
                ],
                "metadata": {"example": True},
            },
        },
        {
            "name": "signon_high_risk_step_up",
            "display_name": "Step-up MFA on High Risk Sign-on",
            "description": "Require MFA when risk score is high; otherwise allow.",
            "policy_type": "signon",
            "category": "risk",
            "template_data": {
                "id": "tpl-signon-risk",
                "type": "signon",
                "scope": "tenant",
                "rules": [
                    {
                        "id": "rule-risk-mfa",
                        "name": "High risk requires MFA",
                        "conditions": [
                            {"type": "risk_level", "op": "in", "value": ["high", "critical"]}
                        ],
                        "actions": [{"type": "require_mfa"}],
                        "priority": 50,
                    },
                    {
                        "id": "rule-allow",
                        "name": "Default allow",
                        "conditions": [],
                        "actions": [{"type": "allow"}],
                        "priority": 100,
                    },
                ],
                "metadata": {"example": True},
            },
        },
        {
            "name": "approval_after_hours",
            "display_name": "After-hours Approval Required",
            "description": "Require approval for access outside business hours.",
            "policy_type": "approval",
            "category": "time",
            "template_data": {
                "id": "tpl-approval-hours",
                "type": "approval",
                "scope": "tenant",
                "rules": [
                    {
                        "id": "rule-after-hours",
                        "name": "After-hours approval",
                        "conditions": [
                            {"type": "time", "op": "outside", "value": {"start": "08:00", "end": "18:00", "tz": "UTC"}}
                        ],
                        "actions": [{"type": "require_approval", "params": {"approvers": ["SOC_MANAGER"]}}],
                        "priority": 80,
                    },
                    {
                        "id": "rule-allow-day",
                        "name": "Allow business hours",
                        "conditions": [],
                        "actions": [{"type": "allow"}],
                        "priority": 100,
                    },
                ],
                "metadata": {"example": True},
            },
        },
        {
            "name": "sod_prod_admin_deployer",
            "display_name": "SoD: Prod Admin cannot Deploy",
            "description": "Prevent combining prod-admin role with deployer duties.",
            "policy_type": "sod",
            "category": "sod",
            "template_data": {
                "id": "tpl-sod-prod",
                "type": "sod",
                "scope": "tenant",
                "rules": [
                    {
                        "id": "rule-sod",
                        "name": "No prod-admin + deployer",
                        "conditions": [
                            {"type": "role", "op": "includes", "value": ["prod-admin"]},
                            {"type": "role", "op": "includes", "value": ["deployer"]},
                        ],
                        "actions": [{"type": "deny"}],
                        "priority": 70,
                    }
                ],
                "metadata": {"example": True},
            },
        },
    ]

    created = 0
    for tpl in templates:
        exists = db.execute(
            text("SELECT 1 FROM policy_templates WHERE name = :name"),
            {"name": tpl["name"]},
        ).fetchone()
        if exists:
            continue
        db.execute(
            text(
                """
                INSERT INTO policy_templates
                (name, display_name, description, policy_type, template_data, is_system, category)
                VALUES (:name, :display_name, :description, :policy_type, :template_data, true, :category)
                """
            ),
            {
                "name": tpl["name"],
                "display_name": tpl["display_name"],
                "description": tpl["description"],
                "policy_type": tpl["policy_type"],
                "template_data": json.dumps(tpl["template_data"]),
                "category": tpl.get("category"),
            },
        )
        created += 1
    db.commit()
    print(f"  📊 Created {created} policy templates")
    return created


def seed_playbooks(tenant_id: UUID, db: Session) -> int:
    """
    Seed a small set of shared/builtin playbooks (sg_admin tenant).
    Kept minimal to avoid noise; primarily to unblock UI and mappings.
    """
    print("📘 Seeding playbooks (shared)...")
    tenant_id_str = str(tenant_id)
    playbooks = [
        {
            "key": "PB-IR-001",
            "name": "Contain Ransomware",
            "description": "Isolate host, disable accounts, notify SOC.",
            "target_type": "endpoint",
            "workflow_ref": "contain_ransomware",
            "is_builtin": True,
            "category": "malware",
        },
        {
            "key": "PB-IR-002",
            "name": "Investigate Suspicious Login",
            "description": "Gather auth logs, geo/risk checks, MFA reset if needed.",
            "target_type": "identity",
            "workflow_ref": "investigate_login",
            "is_builtin": True,
            "category": "identity",
        },
        {
            "key": "PB-IR-003",
            "name": "Cloud Misconfiguration",
            "description": "Snapshot config, apply guardrail, open ticket.",
            "target_type": "cloud",
            "workflow_ref": "cloud_guardrail",
            "is_builtin": True,
            "category": "cloud",
        },
    ]
    created = 0
    for pb in playbooks:
        exists = db.execute(
            text("SELECT 1 FROM security_ops.playbooks WHERE tenant_id=:tid AND key=:key"),
            {"tid": tenant_id_str, "key": pb["key"]},
        ).fetchone()
        if exists:
            continue
        db.execute(
            text(
                """
                INSERT INTO playbooks
                (tenant_id, key, name, description, target_type, workflow_ref, is_builtin, category, created_at, updated_at)
                VALUES (:tid, :key, :name, :description, :target_type, :workflow_ref, :is_builtin, :category, now(), now())
                """
            ),
            {**pb, "tid": tenant_id_str},
        )
        created += 1
    db.commit()
    print(f"  📊 Created {created} playbooks")
    return created


def seed_demo_policies(tenant_id: UUID, realm_name: str, db: Session) -> int:
    """
    Seed demo policies for the tenant using existing policy templates.
    
    This keeps /dashboard/policies populated for demos.
    """
    print("📜 Seeding demo policies from templates...")
    
    # Lazy imports to avoid module-level dependency churn
    backend_agents_path = Path(__file__).parent.parent / "agents" / "iam_agent"
    if str(backend_agents_path) not in sys.path:
        sys.path.insert(0, str(backend_agents_path))
    from app.services.policy_service import PolicyService
    from app.models.policies import PolicyCreate
    
    # Existing policy names for idempotency
    existing = {
        row[0]
        for row in db.execute(
            text("SELECT name FROM policies WHERE tenant_id = :tenant_id"),
            {"tenant_id": str(tenant_id)}
        )
    }
    
    templates = db.execute(
        text("""
            SELECT name, display_name, description, policy_type, template_data
            FROM policy_templates
            ORDER BY display_name
        """)
    ).fetchall()
    
    service = PolicyService(db, tenant_id, realm_name)
    created = 0
    for idx, tpl in enumerate(templates, start=1):
        name, display_name, description, policy_type, template_data = tpl
        if name in existing:
            continue
        
        policy = PolicyCreate(
            name=name,
            display_name=display_name,
            description=description,
            policy_type=policy_type,
            policy_data=template_data,
            is_active=True,
            priority=100 + idx,  # deterministic ordering
            scope="tenant",
            scope_id=None,
        )
        created_policy = service.create_policy(policy, created_by="demo-seed")
        if created_policy:
            created += 1
    
    print(f"  📊 Created {created} new policies")
    return created


def seed_demo_alerts(tenant_id: UUID, db: Session) -> List[UUID]:
    """Seed demo security alerts with AI analysis."""
    print("🚨 Seeding security alerts...")
    
    now = datetime.now(timezone.utc)
    alerts_data = [
        {
            "source": "wazuh", "external_id": "WZH-RANS-001",
            "title": "Ransomware Activity Detected on Finance Workstation",
            "description": "Multiple files with .encrypted extension detected. Suspicious process WannaCrypt.exe identified.",
            "raw_severity": "critical", "status": "open",
            "detection_time": now - timedelta(hours=2),
            "asset_id": "finance-ws-042", "user_identifier": "john.smith@demo.sentinelgrid.ai",
            "raw_payload": {
                "rule_id": "91816",
                "rule_name": "Ransomware patterns detected",
                "mitre_tactics": ["TA0040 Impact"],
                "mitre_techniques": ["T1486 Data Encrypted for Impact"],
                "nist_controls": ["PR.IP", "RS.MI"],
                "recommended_playbook": "Contain Ransomware",
                "recommended_playbooks": ["Contain Ransomware", "Isolate Endpoint"],
                "category": "endpoint"
            },
            "ai_severity": "critical", "ai_category": "malware", "ai_confidence": 95.0,
            "rationale": "Ransomware indicators detected including file encryption patterns and known malicious process execution."
        },
        {
            "source": "email_gateway", "external_id": "PHISH-001",
            "title": "User Reported Suspicious Email - CEO Impersonation",
            "description": "User reported email claiming to be from CEO requesting urgent wire transfer.",
            "raw_severity": "high", "status": "open",
            "detection_time": now - timedelta(hours=4),
            "asset_id": None, "user_identifier": "sarah.johnson@demo.sentinelgrid.ai",
            "raw_payload": {
                "sender": "ceo@comp4ny.com",
                "subject": "URGENT: Wire Transfer Required",
                "mitre_tactics": ["TA0001 Initial Access"],
                "mitre_techniques": ["T1566 Phishing"],
                "nist_controls": ["PR.AC", "DE.CM"],
                "recommended_playbook": "Phishing - User Reported",
                "recommended_playbooks": ["Phishing - User Reported", "Quarantine Email"],
                "category": "email"
            },
            "ai_severity": "high", "ai_category": "phishing", "ai_confidence": 88.0,
            "rationale": "Phishing attempt with CEO impersonation and urgent financial request - common BEC attack pattern."
        },
        {
            "source": "wazuh", "external_id": "WZH-AUTH-002",
            "title": "Multiple Failed Login Attempts - Brute Force Attack",
            "description": "Account admin@demo.sentinelgrid.ai: 127 failed login attempts from 15 different IPs in 10 minutes.",
            "raw_severity": "high", "status": "investigating",
            "detection_time": now - timedelta(hours=6),
            "asset_id": "vpn-gateway", "user_identifier": "admin@demo.sentinelgrid.ai",
            "raw_payload": {
                "failed_attempts": 127,
                "source_ips": ["185.220.101.1", "45.142.212.61"],
                "mitre_tactics": ["TA0006 Credential Access"],
                "mitre_techniques": ["T1110 Brute Force"],
                "nist_controls": ["PR.AC", "DE.CM"],
                "recommended_playbook": "Account Lockout / IP Block",
                "recommended_playbooks": ["Account Lockout / IP Block", "Password Reset"],
                "category": "identity"
            },
            "ai_severity": "high", "ai_category": "brute_force", "ai_confidence": 92.0,
            "rationale": "Coordinated brute force attack from multiple IPs targeting admin account - requires immediate blocking."
        },
        {
            "source": "cloudtrail", "external_id": "AWS-CT-001",
            "title": "Unusual IAM Policy Changes from Unknown Location",
            "description": "IAM policy modified to grant admin access from IP in suspicious region.",
            "raw_severity": "medium", "status": "open",
            "detection_time": now - timedelta(hours=8),
            "asset_id": "aws-account-prod", "user_identifier": "deploy.bot@demo.sentinelgrid.ai",
            "raw_payload": {
                "event_name": "PutUserPolicy",
                "source_ip": "185.220.102.34",
                "mitre_tactics": ["TA0003 Persistence"],
                "mitre_techniques": ["T1098 Account Manipulation"],
                "nist_controls": ["PR.AC", "RS.MI"],
                "recommended_playbook": "Cloud IAM Policy Review",
                "recommended_playbooks": ["Cloud IAM Policy Review"],
                "category": "cloud"
            },
            "ai_severity": "medium", "ai_category": "privilege_escalation", "ai_confidence": 75.0,
            "rationale": "Unusual IAM policy modification from unexpected location - may indicate account compromise."
        },
        {
            "source": "wazuh", "external_id": "WZH-MAL-003",
            "title": "Trojan Horse Detected - Engineering Laptop",
            "description": "ClamAV detected Win.Trojan.Generic on engineering laptop.",
            "raw_severity": "high", "status": "open",
            "detection_time": now - timedelta(hours=12),
            "asset_id": "eng-laptop-087", "user_identifier": "mike.wilson@demo.sentinelgrid.ai",
            "raw_payload": {
                "malware_type": "Trojan",
                "file_path": "/home/mike/downloads/invoice.pdf.exe",
                "mitre_tactics": ["TA0002 Execution"],
                "mitre_techniques": ["T1204 User Execution"],
                "nist_controls": ["PR.IP", "DE.CM"],
                "recommended_playbook": "Malware Containment",
                "recommended_playbooks": ["Malware Containment", "Isolate Endpoint"],
                "category": "endpoint"
            },
            "ai_severity": "high", "ai_category": "malware", "ai_confidence": 90.0,
            "rationale": "Trojan malware detected - file quarantined but process may have executed requiring endpoint isolation."
        },
        {
            "source": "prowler", "external_id": "PROWLER-S3-001",
            "title": "S3 Bucket Publicly Accessible - Customer PII Exposed",
            "description": "Bucket customer-data-prod contains files with PII and is publicly readable.",
            "raw_severity": "critical", "status": "open",
            "detection_time": now - timedelta(hours=1),
            "asset_id": "customer-data-prod", "user_identifier": "devops@demo.sentinelgrid.ai",
            "raw_payload": {
                "bucket": "customer-data-prod",
                "records_count": 12450,
                "contains_pii": True,
                "mitre_tactics": ["TA0009 Collection"],
                "mitre_techniques": ["T1537 Data from Information Repositories"],
                "nist_controls": ["PR.DS", "DE.CM"],
                "recommended_playbook": "S3 Public Bucket Remediation",
                "recommended_playbooks": ["S3 Public Bucket Remediation"],
                "category": "cloud"
            },
            "ai_severity": "critical", "ai_category": "data_exposure", "ai_confidence": 98.0,
            "rationale": "Public S3 bucket containing PII data - immediate remediation required to prevent data breach."
        },
        {
            "source": "wazuh", "external_id": "WZH-CRED-001",
            "title": "Credential Dumping Activity - Mimikatz Detected",
            "description": "Mimikatz execution detected on domain controller.",
            "raw_severity": "critical", "status": "open",
            "detection_time": now - timedelta(minutes=30),
            "asset_id": "dc-01", "user_identifier": "SYSTEM",
            "raw_payload": {
                "tool": "mimikatz.exe",
                "technique": "LSASS Memory Dump",
                "mitre_tactics": ["TA0006 Credential Access"],
                "mitre_techniques": ["T1003 OS Credential Dumping"],
                "nist_controls": ["PR.AC", "DE.CM"],
                "recommended_playbook": "Credential Theft Response",
                "recommended_playbooks": ["Credential Theft Response", "Isolate Endpoint"],
                "category": "identity"
            },
            "ai_severity": "critical", "ai_category": "credential_theft", "ai_confidence": 96.0,
            "rationale": "Credential dumping tool detected on domain controller - potential lateral movement and privilege escalation."
        },
    ]
    
    alert_ids = []
    for alert_data in alerts_data:
        # Check if alert exists
        existing = db.execute(
            text("SELECT id FROM security_ops.alerts WHERE tenant_id = :tenant_id AND external_id = :external_id"),
            {"tenant_id": str(tenant_id), "external_id": alert_data["external_id"]}
        ).first()
        
        if existing:
            alert_ids.append(existing[0])
            continue
        
        # Create alert
        alert_id = uuid4()
        raw_payload_json = json.dumps(alert_data["raw_payload"])
        db.execute(
            text("""
                INSERT INTO security_ops.alerts 
                (id, tenant_id, source, external_id, title, description, raw_severity, status, 
                 detection_time, asset_id, user_identifier, raw_payload, created_at, updated_at)
                VALUES (:id, :tenant_id, :source, :external_id, :title, :description, :raw_severity, :status,
                        :detection_time, :asset_id, :user_identifier, CAST(:raw_payload AS jsonb), now(), now())
            """),
            {
                "id": str(alert_id),
                "tenant_id": str(tenant_id),
                "source": alert_data["source"],
                "external_id": alert_data["external_id"],
                "title": alert_data["title"],
                "description": alert_data["description"],
                "raw_severity": alert_data["raw_severity"],
                "status": alert_data["status"],
                "detection_time": alert_data["detection_time"],
                "asset_id": alert_data["asset_id"],
                "user_identifier": alert_data["user_identifier"],
                "raw_payload": raw_payload_json,
            }
        )
        
        # Add AI analysis
        recommended_actions_json = json.dumps([
            "Review alert details and context",
            "Isolate affected assets if necessary",
            "Investigate root cause",
            "Document findings"
        ])
        db.execute(
            text("""
                INSERT INTO security_ops.alert_ai_analysis
                (id, tenant_id, alert_id, model_name, model_version, ai_severity, ai_category, 
                 ai_confidence, rationale, recommended_actions, created_at)
                VALUES (:id, :tenant_id, :alert_id, :model_name, :model_version, :ai_severity, :ai_category,
                        :ai_confidence, :rationale, CAST(:recommended_actions AS jsonb), now())
            """),
            {
                "id": str(uuid4()),
                "tenant_id": str(tenant_id),
                "alert_id": str(alert_id),
                "model_name": "sentinelgrid-ai-v1",
                "model_version": "1.0.0",
                "ai_severity": alert_data["ai_severity"],
                "ai_category": alert_data["ai_category"],
                "ai_confidence": alert_data["ai_confidence"],
                "rationale": alert_data["rationale"],
                "recommended_actions": recommended_actions_json,
            }
        )
        
        alert_ids.append(alert_id)
        print(f"  ✅ Created alert: {alert_data['title']} ({alert_data['ai_severity']})")
    
    db.commit()
    print(f"  📊 Created {len(alerts_data)} alerts with AI analysis")
    return alert_ids


def seed_demo_incidents(tenant_id: UUID, db: Session, alert_lookup: Dict[str, UUID]) -> int:
    """Seed demo incidents mapped to seeded alerts."""
    print("🛠️  Seeding demo incidents...")
    incidents = [
        {
            "external_id": "inc-demo-1",
            "title": "Ransomware containment underway",
            "severity": "critical",
            "status": "open",
            "source": "detection_service",
            "alert_refs": ["WZH-RANS-001"],
            "nist_controls": ["RS.MI", "RS.AN"],
            "mitre_tactics": ["TA0040"],
            "mitre_techniques": ["T1486"],
            "recommended_playbook": "Contain Ransomware",
        },
        {
            "external_id": "inc-demo-2",
            "title": "Credential dumping on domain controller",
            "severity": "critical",
            "status": "investigating",
            "source": "detection_service",
            "alert_refs": ["WZH-CRED-001", "WZH-AUTH-002"],
            "nist_controls": ["DE.CM", "RS.CO"],
            "mitre_tactics": ["TA0006"],
            "mitre_techniques": ["T1003", "T1110"],
            "recommended_playbook": "Credential Theft Response",
        },
    ]

    created = 0
    for inc in incidents:
        exists = db.execute(
            text("SELECT id FROM incidents WHERE tenant_id=:tenant_id AND external_id=:external_id"),
            {"tenant_id": str(tenant_id), "external_id": inc["external_id"]},
        ).first()
        if exists:
            continue

        inc_id = uuid4()
        alert_ids = [str(alert_lookup[a]) for a in inc.get("alert_refs", []) if a in alert_lookup]
        raw_payload = {
            "recommended_playbook": inc.get("recommended_playbook"),
            "related_alert_ids": alert_ids,
        }
        db.execute(
            text("""
                INSERT INTO security_ops.incidents
                (id, tenant_id, source, external_id, title, status, severity,
                 raw_payload, nist_controls, mitre_tactics, mitre_techniques,
                 created_at, updated_at)
                VALUES (:id, :tenant_id, :source, :external_id, :title, :status, :severity,
                        CAST(:raw_payload AS jsonb),
                        CAST(:nist_controls AS jsonb),
                        CAST(:mitre_tactics AS jsonb),
                        CAST(:mitre_techniques AS jsonb),
                        now(), now())
            """),
            {
                "id": str(inc_id),
                "tenant_id": str(tenant_id),
                "source": inc.get("source", "detection_service"),
                "external_id": inc["external_id"],
                "title": inc["title"],
                "status": inc["status"],
                "severity": inc["severity"],
                "raw_payload": json.dumps(raw_payload),
                "nist_controls": json.dumps(inc.get("nist_controls")),
                "mitre_tactics": json.dumps(inc.get("mitre_tactics")),
                "mitre_techniques": json.dumps(inc.get("mitre_techniques")),
            },
        )
        created += 1
        print(f"  ✅ Created incident: {inc['title']} ({inc['severity']})")

    db.commit()
    print(f"  📊 Created {created} incidents")
    return created


def seed_demo_scans(tenant_id: UUID, db: Session) -> int:
    """Seed a few scan records so the Scans page is not empty."""
    print("🧪 Seeding scans...")
    scans = [
        {
            "scanner_id": "appsec-sast",
            "target_ref": "customer-portal@main",
            "status": "completed",
            "summary": {
                "type": "sast",
                "findings": {"critical": 0, "high": 2, "medium": 4, "low": 3},
                "duration_sec": 143,
            },
        },
        {
            "scanner_id": "iac-checks",
            "target_ref": "terraform/aws-prod",
            "status": "completed",
            "summary": {
                "type": "iac",
                "findings": {"critical": 0, "high": 1, "medium": 3, "low": 2},
                "duration_sec": 87,
            },
        },
        {
            "scanner_id": "git-secrets",
            "target_ref": "github.com/demo/sentinelgrid",
            "status": "completed",
            "summary": {
                "type": "git",
                "findings": {"critical": 0, "high": 0, "medium": 1, "low": 5},
                "duration_sec": 52,
            },
        },
    ]

    created = 0
    for scan in scans:
        exists = db.execute(
            text(
                "SELECT 1 FROM scans WHERE tenant_id = :tenant_id AND scanner_id = :scanner_id AND target_ref = :target_ref"
            ),
            {
                "tenant_id": str(tenant_id),
                "scanner_id": scan["scanner_id"],
                "target_ref": scan["target_ref"],
            },
        ).first()
        if exists:
            continue
        db.execute(
            text(
                """
                INSERT INTO scans (id, tenant_id, scanner_id, target_ref, status, summary, created_at, updated_at, started_at, finished_at)
                VALUES (:id, :tenant_id, :scanner_id, :target_ref, :status, CAST(:summary AS jsonb), now(), now(), now() - interval '5 minutes', now())
                """
            ),
            {
                "id": str(uuid4()),
                "tenant_id": str(tenant_id),
                "scanner_id": scan["scanner_id"],
                "target_ref": scan["target_ref"],
                "status": scan["status"],
                "summary": json.dumps(scan["summary"]),
            },
        )
        created += 1

    db.commit()
    print(f"  📊 Created {created} scans")
    return created


def seed_demo_detections(tenant_id: UUID, db: Session) -> int:
    """Seed a handful of detection rules + versions for demo tenant."""
    print("🧭 Seeding detection rules...")
    detections = [
        {
            "rule_key": "SG-DET-DEMO-001",
            "name": "Suspicious Admin Login",
            "description": "Detects admin logins from rare IPs/locations.",
            "category": "identity",
            "severity": "high",
            "query": {"match": {"event.category": "authentication"}},
            "trigger_condition": {"threshold": 1},
        },
        {
            "rule_key": "SG-DET-DEMO-002",
            "name": "Endpoint Malware Indicator",
            "description": "EDR process/start events with known bad binaries.",
            "category": "endpoint",
            "severity": "high",
            "query": {"match": {"event.category": "process"}},
            "trigger_condition": {"threshold": 1},
        },
        {
            "rule_key": "SG-DET-DEMO-003",
            "name": "Cloud IAM Anomaly",
            "description": "Unusual IAM API calls in AWS.",
            "category": "cloud",
            "severity": "medium",
            "query": {"match": {"cloud.service": "iam"}},
            "trigger_condition": {"threshold": 1},
        },
    ]
    created = 0
    for det in detections:
        rule_id = db.execute(
            text(
                """
                INSERT INTO security_ops.detection_rules
                    (id, rule_key, name, description, category, current_version, is_builtin, approval_required, tenant_id, created_by, updated_at)
                VALUES (:id, :rule_key, :name, :description, :category, '1.0.0', true, false, :tenant_id, 'seed', now())
                ON CONFLICT (rule_key, tenant_id) DO NOTHING
                RETURNING id
                """
            ),
            {
                "id": str(uuid4()),
                "rule_key": det["rule_key"],
                "name": det["name"],
                "description": det["description"],
                "category": det["category"],
                "tenant_id": str(tenant_id),
            },
        ).scalar()
        if not rule_id:
            rule_id = db.execute(
                text(
                    "SELECT id FROM security_ops.detection_rules WHERE rule_key=:rk AND tenant_id=:tid"
                ),
                {"rk": det["rule_key"], "tid": str(tenant_id)},
            ).scalar()
        if not rule_id:
            continue

        db.execute(
            text(
                """
                INSERT INTO security_ops.detection_rule_versions
                    (id, rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata, changelog, is_active, created_by)
                VALUES (:id, :rule_id, '1.0.0', :index_pattern, CAST(:query AS jsonb), CAST(:trigger AS jsonb),
                        :severity, '{}'::jsonb, '{}'::jsonb, 'seed', true, 'seed')
                ON CONFLICT (rule_id, version) DO NOTHING
                """
            ),
            {
                "id": str(uuid4()),
                "rule_id": str(rule_id),
                "index_pattern": f"sg-{tenant_id}-logs-*",
                "query": json.dumps(det["query"]),
                "trigger": json.dumps(det["trigger_condition"]),
                "severity": det["severity"],
            },
        )
        created += 1

    db.commit()
    print(f"  📊 Created {created} detection rules")
    return created


def seed_catalog_detections(tenant_id: UUID, db: Session, catalog_path: Optional[Path] = None) -> int:
    """
    Lightweight seeding of catalog detections for UI visibility.
    Uses cfg/detections/catalog.yaml and inserts minimal rule/version rows.
    """
    from pathlib import Path
    catalog_path = catalog_path or (REPO_ROOT / "cfg" / "detections" / "catalog.yaml")
    if not catalog_path.exists():
        print(f"  ⚠️  Catalog not found at {catalog_path}, skipping catalog detections")
        return 0
    data = yaml.safe_load(catalog_path.read_text()) or {}
    detections = data.get("detections", [])
    if not detections:
        print("  ⚠️  No detections in catalog, skipping")
        return 0

    created = 0
    for det in detections:
        rule_key = det.get("id")
        name = det.get("name") or rule_key
        if not rule_key or not name:
            continue
        category = det.get("category", "general")
        severity = det.get("severity", "medium")
        # Insert rule if missing
        rule_id = db.execute(
            text(
                """
                INSERT INTO security_ops.detection_rules
                    (id, rule_key, name, description, category, current_version, is_builtin, approval_required, tenant_id, created_by, updated_at)
                VALUES (:id, :rule_key, :name, :description, :category, '1.0.0', false, false, :tenant_id, 'seed-catalog', now())
                ON CONFLICT (rule_key, tenant_id) DO NOTHING
                RETURNING id
                """
            ),
            {
                "id": str(uuid4()),
                "rule_key": rule_key,
                "name": name,
                "description": det.get("description", ""),
                "category": category,
                "tenant_id": str(tenant_id),
            },
        ).scalar()
        if not rule_id:
            rule_id = db.execute(
                text(
                    "SELECT id FROM security_ops.detection_rules WHERE rule_key=:rk AND tenant_id=:tid"
                ),
                {"rk": rule_key, "tid": str(tenant_id)},
            ).scalar()
        if not rule_id:
            continue
        # Ensure tenant rows are marked non-builtin for visibility
        db.execute(
            text(
                "UPDATE security_ops.detection_rules SET is_builtin=false WHERE id=:rid"
            ),
            {"rid": str(rule_id)},
        )
        db.execute(
            text(
                """
                INSERT INTO security_ops.detection_rule_versions
                    (id, rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata, changelog, is_active, created_by)
                VALUES (:id, :rule_id, '1.0.0', :index_pattern, CAST(:query AS jsonb), CAST(:trigger AS jsonb),
                        :severity, '{}'::jsonb, '{}'::jsonb, 'catalog-seed', true, 'seed-catalog')
                ON CONFLICT (rule_id, version) DO NOTHING
                """
            ),
            {
                "id": str(uuid4()),
                "rule_id": str(rule_id),
                "index_pattern": f"sg-{tenant_id}-logs-*",
                "query": json.dumps(det.get("query") or {"match_all": {}}),
                "trigger": json.dumps(det.get("trigger_condition") or {"threshold": 1}),
                "severity": severity,
            },
        )
        created += 1

    db.commit()
    print(f"  📊 Catalog detections seeded: {created}")
    return created


def seed_catalog_playbooks(tenant_id: UUID, db: Session, catalog_path: Optional[Path] = None) -> int:
    """
    Seed playbooks from catalog.yaml into the target tenant (non-builtin so they render in UI).
    Keeps the payload minimal to match current playbooks schema.
    """
    from pathlib import Path
    catalog_path = catalog_path or (REPO_ROOT / "cfg" / "playbooks" / "catalog.yaml")
    if not catalog_path.exists():
        print(f"  ⚠️  Playbook catalog not found at {catalog_path}, skipping")
        return 0
    data = yaml.safe_load(catalog_path.read_text()) or {}
    playbooks = data.get("playbooks", [])
    if not playbooks:
        print("  ⚠️  No playbooks in catalog, skipping")
        return 0

    created = 0
    for pb in playbooks:
        key = pb.get("id")
        if not key:
            continue
        name = pb.get("name", key)
        description = pb.get("description", "")
        category = pb.get("owner") or pb.get("incident_type") or "general"
        workflow_ref = pb.get("runbook_ref") or key
        triggers = pb.get("triggers") or [f"Alert: {key}"]
        is_template = pb.get("is_template", False)

        exists = db.execute(
            text(
                "SELECT 1 FROM public.playbooks WHERE tenant_id=:tid AND key=:key"
            ),
            {"tid": str(tenant_id), "key": key},
        ).first()
        if exists:
            continue

        db.execute(
            text(
                """
                INSERT INTO public.playbooks
                    (id, tenant_id, key, name, description, target_type, severity_filter, category_filter, workflow_ref,
                     requires_approval, is_enabled, triggers, playbook_key, is_builtin, category, workflow,
                     trigger_conditions, auto_trigger_enabled, trigger_priority, is_template, created_at, updated_at)
                VALUES (:id, :tenant_id, :key, :name, :description, 'alert', '{}'::jsonb, '{}'::jsonb, :workflow_ref,
                        false, true, :triggers, :playbook_key, false, :category, :workflow,
                        '{}'::jsonb, false, 0, :is_template, now(), now())
                """
            ),
            {
                "id": str(uuid4()),
                "tenant_id": str(tenant_id),
                "key": key,
                "name": name,
                "description": description,
                "workflow_ref": workflow_ref,
                "triggers": triggers,
                "playbook_key": key,
                "category": category,
                # minimal workflow skeleton to satisfy UI
                "workflow": json.dumps({"nodes": [], "edges": []}),
                "is_template": is_template,
            },
        )
        created += 1

    db.commit()
    print(f"  📊 Catalog playbooks seeded: {created}")
    return created


def seed_sample_logs_opensearch(tenant_id: UUID) -> None:
    """
    Best-effort: seed a handful of sample logs into OpenSearch so log-management UI is populated.
    Skips silently if OpenSearch is unreachable.
    """
    import urllib.request
    import urllib.error

    os_url = os.getenv("OPENSEARCH_URL", "http://opensearch:9200").rstrip("/")
    date_str = datetime.utcnow().strftime("%Y.%m.%d")
    index = f"sg-{tenant_id}-logs-{date_str}"

    docs = [
        {
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "tenant_id": str(tenant_id),
            "sg": {"tenant_id": str(tenant_id)},
            "event": {"category": ["authentication"], "type": ["login"], "action": "user_login", "outcome": "success"},
            "user": {"email": "admin@demo.sentinelgrid.ai"},
            "source": {"ip": "203.0.113.10"},
        },
        {
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "tenant_id": str(tenant_id),
            "sg": {"tenant_id": str(tenant_id)},
            "event": {"category": ["process"], "type": ["start"], "action": "edr_alert", "outcome": "success"},
            "host": {"hostname": "workstation-01"},
            "process": {"name": "rundll32.exe", "command_line": "rundll32.exe bad.dll"},
        },
        {
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "tenant_id": str(tenant_id),
            "sg": {"tenant_id": str(tenant_id)},
            "event": {"category": ["iam"], "type": ["policy"], "action": "cloud_api_call", "outcome": "success"},
            "cloud": {"provider": "aws", "service": "iam", "region": "us-east-1"},
            "source": {"ip": "198.51.100.25"},
            "user": {"email": "sso.user@demo.sentinelgrid.ai"},
        },
    ]

    lines = []
    for doc in docs:
        lines.append(json.dumps({"index": {"_index": index}}))
        lines.append(json.dumps(doc))
    payload = ("\n".join(lines) + "\n").encode("utf-8")

    req = urllib.request.Request(
        f"{os_url}/_bulk",
        data=payload,
        headers={"Content-Type": "application/x-ndjson"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status >= 300:
                raise RuntimeError(f"Bulk ingest failed: {resp.status}")
        print(f"  📊 Seeded sample logs into OpenSearch index {index}")
    except Exception as e:
        print(f"  ⚠️  Skipping OpenSearch log seed: {e}")


def seed_knowledge_base() -> None:
    """
    Best-effort: load core knowledge base (NIST/MITRE/OWASP/playbooks) into model_gateway.
    """
    model_gateway = os.getenv("MODEL_GATEWAY_URL", "http://model_gateway:8000").rstrip("/")
    try:
        resp = httpx.post(
            f"{model_gateway}/internal/llm/knowledge-base/load",
            json={"frameworks": ["nist", "mitre", "owasp", "playbooks"], "async_load": False},
            timeout=60.0,
            verify=False,
        )
        resp.raise_for_status()
        data = resp.json() if resp.content else {}
        total = data.get("summary", {}).get("total_loaded")
        print(f"  📚 Knowledge base seeded via model_gateway ({total or 'ok'} items)")
    except Exception as e:
        print(f"  ⚠️  Skipping knowledge base seed: {e}")


# ============================================================================
# NimbusEdge Technologies Demo Data Seeding Functions
# ============================================================================

def seed_nimbusedge_employees(keycloak_admin, tenant_id: UUID, db: Session) -> Dict[str, str]:
    """Create NimbusEdge employees in Keycloak with department/role attributes.
    
    Args:
        keycloak_admin: KeycloakAdmin instance initialized for the demo realm
        tenant_id: UUID of the demo tenant
        db: Database session
    """
    print("👥 Seeding NimbusEdge employees...")
    
    user_ids = {}
    
    for emp_data in NIMBUSEDGE_EMPLOYEES:
        username = emp_data["email"]
        try:
            # Check if user exists
            # get_users() uses realm from KeycloakAdmin initialization
            users = keycloak_admin.get_users(query={"username": username})
            if users:
                user_id = users[0]["id"]
                # Update existing user to ensure tenant_id attribute is set
                try:
                    # get_user() uses realm from KeycloakAdmin initialization
                    user_details = keycloak_admin.get_user(user_id)
                    current_attrs = user_details.get("attributes", {})
                    current_tenant_id = current_attrs.get("tenant_id", [None])[0] if isinstance(current_attrs.get("tenant_id"), list) else current_attrs.get("tenant_id")

                    # Ensure profile basics are populated to satisfy required attributes
                    profile_update = {}
                    if not user_details.get("firstName"):
                        profile_update["firstName"] = emp_data["first_name"]
                    if not user_details.get("lastName"):
                        profile_update["lastName"] = emp_data["last_name"]
                    if not user_details.get("email"):
                        profile_update["email"] = username
                    profile_update["emailVerified"] = True
                    if profile_update:
                        keycloak_admin.update_user(user_id, profile_update)

                    if current_tenant_id != str(tenant_id):
                        # Try python-keycloak first
                        try:
                            update_data = {
                                "attributes": {
                                    **current_attrs,
                                    "tenant_id": [str(tenant_id)]
                                }
                            }
                            keycloak_admin.update_user(user_id, update_data)
                        except Exception as e:
                            print(f"  ⚠️  python-keycloak update failed: {e}")
                        
                        # Also try REST API (more reliable)
                        if set_user_tenant_id_via_rest_api(user_id, tenant_id, REALM_NAME):
                            print(f"  ✅ User '{username}' already exists - updated tenant_id attribute via REST API")
                        else:
                            print(f"  ⚠️  User '{username}' exists but failed to update tenant_id attribute")
                    else:
                        print(f"  ⏭️  User '{username}' already exists with correct tenant_id")
                except KeycloakError as e:
                    print(f"  ⚠️  User '{username}' exists but failed to update tenant_id: {e}")
                
                user_ids[username] = user_id
                continue
            
            # Create user with department and role attributes
            kc_user_data = {
                "username": username,
                "email": username,
                "firstName": emp_data["first_name"],
                "lastName": emp_data["last_name"],
                "enabled": True,
                "emailVerified": True,
                "attributes": {
                    "tenant_id": [str(tenant_id)],
                    "department": [emp_data["department"]],
                    "role": [emp_data["role"]],
                },
                "requiredActions": [],
            }
            
            # create_user() uses realm from KeycloakAdmin initialization
            user_id = keycloak_admin.create_user(kc_user_data)
            
            # Set password (non-temporary, simple shareable password)
            # set_user_password() uses realm from KeycloakAdmin initialization
            keycloak_admin.set_user_password(user_id, DEMO_PASSWORD, temporary=False)
            
            # Clear required actions
            # update_user() uses realm from KeycloakAdmin initialization
            keycloak_admin.update_user(user_id, {"requiredActions": []})
            
            # CRITICAL: Ensure tenant_id attribute is set via REST API (more reliable)
            # python-keycloak may not persist attributes correctly during creation
            if not set_user_tenant_id_via_rest_api(user_id, tenant_id, REALM_NAME):
                print(f"  ⚠️  Warning: Failed to set tenant_id attribute via REST API for {username}")
            
            # Assign role
            try:
                # get_realm_role() uses realm from KeycloakAdmin initialization
                role = keycloak_admin.get_realm_role(emp_data["keycloak_role"])
                # assign_realm_roles() uses realm from KeycloakAdmin initialization
                keycloak_admin.assign_realm_roles(user_id, [role])
            except KeycloakError as e:
                print(f"  ⚠️  Error assigning role to {username}: {e}")
            
            user_ids[username] = user_id
            print(f"  ✅ Created user '{username}' ({emp_data['name']}) with role {emp_data['keycloak_role']}")
            
        except KeycloakError as e:
            print(f"  ⚠️  Error creating user {username}: {e}")
    
    return user_ids


def seed_nimbusedge_assets(tenant_id: UUID, user_id_map: Dict[str, str], db: Session) -> int:
    """Create NimbusEdge company-issued devices in assets table (CMDB)."""
    print("💻 Seeding NimbusEdge assets (devices)...")
    
    # Create email to employee data mapping for department lookup
    email_to_employee = {emp["email"]: emp for emp in NIMBUSEDGE_EMPLOYEES}
    
    created = 0
    
    for device_data in NIMBUSEDGE_DEVICES:
        employee_email = device_data["employee_email"]
        
        # Look up employee data for department
        employee = email_to_employee.get(employee_email)
        department = employee["department"] if employee else None
        
        # Extract manufacturer from make_model
        make_model = device_data["make_model"]
        manufacturer = None
        if "MacBook" in make_model or "iPhone" in make_model:
            manufacturer = "Apple"
        elif "Pixel" in make_model:
            manufacturer = "Google"
        elif "Samsung" in make_model:
            manufacturer = "Samsung"
        elif "Surface" in make_model:
            manufacturer = "Microsoft"
        
        # Check if asset already exists
        result = db.execute(
            text("SELECT id FROM assets WHERE tenant_id = :tenant_id AND asset_id = :asset_id"),
            {"tenant_id": str(tenant_id), "asset_id": device_data["serial_number"]}
        ).first()
        
        if result:
            print(f"  ⏭️  Asset '{device_data['serial_number']}' already exists")
            continue
        
        # Create asset record
        asset_id = uuid4()
        hardware_specs = json.dumps({
            "make_model": make_model,
            "primary": device_data["primary"],
            "device_category": "company_issued"
        })
        
        # Get Keycloak user_id if available
        user_id = user_id_map.get(employee_email)
        
        db.execute(
            text("""
                INSERT INTO assets 
                (id, tenant_id, asset_id, asset_type, name, manufacturer, model, serial_number,
                 operating_system, owner, user_id, department, source, hardware_specs, created_at, updated_at)
                VALUES (:id, :tenant_id, :asset_id, :asset_type, :name, :manufacturer, :model, :serial_number,
                        :operating_system, :owner, :user_id, :department, :source, CAST(:hardware_specs AS jsonb), now(), now())
            """),
            {
                "id": str(asset_id),
                "tenant_id": str(tenant_id),
                "asset_id": device_data["serial_number"],
                "asset_type": device_data["device_type"],
                "name": make_model,
                "manufacturer": manufacturer,
                "model": make_model,
                "serial_number": device_data["serial_number"],
                "operating_system": device_data["os"],
                "owner": employee_email,
                "user_id": user_id,  # Keycloak user ID if available
                "department": department,
                "source": "manual",  # Demo/seed data
                "hardware_specs": hardware_specs,
            }
        )
        
        created += 1
        print(f"  ✅ Created asset: {make_model} ({device_data['serial_number']})")
    
    db.commit()
    print(f"  📊 Created {created} new assets")
    return created


def seed_nimbusedge_app_access(tenant_id: UUID, user_id_map: Dict[str, str], app_id_map: Dict[str, UUID], db: Session) -> int:
    """Map NimbusEdge employees to their apps via user_entitlements."""
    print("🔗 Seeding NimbusEdge app access mappings...")
    
    created_entitlements = 0
    created_mappings = 0
    
    # First, create entitlements for each app if they don't exist
    for app_name, app_id in app_id_map.items():
        # Create basic access entitlement for each app
        entitlement_name = f"{app_name}_access"
        
        # Check if entitlement exists
        result = db.execute(
            text("SELECT id FROM entitlements WHERE tenant_id = :tenant_id AND app_id = :app_id AND name = :name"),
            {"tenant_id": str(tenant_id), "app_id": str(app_id), "name": entitlement_name}
        ).first()
        
        if result:
            # Store entitlement_id for later use
            entitlement_id = result[0]
        else:
            # Create entitlement
            entitlement_id = uuid4()
            db.execute(
                text("""
                    INSERT INTO entitlements 
                    (id, tenant_id, app_id, name, display_name, description, entitlement_type, created_at, updated_at)
                    VALUES (:id, :tenant_id, :app_id, :name, :display_name, :description, :entitlement_type, now(), now())
                """),
                {
                    "id": str(entitlement_id),
                    "tenant_id": str(tenant_id),
                    "app_id": str(app_id),
                    "name": entitlement_name,
                    "display_name": f"{app_name.replace('_', ' ').title()} Access",
                    "description": f"Access to {app_name}",
                    "entitlement_type": "permission",
                }
            )
            created_entitlements += 1
        
        # Also create read-only entitlement for apps that need it
        if app_name == "github":
            read_only_name = f"{app_name}_read_only"
            read_only_result = db.execute(
                text("SELECT id FROM entitlements WHERE tenant_id = :tenant_id AND app_id = :app_id AND name = :name"),
                {"tenant_id": str(tenant_id), "app_id": str(app_id), "name": read_only_name}
            ).first()
            
            if not read_only_result:
                read_only_entitlement_id = uuid4()
                db.execute(
                    text("""
                        INSERT INTO entitlements 
                        (id, tenant_id, app_id, name, display_name, description, entitlement_type, created_at, updated_at)
                        VALUES (:id, :tenant_id, :app_id, :name, :display_name, :description, :entitlement_type, now(), now())
                    """),
                    {
                        "id": str(read_only_entitlement_id),
                        "tenant_id": str(tenant_id),
                        "app_id": str(app_id),
                        "name": read_only_name,
                        "display_name": f"{app_name.replace('_', ' ').title()} Read-Only",
                        "description": f"Read-only access to {app_name}",
                        "entitlement_type": "permission",
                    }
                )
                created_entitlements += 1
    
    db.commit()
    
    # Map employees to apps
    app_name_mapping = {
        "Google Workspace": "google_workspace",
        "Slack": "slack",
        "Notion": "notion",
        "GitHub": "github",
        "Jira": "jira",
        "Zoom": "zoom",
    }
    
    for emp_data in NIMBUSEDGE_EMPLOYEES:
        employee_email = emp_data["email"]
        user_id = user_id_map.get(employee_email)
        
        if not user_id:
            print(f"  ⚠️  User '{employee_email}' not found in user_id_map, skipping app access")
            continue
        
        for app_display_name in emp_data["apps"]:
            # Handle special case: "GitHub (read-only)"
            is_read_only = "(read-only)" in app_display_name
            app_display_name_clean = app_display_name.replace(" (read-only)", "").strip()
            
            app_name = app_name_mapping.get(app_display_name_clean)
            if not app_name:
                print(f"  ⚠️  App '{app_display_name_clean}' not found in mapping, skipping")
                continue
            
            app_id = app_id_map.get(app_name)
            if not app_id:
                print(f"  ⚠️  App '{app_name}' not found in app_id_map, skipping")
                continue
            
            # Determine entitlement name
            if is_read_only and app_name == "github":
                entitlement_name = "github_read_only"
            else:
                entitlement_name = f"{app_name}_access"
            
            # Get entitlement_id
            entitlement_result = db.execute(
                text("SELECT id FROM entitlements WHERE tenant_id = :tenant_id AND app_id = :app_id AND name = :name"),
                {"tenant_id": str(tenant_id), "app_id": str(app_id), "name": entitlement_name}
            ).first()
            
            if not entitlement_result:
                print(f"  ⚠️  Entitlement '{entitlement_name}' not found, skipping")
                continue
            
            entitlement_id = entitlement_result[0]
            
            # Check if user_entitlement already exists
            existing = db.execute(
                text("SELECT id FROM user_entitlements WHERE tenant_id = :tenant_id AND user_id = :user_id AND entitlement_id = :entitlement_id"),
                {"tenant_id": str(tenant_id), "user_id": user_id, "entitlement_id": str(entitlement_id)}
            ).first()
            
            if existing:
                continue  # Already mapped
            
            # Create user_entitlement
            user_entitlement_id = uuid4()
            db.execute(
                text("""
                    INSERT INTO user_entitlements 
                    (id, tenant_id, user_id, entitlement_id, status, created_at, updated_at)
                    VALUES (:id, :tenant_id, :user_id, :entitlement_id, 'active', now(), now())
                """),
                {
                    "id": str(user_entitlement_id),
                    "tenant_id": str(tenant_id),
                    "user_id": user_id,
                    "entitlement_id": str(entitlement_id),
                }
            )
            created_mappings += 1
    
    db.commit()
    print(f"  📊 Created {created_entitlements} new entitlements")
    print(f"  📊 Created {created_mappings} app access mappings")
    return created_mappings


def main():
    """Main orchestration function."""
    print("=" * 70)
    print("🌱 SentinelGrid Demo Data Seeding")
    print("=" * 70)
    print()
    print(f"Tenant: {TENANT_NAME} (slug: {TENANT_SLUG})")
    print(f"Realm: {REALM_NAME}")
    print(f"Demo Password: {DEMO_PASSWORD}")
    print()
    
    # Database setup
    engine = create_engine(DB_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    # Ensure security_ops schema is available without schema-qualified names
    try:
        db.execute(text("SET search_path = security_ops, public"))
        db.commit()
    except Exception:
        pass
    
    try:
        # 1. Create tenant
        sg_admin_tenant_id = ensure_sg_admin_tenant(db)
        print()

        tenant_id = create_demo_tenant(db)
        seed_onboarding_preferences(db, tenant_id)
        print()
        
        # 2. Keycloak setup (if available and not skipped)
        keycloak_admin = None
        user_ids = {}
        nimbusedge_user_ids = {}
        
        if not SKIP_KEYCLOAK and KEYCLOAK_AVAILABLE:
            try:
                from keycloak import KeycloakAdmin
                # Create master realm admin for realm creation operations
                master_keycloak_admin = KeycloakAdmin(
                    server_url=KEYCLOAK_URL,
                    username=KEYCLOAK_ADMIN_USER,
                    password=KEYCLOAK_ADMIN_PASSWORD,
                    realm_name="master",
                    verify=KEYCLOAK_VERIFY
                )
                
                # Create demo realm using master admin
                create_demo_realm(master_keycloak_admin)
                
                # Create demo realm admin instance for all demo realm operations
                # This is required because python-keycloak methods use the realm from initialization
                # user_realm_name="master" tells it to authenticate against master realm (where admin exists)
                # but work with the demo realm
                demo_keycloak_admin = KeycloakAdmin(
                    server_url=KEYCLOAK_URL,
                    username=KEYCLOAK_ADMIN_USER,
                    password=KEYCLOAK_ADMIN_PASSWORD,
                    realm_name=REALM_NAME,  # "demo" realm - operations will target this realm
                    user_realm_name="master",  # Authenticate against master realm (where admin user exists)
                    verify=KEYCLOAK_VERIFY
                )
                
                # Use demo realm admin for all demo realm operations
                clients = create_demo_clients(demo_keycloak_admin)
                create_demo_roles(demo_keycloak_admin)
                
                # Create tenant_id mapper for BOTH web and API clients
                # CRITICAL: Web client is used for login, so mapper must be on web client too
                if "web" in clients:
                    create_tenant_id_mapper(demo_keycloak_admin, clients["web"], "web")
                if "api" in clients:
                    create_tenant_id_mapper(demo_keycloak_admin, clients["api"], "api")
                
                user_ids = create_demo_users(demo_keycloak_admin, tenant_id)
                print()
                
                # 2a. Create NimbusEdge employees
                nimbusedge_user_ids = {}
                if demo_keycloak_admin:
                    nimbusedge_user_ids = seed_nimbusedge_employees(demo_keycloak_admin, tenant_id, db)
                    # Merge into user_ids for summary
                    user_ids.update(nimbusedge_user_ids)
                    print()
            except Exception as e:
                print(f"⚠️  Keycloak setup failed: {e}")
                print("   Continuing with database-only setup...")
                print()
        else:
            if SKIP_KEYCLOAK:
                print("⏭️  Skipping Keycloak setup (SKIP_KEYCLOAK=true)")
            else:
                print("⏭️  Skipping Keycloak setup (Keycloak library not available)")
            print()
        
        # 3. IAM Portal Data
        app_ids = seed_demo_apps(tenant_id, db)
        print()
        
        seed_demo_access_profiles(tenant_id, db)
        print()

        # 3a. Policy templates (used by visual builder)
        seed_policy_templates(db)
        print()

        # 3b. Playbooks (shared/builtin seeded under sg_admin if present)
        try:
            if sg_admin_tenant_id:
                seed_playbooks(sg_admin_tenant_id, db)
        except Exception as e:
            print(f"⚠️  Skipped playbook seeding: {e}")
        print()
        
        # 3c. Policies (for IAM dashboard)
        seed_demo_policies(tenant_id, REALM_NAME, db)
        print()
        
        # 4. NimbusEdge Assets (devices)
        # Note: assets can be seeded even without Keycloak users (user_id will be NULL)
        # Only require tenant_id which is always available
        if nimbusedge_user_ids:
            seed_nimbusedge_assets(tenant_id, nimbusedge_user_ids, db)
        else:
            # Seed assets even if no user_ids available (user_id will be NULL)
            seed_nimbusedge_assets(tenant_id, {}, db)
        print()
        
        # 5. NimbusEdge App Access Mappings
        if keycloak_admin and nimbusedge_user_ids:
            seed_nimbusedge_app_access(tenant_id, nimbusedge_user_ids, app_ids, db)
            print()
        
        # 6. Security Alerts
        alert_ids = seed_demo_alerts(tenant_id, db)
        # Build lookup by external_id for incident seeding
        alert_rows = db.execute(
            text("SELECT external_id, id FROM alerts WHERE tenant_id=:tenant_id"),
            {"tenant_id": str(tenant_id)}
        ).fetchall()
        alert_lookup = {row[0]: row[1] for row in alert_rows}
        seed_demo_incidents(tenant_id, db, alert_lookup)
        print()

        # 7. Scans (AppSec/IaC/Git)
        seed_demo_scans(tenant_id, db)
        print()

        # 8. Detections for SIEM UI
        seed_demo_detections(tenant_id, db)
        # Catalog detections (UI breadth)
        seed_catalog_detections(tenant_id, db)
        print()

        # 9. Playbooks (catalog into demo for visibility)
        seed_catalog_playbooks(tenant_id, db)
        print()

        # 10. Sample logs into OpenSearch (best-effort)
        seed_sample_logs_opensearch(tenant_id)
        print()

        # 11. Knowledge base (NIST/MITRE/OWASP/playbooks) into model_gateway
        seed_knowledge_base()
        print()
        
        # Summary
        print("=" * 70)
        print("✅ Demo data seeding completed successfully!")
        print("=" * 70)
        print()
        print("📋 Summary:")
        print(f"  • Tenant ID: {tenant_id}")
        print(f"  • Apps created: {len(app_ids)}")
        print(f"  • Alerts created: {len(alert_ids)}")
        print(f"  • Incidents created: {db.execute(text('SELECT COUNT(*) FROM security_ops.incidents WHERE tenant_id=:tid'), {'tid': str(tenant_id)}).scalar()}")
        if user_ids:
            print(f"  • Users created: {len(user_ids)}")
        if nimbusedge_user_ids:
            print(f"  • NimbusEdge employees: {len(nimbusedge_user_ids)}")
            print(f"  • NimbusEdge assets (devices): 10")
        if user_ids or nimbusedge_user_ids:
            print()
            print("🔑 Demo Credentials:")
            print(f"  Password for all users: {DEMO_PASSWORD}")
            print()
            print("  Users created:")
            for username, user_id in user_ids.items():
                print(f"    • {username}")
        print()
        
    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ Error during seeding: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
