"""
Helper functions to fetch secrets from HashiCorp Vault.
"""

import os
import subprocess
import logging

logger = logging.getLogger(__name__)

VAULT_ADDR = os.getenv("VAULT_ADDR", "https://dev.vault.sentinelgrid.ai:8210")
VAULT_INTERNAL_ADDR = os.getenv("VAULT_INTERNAL_ADDR", "https://vault:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "")
VAULT_CONTAINER = os.getenv("VAULT_CONTAINER", "vault")


def _read_root_token_from_container() -> str | None:
    """Try to read the persisted root token from the Vault container volume."""
    try:
        result = subprocess.run(
            ["docker", "exec", VAULT_CONTAINER, "cat", "/vault/file/.vault_root_token"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        token = result.stdout.strip()
        return token or None
    except Exception:
        return None


def _get_vault_token() -> str:
    """Get a token from env or by reading the stored root token from the container."""
    if VAULT_TOKEN:
        return VAULT_TOKEN
    token = _read_root_token_from_container()
    if token:
        return token
    # Fallback to legacy dev token if nothing else is available
    return "sentinelgrid-dev-root-token"


def get_vault_secret(path: str, field: str = "value") -> str:
    """
    Fetch a secret from Vault using docker exec.
    
    Args:
        path: Vault secret path (e.g., "sentinelgrid/keycloak/platform-admin-password")
        field: Field name to retrieve (default: "value")
    
    Returns:
        Secret value as string
    
    Raises:
        RuntimeError: If secret cannot be retrieved
    """
    try:
        # Use docker exec to run vault CLI inside the container
        cmd = [
            "docker", "exec",
            "-e", f"VAULT_ADDR={VAULT_INTERNAL_ADDR}",
            "-e", f"VAULT_TOKEN={_get_vault_token()}",
            "-e", "VAULT_SKIP_VERIFY=true",
            VAULT_CONTAINER,
            "vault", "kv", "get", "-field", field, path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False
        )
        
        if result.returncode != 0:
            # Try alternative: direct curl to Vault API
            logger.warning(f"Vault CLI failed, trying API: {result.stderr}")
            return get_vault_secret_via_api(path, field)
        
        secret = result.stdout.strip()
        if not secret:
            raise RuntimeError(f"Empty secret returned from Vault path: {path}")
        
        return secret
        
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Timeout fetching secret from Vault: {path}")
    except Exception as e:
        logger.error(f"Error fetching secret from Vault: {e}")
        raise RuntimeError(f"Failed to fetch secret from Vault: {path}") from e


def get_vault_secret_via_api(path: str, field: str = "value") -> str:
    """
    Fetch a secret from Vault using HTTP API (fallback method).
    
    Args:
        path: Vault secret path (e.g., "sentinelgrid/keycloak/platform-admin-password")
        field: Field name to retrieve (default: "value")
    
    Returns:
        Secret value as string
    """
    import requests
    
    # Vault KV v2 API path format: /v1/{mount_path}/data/{secret_path}
    api_path = f"{VAULT_ADDR}/v1/{path}"
    
    headers = {"X-Vault-Token": _get_vault_token()}
    
    try:
        response = requests.get(api_path, headers=headers, timeout=5, verify=False)
        response.raise_for_status()
        
        data = response.json()
        # KV v2 returns data in data.data
        secret_data = data.get("data", {}).get("data", {})
        
        if field not in secret_data:
            raise RuntimeError(f"Field '{field}' not found in secret: {path}")
        
        return secret_data[field]
        
    except Exception as e:
        logger.error(f"Error fetching secret via API: {e}")
        raise RuntimeError(f"Failed to fetch secret from Vault API: {path}") from e


def get_platform_admin_password() -> str:
    """Get platform admin password from Vault."""
    return get_vault_secret("sentinelgrid/keycloak/platform-admin-password")


def get_test_customer_password() -> str:
    """Get test customer password from Vault (if stored)."""
    # Default test password if not in Vault
    try:
        return get_vault_secret("sentinelgrid/keycloak/test-customer-password")
    except RuntimeError:
        # Fallback to default test password
        return os.getenv("TEST_PASSWORD", "Test1234")
