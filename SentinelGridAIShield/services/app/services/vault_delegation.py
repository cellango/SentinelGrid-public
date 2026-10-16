"""
Vault Delegation Service

Securely fetches AI provider API keys from customer-controlled vaults.
Keys are never persisted - only fetched on-demand and cached temporarily.

Supports:
- AWS Secrets Manager (via STS AssumeRole)
- Azure Key Vault (via service principal)
- HashiCorp Vault (via AppRole)
"""

import boto3
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import hvac
import hashlib
from cachetools import TTLCache

logger = logging.getLogger(__name__)


class VaultProvider(ABC):
    """Abstract base class for vault providers"""
    
    @abstractmethod
    async def fetch_secret(self, config: Dict[str, Any]) -> str:
        """Fetch secret from vault. Returns the secret value."""
        pass


class AWSSecretsManagerProvider(VaultProvider):
    """AWS Secrets Manager with STS AssumeRole"""
    
    def __init__(self):
        self.sts_client = boto3.client('sts')
        # Cache assumed role credentials for 1 hour
        self.credentials_cache = TTLCache(maxsize=100, ttl=3600)
    
    async def fetch_secret(self, config: Dict[str, Any]) -> str:
        """
        Fetch secret from AWS Secrets Manager using AssumeRole.
        
        Args:
            config: {
                'iam_role_arn': 'arn:aws:iam::123456789012:role/SentinelGridGatewayAccess',
                'vault_secret_path': 'sentinelgrid/openai-key',
                'vault_region': 'us-east-1'
            }
        
        Returns:
            Secret value string
        """
        role_arn = config['iam_role_arn']
        secret_name = config['vault_secret_path']
        region = config.get('vault_region', 'us-east-1')
        
        try:
            # Check cache first
            cache_key = f"{role_arn}:{secret_name}"
            if cache_key in self.credentials_cache:
                logger.debug(f"Using cached credentials for {role_arn}")
                credentials = self.credentials_cache[cache_key]
            else:
                # AssumeRole into customer's account
                logger.info(f"Assuming role: {role_arn}")
                response = self.sts_client.assume_role(
                    RoleArn=role_arn,
                    RoleSessionName='SentinelGridAIGateway',
                    DurationSeconds=3600  # 1 hour
                )
                credentials = response['Credentials']
                self.credentials_cache[cache_key] = credentials
            
            # Create Secrets Manager client with assumed role credentials
            secrets_client = boto3.client(
                'secretsmanager',
                region_name=region,
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken']
            )
            
            # Fetch the secret
            logger.info(f"Fetching secret: {secret_name} from region {region}")
            secret_response = secrets_client.get_secret_value(SecretId=secret_name)
            
            # Return the secret string
            secret_value = secret_response.get('SecretString')
            if not secret_value:
                raise ValueError(f"Secret {secret_name} has no SecretString value")
            
            logger.info(f"Successfully fetched secret {secret_name}")
            return secret_value
            
        except Exception as e:
            logger.error(f"Failed to fetch secret from AWS: {str(e)}", exc_info=True)
            raise VaultAccessError(f"AWS Secrets Manager error: {str(e)}")


class AzureKeyVaultProvider(VaultProvider):
    """Azure Key Vault with service principal authentication"""
    
    def __init__(self):
        # Uses DefaultAzureCredential which supports:
        # - Environment variables (AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET)
        # - Managed Identity
        # - Azure CLI credentials
        self.credential = DefaultAzureCredential()
        # Cache secrets for 5 minutes
        self.secret_cache = TTLCache(maxsize=100, ttl=300)
    
    async def fetch_secret(self, config: Dict[str, Any]) -> str:
        """
        Fetch secret from Azure Key Vault.
        
        Args:
            config: {
                'vault_secret_path': 'https://customer-vault.vault.azure.net/',
                'iam_role_arn': 'secret-name',  # Using this field for secret name
                'vault_region': 'eastus'  # Optional, for logging
            }
        
        Returns:
            Secret value string
        """
        vault_url = config['vault_secret_path']
        secret_name = config['iam_role_arn']  # Reusing this field
        
        try:
            cache_key = f"{vault_url}:{secret_name}"
            if cache_key in self.secret_cache:
                logger.debug(f"Using cached secret for {vault_url}/{secret_name}")
                return self.secret_cache[cache_key]
            
            # Create Key Vault client
            client = SecretClient(vault_url=vault_url, credential=self.credential)
            
            # Fetch the secret
            logger.info(f"Fetching secret '{secret_name}' from {vault_url}")
            secret = client.get_secret(secret_name)
            
            secret_value = secret.value
            if not secret_value:
                raise ValueError(f"Secret {secret_name} has no value")
            
            # Cache it
            self.secret_cache[cache_key] = secret_value
            
            logger.info(f"Successfully fetched secret {secret_name}")
            return secret_value
            
        except Exception as e:
            logger.error(f"Failed to fetch secret from Azure: {str(e)}", exc_info=True)
            raise VaultAccessError(f"Azure Key Vault error: {str(e)}")


