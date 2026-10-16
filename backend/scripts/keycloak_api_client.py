"""
Synchronous Keycloak Admin REST API Client for seeding scripts.

Uses direct REST API calls via httpx (sync) instead of python-keycloak library
for consistency with the rest of the codebase.
"""

import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger(__name__)


class KeycloakAPIError(Exception):
    """Base exception for Keycloak API errors."""
    pass


class KeycloakAdminAPIClient:
    """
    Synchronous Keycloak Admin REST API v2 client.
    
    Uses direct REST API calls for consistency with IAM Agent's KeycloakAdminClient.
    """
    
    def __init__(
        self,
        server_url: str,
        admin_user: str,
        admin_password: str,
        verify: bool = False
    ):
        """
        Initialize Keycloak Admin client.
        
        Args:
            server_url: Keycloak server URL
            admin_user: Admin username
            admin_password: Admin password
            verify: Verify SSL certificates (default False for dev)
        """
        self.server_url = server_url.rstrip('/')
        self.admin_user = admin_user
        self.admin_password = admin_password
        self.verify = verify
        
        # Token caching for performance
        self._admin_token: Optional[str] = None
        self._token_expiry: Optional[float] = None
        
        # Connection pool for performance
        self._client = httpx.Client(
            timeout=30.0,
            verify=verify
        )
        
        logger.info(f"KeycloakAdminAPIClient initialized for {self.server_url}")
    
    def _get_admin_token(self) -> str:
        """
        Get admin access token from Keycloak.
        
        Uses token caching to reduce authentication overhead.
        
        Returns:
            Admin access token
        
        Raises:
            KeycloakAPIError: If token acquisition fails
        """
        # Return cached token if still valid (90% threshold for safety)
        if self._admin_token and self._token_expiry:
            if time.time() < self._token_expiry:
                logger.debug("Using cached admin token")
                return self._admin_token
        
        logger.debug("Requesting new admin token")
        
        try:
            response = self._client.post(
                f"{self.server_url}/realms/master/protocol/openid-connect/token",
                data={
                    "grant_type": "password",
                    "client_id": "admin-cli",
                    "username": self.admin_user,
                    "password": self.admin_password
                }
            )
            response.raise_for_status()
            
            token_data = response.json()
            self._admin_token = token_data["access_token"]
            
            # Cache token until 90% of expiry
            expires_in = token_data.get("expires_in", 60)
            self._token_expiry = time.time() + (expires_in * 0.9)
            
            logger.info(f"✅ Admin token acquired (expires in {expires_in}s)")
            return self._admin_token
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get admin token: {e.response.status_code} - {e.response.text}")
            raise KeycloakAPIError(f"Authentication failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Failed to get admin token: {e}")
            raise KeycloakAPIError(f"Authentication error: {str(e)}")
    
    def _make_request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 3
    ) -> httpx.Response:
        """
        Make authenticated request to Keycloak Admin API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (e.g., "/realms/{realm}/users" or "/realms/{realm}")
            json_data: JSON payload for POST/PUT
            params: Query parameters
            retry_count: Number of retries on failure
        
        Returns:
            httpx.Response object
        
        Raises:
            KeycloakAPIError: On request failure after retries
        """
        token = self._get_admin_token()
        url = f"{self.server_url}/admin{path}"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        for attempt in range(retry_count):
            try:
                response = self._client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json_data,
                    params=params
                )
                
                # Success - return response
                return response
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401 and attempt < retry_count - 1:
                    # Token expired, clear cache and retry
                    logger.warning("Token expired, refreshing and retrying")
                    self._admin_token = None
                    token = self._get_admin_token()
                    headers["Authorization"] = f"Bearer {token}"
                    continue
                raise
            
            except httpx.TimeoutException:
                if attempt < retry_count - 1:
                    wait_time = 0.5 * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Request timeout, retrying in {wait_time}s (attempt {attempt + 1})")
                    time.sleep(wait_time)
                    continue
                raise KeycloakAPIError(f"Request timeout after {retry_count} attempts")
            
            except Exception as e:
                logger.error(f"Request failed: {method} {url} - {e}")
                raise KeycloakAPIError(f"Request failed: {str(e)}")
        
        raise KeycloakAPIError(f"Request failed after {retry_count} attempts")
    
    # ========================================================================
    # Realm Management Methods
    # ========================================================================
    
    def get_realm(self, realm_name: str) -> Optional[Dict[str, Any]]:
        """Get realm by name."""
        try:
            response = self._make_request("GET", f"/realms/{realm_name}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise KeycloakAPIError(f"Failed to get realm: {e.response.status_code}")
    
    def create_realm(self, realm_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new realm."""
        response = self._make_request("POST", "/realms", json_data=realm_config)
        
        if response.status_code == 201:
            logger.info(f"✅ Created realm: {realm_config.get('realm')}")
            # Get the created realm
            return self.get_realm(realm_config['realm'])
        elif response.status_code == 409:
            logger.info(f"⏭️  Realm {realm_config.get('realm')} already exists")
            return self.get_realm(realm_config['realm'])
        else:
            error_msg = response.text
            raise KeycloakAPIError(f"Failed to create realm: {response.status_code} - {error_msg}")
    
    # ========================================================================
    # Client Management Methods
    # ========================================================================
    
    def get_clients(self, realm: str, query: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Get clients in a realm."""
        params = query or {}
        response = self._make_request("GET", f"/realms/{realm}/clients", params=params)
        response.raise_for_status()
        return response.json()
    
    def create_client(self, realm: str, client_data: Dict[str, Any]) -> str:
        """Create a client in a realm. Returns client UUID."""
        response = self._make_request("POST", f"/realms/{realm}/clients", json_data=client_data)
        
        if response.status_code == 201:
            # Extract client_id from Location header
            location = response.headers.get("Location", "")
            client_id = location.split("/")[-1]
            logger.info(f"✅ Created client: {client_data.get('clientId')}")
            return client_id
        elif response.status_code == 409:
            # Client exists, find it
            clients = self.get_clients(realm, {"clientId": client_data["clientId"]})
            if clients:
                logger.info(f"⏭️  Client {client_data.get('clientId')} already exists")
                return clients[0]["id"]
            raise KeycloakAPIError(f"Client exists but could not find it: {client_data['clientId']}")
        else:
            error_msg = response.text
            raise KeycloakAPIError(f"Failed to create client: {response.status_code} - {error_msg}")
    
    def get_client_secrets(self, realm: str, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client secret."""
        try:
            response = self._make_request("GET", f"/realms/{realm}/clients/{client_id}/client-secret")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise KeycloakAPIError(f"Failed to get client secret: {e.response.status_code}")
    
    # ========================================================================
    # Role Management Methods
    # ========================================================================
    
    def get_realm_roles(self, realm: str) -> List[Dict[str, Any]]:
        """Get all realm roles."""
        response = self._make_request("GET", f"/realms/{realm}/roles")
        response.raise_for_status()
        return response.json()
    
    def get_realm_role(self, realm: str, role_name: str) -> Optional[Dict[str, Any]]:
        """Get realm role by name."""
        try:
            response = self._make_request("GET", f"/realms/{realm}/roles/{role_name}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise KeycloakAPIError(f"Failed to get role: {e.response.status_code}")
    
    def create_realm_role(self, realm: str, role_data: Dict[str, Any]) -> None:
        """Create a realm role."""
        response = self._make_request("POST", f"/realms/{realm}/roles", json_data=role_data)
        
        if response.status_code == 201:
            logger.info(f"✅ Created role: {role_data.get('name')}")
        elif response.status_code == 409:
            logger.info(f"⏭️  Role {role_data.get('name')} already exists")
        else:
            error_msg = response.text
            raise KeycloakAPIError(f"Failed to create role: {response.status_code} - {error_msg}")
    
    def assign_realm_role(self, realm: str, user_id: str, role_name: str) -> None:
        """Assign realm role to user."""
        role = self.get_realm_role(realm, role_name)
        if not role:
            raise KeycloakAPIError(f"Role not found: {role_name}")
        
        response = self._make_request(
            "POST",
            f"/realms/{realm}/users/{user_id}/role-mappings/realm",
            json_data=[role]
        )
        
        if response.status_code in [200, 204]:
            logger.info(f"✅ Assigned role {role_name} to user {user_id}")
        else:
            raise KeycloakAPIError(f"Failed to assign role: {response.status_code}")
    
    # ========================================================================
    # User Management Methods
    # ========================================================================
    
    def get_users(self, realm: str, query: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Get users in a realm."""
        params = query or {}
        response = self._make_request("GET", f"/realms/{realm}/users", params=params)
        response.raise_for_status()
        return response.json()
    
    def create_user(self, realm: str, user_data: Dict[str, Any]) -> str:
        """Create a user in a realm. Returns user ID."""
        response = self._make_request("POST", f"/realms/{realm}/users", json_data=user_data)
        
        if response.status_code == 201:
            # Extract user_id from Location header
            location = response.headers.get("Location", "")
            user_id = location.split("/")[-1]
            logger.info(f"✅ Created user: {user_data.get('username')}")
            return user_id
        elif response.status_code == 409:
            # User exists, find it
            users = self.get_users(realm, {"username": user_data["username"], "exact": "true"})
            if users:
                logger.info(f"⏭️  User {user_data.get('username')} already exists")
                return users[0]["id"]
            raise KeycloakAPIError(f"User exists but could not find it: {user_data['username']}")
        else:
            error_msg = response.text
            raise KeycloakAPIError(f"Failed to create user: {response.status_code} - {error_msg}")
    
    def set_user_password(self, realm: str, user_id: str, password: str, temporary: bool = False) -> None:
        """Set user password."""
        response = self._make_request(
            "PUT",
            f"/realms/{realm}/users/{user_id}/reset-password",
            json_data={
                "type": "password",
                "value": password,
                "temporary": temporary
            }
        )
        
        if response.status_code not in [200, 204]:
            error_msg = response.text
            logger.error(f"Password set failed: {response.status_code} - {error_msg}")
            raise KeycloakAPIError(f"Failed to set password: {response.status_code} - {error_msg}")
        
        logger.info(f"✅ Password set for user {user_id}")
    
    # ========================================================================
    # Client Scope Management Methods
    # ========================================================================
    
    def get_client_scopes(self, realm: str) -> List[Dict[str, Any]]:
        """Get all client scopes in a realm."""
        response = self._make_request("GET", f"/realms/{realm}/client-scopes")
        response.raise_for_status()
        return response.json()
    
    def create_client_scope(self, realm: str, scope_data: Dict[str, Any]) -> str:
        """Create a client scope. Returns scope ID."""
        response = self._make_request("POST", f"/realms/{realm}/client-scopes", json_data=scope_data)
        
        if response.status_code == 201:
            location = response.headers.get("Location", "")
            scope_id = location.split("/")[-1]
            logger.info(f"✅ Created client scope: {scope_data.get('name')}")
            return scope_id
        elif response.status_code == 409:
            # Scope exists, find it
            scopes = self.get_client_scopes(realm)
            for scope in scopes:
                if scope.get("name") == scope_data["name"]:
                    logger.info(f"⏭️  Client scope {scope_data.get('name')} already exists")
                    return scope["id"]
            raise KeycloakAPIError(f"Scope exists but could not find it: {scope_data['name']}")
        else:
            error_msg = response.text
            raise KeycloakAPIError(f"Failed to create client scope: {response.status_code} - {error_msg}")
    
    def add_mapper_to_client_scope(self, realm: str, scope_id: str, mapper_data: Dict[str, Any]) -> None:
        """Add protocol mapper to client scope."""
        response = self._make_request(
            "POST",
            f"/realms/{realm}/client-scopes/{scope_id}/protocol-mappers/models",
            json_data=mapper_data
        )
        
        if response.status_code == 201:
            logger.info(f"✅ Added mapper {mapper_data.get('name')} to scope")
        elif response.status_code == 409:
            logger.info(f"⏭️  Mapper {mapper_data.get('name')} already exists")
        else:
            error_msg = response.text
            raise KeycloakAPIError(f"Failed to add mapper: {response.status_code} - {error_msg}")
    
    def get_mappers_from_client_scope(self, realm: str, scope_id: str) -> List[Dict[str, Any]]:
        """Get protocol mappers from client scope."""
        response = self._make_request("GET", f"/realms/{realm}/client-scopes/{scope_id}/protocol-mappers/models")
        response.raise_for_status()
        return response.json()
    
    def get_default_client_scopes(self, realm: str, client_id: str) -> List[Dict[str, Any]]:
        """Get default client scopes for a client."""
        response = self._make_request("GET", f"/realms/{realm}/clients/{client_id}/default-client-scopes")
        response.raise_for_status()
        return response.json()
    
    def add_default_client_scope(self, realm: str, client_id: str, scope_id: str) -> None:
        """Add default client scope to a client."""
        response = self._make_request(
            "PUT",
            f"/realms/{realm}/clients/{client_id}/default-client-scopes/{scope_id}"
        )
        
        if response.status_code in [200, 204]:
            logger.info(f"✅ Added default scope to client {client_id}")
        else:
            raise KeycloakAPIError(f"Failed to add default scope: {response.status_code}")
    
    def close(self):
        """Close connection pool."""
        if self._client:
            self._client.close()
            self._client = None

