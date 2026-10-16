"""
Vault Client - Wrapper around hvac for SentinelGrid-specific operations.
Handles tenant-scoped secret operations with automatic path prefixing.
"""

import logging
from typing import Dict, Any, Optional, List
import hvac
from hvac.exceptions import VaultError, InvalidPath, Forbidden

logger = logging.getLogger(__name__)


class VaultClient:
    """
    HashiCorp Vault client with SentinelGrid multi-tenancy support.
    
    Automatically handles:
    - Tenant path prefixing
    - Token refresh
    - Error handling
    - Audit logging
    """
    
    def __init__(
        self,
        url: str,
        token: str,
        tenant_id: Optional[str] = None,
        org_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        verify: bool = False
    ):
        """
        Initialize Vault client.
        
        Args:
            url: Vault server URL
            token: Vault token
            tenant_id: Tenant UUID (for tenant-scoped operations)
            org_id: Organization UUID (for org-scoped operations)
            customer_id: Customer UUID (for customer-scoped operations)
            verify: Verify SSL certificates
        """
        self.url = url
        self.token = token
        self.tenant_id = tenant_id
        self.org_id = org_id
        self.customer_id = customer_id
        
        self.client = hvac.Client(url=url, token=token, verify=verify)
        
        if not self.client.is_authenticated():
            raise ValueError("Failed to authenticate with Vault")
        
        logger.info(f"Vault client initialized for tenant: {tenant_id}")
    
    # ========================================================================
    # KV Secrets Engine
    # ========================================================================
    
    def get_secret(self, key: str, scope: str = "tenant") -> Optional[Dict[str, Any]]:
        """
        Retrieve a secret from KV store.
        
        Args:
            key: Secret key
            scope: Scope level ("tenant", "org", "customer")
        
        Returns:
            Secret data or None if not found
        """
        path = self._build_kv_path(key, scope)
        
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=self._get_mount_point(scope)
            )
            return response["data"]["data"]
        except InvalidPath:
            logger.debug(f"Secret not found: {path}")
            return None
        except Forbidden:
            logger.warning(f"Access denied to secret: {path}")
            raise
        except VaultError as e:
            logger.error(f"Vault error reading secret {path}: {e}")
            raise
    
    def put_secret(
        self,
        key: str,
        value: Dict[str, Any],
        scope: str = "tenant"
    ) -> bool:
        """
        Store a secret in KV store.
        
        Args:
            key: Secret key
            value: Secret data
            scope: Scope level ("tenant", "org", "customer")
        
        Returns:
            True if successful
        """
        path = self._build_kv_path(key, scope)
        
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=value,
                mount_point=self._get_mount_point(scope)
            )
            logger.info(f"Secret stored: {path}")
            return True
        except Forbidden:
            logger.warning(f"Access denied to store secret: {path}")
            raise
        except VaultError as e:
            logger.error(f"Vault error storing secret {path}: {e}")
            raise
    
    def delete_secret(self, key: str, scope: str = "tenant") -> bool:
        """
        Delete a secret from KV store.
        
        Args:
            key: Secret key
            scope: Scope level
        
        Returns:
            True if successful
        """
        path = self._build_kv_path(key, scope)
        
        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=path,
                mount_point=self._get_mount_point(scope)
            )
            logger.info(f"Secret deleted: {path}")
            return True
        except VaultError as e:
            logger.error(f"Vault error deleting secret {path}: {e}")
            raise
    
    def list_secrets(self, scope: str = "tenant") -> List[str]:
        """
        List secrets in scope.
        
        Args:
            scope: Scope level
        
        Returns:
            List of secret keys
        """
        path = self._build_kv_path("", scope)
        
        try:
            response = self.client.secrets.kv.v2.list_secrets(
                path=path,
                mount_point=self._get_mount_point(scope)
            )
            return response["data"]["keys"]
        except InvalidPath:
            return []
        except VaultError as e:
            logger.error(f"Vault error listing secrets: {e}")
            raise
    
    # ========================================================================
    # Transit Encryption Engine
    # ========================================================================
    
    def encrypt(
        self,
        plaintext: str,
        context: Optional[str] = None
    ) -> str:
        """
        Encrypt data using tenant-specific encryption key.
        
        Args:
            plaintext: Data to encrypt
            context: Optional encryption context
        
        Returns:
            Ciphertext (vault:v1:...)
        """
        if not self.tenant_id:
            raise ValueError("tenant_id required for encryption")
        
        try:
            import base64
            plaintext_b64 = base64.b64encode(plaintext.encode()).decode()
            
            kwargs = {"plaintext": plaintext_b64}
            if context:
                kwargs["context"] = base64.b64encode(context.encode()).decode()
            
            response = self.client.secrets.transit.encrypt_data(
                name=self.tenant_id,
                **kwargs
            )
            return response["data"]["ciphertext"]
        except VaultError as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(
        self,
        ciphertext: str,
        context: Optional[str] = None
    ) -> str:
        """
        Decrypt data using tenant-specific encryption key.
        
        Args:
            ciphertext: Encrypted data
            context: Optional encryption context
        
        Returns:
            Decrypted plaintext
        """
        if not self.tenant_id:
            raise ValueError("tenant_id required for decryption")
        
        try:
            import base64
            
            kwargs = {"ciphertext": ciphertext}
            if context:
                kwargs["context"] = base64.b64encode(context.encode()).decode()
            
            response = self.client.secrets.transit.decrypt_data(
                name=self.tenant_id,
                **kwargs
            )
            plaintext_b64 = response["data"]["plaintext"]
            return base64.b64decode(plaintext_b64).decode()
        except VaultError as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    # ========================================================================
    # Database Dynamic Credentials
    # ========================================================================
    
    def get_database_credentials(
        self,
        role: str,
        ttl: str = "1h"
    ) -> Dict[str, Any]:
        """
        Generate dynamic database credentials.
        
        Args:
            role: Database role (e.g., "readonly", "readwrite")
            ttl: Credential lifetime
        
        Returns:
            Dict with username, password, lease_id
        """
        if not self.tenant_id:
            raise ValueError("tenant_id required for database credentials")
        
        role_name = f"{self.tenant_id}-{role}"
        
        try:
            response = self.client.secrets.database.generate_credentials(
                name=role_name
            )
            return {
                "username": response["data"]["username"],
                "password": response["data"]["password"],
                "lease_id": response["lease_id"],
                "lease_duration": response["lease_duration"]
            }
        except VaultError as e:
            logger.error(f"Failed to generate database credentials: {e}")
            raise
    
    def revoke_database_credentials(self, lease_id: str) -> bool:
        """
        Revoke dynamic database credentials.
        
        Args:
            lease_id: Lease ID from generate_credentials
        
        Returns:
            True if successful
        """
        try:
            self.client.sys.revoke_lease(lease_id)
            logger.info(f"Revoked lease: {lease_id}")
            return True
        except VaultError as e:
            logger.error(f"Failed to revoke lease: {e}")
            raise
    
    # ========================================================================
    # PKI Engine
    # ========================================================================
    
    def issue_certificate(
        self,
        common_name: str,
        alt_names: Optional[List[str]] = None,
        ttl: str = "8760h"  # 1 year
    ) -> Dict[str, Any]:
        """
        Issue a certificate from tenant-specific PKI.
        
        Args:
            common_name: Certificate common name
            alt_names: Alternative names
            ttl: Certificate lifetime
        
        Returns:
            Dict with certificate, private_key, ca_chain
        """
        if not self.tenant_id:
            raise ValueError("tenant_id required for PKI operations")
        
        pki_mount = f"pki_{self.tenant_id}"
        
        try:
            response = self.client.secrets.pki.generate_certificate(
                name="default",
                common_name=common_name,
                alt_names=alt_names or [],
                ttl=ttl,
                mount_point=pki_mount
            )
            return {
                "certificate": response["data"]["certificate"],
                "private_key": response["data"]["private_key"],
                "ca_chain": response["data"]["ca_chain"],
                "serial_number": response["data"]["serial_number"]
            }
        except VaultError as e:
            logger.error(f"Failed to issue certificate: {e}")
            raise
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _build_kv_path(self, key: str, scope: str) -> str:
        """Build full Vault path based on scope."""
        if scope == "tenant":
            if not self.tenant_id:
                raise ValueError("tenant_id required for tenant scope")
            return f"tenants/{self.tenant_id}/kv/{key}"
        elif scope == "org":
            if not self.org_id:
                raise ValueError("org_id required for org scope")
            return f"organizations/{self.org_id}/kv/{key}"
        elif scope == "customer":
            if not self.customer_id:
                raise ValueError("customer_id required for customer scope")
            return f"customers/{self.customer_id}/kv/{key}"
        else:
            raise ValueError(f"Invalid scope: {scope}")
    
    def _get_mount_point(self, scope: str) -> str:
        """Get KV mount point for scope."""
        if scope == "tenant":
            return f"tenants/{self.tenant_id}/kv"
        elif scope == "org":
            return f"organizations/{self.org_id}/kv"
        elif scope == "customer":
            return f"customers/{self.customer_id}/kv"
        else:
            return "secret"  # Default KV v2 mount
    
    def is_healthy(self) -> bool:
        """Check if Vault is healthy and accessible."""
        try:
            return self.client.sys.is_initialized() and not self.client.sys.is_sealed()
        except Exception as e:
            logger.error(f"Vault health check failed: {e}")
            return False

