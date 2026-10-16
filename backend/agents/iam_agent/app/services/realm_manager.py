"""
Realm Manager - Handles realm creation and management for hybrid architecture.
Manages both shared and dedicated realms based on pricing tier.
"""

import logging
import uuid
from typing import Optional, Dict, Any
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError

from .pricing_service import PricingService
from .security import SecurityService
from .realm_creation_service import RealmCreationService, RealmType, RealmCreationError, RealmNamingError

logger = logging.getLogger(__name__)


class RealmManager:
    """
    Manages Keycloak realms for hybrid architecture.
    Handles realm creation, client setup, role creation, and protocol mappers.
    """
    
    def __init__(self, keycloak_admin: KeycloakAdmin):
        """
        Initialize Realm Manager.
        
        Args:
            keycloak_admin: KeycloakAdmin instance (should be using master realm)
        """
        self.admin = keycloak_admin
        self.pricing = PricingService

    def _generate_customer_slug(self, name: str) -> str:
        """Generate a safe customer slug from name (fallback for legacy tests)."""
        slug = (name or "customer").strip().lower().replace(" ", "-")
        return slug or "customer"
    
    def get_realm_for_customer(
        self,
        customer_id: str,
        customer_data: Dict[str, Any]
    ) -> str:
        """
        Get realm name for customer (handles both shared and dedicated).
        
        Args:
            customer_id: Customer UUID
            customer_data: Customer data dictionary with pricing_tier, user_count, etc.
        
        Returns:
            Realm name (either "sentinelgrid" for shared or dedicated realm name)
        """
        # Check if customer has dedicated realm
        if customer_data.get("has_dedicated_realm"):
            realm_name = customer_data.get("realm_name")
            if realm_name:
                return realm_name
        
        # Determine if customer should have dedicated realm
        pricing_tier = customer_data.get("pricing_tier", "starter")
        user_count = customer_data.get("user_count", 0)
        org_count = customer_data.get("org_count", 0)
        
        strategy = PricingService.get_realm_strategy(pricing_tier, user_count, org_count)
        
        if strategy == "dedicated":
            # Auto-upgrade to dedicated realm
            realm_name = self._generate_realm_name(customer_data.get("name", "customer"))
            return realm_name
        
        # Default: shared realm
        return "sentinelgrid"
    
    def get_realm_for_org(self, org_id: str, org_data: Dict[str, Any]) -> str:
        """
        Get realm name for org (always dedicated realm).
        
        Args:
            org_id: Organization UUID
            org_data: Organization data dictionary
        
        Returns:
            Realm name (always dedicated for orgs)
        """
        return org_data.get("realm_name", "sentinelgrid")
    
    async def create_dedicated_realm(
        self,
        realm_name: str,
        customer_data: Dict[str, Any],
        organization_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create a dedicated realm in Keycloak.
        
        Args:
            realm_name: Name of the realm to create
            customer_data: Customer data dictionary
            organization_data: Optional organization data
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if realm already exists
            try:
                existing = self.admin.get_realm(realm_name)
                logger.warning(f"Realm {realm_name} already exists, skipping creation")
                return True
            except KeycloakError as e:
                if "not found" not in str(e).lower():
                    raise  # Re-raise if it's another error
                pass  # Realm doesn't exist, create it
            
            # Create realm configuration
            realm_config = {
                "realm": realm_name,
                "enabled": True,
                "displayName": customer_data.get("name", realm_name),
                "loginWithEmailAllowed": True,
                "duplicateEmailsAllowed": False,
                "resetPasswordAllowed": True,
                "editUsernameAllowed": False,
                "bruteForceProtected": True,
                "rememberMe": True,
                "verifyEmail": False,
                "accessTokenLifespan": 3600,
                "ssoSessionIdleTimeout": 1800,
                # Security settings
                "passwordPolicy": "length(8) and digits(1) and lowerCase(1) and upperCase(1) and notUsername",
                "otpPolicyType": "totp",
                "otpPolicyAlgorithm": "HmacSHA1",
                "otpPolicyInitialCounter": 0,
                "otpPolicyDigits": 6,
                "otpPolicyLookAheadWindow": 1,
                "otpPolicyPeriod": 30,
            }
            
            # Use centralized realm creation service
            # CRITICAL: This ensures User Profile is configured
            service = RealmCreationService(self.admin)
            
            # Generate customer slug from customer name
            customer_slug = self._generate_customer_slug(customer_data.get("name", realm_name))
            
            result = service.create_realm(
                realm_name=realm_name,
                realm_type=RealmType.DEDICATED_CUSTOMER,
                display_name=customer_data.get("name", realm_name),
                customer_slug=customer_slug
            )
            
            if not result["user_profile_configured"]:
                logger.error(f"⚠️  CRITICAL: User Profile not configured for {realm_name}")
                return False
            
            logger.info(f"✅ Created dedicated realm: {realm_name} (status: {result['status']})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create realm {realm_name}: {e}", exc_info=True)
            return False
    
    def _generate_realm_name(self, customer_name: str) -> str:
        """
        Generate enterprise realm name from customer name.
        Follows naming convention: sg-ent-{slug}
        
        Args:
            customer_name: Customer company name
        
        Returns:
            Sanitized realm name following sg-ent-* convention
        """
        # Sanitize and create slug
        slug = customer_name.lower().replace(" ", "-").replace("_", "-")
        # Remove special characters
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        # Remove consecutive dashes
        while "--" in slug:
            slug = slug.replace("--", "-")
        # Remove leading/trailing dashes
        slug = slug.strip("-")
        # Truncate if too long (max 50 chars for slug part)
        if len(slug) > 50:
            slug = slug[:50].rstrip("-")
        # Follow naming convention: sg-ent-{slug}
        return f"sg-ent-{slug}"
    
    def _create_realm_clients(self, realm_name: str):
        """Create clients for realm with realm-specific naming."""
        clients_to_create = [
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
                "clientId": f"{realm_name}-frontend",
                "name": f"{realm_name} Frontend Client",
                "enabled": True,
                "publicClient": True,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": True,
                "redirectUris": ["http://localhost:3001/*", "https://app.sentinelgrid.com/*"],
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
        
        for client_data in clients_to_create:
            client_id = client_data["clientId"]
            try:
                # Check if client exists
                clients = self.admin.get_clients(query={"clientId": client_id})
                if clients:
                    logger.info(f"⏭️  Client '{client_id}' already exists in realm {realm_name}")
                    continue
                
                # Create client
                self.admin.create_client(client_data, realm_name=realm_name)
                logger.info(f"✅ Created client '{client_id}' in realm {realm_name}")
            except KeycloakError as e:
                logger.error(f"❌ Error creating client '{client_id}': {e}")
                raise
    
    def _create_realm_roles(self, realm_name: str):
        """Create roles for realm (same structure as seeder)."""
        roles_to_create = [
            {"name": "TENANT_ADMIN", "description": "Full control over tenant"},
            {"name": "SOC_MANAGER", "description": "Manage incidents, playbooks, team"},
            {"name": "SOC_ANALYST", "description": "View and triage alerts, manage incidents"},
            {"name": "VIEW_ONLY", "description": "Read-only access"},
        ]
        
        for role_data in roles_to_create:
            role_name = role_data["name"]
            try:
                # Check if role exists
                try:
                    self.admin.get_realm_role(role_name, realm_name=realm_name)
                    logger.info(f"⏭️  Role '{role_name}' already exists in realm {realm_name}")
                    continue
                except KeycloakError as e:
                    if "not found" not in str(e).lower():
                        raise
                
                # Create role
                self.admin.create_realm_role(role_data, realm_name=realm_name)
                logger.info(f"✅ Created role '{role_name}' in realm {realm_name}")
            except KeycloakError as e:
                logger.error(f"❌ Error creating role '{role_name}': {e}")
                raise
    
    def _create_protocol_mapper(self, realm_name: str):
        """
        Create sentinelgrid-tenant client scope with sg.* nested claims.
        This replaces the old flat tenant_id mapper with proper nested structure.
        """
        try:
            # Check if scope already exists
            scopes = self.admin.get_client_scopes()
            scope_id = None
            for scope in scopes:
                if scope.get("name") == "sentinelgrid-tenant":
                    logger.info(f"⏭️  Client scope 'sentinelgrid-tenant' already exists")
                    scope_id = scope.get("id")
                    break
            
            if not scope_id:
                # Create client scope
                scope_data = {
                    "name": "sentinelgrid-tenant",
                    "description": "SentinelGrid tenant information claims",
                    "protocol": "openid-connect",
                    "attributes": {
                        "include.in.token.scope": "true",
                        "display.on.consent.screen": "false"
                    }
                }
                
                scope_id = self.admin.create_client_scope(scope_data, realm_name=realm_name)
                logger.info(f"✅ Created client scope 'sentinelgrid-tenant'")
            
            # Add protocol mappers to scope (sg.* nested claims)
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
            
            # Get existing mappers to avoid duplicates
            existing_mappers = self.admin.get_mappers_from_client_scope(scope_id)
            existing_mapper_names = {m.get("name") for m in existing_mappers}
            
            for mapper in mappers:
                if mapper["name"] not in existing_mapper_names:
                    self.admin.add_mapper_to_client_scope(scope_id, mapper)
                    logger.info(f"✅ Added mapper '{mapper['name']}' to client scope")
                else:
                    logger.info(f"⏭️  Mapper '{mapper['name']}' already exists")
            
            # Attach scope to all clients in realm
            clients = self.admin.get_clients()
            for client in clients:
                client_id = client.get("id")
                client_name = client.get("clientId")
                try:
                    # Check if scope is already attached
                    default_scopes = self.admin.get_default_client_scopes(client_id)
                    if any(s.get("name") == "sentinelgrid-tenant" for s in default_scopes):
                        logger.info(f"⏭️  Scope already attached to client '{client_name}'")
                        continue
                    
                    self.admin.add_default_client_scope(client_id, scope_id, realm_name=realm_name)
                    logger.info(f"✅ Attached scope to client '{client_name}'")
                except Exception as e:
                    logger.warning(f"Could not attach scope to client '{client_name}': {e}")
            
        except KeycloakError as e:
            logger.error(f"❌ Error creating protocol mapper: {e}")
            raise