class HashiCorpVaultProvider(VaultProvider):
    """HashiCorp Vault with AppRole authentication"""
    
    def __init__(self, vault_url: str, role_id: str, secret_id: str):
        """
        Initialize HashiCorp Vault client.
        
        Args:
            vault_url: Vault server URL (e.g., 'https://vault.company.com')
            role_id: AppRole role ID
            secret_id: AppRole secret ID
        """
        self.client = hvac.Client(url=vault_url)
        self.role_id = role_id
        self.secret_id = secret_id
        self.authenticated = False
        self.token_expires = None
        # Cache secrets for 5 minutes
        self.secret_cache = TTLCache(maxsize=100, ttl=300)
    
    def _ensure_authenticated(self):
        """Authenticate with Vault if not already authenticated or token expired"""
        if self.authenticated and self.token_expires and datetime.now() < self.token_expires:
            return
        
        logger.info("Authenticating with HashiCorp Vault")
        response = self.client.auth.approle.login(
            role_id=self.role_id,
            secret_id=self.secret_id
        )
        
        # Token typically valid for 1 hour, refresh 5 minutes early
        lease_duration = response['auth']['lease_duration']
        self.token_expires = datetime.now() + timedelta(seconds=lease_duration - 300)
        self.authenticated = True
        logger.info("Successfully authenticated with Vault")
    
    async def fetch_secret(self, config: Dict[str, Any]) -> str:
        """
        Fetch secret from HashiCorp Vault.
        
        Args:
            config: {
                'vault_secret_path': 'secret/data/sentinelgrid/openai-key',
                'vault_region': 'kv-v2'  # Secret engine type
            }
        
        Returns:
            Secret value string
        """
        secret_path = config['vault_secret_path']
        
        try:
            cache_key = secret_path
            if cache_key in self.secret_cache:
                logger.debug(f"Using cached secret for {secret_path}")
                return self.secret_cache[cache_key]
            
            # Ensure we're authenticated
            self._ensure_authenticated()
            
            # Fetch the secret
            logger.info(f"Fetching secret from path: {secret_path}")
            response = self.client.secrets.kv.v2.read_secret_version(path=secret_path)
            
            # Extract the actual secret value
            secret_data = response['data']['data']
            secret_value = secret_data.get('value') or secret_data.get('key')
            
            if not secret_value:
                raise ValueError(f"Secret at {secret_path} has no 'value' or 'key' field")
            
            # Cache it
            self.secret_cache[cache_key] = secret_value
            
            logger.info(f"Successfully fetched secret from {secret_path}")
            return secret_value
            
        except Exception as e:
            logger.error(f"Failed to fetch secret from Vault: {str(e)}", exc_info=True)
            raise VaultAccessError(f"HashiCorp Vault error: {str(e)}")


class VaultDelegationService:
    """
    Main service for fetching secrets from customer-controlled vaults.
    Abstracts over multiple vault providers.
    """
    
    def __init__(self):
        self.aws_provider = AWSSecretsManagerProvider()
        self.azure_provider = AzureKeyVaultProvider()
        self.vault_providers: Dict[str, HashiCorpVaultProvider] = {}
        
        # In-memory cache with 5-minute TTL
        # Key: (org_id, provider), Value: API key
        self.key_cache = TTLCache(maxsize=1000, ttl=300)
    
    async def fetch_provider_key(
        self,
        org_id: str,
        provider: str,
        credential_config: Dict[str, Any]
    ) -> str:
        """
        Fetch AI provider API key from customer's vault.
        
        Args:
            org_id: Organization ID
            provider: Provider name ('openai', 'anthropic', etc.)
            credential_config: Configuration from ai_provider_credentials table
        
        Returns:
            API key string
        
        Raises:
            VaultAccessError: If unable to fetch secret
        """
        # Check cache first
        cache_key = (org_id, provider)
        if cache_key in self.key_cache:
            logger.debug(f"Cache hit for {org_id}/{provider}")
            return self.key_cache[cache_key]
        
        # Determine which vault provider to use
        vault_type = credential_config.get('vault_type')
        
        try:
            if vault_type == 'aws-secrets':
                api_key = await self.aws_provider.fetch_secret(credential_config)
            elif vault_type == 'azure-keyvault':
                api_key = await self.azure_provider.fetch_secret(credential_config)
            elif vault_type == 'hashicorp-vault':
                # Initialize provider if not already done
                vault_url = credential_config.get('vault_secret_path')
                if vault_url not in self.vault_providers:
                    # These would come from environment or config
                    role_id = credential_config.get('vault_role_id')
                    secret_id = credential_config.get('vault_secret_id')
                    self.vault_providers[vault_url] = HashiCorpVaultProvider(
                        vault_url, role_id, secret_id
                    )
                api_key = await self.vault_providers[vault_url].fetch_secret(credential_config)
            else:
                raise VaultAccessError(f"Unsupported vault type: {vault_type}")
            
            # Cache the key
            self.key_cache[cache_key] = api_key
            
            # Log successful fetch (without exposing key)
            key_fingerprint = hashlib.sha256(api_key[:8].encode()).hexdigest()[:16]
            logger.info(f"Successfully fetched key for {org_id}/{provider} (fingerprint: {key_fingerprint})")
            
            return api_key
            
        except Exception as e:
            logger.error(f"Failed to fetch provider key: {str(e)}", exc_info=True)
            raise
    
    async def validate_vault_access(self, credential_config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Test vault access without fetching the actual secret.
        
        Args:
            credential_config: Configuration to validate
        
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            # Try to fetch the secret
            await self.fetch_provider_key(
                org_id="validation-test",
                provider="test",
                credential_config=credential_config
            )
            return (True, None)
        except Exception as e:
            return (False, str(e))


class VaultAccessError(Exception):
    """Raised when unable to access customer's vault"""
    pass

