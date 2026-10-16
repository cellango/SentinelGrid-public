"""
Multi-Tenant Realm Manager - Manages shared realms with Keycloak Organizations.
Handles realm selection, capacity management, and organization/group creation.
"""

import logging
from typing import Optional, Dict, Any, List
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class MultiTenantRealmManager:
    """
    Manages multi-tenant realms (sg-mt-*) with Keycloak Organizations support.
    Handles realm selection, capacity tracking, and tenant isolation within shared realms.
    """
    
    # Realm capacity configuration
    DEFAULT_MAX_TENANTS_PER_REALM = 1000
    REALM_CAPACITY_THRESHOLD = 0.85  # 85% utilization triggers warning
    
    def __init__(self, keycloak_admin: KeycloakAdmin, db_session: Session):
        """
        Initialize Multi-Tenant Realm Manager.
        
        Args:
            keycloak_admin: KeycloakAdmin instance (should be using master realm)
            db_session: SQLAlchemy database session
        """
        self.admin = keycloak_admin
        self.db = db_session
        self.supports_organizations = self._check_organizations_support()
    
    def _check_organizations_support(self) -> bool:
        """
        Check if Keycloak version supports Organizations feature.
        Organizations were introduced in Keycloak 25.
        
        Returns:
            True if Organizations are supported, False otherwise
        """
        try:
            # Try to access Organizations API endpoint
            # This is a simple check - in production, you might want to check version
            server_info = self.admin.get_server_info()
            version = server_info.get("systemInfo", {}).get("version", "")
            
            # Extract major version (e.g., "26.0.4" -> 26)
            major_version = int(version.split(".")[0]) if version else 0
            
            supports_orgs = major_version >= 25
            logger.info(f"Keycloak version: {version}, Organizations support: {supports_orgs}")
            return supports_orgs
            
        except Exception as e:
            logger.warning(f"Could not determine Keycloak version, assuming no Organizations support: {e}")
            return False
    
    def get_available_shared_realm(self, region: str = "us") -> str:
        """
        Find an available multi-tenant realm in the specified region.
        If all realms are at capacity, creates a new shard.
        
        Args:
            region: Region code (us, eu, ap, etc.)
        
        Returns:
            Realm name (e.g., "sg-mt-us-1")
        """
        # Query database for available realm in region
        result = self.db.execute(
            text("""
                SELECT realm_name, tenant_count, max_tenants
                FROM realms
                WHERE realm_type = 'multi_tenant'
                AND region = :region
                AND status = 'active'
                AND (max_tenants IS NULL OR tenant_count < max_tenants)
                ORDER BY tenant_count ASC
                LIMIT 1
            """),
            {"region": region}
        ).first()
        
        if result:
            realm_name = result[0]
            logger.info(f"Selected existing realm: {realm_name} ({result[1]}/{result[2]} tenants)")
            return realm_name
        
        # No available realm found - create new shard
        logger.info(f"No available realm in region {region}, creating new shard")
        return self._create_new_shard(region)
    
    def _create_new_shard(self, region: str) -> str:
        """
        Create a new multi-tenant realm shard in the specified region.
        
        Args:
            region: Region code
        
        Returns:
            New realm name
        """
        # Get next shard number for region
        result = self.db.execute(
            text("""
                SELECT COALESCE(MAX(shard_number), 0) + 1
                FROM realms
                WHERE realm_type = 'multi_tenant'
                AND region = :region
            """),
            {"region": region}
        ).scalar()
        
        shard_number = result or 1
        realm_name = f"sg-mt-{region}-{shard_number}"
        
        logger.info(f"Creating new multi-tenant realm shard: {realm_name}")
        
        # Create realm in Keycloak
        success = self.create_multi_tenant_realm(realm_name, region, shard_number)
        
        if not success:
            raise Exception(f"Failed to create realm shard: {realm_name}")
        
        return realm_name
    
    def create_multi_tenant_realm(
        self,
        realm_name: str,
        region: str,
        shard_number: int,
        max_tenants: int = DEFAULT_MAX_TENANTS_PER_REALM
    ) -> bool:
        """
        Create a new multi-tenant realm in Keycloak and register in database.
        
        Args:
            realm_name: Realm name (e.g., "sg-mt-us-1")
            region: Region code
            shard_number: Shard number
            max_tenants: Maximum tenants for this realm
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if realm already exists in Keycloak
            try:
                existing = self.admin.get_realm(realm_name)
                logger.warning(f"Realm {realm_name} already exists in Keycloak")
                keycloak_realm_id = existing.get("id")
            except KeycloakError as e:
                if "not found" not in str(e).lower():
                    raise
                
                # Use centralized realm creation service
                # CRITICAL: This ensures User Profile is configured
                from app.services.realm_creation_service import RealmCreationService, RealmType
                
                service = RealmCreationService(self.admin)
                result = service.create_realm(
                    realm_name=realm_name,
                    realm_type=RealmType.MULTI_TENANT,
                    display_name=f"SentinelGrid Multi-Tenant ({region.upper()} Shard {shard_number})",
                    region=region,
                    shard_number=shard_number
                )
                
                if not result["user_profile_configured"]:
                    logger.error(f"⚠️  CRITICAL: User Profile not configured for {realm_name}")
                    raise Exception(f"User Profile configuration failed for {realm_name}")
                
                logger.info(f"✅ Created realm in Keycloak: {realm_name} (status: {result['status']})")
                
                # Get realm ID
                realm_info = self.admin.get_realm(realm_name)
                keycloak_realm_id = realm_info.get("id")
                
                # Create sentinelgrid-tenant client scope with protocol mappers
                # (This is not handled by RealmCreationService, so we do it here)
                original_realm = self.admin.realm_name
                self.admin.realm_name = realm_name
                try:
                    self._create_tenant_client_scope(realm_name)
                    logger.info(f"✅ Configured client scope for realm {realm_name}")
                finally:
                    self.admin.realm_name = original_realm
            
            # Register realm in database
            self.db.execute(
                text("""
                    INSERT INTO realms (realm_name, realm_type, region, shard_number, max_tenants, status, keycloak_realm_id)
                    VALUES (:realm_name, 'multi_tenant', :region, :shard_number, :max_tenants, 'active', :keycloak_realm_id)
                    ON CONFLICT (realm_name) DO UPDATE
                    SET keycloak_realm_id = :keycloak_realm_id,
                        updated_at = now()
                """),
                {
                    "realm_name": realm_name,
                    "region": region,
                    "shard_number": shard_number,
                    "max_tenants": max_tenants,
                    "keycloak_realm_id": keycloak_realm_id
                }
            )
            self.db.commit()
            
            logger.info(f"✅ Registered realm {realm_name} in database")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create multi-tenant realm {realm_name}: {e}", exc_info=True)
            self.db.rollback()
            return False
    
    def assign_tenant_to_shared_realm(
        self,
        tenant_id: str,
        tenant_slug: str,
        realm_name: str,
        customer_id: str
    ) -> Dict[str, Any]:
        """
        Assign a tenant to a shared realm by creating an Organization or Group.
        
        Args:
            tenant_id: Tenant UUID
            tenant_slug: Tenant slug (for org/group name)
            realm_name: Target realm name
            customer_id: Customer UUID
        
        Returns:
            Dict with org_id or group_id
        """
        if self.supports_organizations:
            return self._create_keycloak_organization(realm_name, tenant_id, tenant_slug)
        else:
            return self._create_keycloak_group(realm_name, tenant_id, tenant_slug)
    
    def _create_keycloak_organization(
        self,
        realm_name: str,
        tenant_id: str,
        tenant_slug: str
    ) -> Dict[str, Any]:
        """
        Create a Keycloak Organization for tenant isolation.
        Requires Keycloak 25+.
        
        Args:
            realm_name: Realm name
            tenant_id: Tenant UUID
            tenant_slug: Tenant slug
        
        Returns:
            Dict with keycloak_org_id
        """
        try:
            # Switch to target realm
            original_realm = getattr(self.admin, "realm_name", None)
            setattr(self.admin, "realm_name", realm_name)
            
            try:
                # Create organization using Keycloak Organizations API
                # Note: python-keycloak may not have Organizations support yet
                # We'll use raw API calls
                org_data = {
                    "name": tenant_slug,
                    "displayName": tenant_slug.replace("-", " ").title(),
                    "enabled": True,
                    "attributes": {
                        "tenant_id": [tenant_id],
                        "tenant_slug": [tenant_slug]
                    }
                }
                
                # Use raw connection to call Organizations API
                # This is a placeholder - actual implementation depends on KC version
                connection = self.admin.connection
                url = f"{connection.base_url}/admin/realms/{realm_name}/organizations"
                
                response = connection.raw_post(url, data=org_data)
                org_id = response.get("id")
                
                logger.info(f"✅ Created Keycloak Organization: {tenant_slug} (ID: {org_id})")
                
                return {
                    "keycloak_org_id": org_id,
                    "keycloak_group_id": None
                }
                
            except Exception as e:
                logger.warning(f"Failed to create Organization (falling back to groups): {e}")
                # Fallback to groups
                return self._create_keycloak_group(realm_name, tenant_id, tenant_slug)
            finally:
                setattr(self.admin, "realm_name", original_realm)
                
        except Exception as e:
            logger.error(f"❌ Failed to create organization for tenant {tenant_slug}: {e}")
            raise
    
    def _create_keycloak_group(
        self,
        realm_name: str,
        tenant_id: str,
        tenant_slug: str
    ) -> Dict[str, Any]:
        """
        Create a Keycloak Group for tenant isolation (fallback if Organizations not supported).
        
        Args:
            realm_name: Realm name
            tenant_id: Tenant UUID
            tenant_slug: Tenant slug
        
        Returns:
            Dict with keycloak_group_id
        """
        try:
            # Switch to target realm
            original_realm = getattr(self.admin, "realm_name", None)
            setattr(self.admin, "realm_name", realm_name)
            
            try:
                # Create parent group "/tenants" if it doesn't exist
                parent_group_id = self._ensure_tenants_parent_group(realm_name)
                
                # Create tenant group
                group_data = {
                    "name": tenant_slug,
                    "attributes": {
                        "tenant_id": [tenant_id],
                        "tenant_slug": [tenant_slug]
                    }
                }
                
                group_id = self.admin.create_group(group_data, parent=parent_group_id)
                logger.info(f"✅ Created Keycloak Group: /tenants/{tenant_slug} (ID: {group_id})")
                
                return {
                    "keycloak_org_id": None,
                    "keycloak_group_id": group_id
                }
                
            finally:
                setattr(self.admin, "realm_name", original_realm)
                
        except Exception as e:
            logger.error(f"❌ Failed to create group for tenant {tenant_slug}: {e}")
            raise
    
    def _ensure_tenants_parent_group(self, realm_name: str) -> str:
        """
        Ensure /tenants parent group exists in realm.
        
        Args:
            realm_name: Realm name
        
        Returns:
            Parent group ID
        """
        try:
            # Check if /tenants group exists
            groups = self.admin.get_groups({"search": "tenants"})
            for group in groups:
                if group.get("name") == "tenants" and group.get("path") == "/tenants":
                    return group.get("id")
            
            # Create /tenants group
            group_data = {
                "name": "tenants",
                "attributes": {
                    "description": ["Parent group for all tenant groups in shared realm"]
                }
            }
            
            group_id = self.admin.create_group(group_data)
            logger.info(f"✅ Created /tenants parent group in realm {realm_name}")
            return group_id
            
        except Exception as e:
            logger.error(f"Failed to ensure /tenants parent group: {e}")
            raise
    
    def _create_realm_clients(self, realm_name: str):
        """Create standard clients for realm."""
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
                clients = self.admin.get_clients(query={"clientId": client_id})
                if clients:
                    logger.info(f"⏭️  Client '{client_id}' already exists")
                    continue
                
                self.admin.create_client(client_data, realm_name=realm_name)
                logger.info(f"✅ Created client '{client_id}'")
            except KeycloakError as e:
                logger.error(f"❌ Error creating client '{client_id}': {e}")
                raise
    
    def _create_realm_roles(self, realm_name: str):
        """Create standard roles for realm."""
        roles_to_create = [
            {"name": "TENANT_ADMIN", "description": "Full control over tenant"},
            {"name": "SOC_MANAGER", "description": "Manage incidents, playbooks, team"},
            {"name": "SOC_ANALYST", "description": "View and triage alerts, manage incidents"},
            {"name": "VIEW_ONLY", "description": "Read-only access"},
        ]
        
        for role_data in roles_to_create:
            role_name = role_data["name"]
            try:
                try:
                    self.admin.get_realm_role(role_name, realm_name=realm_name)
                    logger.info(f"⏭️  Role '{role_name}' already exists")
                    continue
                except KeycloakError as e:
                    if "not found" not in str(e).lower():
                        raise
                
                self.admin.create_realm_role(role_data, realm_name=realm_name)
                logger.info(f"✅ Created role '{role_name}'")
            except KeycloakError as e:
                logger.error(f"❌ Error creating role '{role_name}': {e}")
                raise
    
    def _create_tenant_client_scope(self, realm_name: str):
        """
        Create sentinelgrid-tenant client scope with protocol mappers for sg.* claims.
        This scope will be attached to all clients to inject tenant information into tokens.
        """
        try:
            # Check if scope already exists
            scopes = self.admin.get_client_scopes()
            for scope in scopes:
                if scope.get("name") == "sentinelgrid-tenant":
                    logger.info(f"⏭️  Client scope 'sentinelgrid-tenant' already exists")
                    return
            
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
            
            # Add protocol mappers to scope
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
            
            for mapper in mappers:
                self.admin.add_mapper_to_client_scope(scope_id, mapper)
                logger.info(f"✅ Added mapper '{mapper['name']}' to client scope")
            
            # Attach scope to all clients
            clients = self.admin.get_clients()
            for client in clients:
                client_id = client.get("id")
                try:
                    self.admin.add_default_client_scope(client_id, scope_id, realm_name=realm_name)
                    logger.info(f"✅ Attached scope to client '{client.get('clientId')}'")
                except Exception as e:
                    logger.warning(f"Could not attach scope to client '{client.get('clientId')}': {e}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create tenant client scope: {e}")
            raise
    
    def get_realm_status(self, realm_name: str) -> Dict[str, Any]:
        """
        Get status and capacity information for a realm.
        
        Args:
            realm_name: Realm name
        
        Returns:
            Dict with realm status information
        """
        result = self.db.execute(
            text("""
                SELECT 
                    realm_name,
                    realm_type,
                    region,
                    shard_number,
                    tenant_count,
                    max_tenants,
                    CASE 
                        WHEN max_tenants IS NULL THEN NULL
                        ELSE ROUND((tenant_count::NUMERIC / max_tenants::NUMERIC) * 100, 2)
                    END AS utilization_percent,
                    status
                FROM realms
                WHERE realm_name = :realm_name
            """),
            {"realm_name": realm_name}
        ).first()
        
        if not result:
            return None
        
        return {
            "realm_name": result[0],
            "realm_type": result[1],
            "region": result[2],
            "shard_number": result[3],
            "tenant_count": result[4],
            "max_tenants": result[5],
            "utilization_percent": float(result[6]) if result[6] else None,
            "status": result[7]
        }
    
    def list_realms_by_region(self, region: str) -> List[Dict[str, Any]]:
        """
        List all realms in a specific region.
        
        Args:
            region: Region code
        
        Returns:
            List of realm status dicts
        """
        results = self.db.execute(
            text("""
                SELECT 
                    realm_name,
                    realm_type,
                    region,
                    shard_number,
                    tenant_count,
                    max_tenants,
                    status
                FROM realms
                WHERE region = :region
                ORDER BY realm_type, shard_number
            """),
            {"region": region}
        ).fetchall()
        
        return [
            {
                "realm_name": r[0],
                "realm_type": r[1],
                "region": r[2],
                "shard_number": r[3],
                "tenant_count": r[4],
                "max_tenants": r[5],
                "status": r[6]
            }
            for r in results
        ]
