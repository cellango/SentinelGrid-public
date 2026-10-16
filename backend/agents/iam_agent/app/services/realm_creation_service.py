"""
Realm Creation Service - Centralized realm creation with enforced standards.

CRITICAL: This service ensures all realms are created with:
1. User Profile configuration (tenant_id attribute) - REQUIRED for Keycloak v25+
2. Standard clients (web, api, iam-agent)
3. Standard roles (TENANT_ADMIN, SOC_MANAGER, SOC_ANALYST, VIEW_ONLY)
4. Protocol mappers for tenant_id
5. Naming convention enforcement

This is a foundational service - all realm creation MUST go through this service.
"""

import logging
import re
from typing import Optional, Dict, Any, List
from enum import Enum

from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError

# Import centralized User Profile configuration
import sys
# Add /app/libs to path for sg_core imports (mounted at /app/libs in container)
libs_path = "/app/libs"
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)
from sg_core.keycloak_user_profile import configure_realm_user_profile

from app.core.config import settings

logger = logging.getLogger(__name__)


class RealmType(str, Enum):
    """Realm type enumeration."""
    PLATFORM_ADMIN = "platform_admin"
    MULTI_TENANT = "multi_tenant"
    DEDICATED_CUSTOMER = "dedicated_customer"
    DEMO = "demo"


class RealmCreationError(Exception):
    """Exception raised when realm creation fails."""
    pass


class RealmNamingError(Exception):
    """Exception raised when realm name doesn't follow conventions."""
    pass


