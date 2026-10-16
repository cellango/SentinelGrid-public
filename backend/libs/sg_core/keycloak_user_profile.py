"""
Keycloak User Profile Configuration Library

CRITICAL: Keycloak v25+ requires custom attributes to be defined in the User Profile schema
before they can persist. This library provides a centralized, reusable function to configure
User Profile with tenant_id and customer_id attributes.

This is a foundational requirement for multi-tenant isolation in SentinelGrid.
"""

import logging
import os
from typing import Optional, Dict, Any, Union
import httpx

logger = logging.getLogger(__name__)


def _keycloak_verify_tls(verify_tls: Optional[bool] = None) -> bool:
    """Resolve Keycloak TLS verification with a production fail-closed default."""
    if verify_tls is not None:
        resolved = verify_tls
    else:
        resolved = os.getenv("KEYCLOAK_VERIFY_TLS", "false").lower() == "true"

    if os.getenv("ENVIRONMENT", "development").strip().lower() == "production" and resolved is not True:
        raise ValueError("KEYCLOAK_VERIFY_TLS must be enabled in production")

    return resolved


def configure_realm_user_profile(
    realm_name: str,
    keycloak_url: Optional[str] = None,
    admin_user: Optional[str] = None,
    admin_password: Optional[str] = None,
    admin_token: Optional[str] = None,
    verify_tls: Optional[bool] = None,
) -> bool:
    """
    Configure User Profile for a Keycloak realm to enable custom attributes (tenant_id, customer_id).
    
    CRITICAL: This MUST be done before creating any users in Keycloak v25+
    Without this, custom attributes will not persist.
    
    Args:
        realm_name: Name of the Keycloak realm
        keycloak_url: Keycloak server URL (defaults to KEYCLOAK_URL env var or https://localhost:8443)
        admin_user: Keycloak admin username (defaults to KEYCLOAK_ADMIN_USER env var or "admin")
        admin_password: Keycloak admin password (defaults to KEYCLOAK_ADMIN_PASSWORD env var or "admin")
        admin_token: Optional pre-obtained admin token (if provided, skips token acquisition)
    
    Returns:
        True if successful, False otherwise
    
    Raises:
        Exception: If critical errors occur (should be caught by caller)
    """
    # Get configuration from environment or parameters (default to local HTTPS)
    keycloak_url = keycloak_url or os.getenv("KEYCLOAK_URL") or "https://localhost:8443"
    if not keycloak_url.startswith("http"):
        keycloak_url = f"https://{keycloak_url}"
    admin_user = admin_user or os.getenv("KEYCLOAK_ADMIN_USER", "admin")
    admin_password = admin_password or os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
    
    logger.info(f"Configuring User Profile for realm '{realm_name}' at {keycloak_url}")
    
    try:
        # Get admin token if not provided
        if not admin_token:
            admin_token = _get_admin_token(
                keycloak_url,
                admin_user,
                admin_password,
                verify_tls=_keycloak_verify_tls(verify_tls),
            )
            if not admin_token:
                logger.error(f"Failed to obtain admin token for User Profile configuration")
                return False
        
        profile_url = f"{keycloak_url}/admin/realms/{realm_name}/users/profile"
        
        # Get current profile
        with httpx.Client(timeout=10.0, verify=_keycloak_verify_tls(verify_tls)) as client:
            get_response = client.get(
                profile_url,
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if get_response.status_code == 200:
                profile = get_response.json()
            elif get_response.status_code == 404:
                # Realm doesn't exist yet - this is OK, we'll create it
                logger.warning(f"Realm '{realm_name}' does not exist yet - User Profile will be configured when realm is created")
                return False
            else:
                error_text = get_response.text[:200] if get_response.text else "Unknown error"
                logger.warning(f"Could not get current profile: {get_response.status_code} - {error_text}")
                profile = {"attributes": []}
            
            # Ensure attributes array exists
            if "attributes" not in profile:
                profile["attributes"] = []
            
            # Add tenant_id and customer_id attributes if not present
            existing_attr_names = [attr.get("name") for attr in profile.get("attributes", [])]
            
            custom_attributes = [
                {
                    "name": "tenant_id",
                    "displayName": "Tenant ID",
                    "validations": {},
                    "annotations": {
                        "description": "Universal tenant isolation boundary for multi-tenancy"
                    },
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
                    "annotations": {
                        "description": "Customer identifier for billing and organization"
                    },
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
                logger.info(f"  User Profile already has custom attributes for realm '{realm_name}'")
                return True  # Already configured - success
            
            # Update User Profile
            update_response = client.put(
                profile_url,
                json=profile,
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if update_response.status_code in [200, 204]:
                logger.info(f"✅ User Profile configured for realm '{realm_name}' with {added_count} custom attributes")
                return True
            else:
                error_text = update_response.text[:200] if update_response.text else "Unknown error"
                logger.error(f"Failed to update User Profile for realm '{realm_name}': {update_response.status_code} - {error_text}")
                return False
                
    except Exception as e:
        logger.error(f"Error configuring User Profile for realm '{realm_name}': {e}", exc_info=True)
        return False


def _get_admin_token(
    keycloak_url: str,
    admin_user: str,
    admin_password: str,
    verify_tls: Optional[bool] = None,
) -> Optional[str]:
    """
    Get admin token from Keycloak master realm.
    
    Args:
        keycloak_url: Keycloak server URL
        admin_user: Admin username
        admin_password: Admin password
    
    Returns:
        Admin token string or None if failed
    """
    try:
        token_realm = os.getenv("KEYCLOAK_ADMIN_TOKEN_REALM", "master")
        token_url = f"{keycloak_url}/realms/{token_realm}/protocol/openid-connect/token"
        use_service_account = os.getenv("KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT", "false").lower() == "true"
        client_id = os.getenv("KEYCLOAK_ADMIN_CLIENT_ID", "sg-core-keycloak-user-profile")
        client_secret = os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET")
        token_payload = {
            "client_id": "admin-cli",
            "username": admin_user,
            "password": admin_password,
            "grant_type": "password",
        }
        if use_service_account and client_secret:
            token_payload = {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
            }
        
        with httpx.Client(timeout=10.0, verify=_keycloak_verify_tls(verify_tls)) as client:
            token_response = client.post(
                token_url,
                data=token_payload
            )
            
            if token_response.status_code == 200:
                return token_response.json()["access_token"]
            else:
                logger.error(f"Failed to get admin token: {token_response.status_code} - {token_response.text[:200]}")
                return None
                
    except Exception as e:
        logger.error(f"Error getting admin token: {e}", exc_info=True)
        return None


def verify_user_profile_configured(
    realm_name: str,
    keycloak_url: Optional[str] = None,
    admin_token: Optional[str] = None,
    verify_tls: Optional[bool] = None,
) -> bool:
    """
    Verify that User Profile is configured with tenant_id attribute.
    
    Args:
        realm_name: Name of the Keycloak realm
        keycloak_url: Keycloak server URL
        admin_token: Optional pre-obtained admin token
    
    Returns:
        True if tenant_id attribute exists in User Profile, False otherwise
    """
    # Resolve Keycloak URL (prefer explicit arg, then env, finally localhost fallback)
    keycloak_url = keycloak_url or os.getenv("KEYCLOAK_URL") or "https://localhost:8443"
    if not keycloak_url.startswith("http"):
        keycloak_url = f"https://{keycloak_url}"
    
    try:
        if not admin_token:
            admin_user = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
            admin_password = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
            admin_token = _get_admin_token(
                keycloak_url,
                admin_user,
                admin_password,
                verify_tls=_keycloak_verify_tls(verify_tls),
            )
            if not admin_token:
                return False
        
        profile_url = f"{keycloak_url}/admin/realms/{realm_name}/users/profile"
        
        with httpx.Client(timeout=10.0, verify=_keycloak_verify_tls(verify_tls)) as client:
            response = client.get(
                profile_url,
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                profile = response.json()
                attributes = profile.get("attributes", [])
                attr_names = [attr.get("name") for attr in attributes]
                return "tenant_id" in attr_names
            else:
                logger.warning(f"Could not verify User Profile: {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"Error verifying User Profile: {e}", exc_info=True)
        return False
