"""Keycloak Admin API client for role operations."""

import logging
from typing import Optional, List, Dict, Any
import httpx

from app.core.config import (
    KeycloakAdminAuthConfigError,
    resolve_keycloak_admin_runtime_auth,
    settings,
)

logger = logging.getLogger(__name__)

try:
    from keycloak import KeycloakAdmin, KeycloakOpenID  # type: ignore
except Exception:  # pragma: no cover - optional dependency in some test contexts
    KeycloakAdmin = None
    KeycloakOpenID = None


class KeycloakClient:
    """Keycloak client for token validation and basic operations."""
    
    def __init__(self):
        self.server_url = settings.KEYCLOAK_URL
        self.realm = settings.KEYCLOAK_REALM
        # Optional admin client for flows that need realm/user creation
        try:
            if KeycloakAdmin is None:
                raise RuntimeError("python-keycloak is not installed")

            admin_kwargs = {
                "server_url": f"{self.server_url}/",
                "realm_name": self.realm,
                "verify": settings.KEYCLOAK_VERIFY_TLS,
            }
            admin_auth = resolve_keycloak_admin_runtime_auth()
            admin_kwargs["user_realm_name"] = admin_auth.user_realm_name
            admin_kwargs.update(admin_auth.python_keycloak_kwargs)

            self.admin = KeycloakAdmin(**admin_kwargs)
        except KeycloakAdminAuthConfigError:
            raise
        except Exception as e:
            logger.warning(f"Keycloak admin client not available: {e}")
            self.admin = None
    
    def get_public_key(self) -> Optional[str]:
        """Get Keycloak public key for token validation."""
        try:
            import httpx
            response = httpx.get(
                f"{self.server_url}/realms/{self.realm}",
                timeout=5.0,
                verify=settings.KEYCLOAK_VERIFY_TLS
            )
            if response.status_code == 200:
                realm_info = response.json()
                return realm_info.get("public_key")
        except Exception as e:
            logger.error(f"Error getting Keycloak public key: {e}")
        return None