class RealmCreationService:
    """
    Centralized realm creation service with enforced standards.
    
    This service ensures all realms are created with:
    - User Profile configuration (CRITICAL for Keycloak v25+)
    - Standard clients, roles, and protocol mappers
    - Naming convention enforcement
    """
    
    def __init__(self, keycloak_admin: KeycloakAdmin):
        """
        Initialize realm creation service.
        
        Args:
            keycloak_admin: KeycloakAdmin instance (should be authenticated against master realm)
        """
        self.admin = keycloak_admin
        # Prefer the URL used to instantiate the admin client to avoid stale env defaults.
        connection_url = None
        try:
            connection_url = getattr(getattr(keycloak_admin, "connection", None), "server_url", None)
        except Exception:
            connection_url = None
        self.keycloak_url = connection_url or getattr(keycloak_admin, "server_url", None) or settings.KEYCLOAK_URL or "https://localhost:8443"
    
    def create_realm(
        self,
        realm_name: str,
        realm_type: RealmType,
        display_name: Optional[str] = None,
        region: Optional[str] = None,
        shard_number: Optional[int] = None,
        customer_slug: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new realm with all standard configuration.
        
        CRITICAL: This method ensures User Profile is configured before any users are created.
        
        Args:
            realm_name: Name of the realm (must follow naming conventions)
            realm_type: Type of realm (platform_admin, multi_tenant, dedicated_customer, demo)
            display_name: Display name for the realm (defaults to realm_name)
            region: Region code for multi-tenant realms (e.g., "us", "eu")
            shard_number: Shard number for multi-tenant realms (e.g., 1, 2)
            customer_slug: Customer slug for dedicated customer realms
            **kwargs: Additional realm configuration options
        
        Returns:
            Dictionary with realm information:
            {
                "realm_name": str,
                "keycloak_realm_id": str,
                "status": "created" | "exists",
                "user_profile_configured": bool
            }
        
        Raises:
            RealmNamingError: If realm name doesn't follow conventions
            RealmCreationError: If realm creation fails
        """
        # Validate realm name
        self._validate_realm_name(realm_name, realm_type, region, shard_number, customer_slug)
        
        # Check if realm already exists
        try:
            existing_realm = self.admin.get_realm(realm_name)
            logger.info(f"Realm '{realm_name}' already exists")
            
            # Verify User Profile is configured (fail-safe)
            user_profile_configured = self._configure_user_profile(realm_name)
            
            return {
                "realm_name": realm_name,
                "keycloak_realm_id": existing_realm.get("id", ""),
                "status": "exists",
                "user_profile_configured": user_profile_configured
            }
        except KeycloakError as e:
            if "not found" not in str(e).lower():
                raise RealmCreationError(f"Error checking realm existence: {e}")
            # Realm doesn't exist, continue with creation
            pass
        
        # Create realm configuration
        realm_config = self._build_realm_config(
            realm_name,
            realm_type,
            display_name,
            region,
            shard_number,
            **kwargs
        )
        
        try:
            # Create realm
            self.admin.create_realm(realm_config)
            logger.info(f"✅ Created realm: {realm_name}")
            
            # Get realm ID
            realm_info = self.admin.get_realm(realm_name)
            keycloak_realm_id = realm_info.get("id", "")
            
            # CRITICAL: Configure User Profile BEFORE creating any users
            user_profile_configured = self._configure_user_profile(realm_name)
            if not user_profile_configured:
                logger.error(f"⚠️  WARNING: User Profile configuration failed for realm '{realm_name}'")
                logger.error("⚠️  Custom attributes (tenant_id) will NOT persist without User Profile configuration")
                # Don't fail - allow realm creation to continue, but log critical warning
            
            # Switch to new realm for configuration
            original_realm = getattr(self.admin, "realm_name", None)
            if original_realm is not None:
                self.admin.realm_name = realm_name
            
            try:
                # Create standard clients
                self._create_standard_clients(realm_name, realm_type)
                
                # Create standard roles
                self._create_standard_roles(realm_name)
                
                # Create protocol mappers
                self._create_protocol_mappers(realm_name)
                
                logger.info(f"✅ Configured realm '{realm_name}' with clients, roles, and mappers")
            finally:
                # Restore original realm
                if original_realm is not None:
                    self.admin.realm_name = original_realm
            
            return {
                "realm_name": realm_name,
                "keycloak_realm_id": keycloak_realm_id,
                "status": "created",
                "user_profile_configured": user_profile_configured
            }
            
        except KeycloakError as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower() or "409" in error_msg:
                logger.info(f"Realm '{realm_name}' was created concurrently")
                # Realm was created by another process - verify User Profile
                user_profile_configured = self._configure_user_profile(realm_name)
                realm_info = self.admin.get_realm(realm_name)
                return {
                    "realm_name": realm_name,
                    "keycloak_realm_id": realm_info.get("id", ""),
                    "status": "exists",
                    "user_profile_configured": user_profile_configured
                }
            else:
                raise RealmCreationError(f"Failed to create realm '{realm_name}': {e}")
    
    def _validate_realm_name(
        self,
        realm_name: str,
        realm_type: RealmType,
        region: Optional[str] = None,
        shard_number: Optional[int] = None,
        customer_slug: Optional[str] = None
    ) -> None:
        """
        Validate realm name follows naming conventions.
        
        Naming conventions:
        - Platform admin: `sg-admin`
        - Multi-tenant: `sg-mt-{region}-{shard}` (e.g., `sg-mt-us-1`)
        - Dedicated customer: `{customer-slug}` (validated slug)
        - Demo: `demo`
        
        Raises:
            RealmNamingError: If name doesn't follow conventions
        """
        if realm_type == RealmType.PLATFORM_ADMIN:
            if realm_name != "sg-admin":
                raise RealmNamingError(f"Platform admin realm must be named 'sg-admin', got '{realm_name}'")
        
        elif realm_type == RealmType.MULTI_TENANT:
            if not region or shard_number is None:
                raise RealmNamingError(f"Multi-tenant realm requires region and shard_number")
            expected_name = f"sg-mt-{region.lower()}-{shard_number}"
            if realm_name != expected_name:
                raise RealmNamingError(
                    f"Multi-tenant realm name must be '{expected_name}', got '{realm_name}'"
                )
        
        elif realm_type == RealmType.DEDICATED_CUSTOMER:
            if not customer_slug:
                raise RealmNamingError(f"Dedicated customer realm requires customer_slug")
            # Validate slug format (alphanumeric, hyphens, underscores, max 50 chars)
            if not re.match(r'^[a-z0-9]([a-z0-9\-_]*[a-z0-9])?$', customer_slug.lower()):
                raise RealmNamingError(
                    f"Customer slug must be lowercase alphanumeric with hyphens/underscores, got '{customer_slug}'"
                )
            if len(customer_slug) > 50:
                raise RealmNamingError(f"Customer slug must be <= 50 characters, got {len(customer_slug)}")
            if realm_name != customer_slug:
                raise RealmNamingError(
                    f"Dedicated customer realm name must match customer_slug '{customer_slug}', got '{realm_name}'"
                )
        
        elif realm_type == RealmType.DEMO:
            if realm_name != "demo":
                raise RealmNamingError(f"Demo realm must be named 'demo', got '{realm_name}'")
        
        # General validation: realm name must be valid Keycloak realm name
        if not re.match(r'^[a-z0-9]([a-z0-9\-_]*[a-z0-9])?$', realm_name.lower()):
            raise RealmNamingError(
                f"Realm name must be lowercase alphanumeric with hyphens/underscores, got '{realm_name}'"
            )
        
        if len(realm_name) > 63:  # Keycloak limit
            raise RealmNamingError(f"Realm name must be <= 63 characters, got {len(realm_name)}")
    
    def _build_realm_config(
        self,
        realm_name: str,
        realm_type: RealmType,
        display_name: Optional[str] = None,
        region: Optional[str] = None,
        shard_number: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Build realm configuration dictionary."""
        if not display_name:
            if realm_type == RealmType.MULTI_TENANT and region and shard_number is not None:
                display_name = f"SentinelGrid Multi-Tenant ({region.upper()} Shard {shard_number})"
            elif realm_type == RealmType.PLATFORM_ADMIN:
                display_name = "SentinelGrid Platform Admin"
            else:
                display_name = realm_name
        
        # Base configuration
        config = {
            "realm": realm_name,
            "enabled": True,
            "displayName": display_name,
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
        
        # Password policy based on realm type
        if realm_type == RealmType.PLATFORM_ADMIN:
            config["passwordPolicy"] = "length(12) and digits(1) and lowerCase(1) and upperCase(1) and specialChars(1) and notUsername"
        else:
            config["passwordPolicy"] = "length(8) and digits(1) and lowerCase(1) and upperCase(1) and notUsername"
        
        # Apply any additional configuration from kwargs
        config.update(kwargs)
        
        return config
    
    def _configure_user_profile(self, realm_name: str) -> bool:
        """
        Configure User Profile with tenant_id attribute.
        
        CRITICAL: This MUST be done before creating any users in Keycloak v25+
        
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Configuring User Profile for realm '{realm_name}'...")
        
        try:
            # Use centralized User Profile configuration library
            success = configure_realm_user_profile(
                realm_name=realm_name,
                keycloak_url=self.keycloak_url
            )
            
            if success:
                logger.info(f"✅ User Profile configured for realm '{realm_name}'")
            else:
                logger.error(f"❌ User Profile configuration failed for realm '{realm_name}'")
            
            return success
            
        except Exception as e:
            logger.error(f"Error configuring User Profile for realm '{realm_name}': {e}", exc_info=True)
            return False
    
    def _create_standard_clients(self, realm_name: str, realm_type: RealmType) -> None:
        """Create standard clients for realm."""
        clients = []
        
        if realm_type == RealmType.PLATFORM_ADMIN:
            # Platform admin has admin client
            clients.append({
                "clientId": f"{realm_name}-admin",
                "name": "Platform Admin Client",
                "enabled": True,
                "publicClient": False,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": True,
                "serviceAccountsEnabled": True,
                "redirectUris": [],
            })
        else:
            # Standard clients for all other realm types
            clients.extend([
                {
                    "clientId": f"{realm_name}-web",
                    "name": f"{realm_name} Web Client",
                    "enabled": True,
                    "publicClient": True,
                    "standardFlowEnabled": True,
                    "directAccessGrantsEnabled": True,
                    "redirectUris": ["http://localhost:3000/*", "https://*.sentinelgrid.com/*"],
                    "webOrigins": ["+"],
                },
                {
                    "clientId": f"{realm_name}-api",
                    "name": f"{realm_name} API Client",
                    "enabled": True,
                    "publicClient": False,
                    "standardFlowEnabled": True,
                    "directAccessGrantsEnabled": True,
                    "serviceAccountsEnabled": True,
                    "redirectUris": [],
                }
            ])
        
        # IAM Agent client (for all realms)
        clients.append({
            "clientId": "sentinelgrid-iam-agent",
            "name": "SentinelGrid IAM Agent Client",
            "enabled": True,
            "publicClient": False,
            "serviceAccountsEnabled": True,
            "authorizationServicesEnabled": True,
            "directAccessGrantsEnabled": True,
            "redirectUris": [],
        })
        
        # Create clients
        for client_data in clients:
            try:
                self.admin.create_client(client_data)
                logger.info(f"✅ Created client '{client_data['clientId']}' in realm '{realm_name}'")
            except KeycloakError as e:
                error_msg = str(e)
                if "already exists" in error_msg.lower() or "409" in error_msg:
                    logger.info(f"⏭️  Client '{client_data['clientId']}' already exists in realm '{realm_name}'")
                else:
                    logger.warning(f"Failed to create client '{client_data['clientId']}': {e}")
    
    def _create_standard_roles(self, realm_name: str) -> None:
        """Create standard roles for realm."""
        roles = [
            {"name": "TENANT_ADMIN", "description": "Full control over tenant"},
            {"name": "SOC_MANAGER", "description": "Manage incidents, playbooks, team"},
            {"name": "SOC_ANALYST", "description": "View and triage alerts, manage incidents"},
            {"name": "VIEW_ONLY", "description": "Read-only access"},
        ]
        
        for role in roles:
            try:
                self.admin.create_realm_role(role)
                logger.info(f"✅ Created role '{role['name']}' in realm '{realm_name}'")
            except KeycloakError as e:
                error_msg = str(e)
                if "already exists" in error_msg.lower() or "409" in error_msg:
                    logger.info(f"⏭️  Role '{role['name']}' already exists in realm '{realm_name}'")
                else:
                    logger.warning(f"Failed to create role '{role['name']}': {e}")
    
    def _create_protocol_mappers(self, realm_name: str) -> None:
        """Create protocol mappers for tenant_id claim."""
        # Get API client ID
        try:
            clients = self.admin.get_clients()
            api_client = next(
                (c for c in clients if c.get("clientId") == f"{realm_name}-api" or c.get("clientId") == "sentinelgrid-iam-agent"),
                None
            )
            
            if not api_client:
                logger.warning(f"Could not find API client in realm '{realm_name}' for protocol mapper")
                return
            
            client_id = api_client.get("id")
            
            # Check if mapper already exists
            existing_mappers = self.admin.get_mappers_from_client(client_id)
            mapper_names = [m.get("name") for m in existing_mappers]
            
            if "tenant-id-mapper" in mapper_names:
                logger.info(f"⏭️  Protocol mapper 'tenant-id-mapper' already exists in realm '{realm_name}'")
                return
            
            # Create tenant_id mapper
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
            
            self.admin.add_mapper_to_client(client_id, mapper_data)
            logger.info(f"✅ Created protocol mapper 'tenant-id-mapper' in realm '{realm_name}'")
            
        except KeycloakError as e:
            logger.warning(f"Failed to create protocol mapper in realm '{realm_name}': {e}")
