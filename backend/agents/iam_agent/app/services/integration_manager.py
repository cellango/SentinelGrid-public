"""
Integration Manager Service
Manages integrations with external systems (Active Directory, Okta, etc.)
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

from app.services.keycloak_client import KeycloakClient
from app.services.connector_framework import ConnectorFactory, SyncDirection

logger = logging.getLogger(__name__)


class IntegrationType(str, Enum):
    """Types of integrations."""
    ACTIVE_DIRECTORY = "active_directory"
    AZURE_AD = "azure_ad"
    OKTA = "okta"
    GOOGLE_WORKSPACE = "google_workspace"
    AWS_IAM = "aws_iam"
    GITHUB = "github"
    CUSTOM = "custom"


class IntegrationStatus(str, Enum):
    """Integration status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    SYNCING = "syncing"


class IntegrationManager:
    """Service for managing external system integrations."""
    
    def __init__(self, keycloak_client: KeycloakClient):
        self.keycloak_client = keycloak_client
    
    def create_active_directory_integration(
        self,
        name: str,
        domain: str,
        ldap_url: str,
        bind_dn: str,
        bind_password: str,
        users_dn: str,
        tenant_id: Optional[str] = None,
        sync_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create Active Directory integration.
        
        This creates an LDAP user federation with Active Directory-specific settings.
        """
        try:
            from app.services.protocol_manager import ProtocolManager
            protocol_manager = ProtocolManager(self.keycloak_client)
            
            # Configure LDAP with Active Directory vendor settings
            ad_config = {
                "vendor": "active_directory",
                "username_attribute": "sAMAccountName",
                "rdn_attribute": "sAMAccountName",
                "uuid_attribute": "objectGUID",
                "user_object_classes": "person, organizationalPerson, user"
            }
            
            if sync_config:
                ad_config.update(sync_config)
            
            ldap_result = protocol_manager.configure_ldap_federation(
                provider_name=name,
                connection_url=ldap_url,
                bind_dn=bind_dn,
                bind_credential=bind_password,
                users_dn=users_dn,
                tenant_id=tenant_id,
                config=ad_config
            )
            
            # Store integration metadata
            integration = {
                "integration_id": self._generate_integration_id(),
                "name": name,
                "type": IntegrationType.ACTIVE_DIRECTORY.value,
                "status": IntegrationStatus.ACTIVE.value,
                "domain": domain,
                "ldap_config_id": ldap_result.get("provider_name"),
                "tenant_id": tenant_id,
                "sync_enabled": sync_config.get("sync_enabled", True) if sync_config else True,
                "sync_schedule": sync_config.get("sync_schedule", "0 0 * * *") if sync_config else "0 0 * * *",
                "created_at": datetime.utcnow().isoformat()
            }
            
            # TODO: Store in database
            
            return integration
            
        except Exception as e:
            logger.error(f"Error creating Active Directory integration: {e}")
            raise
    
    def create_azure_ad_integration(
        self,
        name: str,
        tenant_id_azure: str,
        client_id: str,
        client_secret: str,
        tenant_id: Optional[str] = None,
        sync_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create Azure AD integration.
        
        Azure AD can be integrated via:
        - SAML 2.0 identity provider
        - SCIM 2.0 for provisioning
        - OIDC
        """
        try:
            from app.services.protocol_manager import ProtocolManager
            protocol_manager = ProtocolManager(self.keycloak_client)
            
            # Configure Azure AD as SAML identity provider
            entity_id = f"https://sts.windows.net/{tenant_id_azure}/"
            sso_url = f"https://login.microsoftonline.com/{tenant_id_azure}/saml2"
            
            # Get Azure AD certificate (would need to be fetched from metadata)
            certificate = sync_config.get("certificate") if sync_config else None
            
            if certificate:
                saml_result = protocol_manager.configure_saml_identity_provider(
                    alias=f"azure-ad-{tenant_id_azure}",
                    entity_id=entity_id,
                    sso_url=sso_url,
                    certificate=certificate,
                    tenant_id=tenant_id,
                    config={
                        "name_id_format": "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"
                    }
                )
            
            integration = {
                "integration_id": self._generate_integration_id(),
                "name": name,
                "type": IntegrationType.AZURE_AD.value,
                "status": IntegrationStatus.ACTIVE.value,
                "azure_tenant_id": tenant_id_azure,
                "client_id": client_id,
                "tenant_id": tenant_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # TODO: Store in database
            
            return integration
            
        except Exception as e:
            logger.error(f"Error creating Azure AD integration: {e}")
            raise
    
    def create_okta_integration(
        self,
        name: str,
        okta_domain: str,
        client_id: str,
        client_secret: str,
        tenant_id: Optional[str] = None,
        sync_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create Okta integration.
        
        Okta can be integrated via SAML or OIDC.
        """
        try:
            from app.services.protocol_manager import ProtocolManager
            protocol_manager = ProtocolManager(self.keycloak_client)
            
            # Configure Okta as OIDC identity provider
            # Or use SAML if preferred
            
            integration = {
                "integration_id": self._generate_integration_id(),
                "name": name,
                "type": IntegrationType.OKTA.value,
                "status": IntegrationStatus.ACTIVE.value,
                "okta_domain": okta_domain,
                "client_id": client_id,
                "tenant_id": tenant_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # TODO: Store in database and configure OIDC provider
            
            return integration
            
        except Exception as e:
            logger.error(f"Error creating Okta integration: {e}")
            raise
    
    def sync_integration(
        self,
        integration_id: str,
        sync_type: str = "full",
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Trigger a sync for an integration.
        
        Sync types:
        - full: Full sync of users and groups
        - incremental: Sync only changes since last sync
        - users: Sync only users
        - groups: Sync only groups
        """
        try:
            # Get integration configuration
            integration = self.get_integration(integration_id, tenant_id)
            if not integration:
                raise ValueError(f"Integration {integration_id} not found")
            
            integration_type = IntegrationType(integration["type"])
            
            # Use connector framework
            connector_type = integration["type"]
            try:
                connector = ConnectorFactory.create(connector_type, integration)
                
                # Determine sync direction
                direction = SyncDirection.IMPORT  # Default to import
                if sync_type == "export":
                    direction = SyncDirection.EXPORT
                elif sync_type == "bidirectional":
                    direction = SyncDirection.BIDIRECTIONAL
                
                # Execute sync
                if sync_type in ["full", "users"]:
                    users_result = connector.sync_users(direction)
                else:
                    users_result = {"status": "skipped"}
                
                if sync_type in ["full", "groups"]:
                    groups_result = connector.sync_groups(direction)
                else:
                    groups_result = {"status": "skipped"}
                
                sync_result = {
                    "users": users_result,
                    "groups": groups_result
                }
                
            except ValueError as e:
                # Connector type not found, fallback to old method
                logger.warning(f"Connector not found, using legacy sync: {e}")
                if integration_type == IntegrationType.ACTIVE_DIRECTORY:
                    sync_result = self._sync_ldap_users(integration)
                elif integration_type == IntegrationType.AZURE_AD:
                    sync_result = self._sync_azure_ad_users(integration)
                else:
                    sync_result = {"status": "not_implemented"}
            
            return {
                "integration_id": integration_id,
                "sync_type": sync_type,
                "status": "completed",
                "synced_at": datetime.utcnow().isoformat(),
                "result": sync_result
            }
            
        except Exception as e:
            logger.error(f"Error syncing integration: {e}")
            raise
    
    def list_integrations(
        self,
        integration_type: Optional[IntegrationType] = None,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all integrations, optionally filtered by type."""
        # TODO: Fetch from database
        integrations = []
        return integrations
    
    def get_integration(
        self,
        integration_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get a specific integration."""
        # TODO: Fetch from database
        return None
    
    def update_integration(
        self,
        integration_id: str,
        updates: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update an integration."""
        # TODO: Implement update
        return {
            "integration_id": integration_id,
            "status": "updated",
            "updated_at": datetime.utcnow().isoformat()
        }
    
    def delete_integration(
        self,
        integration_id: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete an integration."""
        # TODO: Implement delete
        return {
            "integration_id": integration_id,
            "status": "deleted",
            "deleted_at": datetime.utcnow().isoformat()
        }
    
    def test_integration_connection(
        self,
        integration_id: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Test connection to an integration."""
        try:
            integration = self.get_integration(integration_id, tenant_id)
            if not integration:
                raise ValueError(f"Integration {integration_id} not found")
            
            # Test connection based on integration type
            integration_type = IntegrationType(integration["type"])
            
            if integration_type == IntegrationType.ACTIVE_DIRECTORY:
                # Test LDAP connection
                result = self._test_ldap_connection(integration)
            else:
                result = {"status": "not_implemented"}
            
            return {
                "integration_id": integration_id,
                "status": result.get("status", "unknown"),
                "tested_at": datetime.utcnow().isoformat(),
                "details": result
            }
            
        except Exception as e:
            logger.error(f"Error testing integration: {e}")
            return {
                "integration_id": integration_id,
                "status": "failed",
                "error": str(e),
                "tested_at": datetime.utcnow().isoformat()
            }
    
    def _sync_ldap_users(self, integration: Dict[str, Any]) -> Dict[str, Any]:
        """Sync LDAP/AD users."""
        # TODO: Implement LDAP sync via Keycloak Admin API
        return {
            "users_synced": 0,
            "groups_synced": 0
        }
    
    def _sync_azure_ad_users(self, integration: Dict[str, Any]) -> Dict[str, Any]:
        """Sync Azure AD users."""
        # TODO: Implement Azure AD sync
        return {
            "users_synced": 0,
            "groups_synced": 0
        }
    
    def _test_ldap_connection(self, integration: Dict[str, Any]) -> Dict[str, Any]:
        """Test LDAP connection."""
        # TODO: Implement LDAP connection test
        return {
            "status": "connected"
        }
    
    def _generate_integration_id(self) -> str:
        """Generate a unique integration ID."""
        return f"int-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{id(self)}"

