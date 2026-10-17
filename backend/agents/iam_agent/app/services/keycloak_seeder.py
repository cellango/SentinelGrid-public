"""Keycloak Seeder Service - Idempotent Keycloak configuration seeding.

TODO: Migrate to KeycloakAdminClient (direct REST API)
======================================================
This module currently uses python-keycloak (KeycloakAdmin) which has compatibility
issues with Keycloak v25.0. The KeycloakAdminClient (direct REST API) has been
implemented and is now used in the signup flow.

Migration Status:
- ✅ Signup API migrated to KeycloakAdminClient
- ⏳ Seeder migration in progress (lower priority - only used for initialization)
- The seeder will continue to work for realm/client/role creation
- User creation via signup now uses the new client with attribute verification

For production use, user creation goes through the signup API (already migrated).
The seeder is only used for initial Keycloak configuration and test data.
"""

import logging
import os
import asyncio
from typing import Dict, Any, Optional, List
from uuid import uuid4
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError

from app.core.config import (
    KeycloakAdminAuthConfigError,
    resolve_keycloak_admin_runtime_auth,
    settings,
)
from app.services.keycloak_client import KeycloakClient
from app.services.keycloak_admin_client import KeycloakAdminClient

logger = logging.getLogger(__name__)


class SeedingResult:
    """Result of seeding operation."""
    
    def __init__(self):
        self.success = True
        self.errors: List[str] = []
        self.created: List[str] = []
        self.updated: List[str] = []
        self.skipped: List[str] = []
    
    def add_error(self, resource: str, error: str):
        """Add an error."""
        self.success = False
        self.errors.append(f"{resource}: {error}")
        logger.error(f"Seeding error - {resource}: {error}")
    
    def add_created(self, resource: str):
        """Add a created resource."""
        self.created.append(resource)
        logger.info(f"✅ Created: {resource}")
    
    def add_updated(self, resource: str):
        """Add an updated resource."""
        self.updated.append(resource)
        logger.info(f"🔄 Updated: {resource}")
    
    def add_skipped(self, resource: str):
        """Add a skipped resource."""
        self.skipped.append(resource)
        logger.info(f"⏭️  Skipped: {resource}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "errors": self.errors
        }


