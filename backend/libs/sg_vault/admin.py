"""
Vault Admin Service - Administrative operations for Vault management.
Handles tenant provisioning, policy creation, and secrets engine configuration.
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import hvac
from hvac.exceptions import VaultError

logger = logging.getLogger(__name__)


class VaultAdminService:
    """
    Administrative service for HashiCorp Vault.
    
    Used for:
    - Provisioning new tenants
    - Creating policies
    - Enabling secrets engines
    - Managing access
    """
    
    def __init__(self, url: str, token: str, verify: bool = False):
        """
        Initialize Vault admin service.
        
        Args:
            url: Vault server URL
            token: Root or admin token
            verify: Verify SSL certificates
        """
        self.url = url
        self.client = hvac.Client(url=url, token=token, verify=verify)
        
        if not self.client.is_authenticated():
            raise ValueError("Failed to authenticate with Vault")
        
        logger.info("Vault admin service initialized")
    
    # ========================================================================
    # Tenant Provisioning
    # ========================================================================
    
    def provision_tenant(
        self,
        tenant_id: str,
        org_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        features: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Provision complete Vault setup for new tenant.
        
        Args:
            tenant_id: Tenant UUID
            org_id: Organization UUID
            customer_id: Customer UUID
            features: List of features to enable ["kv", "transit", "database", "pki"]
        
        Returns:
            Dict with entity_id, policy_name, token, paths_created
        """
        features = features or ["kv", "transit"]
        
        logger.info(f"Provisioning Vault for tenant: {tenant_id}")
        
        try:
            # 1. Create entity
            entity_id = self.create_tenant_entity(
                tenant_id=tenant_id,
                org_id=org_id,
                customer_id=customer_id
            )
            
            # 2. Create policy
            policy_name = self.create_tenant_policy(
                tenant_id=tenant_id,
                org_id=org_id,
                customer_id=customer_id
            )
            
            # 3. Enable secrets engines
            paths_created = []
            
            if "kv" in features:
                self.enable_kv_for_tenant(tenant_id)
                paths_created.append(f"tenants/{tenant_id}/kv")
            
            if "transit" in features:
                self.create_encryption_key(tenant_id)
                paths_created.append(f"transit/keys/{tenant_id}")
            
            if "database" in features:
                self.configure_database_for_tenant(tenant_id)
                paths_created.append(f"database/roles/{tenant_id}-*")
            
            if "pki" in features:
                self.setup_pki_for_tenant(tenant_id)
                paths_created.append(f"pki_{tenant_id}")
            
            # 4. Generate token
            token = self.create_tenant_token(
                tenant_id=tenant_id,
                entity_id=entity_id,
                policy_name=policy_name
            )
            
            logger.info(f"✅ Vault provisioned for tenant: {tenant_id}")
            
            return {
                "entity_id": entity_id,
                "policy_name": policy_name,
                "token": token,
                "token_accessor": self.client.lookup_token()["data"]["accessor"],
                "paths_created": paths_created,
                "features_enabled": features
            }
            
        except Exception as e:
            logger.error(f"Failed to provision Vault for tenant {tenant_id}: {e}")
            raise
    
    # ========================================================================
    # Entity Management
    # ========================================================================
    
    def create_tenant_entity(
        self,
        tenant_id: str,
        org_id: Optional[str] = None,
        customer_id: Optional[str] = None
    ) -> str:
        """
        Create Vault entity for tenant with metadata.
        
        Args:
            tenant_id: Tenant UUID
            org_id: Organization UUID
            customer_id: Customer UUID
        
        Returns:
            Entity ID
        """
        metadata = {"tenant_id": tenant_id}
        if org_id:
            metadata["org_id"] = org_id
        if customer_id:
            metadata["customer_id"] = customer_id
        
        try:
            response = self.client.secrets.identity.create_or_update_entity(
                name=f"tenant-{tenant_id}",
                metadata=metadata
            )
            entity_id = response["data"]["id"]
            logger.info(f"Created Vault entity: {entity_id}")
            return entity_id
        except VaultError as e:
            logger.error(f"Failed to create entity: {e}")
            raise
    
    # ========================================================================
    # Policy Management
    # ========================================================================
    
    def create_tenant_policy(
        self,
        tenant_id: str,
        org_id: Optional[str] = None,
        customer_id: Optional[str] = None
    ) -> str:
        """
        Create tenant-specific Vault policy from template.
        
        Args:
            tenant_id: Tenant UUID
            org_id: Organization UUID
            customer_id: Customer UUID
        
        Returns:
            Policy name
        """
        policy_name = f"tenant-{tenant_id}-policy"
        
        # Load policy template
        template_path = Path(__file__).parent.parent.parent.parent / "infra" / "vault" / "policies" / "tenant-policy-template.hcl"
        
        try:
            with open(template_path, "r") as f:
                template = f.read()
        except FileNotFoundError:
            logger.warning(f"Policy template not found, using inline template")
            template = self._get_inline_policy_template()
        
        # Replace placeholders
        policy_content = template.replace("{{TENANT_ID}}", tenant_id)
        if org_id:
            policy_content = policy_content.replace("{{ORG_ID}}", org_id)
        else:
            # Remove org-level access if no org
            policy_content = policy_content.replace("{{ORG_ID}}", "none")
        
        if customer_id:
            policy_content = policy_content.replace("{{CUSTOMER_ID}}", customer_id)
        else:
            policy_content = policy_content.replace("{{CUSTOMER_ID}}", "none")
        
        # Create policy
        try:
            self.client.sys.create_or_update_policy(
                name=policy_name,
                policy=policy_content
            )
            logger.info(f"Created Vault policy: {policy_name}")
            return policy_name
        except VaultError as e:
            logger.error(f"Failed to create policy: {e}")
            raise
    
    def _get_inline_policy_template(self) -> str:
        """Fallback inline policy template."""
        return '''
# Tenant KV access
path "tenants/{{TENANT_ID}}/kv/data/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Transit encryption
path "transit/encrypt/{{TENANT_ID}}" {
  capabilities = ["update"]
}

path "transit/decrypt/{{TENANT_ID}}" {
  capabilities = ["update"]
}

# Deny other tenants
path "tenants/+/kv/*" {
  capabilities = ["deny"]
}

path "transit/encrypt/+" {
  capabilities = ["deny"]
}

path "transit/decrypt/+" {
  capabilities = ["deny"]
}
'''
    
    # ========================================================================
    # Secrets Engine Configuration
    # ========================================================================
    
    def enable_kv_for_tenant(self, tenant_id: str) -> bool:
        """Enable KV v2 secrets engine for tenant."""
        mount_point = f"tenants/{tenant_id}/kv"
        
        try:
            # Check if already enabled
            mounts = self.client.sys.list_mounted_secrets_engines()
            if f"{mount_point}/" in mounts:
                logger.info(f"KV already enabled for tenant: {tenant_id}")
                return True
            
            # Enable KV v2
            self.client.sys.enable_secrets_engine(
                backend_type="kv-v2",
                path=mount_point
            )
            logger.info(f"Enabled KV for tenant: {tenant_id}")
            return True
        except VaultError as e:
            logger.error(f"Failed to enable KV: {e}")
            raise
    
    def create_encryption_key(self, tenant_id: str) -> bool:
        """Create transit encryption key for tenant."""
        try:
            # Check if transit engine is enabled
            mounts = self.client.sys.list_mounted_secrets_engines()
            if "transit/" not in mounts:
                self.client.sys.enable_secrets_engine(
                    backend_type="transit",
                    path="transit"
                )
                logger.info("Enabled transit secrets engine")
            
            # Create tenant-specific key
            self.client.secrets.transit.create_key(name=tenant_id)
            logger.info(f"Created encryption key for tenant: {tenant_id}")
            return True
        except VaultError as e:
            # Key might already exist
            if "already exists" in str(e).lower():
                logger.info(f"Encryption key already exists for tenant: {tenant_id}")
                return True
            logger.error(f"Failed to create encryption key: {e}")
            raise
    
    def configure_database_for_tenant(self, tenant_id: str) -> bool:
        """Configure database secrets engine for tenant."""
        # This would be implemented when we add dynamic database credentials
        logger.info(f"Database engine configuration skipped (not yet implemented)")
        return True
    
    def setup_pki_for_tenant(self, tenant_id: str) -> bool:
        """Set up PKI secrets engine for tenant."""
        pki_mount = f"pki_{tenant_id}"
        
        try:
            # Enable PKI engine
            self.client.sys.enable_secrets_engine(
                backend_type="pki",
                path=pki_mount,
                config={"max_lease_ttl": "87600h"}  # 10 years
            )
            
            # Generate root CA
            self.client.secrets.pki.generate_root(
                type="internal",
                common_name=f"Tenant {tenant_id} Root CA",
                mount_point=pki_mount
            )
            
            logger.info(f"Set up PKI for tenant: {tenant_id}")
            return True
        except VaultError as e:
            if "already in use" in str(e).lower():
                logger.info(f"PKI already configured for tenant: {tenant_id}")
                return True
            logger.error(f"Failed to setup PKI: {e}")
            raise
    
    # ========================================================================
    # Token Management
    # ========================================================================
    
    def create_tenant_token(
        self,
        tenant_id: str,
        entity_id: str,
        policy_name: str,
        ttl: str = "24h"
    ) -> str:
        """
        Create Vault token for tenant.
        
        Args:
            tenant_id: Tenant UUID
            entity_id: Vault entity ID
            policy_name: Policy name
            ttl: Token lifetime
        
        Returns:
            Vault token
        """
        try:
            response = self.client.auth.token.create(
                policies=[policy_name],
                entity_alias=entity_id,
                metadata={"tenant_id": tenant_id},
                renewable=True,
                ttl=ttl,
                explicit_max_ttl="720h"  # 30 days max
            )
            token = response["auth"]["client_token"]
            logger.info(f"Created token for tenant: {tenant_id}")
            return token
        except VaultError as e:
            logger.error(f"Failed to create token: {e}")
            raise
    
    def revoke_tenant_access(self, tenant_id: str, token_accessor: str) -> bool:
        """
        Revoke all access for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            token_accessor: Token accessor to revoke
        
        Returns:
            True if successful
        """
        try:
            self.client.auth.token.revoke_accessor(token_accessor)
            logger.info(f"Revoked access for tenant: {tenant_id}")
            return True
        except VaultError as e:
            logger.error(f"Failed to revoke access: {e}")
            raise