class KeycloakRoleClient:
    """Client for interacting with Keycloak Admin API for role operations."""
    
    def __init__(
        self,
        *,
        server_url: Optional[str] = None,
        realm: Optional[str] = None,
        admin_user: Optional[str] = None,
        admin_password: Optional[str] = None,
        admin_client_id: Optional[str] = None,
        admin_client_secret: Optional[str] = None,
        admin_token_realm: Optional[str] = None,
        use_service_account: Optional[bool] = None,
        verify_tls: Optional[bool] = None,
    ):
        """Initialize Keycloak admin client."""
        self.server_url = server_url or settings.KEYCLOAK_URL
        self.realm = realm or settings.KEYCLOAK_REALM
        self.admin_user = admin_user or settings.KEYCLOAK_ADMIN_USER
        self.admin_password = admin_password or settings.KEYCLOAK_ADMIN_PASSWORD
        self.admin_client_id = admin_client_id or settings.KEYCLOAK_ADMIN_CLIENT_ID
        self.admin_client_secret = admin_client_secret or settings.KEYCLOAK_ADMIN_CLIENT_SECRET
        self.admin_token_realm = admin_token_realm or settings.KEYCLOAK_ADMIN_TOKEN_REALM
        self.verify_tls = settings.KEYCLOAK_VERIFY_TLS if verify_tls is None else verify_tls
        self._admin_auth = resolve_keycloak_admin_runtime_auth(
            use_service_account=use_service_account,
            admin_user=self.admin_user,
            admin_password=self.admin_password,
            admin_client_id=self.admin_client_id,
            admin_client_secret=self.admin_client_secret,
            admin_token_realm=self.admin_token_realm,
        )
        self.use_service_account = self._admin_auth.mode == "service_account"
        self._admin_token: Optional[str] = None
        self._token_expiry: Optional[float] = None
    
    async def _get_admin_token(self) -> Optional[str]:
        """Get admin access token from Keycloak."""
        import time
        
        # Return cached token if still valid
        if self._admin_token and self._token_expiry and time.time() < self._token_expiry:
            return self._admin_token
        
        try:
            async with httpx.AsyncClient(verify=self.verify_tls) as client:
                response = await client.post(
                    f"{self.server_url}/realms/{self._admin_auth.user_realm_name}/protocol/openid-connect/token",
                    data=dict(self._admin_auth.token_payload),
                    timeout=10.0
                )
                response.raise_for_status()
                token_data = response.json()
                self._admin_token = token_data.get("access_token")
                # Set expiry to 90% of actual expiry for safety
                expires_in = token_data.get("expires_in", 60)
                self._token_expiry = time.time() + (expires_in * 0.9)
                return self._admin_token
        except Exception as e:
            logger.error(f"Failed to get admin token: {e}")
            return None
    
    async def _make_request(
        self, 
        method: str, 
        path: str, 
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make authenticated request to Keycloak Admin API."""
        token = await self._get_admin_token()
        if not token:
            return None
        
        url = f"{self.server_url}/admin/realms/{self.realm}/{path}"
        logger.debug(f"🔍 [KeycloakClient._make_request] {method} {url} (realm={self.realm}, path={path}, params={params})")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(verify=self.verify_tls, timeout=30.0) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json_data,
                    params=params
                )
                logger.debug(f"🔍 [KeycloakClient._make_request] Response: status={response.status_code}, path={path}")
                if response.status_code == 204:
                    return {}  # No content
                response.raise_for_status()
                return response.json() if response.content else {}
        except Exception as e:
            logger.error(f"Keycloak API request failed {method} {path}: {e}")
            return None
    
    async def get_user_roles(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's realm roles."""
        result = await self._make_request("GET", f"users/{user_id}/role-mappings/realm")
        return result if isinstance(result, list) else []
    
    async def get_user_role_names(self, user_id: str) -> List[str]:
        """Get user's realm role names."""
        roles = await self.get_user_roles(user_id)
        return [role.get("name") for role in roles if role.get("name")]
    
    async def assign_role_to_user(self, user_id: str, role_name: str) -> bool:
        """Assign a realm role to a user."""
        # First get the role
        role = await self.get_realm_role(role_name)
        if not role:
            logger.error(f"Role {role_name} not found")
            return False
        
        # Assign the role
        result = await self._make_request(
            "POST",
            f"users/{user_id}/role-mappings/realm",
            json_data=[role]
        )
        return result is not None
    
    async def remove_role_from_user(self, user_id: str, role_name: str) -> bool:
        """Remove a realm role from a user."""
        # First get the role
        role = await self.get_realm_role(role_name)
        if not role:
            logger.error(f"Role {role_name} not found")
            return False
        
        # Remove the role
        result = await self._make_request(
            "DELETE",
            f"users/{user_id}/role-mappings/realm",
            json_data=[role]
        )
        return result is not None
    
    async def get_realm_role(self, role_name: str) -> Optional[Dict[str, Any]]:
        """Get a realm role by name."""
        roles = await self.get_realm_roles()
        return next((r for r in roles if r.get("name") == role_name), None)
    
    async def get_realm_roles(self) -> List[Dict[str, Any]]:
        """Get all realm roles."""
        result = await self._make_request("GET", "roles")
        return result if isinstance(result, list) else []
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        return await self._make_request("GET", f"users/{user_id}")
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        result = await self._make_request("GET", "users", params={"username": username})
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return None
    
    async def get_users_with_role(self, role_name: str) -> List[Dict[str, Any]]:
        """Get all users who have a specific role."""
        role = await self.get_realm_role(role_name)
        if not role:
            return []
        
        result = await self._make_request("GET", f"roles/{role_name}/users")
        return result if isinstance(result, list) else []
    
    async def list_users(self, max: int = 100) -> List[Dict[str, Any]]:
        """List all users in the realm."""
        logger.debug(f"🔍 [KeycloakClient.list_users] Calling with realm={self.realm}, max={max}")
        result = await self._make_request("GET", "users", params={"max": max})
        users = result if isinstance(result, list) else []
        logger.debug(f"🔍 [KeycloakClient.list_users] Retrieved {len(users)} users from realm '{self.realm}'")
        return users
    
    async def create_user(self, user_data: Dict[str, Any]) -> Optional[str]:
        """Create a new user. Returns user ID on success."""
        result = await self._make_request("POST", "users", json_data=user_data)
        if result is not None:
            # Extract user ID from Location header or search for the user
            username = user_data.get("username")
            if username:
                user = await self.get_user_by_username(username)
                if user:
                    return user.get("id")
        return None
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID (alias for get_user_by_id for compatibility)."""
        return await self.get_user_by_id(user_id)
    
    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Update an existing user."""
        result = await self._make_request("PUT", f"users/{user_id}", json_data=user_data)
        return result is not None
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        result = await self._make_request("DELETE", f"users/{user_id}")
        return result is not None