class KeycloakSeeder:
    """Idempotent Keycloak configuration seeder."""
    
    def __init__(self):
        """Initialize seeder."""
        self.realm_name = settings.KEYCLOAK_REALM
        self.keycloak_url = settings.KEYCLOAK_URL
        # For initial setup, use default admin account
        # After setup, we'll use service account
        self.admin_user = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
        self.admin_password = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
        
        # Admin user configuration
        self.admin_email = os.getenv("KEYCLOAK_ADMIN_EMAIL", "admin@sentinelgrid.ai")
        self.admin_password_seed = os.getenv("KEYCLOAK_ADMIN_PASSWORD_SEED", "admin123")
        
        # Tenant configuration
        self.default_tenant_name = os.getenv("DEFAULT_TENANT_NAME", "SentinelGrid")
        self.default_tenant_slug = os.getenv("DEFAULT_TENANT_SLUG", "sentinelgrid")
        
        # Demo realm configuration (used for showcase/demo realm seeding)
        self.demo_realm_name = os.getenv("DEMO_REALM_NAME", "demo")
        self.demo_password = os.getenv("DEMO_USER_PASSWORD", "DemoPassword123!")
        self.seed_demo_realm_enabled = os.getenv("KEYCLOAK_SEED_DEMO_REALM", "true").lower() == "true"
        self.demo_locale = os.getenv("DEMO_USER_LOCALE", "en")
        self.demo_timezone = os.getenv("DEMO_USER_TIMEZONE", "America/Chicago")
        
        # Seeding configuration
        self.seed_enabled = os.getenv("KEYCLOAK_SEED_ENABLED", "true").lower() == "true"
        self.dry_run = os.getenv("KEYCLOAK_SEED_DRY_RUN", "false").lower() == "true"
        self.max_retries = int(os.getenv("KEYCLOAK_SEED_MAX_RETRIES", "5"))
        self.retry_delay = int(os.getenv("KEYCLOAK_SEED_RETRY_DELAY", "10"))
        self._runtime_admin_auth = resolve_keycloak_admin_runtime_auth(
            admin_user=self.admin_user,
            admin_password=self.admin_password,
        )
        
        # Initialize admin client (uses master realm for admin operations)
        self.admin: Optional[KeycloakAdmin] = None
        self._init_admin_client()

    def _admin_client_kwargs(self, realm_name: str = "master") -> Dict[str, Any]:
        """Build Keycloak admin client kwargs using configured runtime auth."""
        kwargs: Dict[str, Any] = {
            "server_url": self.keycloak_url,
            "realm_name": realm_name,
            "verify": settings.KEYCLOAK_VERIFY_TLS,
        }
        kwargs["user_realm_name"] = self._runtime_admin_auth.user_realm_name
        kwargs.update(self._runtime_admin_auth.python_keycloak_kwargs)
        return kwargs
    
    def _init_admin_client(self):
        """Initialize Keycloak admin client with retry logic."""
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                self.admin = KeycloakAdmin(**self._admin_client_kwargs("master"))
                # Test the connection by trying to get realms
                self.admin.get_realms()
                logger.info(f"✅ Initialized Keycloak admin client for {self.keycloak_url} (attempt {attempt + 1})")
                return
            except Exception as e:
                error_str = str(e)
                logger.warning(f"Admin client initialization attempt {attempt + 1}/{max_attempts} failed: {error_str}")
                
                if attempt < max_attempts - 1:
                    import time
                    wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s, 8s
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    # Last attempt failed
                    logger.error(f"Failed to initialize admin client after {max_attempts} attempts")
                    if self._runtime_admin_auth.mode != "password":
                        self.admin = None
                        return
                    # If the configured admin account doesn't exist or is disabled, try to create it
                    if "Account disabled" in error_str or "invalid_grant" in error_str or "Invalid user credentials" in error_str:
                        logger.warning(f"Admin account '{self.admin_user}' appears to be disabled or doesn't exist, attempting to create it...")
                        try:
                            # Try to use default admin account to create sentinelgrid-admin
                            self._create_sentinelgrid_admin_account()
                            # Retry initialization with sentinelgrid-admin
                            self.admin = KeycloakAdmin(**self._admin_client_kwargs("master"))
                            logger.info(f"Successfully initialized Keycloak admin client after creating account")
                            return
                        except Exception as e2:
                            logger.error(f"Failed to create admin account and initialize client: {e2}")
                            # Try to re-enable default admin as fallback
                            try:
                                self._re_enable_admin_account()
                                # Retry initialization
                                self.admin = KeycloakAdmin(**self._admin_client_kwargs("master"))
                                logger.info(f"Successfully initialized Keycloak admin client after re-enabling account")
                                return
                            except Exception as e3:
                                logger.error(f"Failed to re-enable admin account and initialize client: {e3}")
                                self.admin = None
            else:
                logger.error(f"Failed to initialize Keycloak admin client: {error_str}")
                self.admin = None
    
    def _create_sentinelgrid_admin_account(self):
        """Create sentinelgrid-admin account in master realm using default admin account."""
        if self._runtime_admin_auth.mode != "password":
            raise KeycloakAdminAuthConfigError(
                "Admin account recovery is only supported in non-production password mode"
            )
        import httpx
        
        # Try to get token using default admin account
        default_admin_user = "admin"
        # Check environment variable first, then fallback to default
        default_admin_password = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
        
        token_url = f"{self.keycloak_url}/realms/master/protocol/openid-connect/token"
        
        with httpx.Client(timeout=10.0, verify=settings.KEYCLOAK_VERIFY_TLS) as client:
            # First, try to enable the admin account if it's disabled
            # We need to use the Keycloak management API, but we need auth for that
            # So we'll try to enable it using the initial admin token (if available)
            # For a fresh Keycloak install, the admin account should be enabled by default
            # But if it was disabled by a previous seeder run, we need to handle it
            
            # Try to get token with default admin
            token_response = client.post(
                token_url,
                data={
                    "grant_type": "password",
                    "username": default_admin_user,
                    "password": default_admin_password,
                    "client_id": "admin-cli"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if token_response.status_code != 200:
                error_text = token_response.text if token_response.text else ""
                logger.warning(f"Could not get admin token with default admin: {token_response.status_code} - {error_text}")
                
                # If account is disabled, we can't enable it without another admin account
                # For a fresh Keycloak install, admin should be enabled
                # If it's disabled, it means a previous seeder run disabled it
                if "user_disabled" in error_text or "Account disabled" in error_text:
                    logger.error("=" * 60)
                    logger.error("⚠️  KEYCLOAK ADMIN ACCOUNT IS DISABLED")
                    logger.error("The default admin account has been disabled (likely by a previous seeder run).")
                    logger.error("")
                    logger.error("SOLUTION: Restart Keycloak to reset the admin account, or:")
                    logger.error("1. Access Keycloak Admin Console: http://localhost:8081/admin")
                    logger.error("2. Use a different admin account if available")
                    logger.error("3. Or manually enable the admin account via Keycloak's database")
                    logger.error("=" * 60)
                    raise Exception("Keycloak admin account is disabled and cannot be automatically enabled")
                else:
                    raise Exception(f"Failed to authenticate with Keycloak admin: {error_text}")
            
            if token_response.status_code == 200:
                token = token_response.json()["access_token"]
                
                # Check if sentinelgrid-admin already exists
                users_url = f"{self.keycloak_url}/admin/realms/master/users"
                users_response = client.get(
                    users_url,
                    params={"username": self.admin_user, "exact": "true"},
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0
                )
                
                if users_response.status_code == 200:
                    existing_users = users_response.json()
                    if existing_users:
                        logger.info(f"User '{self.admin_user}' already exists in master realm")
                        # Enable it if disabled
                        user_id = existing_users[0]["id"]
                        user_data = existing_users[0]
                        if not user_data.get("enabled", False):
                            enable_url = f"{self.keycloak_url}/admin/realms/master/users/{user_id}"
                            client.put(
                                enable_url,
                                json={"enabled": True},
                                headers={
                                    "Authorization": f"Bearer {token}",
                                    "Content-Type": "application/json"
                                }
                            )
                            logger.info(f"Enabled existing user '{self.admin_user}'")
                        return
                
                # Create new sentinelgrid-admin user
                user_data = {
                    "username": self.admin_user,
                    "email": f"{self.admin_user}@sentinelgrid.local",
                    "firstName": "SentinelGrid",
                    "lastName": "Admin",
                    "enabled": True,
                    "emailVerified": False,
                    "requiredActions": []
                }
                
                create_response = client.post(
                    users_url,
                    json=user_data,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0
                )
                
                if create_response.status_code == 201:
                    # Get user ID from Location header
                    location = create_response.headers.get("Location", "")
                    if location:
                        user_id = location.split("/")[-1]
                    else:
                        # Query for the user
                        users_check = client.get(
                            users_url,
                            params={"username": self.admin_user, "exact": "true"},
                            headers={
                                "Authorization": f"Bearer {token}",
                                "Content-Type": "application/json"
                            }
                        )
                        if users_check.status_code == 200:
                            created_users = users_check.json()
                            if created_users:
                                user_id = created_users[0]["id"]
                            else:
                                logger.error("User created but not found")
                                return
                        else:
                            logger.error("Could not verify user creation")
                            return
                    
                    # Set password
                    password_url = f"{self.keycloak_url}/admin/realms/master/users/{user_id}/reset-password"
                    password_response = client.put(
                        password_url,
                        json={
                            "type": "password",
                            "value": self.admin_password,
                            "temporary": False
                        },
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json"
                        }
                    )
                    
                    if password_response.status_code in [204, 200]:
                        logger.info(f"✅ Created and configured '{self.admin_user}' account in master realm")
                    else:
                        logger.warning(f"User created but password set failed: {password_response.status_code}")
                    
                    # Assign admin role
                    try:
                        role_url = f"{self.keycloak_url}/admin/realms/master/roles/admin"
                        role_response = client.get(
                            role_url,
                            headers={
                                "Authorization": f"Bearer {token}",
                                "Content-Type": "application/json"
                            }
                        )
                        if role_response.status_code == 200:
                            role = role_response.json()
                            assign_url = f"{self.keycloak_url}/admin/realms/master/users/{user_id}/role-mappings/realm"
                            assign_response = client.post(
                                assign_url,
                                json=[role],
                                headers={
                                    "Authorization": f"Bearer {token}",
                                    "Content-Type": "application/json"
                                }
                            )
                            if assign_response.status_code in [204, 200]:
                                logger.info(f"✅ Assigned admin role to '{self.admin_user}'")
                    except Exception as e:
                        logger.warning(f"Could not assign admin role: {e}")
                        
                elif create_response.status_code == 409:
                    logger.info(f"User '{self.admin_user}' already exists")
                else:
                    error_text = create_response.text[:300] if create_response.text else "Unknown error"
                    logger.error(f"Failed to create user: {create_response.status_code} - {error_text}")
            else:
                logger.error(f"Could not get admin token: {token_response.status_code}")
    
    def _re_enable_admin_account(self):
        """Re-enable the admin account using REST API (when admin client can't connect)."""
        if self._runtime_admin_auth.mode != "password":
            raise KeycloakAdminAuthConfigError(
                "Admin account recovery is only supported in non-production password mode"
            )
        import httpx
        import base64
        
        # Use basic auth to enable the admin account
        # This is a workaround when the account is disabled
        default_admin_user = "admin"
        default_admin_password = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
        auth_str = f"{default_admin_user}:{default_admin_password}"
        auth_bytes = auth_str.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        # First, try to get admin user ID
        with httpx.Client(timeout=10.0, verify=settings.KEYCLOAK_VERIFY_TLS) as client:
            # Get users endpoint
            users_url = f"{self.keycloak_url}/admin/realms/master/users"
            response = client.get(
                users_url,
                headers={
                    "Authorization": f"Basic {auth_b64}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 401:
                # Try using admin-cli client token instead
                token_url = f"{self.keycloak_url}/realms/master/protocol/openid-connect/token"
                token_response = client.post(
                    token_url,
                    data={
                        "grant_type": "password",
                        "username": default_admin_user,
                        "password": default_admin_password,
                        "client_id": "admin-cli"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if token_response.status_code == 200:
                    token = token_response.json()["access_token"]
                    # Now get users and enable admin
                    users_response = client.get(
                        users_url,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json"
                        }
                    )
                    
                    if users_response.status_code == 200:
                        users = users_response.json()
                        admin_user = next((u for u in users if u.get("username") == "admin"), None)
                        if admin_user:
                            user_id = admin_user["id"]
                            # Enable the user
                            enable_url = f"{self.keycloak_url}/admin/realms/master/users/{user_id}"
                            client.put(
                                enable_url,
                                json={"enabled": True},
                                headers={
                                    "Authorization": f"Bearer {token}",
                                    "Content-Type": "application/json"
                                }
                            )
                            logger.info("Re-enabled admin account via REST API")
    
    async def wait_for_keycloak(self) -> bool:
        """Wait for Keycloak to be ready and admin account to be functional."""
        import httpx
        
        logger.info(f"Waiting for Keycloak to be ready (max {self.max_retries * self.retry_delay}s)...")
        
        for attempt in range(self.max_retries):
            try:
                # First check health endpoint
                async with httpx.AsyncClient(timeout=10.0, verify=settings.KEYCLOAK_VERIFY_TLS) as client:
                    health_response = await client.get(f"{self.keycloak_url}/health/ready")
                    if health_response.status_code == 200:
                        # Also verify admin account works by trying to get a token
                        try:
                            token_response = await client.post(
                                f"{self.keycloak_url}/realms/{self._runtime_admin_auth.user_realm_name}/protocol/openid-connect/token",
                                data=dict(self._runtime_admin_auth.token_payload),
                                headers={"Content-Type": "application/x-www-form-urlencoded"},
                                timeout=10.0
                            )
                            if token_response.status_code == 200:
                                logger.info(f"✅ Keycloak is ready and admin account is functional (attempt {attempt + 1})")
                                return True
                            else:
                                logger.debug(f"Keycloak health OK but admin login not ready (attempt {attempt + 1}/{self.max_retries}): {token_response.status_code}")
                        except Exception as e:
                            logger.debug(f"Admin login check failed (attempt {attempt + 1}/{self.max_retries}): {e}")
            except Exception as e:
                logger.debug(f"Keycloak not ready (attempt {attempt + 1}/{self.max_retries}): {e}")
            
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay)
        
        logger.warning("Keycloak may not be fully ready, continuing anyway...")
        return False
    
    async def seed_all(self) -> SeedingResult:
        """Seed all Keycloak resources."""
        result = SeedingResult()
        
        if not self.seed_enabled:
            logger.info("Keycloak seeding is disabled (KEYCLOAK_SEED_ENABLED=false)")
            result.add_skipped("all (seeding disabled)")
            return result
        
        if self.dry_run:
            logger.info("Keycloak seeding in DRY-RUN mode (KEYCLOAK_SEED_DRY_RUN=true)")
        
        if not self.admin:
            result.add_error("admin_client", "Failed to initialize Keycloak admin client")
            return result
        
        # Wait for Keycloak to be ready
        keycloak_ready = await self.wait_for_keycloak()
        if not keycloak_ready:
            logger.warning("Keycloak readiness check failed, but continuing with seeding...")
        
        # Re-initialize admin client after Keycloak is ready (in case it failed initially)
        if not self.admin:
            logger.info("Re-initializing admin client after Keycloak readiness check...")
            self._init_admin_client()
        
        if not self.admin:
            result.add_error("admin_client", "Failed to initialize Keycloak admin client after readiness check")
            logger.error("Cannot proceed with seeding - admin client not available")
            return result
        
        logger.info("=" * 60)
        logger.info("Starting Keycloak seeding...")
        logger.info("=" * 60)
        
        try:
            # Seed realm
            await self.seed_realm(result)
            
            # Switch to target realm for subsequent operations
            if self.admin:
                self.admin.realm_name = self.realm_name
            
            # Seed clients
            await self.seed_clients(result)
            
            # Configure service account for IAM Agent client
            await self.configure_service_account(result)
            
            # Seed roles
            await self.seed_roles(result)
            
            # Seed protocol mappers
            await self.seed_protocol_mappers(result)
            
            # Seed default tenant FIRST (in PostgreSQL) - required for admin user tenant_id
            await self.seed_default_tenant(result)
            
            # Configure User Profile (CRITICAL for tenant_id persistence)
            await self.seed_user_profile(result)
            
            # Seed admin user (now tenant exists, User Profile configured)
            await self.seed_admin_user(result)
            
            # Seed break-glass account (super admin for emergency access)
            await self.seed_break_glass_account(result)
            
            # Seed demo realm and demo users (for demo.sentinelgrid.ai logins)
            await self.seed_demo_realm(result)
            
            # Certificate request removed - certificates should be created separately via cert service
            
            # DISABLED: Do not disable default admin account
            # This was causing issues where the seeder couldn't run on subsequent attempts
            # The admin account should remain enabled for operational use
            # await self.disable_default_admin(result)
            logger.info("⚠️  Skipping admin account disable - keeping default admin enabled for operational use")
            
        except Exception as e:
            logger.error(f"Unexpected error during seeding: {e}", exc_info=True)
            result.add_error("seeding", str(e))
        
        logger.info("=" * 60)
        logger.info(f"Seeding completed. Success: {result.success}")
        logger.info(f"Created: {len(result.created)}, Updated: {len(result.updated)}, "
                   f"Skipped: {len(result.skipped)}, Errors: {len(result.errors)}")
        logger.info("=" * 60)
        
        return result
    
    async def seed_realm(self, result: SeedingResult):
        """Seed SentinelGrid realm."""
        logger.info("Seeding realm...")
        
        if self.dry_run:
            result.add_skipped("realm (dry-run)")
            return
        
        try:
            # Check if realm exists
            try:
                existing_realm = self.admin.get_realm(self.realm_name)
                logger.info(f"Realm '{self.realm_name}' already exists")
                
                # Update realm configuration
                realm_config = {
                    "enabled": True,
                    "displayName": "SentinelGrid",
                    "sslRequired": "external",  # Require SSL for external connections
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
                
                # Only update if different
                needs_update = any(
                    existing_realm.get(k) != v
                    for k, v in realm_config.items()
                    if k in existing_realm
                )
                
                if needs_update:
                    self.admin.update_realm(self.realm_name, realm_config)
                    result.add_updated(f"realm:{self.realm_name}")
                else:
                    result.add_skipped(f"realm:{self.realm_name}")
                    
            except KeycloakError:
                # Realm doesn't exist, create it
                realm_config = {
                    "realm": self.realm_name,
                    "enabled": True,
                    "displayName": "SentinelGrid",
                    "sslRequired": "external",  # Require SSL for external connections
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
                
                self.admin.create_realm(realm_config)
                result.add_created(f"realm:{self.realm_name}")
                
        except Exception as e:
            result.add_error("realm", str(e))
    
    async def seed_clients(self, result: SeedingResult):
        """Seed Keycloak clients."""
        logger.info("Seeding clients...")
        
        if self.dry_run:
            result.add_skipped("clients (dry-run)")
            return
        
        clients_config = [
            {
                "clientId": "sentinelgrid-web",
                "name": "SentinelGrid Web Client",
                "enabled": True,
                "publicClient": True,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": True,
                "redirectUris": [
                    "http://localhost:3000/*",
                    "http://localhost:3001/*",
                    "https://localhost:3443/*",
                    "https://*.sentinelgrid.com/*"
                ],
                "webOrigins": ["+"],
            },
            {
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
            },
            {
                "clientId": "sentinelgrid-api",
                "name": "SentinelGrid API Client",
                "enabled": True,
                "publicClient": False,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": True,
                "redirectUris": [],
            },
            {
                "clientId": "sentinelgrid-iam-agent",
                "name": "SentinelGrid IAM Agent",
                "enabled": True,
                "publicClient": False,
                "serviceAccountsEnabled": True,
                "standardFlowEnabled": False,
                "directAccessGrantsEnabled": False,
                "redirectUris": [],
            },
        ]
        
        try:
            # Use REST API directly with explicit realm in URL (like test script)
            # This eliminates any caching or realm confusion issues
            import httpx
            
            logger.info(f"Getting clients from realm '{self.realm_name}' via REST API")
            
            # Get admin token for REST API
            admin_token = None
            try:
                # Try to get token from admin client's connection
                if hasattr(self.admin, 'connection') and hasattr(self.admin.connection, 'token'):
                    admin_token = self.admin.connection.token.get('access_token')
                    logger.debug("Got admin token from existing connection")
            except Exception as e:
                logger.debug(f"Could not get token from connection: {e}")
            
            # If no token, get one explicitly
            if not admin_token:
                try:
                    admin_token = self._get_admin_token()
                    logger.debug("Got admin token via REST API")
                except Exception as e:
                    logger.error(f"Exception getting admin token: {e}")
                    result.add_error("clients", f"Exception getting admin token: {str(e)}")
                    return
            
            # Get existing clients via REST API with EXPLICIT realm in URL
            clients_url = f"{self.keycloak_url}/admin/realms/{self.realm_name}/clients"
            logger.info(f"Querying clients from: {clients_url}")
            
            try:
                clients_response = httpx.get(
                    clients_url,
                    headers={
                        "Authorization": f"Bearer {admin_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0,
                    verify=settings.KEYCLOAK_VERIFY_TLS
                )
                
                if clients_response.status_code != 200:
                    logger.error(f"Failed to get clients: {clients_response.status_code} - {clients_response.text[:200]}")
                    result.add_error("clients", f"Failed to get clients: {clients_response.status_code}")
                    return
                
                existing_clients = clients_response.json()
                client_ids = [c.get('clientId') for c in existing_clients]
                logger.info(f"Found {len(existing_clients)} existing clients in realm '{self.realm_name}' (via REST API)")
                logger.info(f"Client IDs found: {client_ids}")
                client_map = {c["clientId"]: c for c in existing_clients}
                
                for client_config in clients_config:
                    client_id = client_config["clientId"]
                    
                    try:
                        if client_id in client_map:
                            # Update existing client - ensure directAccessGrantsEnabled is True
                            existing = client_map[client_id]
                            client_uuid = existing["id"]
                            needs_update = False
                            update_data = {}
                            
                            # Check if directAccessGrantsEnabled needs to be enabled
                            if not existing.get("directAccessGrantsEnabled", False):
                                update_data["directAccessGrantsEnabled"] = True
                                needs_update = True
                            
                            # Update redirect URIs if needed
                            existing_uris = set(existing.get("redirectUris", []))
                            new_uris = set(client_config.get("redirectUris", []))
                            if not new_uris.issubset(existing_uris):
                                update_data["redirectUris"] = list(existing_uris | new_uris)
                                needs_update = True
                            
                            if needs_update:
                                # Update via REST API with explicit realm
                                update_url = f"{self.keycloak_url}/admin/realms/{self.realm_name}/clients/{client_uuid}"
                                update_response = httpx.put(
                                    update_url,
                                    json=update_data,
                                    headers={
                                        "Authorization": f"Bearer {admin_token}",
                                        "Content-Type": "application/json"
                                    },
                                    timeout=10.0,
                                    verify=settings.KEYCLOAK_VERIFY_TLS
                                )
                                if update_response.status_code in [204, 200]:
                                    logger.info(f"✅ Updated client '{client_id}' via REST API")
                                    result.add_updated(f"client:{client_id}")
                                else:
                                    logger.warning(f"⚠️  Update response: {update_response.status_code}")
                                    result.add_updated(f"client:{client_id}")
                            else:
                                result.add_skipped(f"client:{client_id}")
                        else:
                            # Create new client using REST API with EXPLICIT realm in URL
                            logger.info(f"Creating client '{client_id}' in realm '{self.realm_name}' via REST API")
                            create_url = f"{self.keycloak_url}/admin/realms/{self.realm_name}/clients"
                            logger.info(f"POST {create_url}")
                            
                            try:
                                create_response = httpx.post(
                                    create_url,
                                    json=client_config,
                                    headers={
                                        "Authorization": f"Bearer {admin_token}",
                                        "Content-Type": "application/json"
                                    },
                                    timeout=10.0,
                                    verify=settings.KEYCLOAK_VERIFY_TLS
                                )
                                
                                logger.info(f"Create response status: {create_response.status_code}")
                                
                                if create_response.status_code == 201:
                                    logger.info(f"✅ Client '{client_id}' created via REST API in realm '{self.realm_name}'")
                                    
                                    # Verify by querying again with explicit realm
                                    verify_response = httpx.get(
                                        clients_url,
                                        headers={
                                            "Authorization": f"Bearer {admin_token}",
                                            "Content-Type": "application/json"
                                        },
                                        timeout=10.0,
                                        verify=settings.KEYCLOAK_VERIFY_TLS
                                    )
                                    
                                    if verify_response.status_code == 200:
                                        verify_clients = verify_response.json()
                                        created_client = [c for c in verify_clients if c.get('clientId') == client_id]
                                        if created_client:
                                            logger.info(f"✅ Verified client '{client_id}' exists: {created_client[0]['id']}")
                                            result.add_created(f"client:{client_id}")
                                        else:
                                            logger.warning(f"⚠️  Client '{client_id}' created but not found in verification query")
                                            result.add_created(f"client:{client_id}")
                                    else:
                                        logger.warning(f"⚠️  Could not verify client creation: {verify_response.status_code}")
                                        result.add_created(f"client:{client_id}")
                                else:
                                    error_text = create_response.text[:300] if create_response.text else "Unknown error"
                                    logger.error(f"❌ Failed to create client '{client_id}': {create_response.status_code}")
                                    logger.error(f"   Error details: {error_text}")
                                    result.add_error(f"client:{client_id}", f"REST API error: {create_response.status_code} - {error_text}")
                                    
                            except Exception as create_error:
                                logger.error(f"Exception creating client '{client_id}': {create_error}", exc_info=True)
                                result.add_error(f"client:{client_id}", str(create_error))
                            
                    except Exception as e:
                        logger.error(f"Unexpected error processing client '{client_id}': {e}", exc_info=True)
                        result.add_error(f"client:{client_id}", str(e))
                        
            except Exception as e:
                logger.error(f"Exception getting/processing clients: {e}", exc_info=True)
                result.add_error("clients", str(e))
                
        except Exception as e:
            logger.error(f"Exception in seed_clients: {e}", exc_info=True)
            result.add_error("clients", str(e))
    
    async def configure_service_account(self, result: SeedingResult):
        """Configure service account for sentinelgrid-iam-agent client and assign roles."""
        logger.info("Configuring service account for IAM Agent...")
        
        if self.dry_run:
            result.add_skipped("service_account (dry-run)")
            return
        
        if not self.admin:
            result.add_error("service_account", "Admin client not available")
            return
        
        try:
            import httpx
            
            # Get admin token
            admin_token = self._get_admin_token()
            if not admin_token:
                result.add_error("service_account", "Failed to get admin token")
                return
            
            # Get the sentinelgrid-iam-agent client
            clients_url = f"{self.keycloak_url}/admin/realms/{self.realm_name}/clients"
            clients_response = httpx.get(
                clients_url,
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                },
                params={"clientId": "sentinelgrid-iam-agent"},
                timeout=10.0,
                verify=settings.KEYCLOAK_VERIFY_TLS
            )
            
            if clients_response.status_code != 200 or not clients_response.json():
                result.add_error("service_account", "IAM Agent client not found")
                return
            
            client = clients_response.json()[0]
            client_id = client["id"]
            
            # Verify service accounts are enabled
            if not client.get("serviceAccountsEnabled", False):
                logger.warning("Service accounts not enabled for IAM Agent client, enabling...")
                update_url = f"{self.keycloak_url}/admin/realms/{self.realm_name}/clients/{client_id}"
                httpx.put(
                    update_url,
                    json={"serviceAccountsEnabled": True},
                    headers={
                        "Authorization": f"Bearer {admin_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0,
                    verify=settings.KEYCLOAK_VERIFY_TLS
                )
            
            # Get service account user (created automatically by Keycloak)
            service_account_url = f"{self.keycloak_url}/admin/realms/{self.realm_name}/clients/{client_id}/service-account-user"
            sa_response = httpx.get(
                service_account_url,
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                },
                timeout=10.0,
                verify=settings.KEYCLOAK_VERIFY_TLS
            )
            
            if sa_response.status_code != 200:
                result.add_error("service_account", f"Failed to get service account user: {sa_response.status_code}")
                return
            
            service_account_user = sa_response.json()
            sa_user_id = service_account_user["id"]
            
            # Assign realm-management roles to service account
            # These roles allow the service account to manage users, clients, and realms
            realm_management_roles = [
                "manage-users",
                "manage-clients",
                "view-users",
                "view-clients",
                "manage-realm",
                "view-realm"
            ]
            
            # Get realm-management client roles
            realm_mgmt_url = f"{self.keycloak_url}/admin/realms/{self.realm_name}/clients"
            realm_mgmt_response = httpx.get(
                realm_mgmt_url,
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                },
                params={"clientId": "realm-management"},
                timeout=10.0,
                verify=settings.KEYCLOAK_VERIFY_TLS
            )
            
            if realm_mgmt_response.status_code != 200:
                result.add_error("service_account", "Failed to get realm-management client")
                return
            
            realm_mgmt_client = realm_mgmt_response.json()[0]
            realm_mgmt_client_id = realm_mgmt_client["id"]
            
            # Get roles to assign
            roles_to_assign = []
            for role_name in realm_management_roles:
                role_url = f"{self.keycloak_url}/admin/realms/{self.realm_name}/clients/{realm_mgmt_client_id}/roles/{role_name}"
                role_response = httpx.get(
                    role_url,
                    headers={
                        "Authorization": f"Bearer {admin_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0,
                    verify=settings.KEYCLOAK_VERIFY_TLS
                )
                if role_response.status_code == 200:
                    roles_to_assign.append(role_response.json())
                else:
                    logger.warning(f"Role {role_name} not found, skipping")
            
            if roles_to_assign:
                # Assign roles to service account
                assign_url = f"{self.keycloak_url}/admin/realms/{self.realm_name}/users/{sa_user_id}/role-mappings/clients/{realm_mgmt_client_id}"
                assign_response = httpx.post(
                    assign_url,
                    json=roles_to_assign,
                    headers={
                        "Authorization": f"Bearer {admin_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0,
                    verify=settings.KEYCLOAK_VERIFY_TLS
                )
                
                if assign_response.status_code in [204, 200]:
                    logger.info(f"✅ Assigned {len(roles_to_assign)} realm-management roles to service account")
                    result.add_updated("service_account:roles")
                else:
                    logger.warning(f"Failed to assign roles: {assign_response.status_code}")
                    result.add_error("service_account", f"Failed to assign roles: {assign_response.status_code}")
            
            # Configure secrets through the deployment's approved secret store.
            # Bootstrap must never retrieve a client secret merely to log it.
            logger.info("Use approved secret management for credentials; client secrets are not logged")

            result.add_updated("service_account:configured")
            
        except Exception as e:
            logger.error(f"Exception configuring service account: {e}", exc_info=True)
            result.add_error("service_account", str(e))
    
    async def seed_roles(self, result: SeedingResult):
        """Seed realm roles."""
        logger.info("Seeding roles...")
        
        if self.dry_run:
            result.add_skipped("roles (dry-run)")
            return
        
        roles_config = [
            {"name": "TENANT_ADMIN", "description": "Full control over tenant"},
            {"name": "SOC_MANAGER", "description": "Manage incidents, playbooks, team"},
            {"name": "SOC_ANALYST", "description": "View and triage alerts, manage incidents"},
            {"name": "VIEW_ONLY", "description": "Read-only access"},
        ]
        
        try:
            # Get existing roles
            existing_roles = self.admin.get_realm_roles()
            role_names = {r["name"] for r in existing_roles}
            
            for role_config in roles_config:
                role_name = role_config["name"]
                
                try:
                    if role_name in role_names:
                        result.add_skipped(f"role:{role_name}")
                    else:
                        self.admin.create_realm_role(role_config, self.realm_name)
                        result.add_created(f"role:{role_name}")
                        
                except Exception as e:
                    result.add_error(f"role:{role_name}", str(e))
                    
        except Exception as e:
            result.add_error("roles", str(e))
    
    async def seed_protocol_mappers(self, result: SeedingResult):
        """Seed protocol mappers for tenant_id on both web and API clients."""
        logger.info("Seeding protocol mappers...")
        
        if self.dry_run:
            result.add_skipped("protocol_mappers (dry-run)")
            return
        
        try:
            import httpx
            
            # Get admin token
            admin_token = self._get_admin_token()
            if not admin_token:
                result.add_error("protocol_mapper", "Failed to get admin token")
                return
            
            # Get clients via REST API
            clients_url = f"{self.keycloak_url}/admin/realms/{self.realm_name}/clients"
            clients_response = httpx.get(
                clients_url,
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                },
                timeout=10.0,
                verify=settings.KEYCLOAK_VERIFY_TLS
            )
            
            if clients_response.status_code != 200:
                result.add_error("protocol_mapper", f"Failed to get clients: {clients_response.status_code}")
                return
            
            clients = clients_response.json()
            client_map = {c.get("clientId"): c for c in clients}
            
            # Create mapper for both web and API clients
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
                    "userinfo.token.claim": "true"
                }
            }
            
            # Add mapper to sentinelgrid-web client
            web_client = client_map.get("sentinelgrid-web")
            if web_client:
                web_client_id = web_client["id"]
                mappers_url = f"{self.keycloak_url}/admin/realms/{self.realm_name}/clients/{web_client_id}/protocol-mappers/models"
                
                # Check if mapper exists
                mappers_response = httpx.get(
                    mappers_url,
                    headers={
                        "Authorization": f"Bearer {admin_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0,
                    verify=settings.KEYCLOAK_VERIFY_TLS
                )
                
                if mappers_response.status_code == 200:
                    existing_mappers = mappers_response.json()
                    if not any(m.get("name") == "tenant-id-mapper" for m in existing_mappers):
                        create_response = httpx.post(
                            mappers_url,
                            json=mapper_data,
                            headers={
                                "Authorization": f"Bearer {admin_token}",
                                "Content-Type": "application/json"
                            },
                            timeout=10.0,
                            verify=settings.KEYCLOAK_VERIFY_TLS
                        )
                        if create_response.status_code in [201, 200]:
                            result.add_created("protocol_mapper:tenant-id-mapper:web")
                        else:
                            result.add_error("protocol_mapper:web", f"Failed to create: {create_response.status_code}")
                    else:
                        result.add_skipped("protocol_mapper:tenant-id-mapper:web")
            
            # Add mapper to sentinelgrid-api client
            api_client = client_map.get("sentinelgrid-api")
            if api_client:
                api_client_id = api_client["id"]
                mappers_url = f"{self.keycloak_url}/admin/realms/{self.realm_name}/clients/{api_client_id}/protocol-mappers/models"
                
                # Check if mapper exists
                mappers_response = httpx.get(
                    mappers_url,
                    headers={
                        "Authorization": f"Bearer {admin_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0,
                    verify=settings.KEYCLOAK_VERIFY_TLS
                )
                
                if mappers_response.status_code == 200:
                    existing_mappers = mappers_response.json()
                    if not any(m.get("name") == "tenant-id-mapper" for m in existing_mappers):
                        create_response = httpx.post(
                            mappers_url,
                            json=mapper_data,
                            headers={
                                "Authorization": f"Bearer {admin_token}",
                                "Content-Type": "application/json"
                            },
                            timeout=10.0,
                            verify=settings.KEYCLOAK_VERIFY_TLS
                        )
                        if create_response.status_code in [201, 200]:
                            result.add_created("protocol_mapper:tenant-id-mapper:api")
                        else:
                            result.add_error("protocol_mapper:api", f"Failed to create: {create_response.status_code}")
                    else:
                        result.add_skipped("protocol_mapper:tenant-id-mapper:api")
            
        except Exception as e:
            logger.error(f"Exception in seed_protocol_mappers: {e}", exc_info=True)
            result.add_error("protocol_mapper", str(e))
    
    def _get_admin_token(self) -> str:
        """Get admin token for REST API operations."""
        import httpx
        
        token_response = httpx.post(
            f"{self.keycloak_url}/realms/{self._runtime_admin_auth.user_realm_name}/protocol/openid-connect/token",
            data=dict(self._runtime_admin_auth.token_payload),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
            verify=settings.KEYCLOAK_VERIFY_TLS
        )
        if token_response.status_code == 200:
            return token_response.json()["access_token"]
        else:
            raise Exception(f"Failed to get admin token: {token_response.status_code}")

    def _get_default_tenant_id(self) -> Optional[str]:
        """Return the default tenant_id (used for demo users) if available."""
        if not settings.DB_URL:
            return None
        
        try:
            engine = create_engine(settings.DB_URL)
            with engine.connect() as conn:
                db_result = conn.execute(
                    text("SELECT id FROM tenants WHERE slug = :slug LIMIT 1"),
                    {"slug": self.default_tenant_slug}
                ).fetchone()
                if db_result:
                    return str(db_result[0])
        except Exception as e:
            logger.warning(f"Could not fetch default tenant id: {e}")
        return None
    
    def _verify_login(self, username: str, password: str, client_id: str = "sentinelgrid-web") -> bool:
        """Verify that user can log in by attempting token generation."""
        import httpx
        
        token_url = f"{self.keycloak_url}/realms/{self.realm_name}/protocol/openid-connect/token"
        data = {
            "client_id": client_id,
            "username": username,
            "password": password,
            "grant_type": "password",
            "scope": "openid",
        }
        
        try:
            response = httpx.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
                verify=settings.KEYCLOAK_VERIFY_TLS
            )
            
            if response.status_code == 200:
                token_data = response.json()
                if "access_token" in token_data:
                    logger.info(f"✅ Login verification successful for '{username}' in realm '{self.realm_name}'")
                    return True
                else:
                    logger.warning(f"Token response missing access_token: {token_data}")
                    return False
            else:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"error": response.text}
                logger.warning(f"Login verification failed ({response.status_code}) for '{username}': {error_data}")
                return False
        except Exception as e:
            logger.error(f"Error verifying login: {e}")
            return False
    
    async def seed_user_profile(self, result: SeedingResult):
        """
        Configure User Profile to enable custom attributes (tenant_id, customer_id).
        
        CRITICAL: This MUST be done before creating any users in Keycloak v25+
        Without this, custom attributes will not persist.
        """
        logger.info("Configuring User Profile for custom attributes...")
        
        if self.dry_run:
            result.add_skipped("user_profile (dry-run)")
            return
        
        try:
            import httpx
            
            admin_token = self._get_admin_token()
            profile_url = f"{self.keycloak_url}/admin/realms/{self.realm_name}/users/profile"
            
            # Get current profile
            get_response = httpx.get(
                profile_url,
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                },
                timeout=10.0,
                verify=settings.KEYCLOAK_VERIFY_TLS
            )
            
            if get_response.status_code == 200:
                profile = get_response.json()
            else:
                logger.warning(f"Could not get current profile: {get_response.status_code}")
                profile = {"attributes": []}
            
            # Ensure attributes array exists
            if "attributes" not in profile:
                profile["attributes"] = []
            
            # Add tenant_id and customer_id attributes if not present
            existing_attr_names = [attr["name"] for attr in profile["attributes"]]
            
            custom_attributes = [
                {
                    "name": "tenant_id",
                    "displayName": "Tenant ID",
                    "validations": {},
                    "permissions": {
                        "view": ["admin", "user"],
                        "edit": ["admin"]
                    },
                    "multivalued": False
                },
                {
                    "name": "customer_id",
                    "displayName": "Customer ID",
                    "validations": {},
                    "permissions": {
                        "view": ["admin", "user"],
                        "edit": ["admin"]
                    },
                    "multivalued": False
                }
            ]
            
            added_count = 0
            for attr in custom_attributes:
                if attr["name"] not in existing_attr_names:
                    profile["attributes"].append(attr)
                    added_count += 1
                    logger.info(f"  Added attribute: {attr['name']}")
            
            if added_count == 0:
                logger.info("  User Profile already has custom attributes")
                result.add_skipped("user_profile (already configured)")
                return
            
            # Update User Profile
            update_response = httpx.put(
                profile_url,
                json=profile,
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                },
                timeout=10.0,
                verify=settings.KEYCLOAK_VERIFY_TLS
            )
            
            if update_response.status_code in [200, 204]:
                logger.info(f"✅ User Profile configured with {added_count} custom attributes")
                result.add_created("user_profile (tenant_id, customer_id)")
            else:
                error_text = update_response.text[:200] if update_response.text else "Unknown error"
                logger.error(f"Failed to update User Profile: {update_response.status_code} - {error_text}")
                result.add_error("user_profile", f"Failed to update: {update_response.status_code}")
                
        except Exception as e:
            logger.error(f"Error configuring User Profile: {e}", exc_info=True)
            result.add_error("user_profile", str(e))
    
    async def seed_admin_user(self, result: SeedingResult):
        """Seed admin user using explicit REST API calls with realm in URL. Always creates fresh user."""
        logger.info("Seeding admin user...")
        
        if self.dry_run:
            result.add_skipped("admin_user (dry-run)")
            return
        
        try:
            import httpx
            
            # Get admin token for REST API (explicit realm usage)
            try:
                admin_token = self._get_admin_token()
            except Exception as e:
                logger.error(f"Failed to get admin token: {e}")
                result.add_error("admin_user", f"Failed to get admin token: {str(e)}")
                return
            
            # Check if user exists - if it does, log a warning but continue (user should be deleted before seeding)
            users_url = f"{self.keycloak_url}/admin/realms/{self.realm_name}/users"
            params = {"username": self.admin_email, "exact": "true"}
            
            try:
                users_response = httpx.get(
                    users_url,
                    headers={
                        "Authorization": f"Bearer {admin_token}",
                        "Content-Type": "application/json"
                    },
                    params=params,
                    timeout=10.0,
                    verify=settings.KEYCLOAK_VERIFY_TLS
                )
                
                if users_response.status_code == 200:
                    users = users_response.json()
                    if users:
                        logger.warning(f"⚠️  User '{self.admin_email}' already exists in realm '{self.realm_name}'. "
                                     f"Consider deleting the user first (e.g., using scripts/delete-admin-user.py) to ensure clean state.")
                        # Continue anyway - we'll try to create and handle 409 if it fails
                elif users_response.status_code != 200:
                    logger.error(f"Failed to check for existing user: {users_response.status_code}")
                    result.add_error("admin_user", f"Failed to check for existing user: {users_response.status_code}")
                    return
            except Exception as e:
                logger.warning(f"Exception checking for existing user: {e}")
                # Continue anyway
            
            # Create user data
            user_data = {
                "username": self.admin_email,
                "email": self.admin_email,
                "firstName": "Admin",
                "lastName": "SentinelGrid",
                "enabled": True,
                "emailVerified": True,
                "requiredActions": [],
            }
            
            # Create new user using explicit realm in URL
            logger.info(f"Creating user '{self.admin_email}' in realm '{self.realm_name}'")
            user_id = None
            
            try:
                create_response = httpx.post(
                    users_url,
                    json=user_data,
                    headers={
                        "Authorization": f"Bearer {admin_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0,
                    verify=settings.KEYCLOAK_VERIFY_TLS
                )
                
                if create_response.status_code == 201:
                    # Get user ID from Location header or query again
                    location = create_response.headers.get("Location", "")
                    if location:
                        user_id = location.split("/")[-1]
                    else:
                        # Query for the user we just created
                        users_check = httpx.get(
                            users_url,
                            headers={
                                "Authorization": f"Bearer {admin_token}",
                                "Content-Type": "application/json"
                            },
                            params=params,
                            timeout=10.0,
                            verify=settings.KEYCLOAK_VERIFY_TLS
                        )
                        if users_check.status_code == 200:
                            created_users = users_check.json()
                            if created_users:
                                user_id = created_users[0]["id"]
                            else:
                                logger.error("User created but not found in verification query")
                                result.add_error("admin_user", "User created but not found")
                                return
                        else:
                            logger.error("Could not verify user creation")
                            result.add_error("admin_user", "Could not verify user creation")
                            return
                    
                    logger.info(f"✅ Created user '{self.admin_email}' (ID: {user_id}) in realm '{self.realm_name}'")
                elif create_response.status_code == 409:
                    # User already exists
                    logger.warning(f"User already exists (409). Getting existing user ID...")
                    users_check = httpx.get(
                        users_url,
                        headers={
                            "Authorization": f"Bearer {admin_token}",
                            "Content-Type": "application/json"
                        },
                        params=params,
                        timeout=10.0,
                        verify=settings.KEYCLOAK_VERIFY_TLS
                    )
                    if users_check.status_code == 200:
                        existing_users = users_check.json()
                        if existing_users:
                            user_id = existing_users[0]["id"]
                            logger.info(f"Using existing user ID: {user_id}")
                        else:
                            result.add_error("admin_user", "User exists but not found")
                            return
                    else:
                        result.add_error("admin_user", "Could not find existing user")
                        return
                else:
                    error_text = create_response.text[:300] if create_response.text else "Unknown error"
                    logger.error(f"Failed to create user: {create_response.status_code} - {error_text}")
                    result.add_error("admin_user", f"Failed to create user: {create_response.status_code} - {error_text}")
                    return
            except Exception as e:
                logger.error(f"Exception creating user: {e}", exc_info=True)
                result.add_error("admin_user", f"Exception creating user: {str(e)}")
                return
            
            if not user_id:
                result.add_error("admin_user", "User ID not available")
                return
            
            # Set password using explicit realm in URL
            password_url = f"{self.keycloak_url}/admin/realms/{self.realm_name}/users/{user_id}/reset-password"
            try:
                password_response = httpx.put(
                    password_url,
                    json={
                        "type": "password",
                        "value": self.admin_password_seed,
                        "temporary": False
                    },
                    headers={
                        "Authorization": f"Bearer {admin_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0,
                    verify=settings.KEYCLOAK_VERIFY_TLS
                )
                if password_response.status_code not in [204, 200]:
                    logger.warning(f"Password set response: {password_response.status_code}")
                else:
                    logger.info(f"✅ Set password for user {self.admin_email} in realm '{self.realm_name}'")
            except Exception as e:
                logger.warning(f"Could not set password: {e}")
            
            # Set tenant_id attribute
            try:
                # Get current user to preserve other attributes
                user_get_url = f"{self.keycloak_url}/admin/realms/{self.realm_name}/users/{user_id}"
                current_user = httpx.get(
                    user_get_url,
                    headers={
                        "Authorization": f"Bearer {admin_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0,
                    verify=settings.KEYCLOAK_VERIFY_TLS
                ).json()
                
                # Get tenant ID from database
                from app.core.database import engine
                from sqlalchemy import text
                with engine.connect() as conn:
                    db_result = conn.execute(
                        text("SELECT id FROM tenants WHERE slug = :slug LIMIT 1"),
                        {"slug": self.default_tenant_slug}
                    )
                    row = db_result.fetchone()
                    if row:
                        tenant_id = str(row[0])
                        # Update user with tenant_id attribute
                        if 'attributes' not in current_user:
                            current_user['attributes'] = {}
                        current_user['attributes']['tenant_id'] = [tenant_id]
                        current_user['requiredActions'] = []
                        current_user['emailVerified'] = True
                        current_user['enabled'] = True
                        
                        update_response = httpx.put(
                            user_get_url,
                            json=current_user,
                            headers={
                                "Authorization": f"Bearer {admin_token}",
                                "Content-Type": "application/json"
                            },
                            timeout=10.0,
                            verify=settings.KEYCLOAK_VERIFY_TLS
                        )
                        if update_response.status_code in [204, 200]:
                            logger.info(f"✅ Set tenant_id={tenant_id} for user {self.admin_email}")
            except Exception as e:
                logger.warning(f"Could not set tenant_id attribute: {e}")
            
            # Explicitly clear required actions after setting password using explicit realm in URL
            # (Keycloak may add them back after password operations)
            # This matches the test helper's approach in keycloak_account_setup.py
            try:
                user_get_url = f"{self.keycloak_url}/admin/realms/{self.realm_name}/users/{user_id}"
                current_user_response = httpx.get(
                    user_get_url,
                    headers={
                        "Authorization": f"Bearer {admin_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0,
                    verify=settings.KEYCLOAK_VERIFY_TLS
                )
                if current_user_response.status_code == 200:
                    current_user = current_user_response.json()
                    # Always clear required actions to ensure account is fully activated
                    current_user["requiredActions"] = []
                    current_user["emailVerified"] = True
                    
                    clear_response = httpx.put(
                        user_get_url,
                        json=current_user,
                        headers={
                            "Authorization": f"Bearer {admin_token}",
                            "Content-Type": "application/json"
                        },
                        timeout=10.0,
                        verify=settings.KEYCLOAK_VERIFY_TLS
                    )
                    if clear_response.status_code in [204, 200]:
                        logger.info(f"✅ Cleared required actions for user {self.admin_email} in realm '{self.realm_name}'")
                    else:
                        logger.warning(f"Could not clear required actions: {clear_response.status_code}")
            except Exception as e:
                logger.warning(f"Could not clear required actions: {e}")
            
            # Assign TENANT_ADMIN role using explicit realm
            try:
                # Get role ID
                role_url = f"{self.keycloak_url}/admin/realms/{self.realm_name}/roles/TENANT_ADMIN"
                role_response = httpx.get(
                    role_url,
                    headers={
                        "Authorization": f"Bearer {admin_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0,
                    verify=settings.KEYCLOAK_VERIFY_TLS
                )
                if role_response.status_code == 200:
                    role = role_response.json()
                    # Assign role
                    assign_role_url = f"{self.keycloak_url}/admin/realms/{self.realm_name}/users/{user_id}/role-mappings/realm"
                    assign_response = httpx.post(
                        assign_role_url,
                        json=[role],
                        headers={
                            "Authorization": f"Bearer {admin_token}",
                            "Content-Type": "application/json"
                        },
                        timeout=10.0,
                        verify=settings.KEYCLOAK_VERIFY_TLS
                    )
                    if assign_response.status_code in [204, 200]:
                        logger.info(f"✅ Assigned TENANT_ADMIN role to user {self.admin_email} in realm '{self.realm_name}'")
            except Exception as e:
                logger.debug(f"Could not assign role (may not exist yet): {e}")
            
            # Verify login after creation
            logger.info(f"Verifying login for user '{self.admin_email}'...")
            login_success = self._verify_login(self.admin_email, self.admin_password_seed)
            if login_success:
                logger.info(f"✅ Login verification passed for '{self.admin_email}'")
            else:
                logger.warning(f"⚠️  Login verification failed for '{self.admin_email}' - account may not be fully activated")
                result.add_error("admin_user", "Login verification failed")
            
            result.add_created(f"user:{self.admin_email}")
                
        except Exception as e:
            logger.error(f"Unexpected error in seed_admin_user: {e}", exc_info=True)
            result.add_error("admin_user", str(e))
    
    async def seed_default_tenant(self, result: SeedingResult):
        """Seed default tenant in PostgreSQL."""
        logger.info("Seeding default tenant...")
        
        if self.dry_run:
            result.add_skipped("default_tenant (dry-run)")
            return
        
        if not settings.DB_URL:
            logger.warning("DB_URL not configured, skipping tenant creation")
            result.add_skipped("default_tenant (no DB_URL)")
            return
        
        try:
            engine = create_engine(settings.DB_URL)
            SessionLocal = sessionmaker(bind=engine)
            db_session = SessionLocal()
            
            try:
                # Check if tenant exists
                db_result = db_session.execute(
                    text("SELECT id FROM tenants WHERE slug = :slug"),
                    {"slug": self.default_tenant_slug}
                ).fetchone()
                
                if db_result:
                    tenant_id = db_result[0]
                    logger.info(f"Tenant already exists: {tenant_id}")
                    result.add_skipped(f"tenant:{self.default_tenant_slug}")
                else:
                    # Create tenant
                    tenant_id = uuid4()
                    db_session.execute(
                        text("""
                            INSERT INTO tenants (id, name, slug, status, created_at, updated_at)
                            VALUES (:id, :name, :slug, :status, :created_at, :updated_at)
                        """),
                        {
                            "id": str(tenant_id),
                            "name": self.default_tenant_name,
                            "slug": self.default_tenant_slug,
                            "status": "active",
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }
                    )
                    db_session.commit()
                    result.add_created(f"tenant:{self.default_tenant_slug}")
                    
            finally:
                db_session.close()
                
        except Exception as e:
            logger.warning(f"Failed to create default tenant: {e}")
            result.add_error("default_tenant", str(e))
    
    async def seed_break_glass_account(self, result: SeedingResult):
        """Create break-glass account with super admin privileges in master realm."""
        logger.info("Creating break-glass account...")
        
        if self.dry_run:
            result.add_skipped("break_glass_account (dry-run)")
            return
        
        if not self.admin:
            result.add_error("break_glass_account", "Admin client not available")
            return
        
        try:
            import httpx
            
            # Get admin token
            admin_token = self._get_admin_token()
            if not admin_token:
                result.add_error("break_glass_account", "Failed to get admin token")
                return
            
            # Break-glass account configuration
            break_glass_username = os.getenv("KEYCLOAK_BREAK_GLASS_USER", "break-glass-admin")
            break_glass_password = os.getenv("KEYCLOAK_BREAK_GLASS_PASSWORD", "BreakGlass2024!ChangeMe")
            break_glass_email = os.getenv("KEYCLOAK_BREAK_GLASS_EMAIL", "break-glass@sentinelgrid.local")
            
            # Check if break-glass account already exists
            users_url = f"{self.keycloak_url}/admin/realms/master/users"
            params = {"username": break_glass_username, "exact": "true"}
            
            users_response = httpx.get(
                users_url,
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                },
                params=params,
                timeout=10.0,
                verify=settings.KEYCLOAK_VERIFY_TLS
            )
            
            if users_response.status_code == 200:
                existing_users = users_response.json()
                if existing_users:
                    user_id = existing_users[0]["id"]
                    logger.info(f"Break-glass account '{break_glass_username}' already exists, updating...")
                    
                    # Update password and ensure enabled
                    password_url = f"{self.keycloak_url}/admin/realms/master/users/{user_id}/reset-password"
                    httpx.put(
                        password_url,
                        json={
                            "type": "password",
                            "value": break_glass_password,
                            "temporary": False
                        },
                        headers={
                            "Authorization": f"Bearer {admin_token}",
                            "Content-Type": "application/json"
                        },
                        timeout=10.0,
                        verify=settings.KEYCLOAK_VERIFY_TLS
                    )
                    
                    # Ensure enabled
                    httpx.put(
                        f"{self.keycloak_url}/admin/realms/master/users/{user_id}",
                        json={"enabled": True},
                        headers={
                            "Authorization": f"Bearer {admin_token}",
                            "Content-Type": "application/json"
                        },
                        timeout=10.0,
                        verify=settings.KEYCLOAK_VERIFY_TLS
                    )
                    
                    result.add_updated(f"break_glass_account:{break_glass_username}")
                else:
                    # Create new break-glass account
                    user_data = {
                        "username": break_glass_username,
                        "email": break_glass_email,
                        "firstName": "Break",
                        "lastName": "Glass",
                        "enabled": True,
                        "emailVerified": False,
                        "requiredActions": []
                    }
                    
                    create_response = httpx.post(
                        users_url,
                        json=user_data,
                        headers={
                            "Authorization": f"Bearer {admin_token}",
                            "Content-Type": "application/json"
                        },
                        timeout=10.0,
                        verify=settings.KEYCLOAK_VERIFY_TLS
                    )
                    
                    if create_response.status_code == 201:
                        location = create_response.headers.get("Location", "")
                        user_id = location.split("/")[-1] if location else None
                        
                        if not user_id:
                            # Query for the user
                            users_check = httpx.get(
                                users_url,
                                params=params,
                                headers={
                                    "Authorization": f"Bearer {admin_token}",
                                    "Content-Type": "application/json"
                                },
                                timeout=10.0,
                                verify=settings.KEYCLOAK_VERIFY_TLS
                            )
                            if users_check.status_code == 200:
                                created_users = users_check.json()
                                if created_users:
                                    user_id = created_users[0]["id"]
                        
                        if user_id:
                            # Set password
                            password_url = f"{self.keycloak_url}/admin/realms/master/users/{user_id}/reset-password"
                            httpx.put(
                                password_url,
                                json={
                                    "type": "password",
                                    "value": break_glass_password,
                                    "temporary": False
                                },
                                headers={
                                    "Authorization": f"Bearer {admin_token}",
                                    "Content-Type": "application/json"
                                },
                                timeout=10.0,
                                verify=settings.KEYCLOAK_VERIFY_TLS
                            )
                            
                            # Assign admin role (super user privileges)
                            role_url = f"{self.keycloak_url}/admin/realms/master/roles/admin"
                            role_response = httpx.get(
                                role_url,
                                headers={
                                    "Authorization": f"Bearer {admin_token}",
                                    "Content-Type": "application/json"
                                },
                                timeout=10.0,
                                verify=settings.KEYCLOAK_VERIFY_TLS
                            )
                            
                            if role_response.status_code == 200:
                                role = role_response.json()
                                assign_url = f"{self.keycloak_url}/admin/realms/master/users/{user_id}/role-mappings/realm"
                                assign_response = httpx.post(
                                    assign_url,
                                    json=[role],
                                    headers={
                                        "Authorization": f"Bearer {admin_token}",
                                        "Content-Type": "application/json"
                                    },
                                    timeout=10.0,
                                    verify=settings.KEYCLOAK_VERIFY_TLS
                                )
                                
                                if assign_response.status_code in [204, 200]:
                                    logger.info(f"✅ Created break-glass account '{break_glass_username}' with admin privileges")
                                    logger.warning(f"⚠️  BREAK-GLASS ACCOUNT CREDENTIALS:")
                                    logger.warning(f"   Username: {break_glass_username}")
                                    logger.warning(f"   Password: {break_glass_password}")
                                    logger.warning(f"   ⚠️  STORE THESE SECURELY - CHANGE PASSWORD IN PRODUCTION!")
                                    result.add_created(f"break_glass_account:{break_glass_username}")
                                else:
                                    result.add_error("break_glass_account", f"Failed to assign admin role: {assign_response.status_code}")
                            else:
                                result.add_error("break_glass_account", "Failed to get admin role")
                        else:
                            result.add_error("break_glass_account", "Failed to get user ID after creation")
                    else:
                        error_text = create_response.text[:300] if create_response.text else "Unknown error"
                        result.add_error("break_glass_account", f"Failed to create: {create_response.status_code} - {error_text}")
            else:
                result.add_error("break_glass_account", f"Failed to check for existing user: {users_response.status_code}")
                
        except Exception as e:
            logger.error(f"Exception creating break-glass account: {e}", exc_info=True)
            result.add_error("break_glass_account", str(e))
    
    async def seed_demo_realm(self, result: SeedingResult):
        """Seed the demo realm and demo users (used for showcase/demo logins)."""
        logger.info("Seeding demo realm and demo users...")
        
        if self.dry_run:
            result.add_skipped("demo_realm (dry-run)")
            return
        
        if not self.seed_demo_realm_enabled:
            result.add_skipped("demo_realm (disabled)")
            return
        
        demo_realm = self.demo_realm_name
        
        try:
            import httpx
            
            admin_token = self._get_admin_token()
            headers = {
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            }
            
            # ------------------------------------------------------------------
            # Ensure realm exists
            # ------------------------------------------------------------------
            realm_url = f"{self.keycloak_url}/admin/realms/{demo_realm}"
            realm_response = httpx.get(realm_url, headers=headers, timeout=10.0, verify=settings.KEYCLOAK_VERIFY_TLS)
            
            if realm_response.status_code == 200:
                realm_data = realm_response.json()
                if not realm_data.get("enabled", True):
                    httpx.put(
                        realm_url,
                        json={**realm_data, "enabled": True},
                        headers=headers,
                        timeout=10.0,
                        verify=settings.KEYCLOAK_VERIFY_TLS
                    )
                    result.add_updated(f"realm:{demo_realm}")
                else:
                    result.add_skipped(f"realm:{demo_realm}")
            elif realm_response.status_code == 404:
                realm_config = {
                    "realm": demo_realm,
                    "enabled": True,
                    "displayName": "Demo",
                    "sslRequired": "external",
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
                create_realm = httpx.post(
                    f"{self.keycloak_url}/admin/realms",
                    json=realm_config,
                    headers=headers,
                    timeout=10.0,
                    verify=settings.KEYCLOAK_VERIFY_TLS
                )
                if create_realm.status_code in [201, 204]:
                    result.add_created(f"realm:{demo_realm}")
                else:
                    result.add_error(f"realm:{demo_realm}", f"Failed to create realm: {create_realm.status_code}")
                    return
            else:
                result.add_error(f"realm:{demo_realm}", f"Failed to read realm: {realm_response.status_code}")
                return
            
            # ------------------------------------------------------------------
            # Ensure clients exist (minimal set for web/API access)
            # ------------------------------------------------------------------
            clients_config = [
                {
                    "clientId": "sentinelgrid-web",
                    "name": "SentinelGrid Web Client",
                    "enabled": True,
                    "publicClient": True,
                    "standardFlowEnabled": True,
                    "directAccessGrantsEnabled": True,
                    "redirectUris": [
                        "http://localhost:3000/*",
                        "http://localhost:3001/*",
                        "https://localhost:3443/*",
                        "https://*.sentinelgrid.com/*"
                    ],
                    "webOrigins": ["+"],
                },
                {
                    "clientId": "sentinelgrid-api",
                    "name": "SentinelGrid API Client",
                    "enabled": True,
                    "publicClient": False,
                    "standardFlowEnabled": True,
                    "directAccessGrantsEnabled": True,
                    "redirectUris": [],
                },
            ]
            
            clients_url = f"{self.keycloak_url}/admin/realms/{demo_realm}/clients"
            clients_response = httpx.get(clients_url, headers=headers, timeout=10.0, verify=settings.KEYCLOAK_VERIFY_TLS)
            if clients_response.status_code != 200:
                result.add_error(f"clients:{demo_realm}", f"Failed to fetch clients: {clients_response.status_code}")
                return
            
            existing_clients = clients_response.json()
            client_map = {c.get("clientId"): c for c in existing_clients if c.get("clientId")}
            
            for client_config in clients_config:
                client_id = client_config["clientId"]
                if client_id in client_map:
                    # Ensure directAccessGrantsEnabled and redirect URIs are up to date
                    existing = client_map[client_id]
                    update_payload = {}
                    needs_update = False
                    
                    if not existing.get("directAccessGrantsEnabled", False) and client_config.get("directAccessGrantsEnabled"):
                        update_payload["directAccessGrantsEnabled"] = True
                        needs_update = True
                    
                    # Merge redirect URIs
                    existing_uris = set(existing.get("redirectUris", []))
                    new_uris = set(client_config.get("redirectUris", []))
                    if new_uris and not new_uris.issubset(existing_uris):
                        update_payload["redirectUris"] = list(existing_uris | new_uris)
                        needs_update = True
                    
                    if needs_update:
                        update_url = f"{clients_url}/{existing['id']}"
                        update_resp = httpx.put(update_url, json=update_payload, headers=headers, timeout=10.0, verify=settings.KEYCLOAK_VERIFY_TLS)
                        if update_resp.status_code in [204, 200]:
                            result.add_updated(f"client:{client_id}:{demo_realm}")
                        else:
                            result.add_error(f"client:{client_id}:{demo_realm}", f"Failed to update client: {update_resp.status_code}")
                    else:
                        result.add_skipped(f"client:{client_id}:{demo_realm}")
                else:
                    create_resp = httpx.post(clients_url, json=client_config, headers=headers, timeout=10.0, verify=settings.KEYCLOAK_VERIFY_TLS)
                    if create_resp.status_code == 201:
                        result.add_created(f"client:{client_id}:{demo_realm}")
                    elif create_resp.status_code == 409:
                        result.add_skipped(f"client:{client_id}:{demo_realm} (exists)")
                    else:
                        result.add_error(f"client:{client_id}:{demo_realm}", f"Failed to create: {create_resp.status_code}")
            
            # Refresh clients map to get IDs for mapper/roles
            clients_response = httpx.get(clients_url, headers=headers, timeout=10.0, verify=settings.KEYCLOAK_VERIFY_TLS)
            clients = clients_response.json() if clients_response.status_code == 200 else []
            client_map = {c.get("clientId"): c for c in clients if c.get("clientId")}
            
            # ------------------------------------------------------------------
            # Ensure roles exist
            # ------------------------------------------------------------------
            demo_roles = [
                {"name": "TENANT_ADMIN", "description": "Demo Tenant Admin"},
                {"name": "SOC_MANAGER", "description": "Security Operations Manager"},
                {"name": "SOC_ANALYST", "description": "Security Operations Analyst"},
                {"name": "VIEW_ONLY", "description": "View only access"},
            ]
            
            for role in demo_roles:
                role_url = f"{self.keycloak_url}/admin/realms/{demo_realm}/roles/{role['name']}"
                role_resp = httpx.get(role_url, headers=headers, timeout=10.0, verify=settings.KEYCLOAK_VERIFY_TLS)
                if role_resp.status_code == 200:
                    result.add_skipped(f"role:{role['name']}:{demo_realm}")
                elif role_resp.status_code == 404:
                    create_role = httpx.post(
                        f"{self.keycloak_url}/admin/realms/{demo_realm}/roles",
                        json=role,
                        headers=headers,
                        timeout=10.0,
                        verify=settings.KEYCLOAK_VERIFY_TLS
                    )
                    if create_role.status_code in [201, 204]:
                        result.add_created(f"role:{role['name']}:{demo_realm}")
                    elif create_role.status_code == 409:
                        result.add_skipped(f"role:{role['name']}:{demo_realm} (exists)")
                    else:
                        result.add_error(f"role:{role['name']}:{demo_realm}", f"Failed to create: {create_role.status_code}")
                else:
                    result.add_error(f"role:{role['name']}:{demo_realm}", f"Failed to fetch: {role_resp.status_code}")
            
            # ------------------------------------------------------------------
            # Ensure tenant_id protocol mapper for web/api clients (helps inject tenant_id claim)
            # ------------------------------------------------------------------
            mapper_template = {
                "name": "tenant-id-mapper",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-attribute-mapper",
                "config": {
                    "user.attribute": "tenant_id",
                    "claim.name": "tenant_id",
                    "jsonType.label": "String",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "userinfo.token.claim": "true",
                    "aggregate.attrs": "false"
                }
            }
            
            for client_id in ["sentinelgrid-web", "sentinelgrid-api"]:
                client = client_map.get(client_id)
                if not client:
                    continue
                mappers_url = f"{self.keycloak_url}/admin/realms/{demo_realm}/clients/{client['id']}/protocol-mappers/models"
                mappers_resp = httpx.get(mappers_url, headers=headers, timeout=10.0, verify=settings.KEYCLOAK_VERIFY_TLS)
                if mappers_resp.status_code != 200:
                    result.add_error(f"protocol_mapper:{client_id}:{demo_realm}", f"Failed to list: {mappers_resp.status_code}")
                    continue
                existing_mappers = mappers_resp.json()
                if any(m.get("name") == "tenant-id-mapper" for m in existing_mappers):
                    result.add_skipped(f"protocol_mapper:{client_id}:{demo_realm}")
                    continue
                create_mapper = httpx.post(mappers_url, json=mapper_template, headers=headers, timeout=10.0, verify=settings.KEYCLOAK_VERIFY_TLS)
                if create_mapper.status_code in [201, 200]:
                    result.add_created(f"protocol_mapper:{client_id}:{demo_realm}")
                elif create_mapper.status_code == 409:
                    result.add_skipped(f"protocol_mapper:{client_id}:{demo_realm} (exists)")
                else:
                    result.add_error(f"protocol_mapper:{client_id}:{demo_realm}", f"Failed to create: {create_mapper.status_code}")
            
            # ------------------------------------------------------------------
            # Seed demo users
            # ------------------------------------------------------------------
            demo_users = [
                ("admin@demo.sentinelgrid.ai", "Demo", "Admin", "TENANT_ADMIN"),
                ("soc.manager@demo.sentinelgrid.ai", "SOC", "Manager", "SOC_MANAGER"),
                ("analyst1@demo.sentinelgrid.ai", "Analyst", "One", "SOC_ANALYST"),
                ("analyst2@demo.sentinelgrid.ai", "Analyst", "Two", "SOC_ANALYST"),
                ("viewer@demo.sentinelgrid.ai", "ReadOnly", "Viewer", "VIEW_ONLY"),
            ]
            
            tenant_id_attr = self._get_default_tenant_id()
            
            for email, first, last, role_name in demo_users:
                user_payload = {
                    "username": email,
                    "email": email,
                    "firstName": first,
                    "lastName": last,
                    "enabled": True,
                    "emailVerified": True,
                    "attributes": {
                        "locale": [self.demo_locale],
                        "timezone": [self.demo_timezone],
                    }
                }
                if tenant_id_attr:
                    user_payload["attributes"]["tenant_id"] = [tenant_id_attr]
                
                users_url = f"{self.keycloak_url}/admin/realms/{demo_realm}/users"
                lookup = httpx.get(
                    users_url,
                    params={"username": email, "exact": "true"},
                    headers=headers,
                    timeout=10.0,
                    verify=settings.KEYCLOAK_VERIFY_TLS
                )
                
                user_id = None
                if lookup.status_code == 200 and lookup.json():
                    user_id = lookup.json()[0].get("id")
                    # Update attributes to keep locale/timezone populated
                    update_resp = httpx.put(
                        f"{users_url}/{user_id}",
                        json=user_payload,
                        headers=headers,
                        timeout=10.0,
                        verify=settings.KEYCLOAK_VERIFY_TLS
                    )
                    if update_resp.status_code not in [204, 200]:
                        logger.warning(f"Could not update user {email}: {update_resp.status_code}")
                    result.add_updated(f"demo_user:{email}")
                else:
                    create_user = httpx.post(
                        users_url,
                        json=user_payload,
                        headers=headers,
                        timeout=10.0,
                        verify=settings.KEYCLOAK_VERIFY_TLS
                    )
                    if create_user.status_code == 201:
                        location = create_user.headers.get("Location", "")
                        if location:
                            user_id = location.split("/")[-1]
                        else:
                            verify = httpx.get(
                                users_url,
                                params={"username": email, "exact": "true"},
                                headers=headers,
                                timeout=10.0,
                                verify=settings.KEYCLOAK_VERIFY_TLS
                            )
                            if verify.status_code == 200 and verify.json():
                                user_id = verify.json()[0].get("id")
                        result.add_created(f"demo_user:{email}")
                    elif create_user.status_code == 409:
                        result.add_skipped(f"demo_user:{email} (exists)")
                    else:
                        result.add_error(f"demo_user:{email}", f"Failed to create: {create_user.status_code}")
                        continue
                
                if not user_id:
                    result.add_error(f"demo_user:{email}", "User ID not found after creation/update")
                    continue
                
                # Set password
                pwd_resp = httpx.put(
                    f"{users_url}/{user_id}/reset-password",
                    json={"type": "password", "value": self.demo_password, "temporary": False},
                    headers=headers,
                    timeout=10.0,
                    verify=settings.KEYCLOAK_VERIFY_TLS
                )
                if pwd_resp.status_code not in [204, 200]:
                    logger.warning(f"Password set failed for {email}: {pwd_resp.status_code}")
                
                # Clear required actions and ensure emailVerified remains true
                user_get = httpx.get(f"{users_url}/{user_id}", headers=headers, timeout=10.0, verify=settings.KEYCLOAK_VERIFY_TLS)
                if user_get.status_code == 200:
                    current_user = user_get.json()
                    current_user["requiredActions"] = []
                    current_user["emailVerified"] = True
                    current_user["enabled"] = True
                    httpx.put(
                        f"{users_url}/{user_id}",
                        json=current_user,
                        headers=headers,
                        timeout=10.0,
                        verify=settings.KEYCLOAK_VERIFY_TLS
                    )
                
                # Assign realm role
                role_url = f"{self.keycloak_url}/admin/realms/{demo_realm}/roles/{role_name}"
                role_resp = httpx.get(role_url, headers=headers, timeout=10.0, verify=settings.KEYCLOAK_VERIFY_TLS)
                if role_resp.status_code == 200:
                    assign_resp = httpx.post(
                        f"{users_url}/{user_id}/role-mappings/realm",
                        json=[role_resp.json()],
                        headers=headers,
                        timeout=10.0,
                        verify=settings.KEYCLOAK_VERIFY_TLS
                    )
                    if assign_resp.status_code not in [204, 200]:
                        logger.warning(f"Role assignment failed for {email}: {assign_resp.status_code}")
                else:
                    logger.warning(f"Role {role_name} not found for demo realm when assigning to {email}")
            
        except Exception as e:
            logger.error(f"Exception seeding demo realm: {e}", exc_info=True)
            result.add_error("demo_realm", str(e))
    
    async def disable_default_admin(self, result: SeedingResult):
        """Disable the default Keycloak admin user in master realm."""
        logger.info("Disabling default Keycloak admin user...")
        
        if self.dry_run:
            result.add_skipped("disable_default_admin (dry-run)")
            return
        
        try:
            # Switch to master realm to disable default admin
            original_realm = self.admin.realm_name
            self.admin.realm_name = "master"
            
            try:
                # Find the default admin user
                admin_users = self.admin.get_users({"username": "admin"})
                
                if admin_users:
                    admin_user = admin_users[0]
                    user_id = admin_user["id"]
                    
                    # Disable the user (already in master realm, realm_name already set to master)
                    self.admin.update_user(
                        user_id,
                        {"enabled": False}
                    )
                    logger.info("Disabled default Keycloak admin user")
                    result.add_updated("default_admin_user (disabled)")
                else:
                    logger.warning("Default admin user not found in master realm")
                    result.add_skipped("default_admin_user (not found)")
                    
            finally:
                # Restore original realm
                self.admin.realm_name = original_realm
                
        except Exception as e:
            logger.warning(f"Failed to disable default admin user: {e}")
            result.add_error("disable_default_admin", str(e))
    
    async def request_keycloak_certificate(self, result: SeedingResult):
        """Request a certificate for Keycloak from the cert service."""
        logger.info("Requesting certificate for Keycloak...")
        
        if self.dry_run:
            result.add_skipped("keycloak_certificate (dry-run)")
            return
        
        try:
            import httpx
            
            cert_service_url = os.getenv("CERT_SERVICE_URL", "http://cert_service:8000")
            internal_token = settings.INTERNAL_SERVICE_TOKEN
            
            # Request certificate for Keycloak
            request_data = {
                "service_id": "keycloak",
                "service_type": "keycloak",
                "subject_cn": "keycloak.sentinelgrid.local",
                "dns_names": ["keycloak", "keycloak.local", "localhost"],
                "ip_addresses": [],
                "ttl_hours": 8760,  # 1 year
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{cert_service_url}/v1/certificates/enroll-service",
                    json=request_data,
                    headers={
                        "Authorization": f"Bearer {internal_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    cert_data = response.json()
                    cert_id = cert_data.get('certificate_id')
                    logger.info(f"Certificate issued for Keycloak: {cert_id}")
                    
                    # Store certificate and key to files for Keycloak to use
                    cert_dir = os.getenv("KEYCLOAK_CERT_DIR", "/opt/keycloak/certs")
                    os.makedirs(cert_dir, mode=0o755, exist_ok=True)
                    
                    # Write certificate
                    cert_file = os.path.join(cert_dir, "tls.crt")
                    with open(cert_file, 'w') as f:
                        f.write(cert_data.get('certificate_pem', ''))
                    os.chmod(cert_file, 0o644)
                    logger.info(f"Certificate written to {cert_file}")
                    
                    # Write private key (if provided)
                    if cert_data.get('private_key_pem'):
                        key_file = os.path.join(cert_dir, "tls.key")
                        with open(key_file, 'w') as f:
                            f.write(cert_data.get('private_key_pem', ''))
                        os.chmod(key_file, 0o600)  # Restrictive permissions for private key
                        logger.info(f"Private key written to {key_file}")
                    
                    # Write CA chain
                    if cert_data.get('ca_chain_pem'):
                        chain_file = os.path.join(cert_dir, "ca-chain.crt")
                        with open(chain_file, 'w') as f:
                            f.write(cert_data.get('ca_chain_pem', ''))
                        os.chmod(chain_file, 0o644)
                        logger.info(f"CA chain written to {chain_file}")
                    
                    result.add_created(f"keycloak_certificate:{cert_id}")
                    logger.info("Keycloak certificate files created. Keycloak container needs to be restarted to use HTTPS.")
                else:
                    logger.warning(f"Failed to request certificate: {response.status_code} - {response.text}")
                    result.add_error("keycloak_certificate", f"HTTP {response.status_code}: {response.text}")
                    
        except Exception as e:
            logger.warning(f"Failed to request Keycloak certificate: {e}")
            result.add_error("keycloak_certificate", str(e))
