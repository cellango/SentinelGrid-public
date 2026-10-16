"""
Keycloak Admin REST API Client - Direct API Integration.

Replaces python-keycloak library for full control, better performance,
and version independence. Optimized for SaaS scale with connection pooling,
token caching, and async operations.

Industry best practice: Own the integration layer for critical IAM operations.
"""

import logging
import time
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import httpx

from app.core.config import (
    resolve_keycloak_admin_runtime_auth,
    settings,
)

logger = logging.getLogger(__name__)


class KeycloakAPIError(Exception):
    """Base exception for Keycloak API errors."""
    pass


class KeycloakUserExistsError(KeycloakAPIError):
    """User already exists in Keycloak."""
    pass


class KeycloakAttributePersistenceError(KeycloakAPIError):
    """User attributes failed to persist after retries."""
    pass


class KeycloakAdminClient:
    """
    Direct Keycloak Admin REST API v2 client.
    
    Optimized for SaaS performance:
    - Connection pooling with httpx
    - Admin token caching (reduces auth overhead)
    - Async/await for concurrent operations
    - Automatic retry with exponential backoff
    - Comprehensive error handling and logging
    
    Example usage:
        client = KeycloakAdminClient()
        user_id = await client.create_user(
            realm="sentinelgrid",
            username="user@example.com",
            email="user@example.com",
            first_name="John",
            last_name="Doe",
            attributes={"tenant_id": ["uuid-here"]}
        )
    """
    
    def __init__(
        self,
        server_url: Optional[str] = None,
        admin_user: Optional[str] = None,
        admin_password: Optional[str] = None,
        admin_client_id: Optional[str] = None,
        admin_client_secret: Optional[str] = None,
        admin_token_realm: Optional[str] = None,
        use_service_account: Optional[bool] = None,
        verify_tls: Optional[bool] = None,
    ):
        """
        Initialize Keycloak Admin client.
        
        Args:
            server_url: Keycloak server URL (default: from settings)
            admin_user: Admin username (default: from settings)
            admin_password: Admin password (default: from settings)
        """
        self.server_url = (server_url or settings.KEYCLOAK_URL).rstrip('/')
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
        
        # Token caching for performance
        self._admin_token: Optional[str] = None
        self._token_expiry: Optional[float] = None
        
        # Connection pool for performance (reuse connections)
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(f"KeycloakAdminClient initialized for {self.server_url}")
    
    async def __aenter__(self):
        """Context manager entry - create connection pool."""
        self._client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(
                max_connections=100,  # Connection pool for concurrent requests
                max_keepalive_connections=20
            ),
            verify=self.verify_tls
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close connection pool."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _get_client(self) -> httpx.AsyncClient:
        """Get or create httpx client."""
        if self._client is None:
            # Create standalone client if not using context manager
            self._client = httpx.AsyncClient(
                timeout=30.0,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                verify=self.verify_tls
            )
        return self._client
    
    async def _get_admin_token(self) -> str:
        """
        Get admin access token from Keycloak.
        
        Uses token caching to reduce authentication overhead.
        Tokens are cached until 90% of their expiry time.
        
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
        client = self._get_client()
        
        try:
            response = await client.post(
                f"{self.server_url}/realms/{self._admin_auth.user_realm_name}/protocol/openid-connect/token",
                data=dict(self._admin_auth.token_payload),
            )
            response.raise_for_status()
            
            token_data = response.json()
            self._admin_token = token_data["access_token"]
            
            # Cache token until 90% of expiry (e.g., 54 seconds of 60 second token)
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
    
    async def _make_request(
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
            path: API path (e.g., "users" or "users/{id}")
            json_data: JSON payload for POST/PUT
            params: Query parameters
            retry_count: Number of retries on failure
        
        Returns:
            httpx.Response object
        
        Raises:
            KeycloakAPIError: On request failure after retries
        """
        token = await self._get_admin_token()
        url = f"{self.server_url}/admin{path}"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        client = self._get_client()
        
        for attempt in range(retry_count):
            try:
                response = await client.request(
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
                    token = await self._get_admin_token()
                    headers["Authorization"] = f"Bearer {token}"
                    continue
                raise
            
            except httpx.TimeoutException:
                if attempt < retry_count - 1:
                    wait_time = 0.5 * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Request timeout, retrying in {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                    continue
                raise KeycloakAPIError(f"Request timeout after {retry_count} attempts")
            
            except Exception as e:
                logger.error(f"Request failed: {method} {url} - {e}")
                raise KeycloakAPIError(f"Request failed: {str(e)}")
        
        raise KeycloakAPIError(f"Request failed after {retry_count} attempts")
    
    # ========================================================================
    # User Management Methods
    # ========================================================================
    
    async def create_user(
        self,
        realm: str,
        username: str,
        email: str,
        first_name: str,
        last_name: str,
        password: Optional[str] = None,
        enabled: bool = True,
        email_verified: bool = False,
        attributes: Optional[Dict[str, List[str]]] = None,
        required_actions: Optional[List[str]] = None
    ) -> str:
        """
        Create user with attributes.
        
        CRITICAL: Validates attribute format and verifies persistence.
        
        Args:
            realm: Realm name
            username: Username (often email)
            email: User email
            first_name: First name
            last_name: Last name
            password: Optional password (set separately if None)
            enabled: Enable user account
            email_verified: Mark email as verified
            attributes: User attributes (MUST be Dict[str, List[str]] format)
                       Example: {"tenant_id": ["uuid"], "customer_id": ["uuid"]}
            required_actions: Required actions (e.g., ["VERIFY_EMAIL"])
        
        Returns:
            User ID (UUID string)
        
        Raises:
            KeycloakUserExistsError: If user already exists
            KeycloakAttributePersistenceError: If attributes don't persist
            KeycloakAPIError: On other failures
        """
        # Validate attributes format (common mistake: using strings instead of lists)
        if attributes:
            for key, value in attributes.items():
                if not isinstance(value, list):
                    raise ValueError(
                        f"Attribute '{key}' must be a list, got {type(value).__name__}. "
                        f"Correct format: {{'tenant_id': ['value']}} not {{'tenant_id': 'value'}}"
                    )
        
        user_payload = {
            "username": username,
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": enabled,
            "emailVerified": email_verified,
            "attributes": attributes or {},
            "requiredActions": required_actions or []
        }
        
        logger.info(f"Creating user: {username} in realm: {realm}")
        
        try:
            response = await self._make_request(
                "POST",
                f"/realms/{realm}/users",
                json_data=user_payload
            )
            
            if response.status_code == 201:
                # Extract user_id from Location header
                location = response.headers.get("Location", "")
                user_id = location.split("/")[-1]
                
                logger.info(f"✅ User created: {user_id}")
                
                # Set password if provided
                if password:
                    await self.set_user_password(realm, user_id, password, temporary=False)
                
                # CRITICAL: Verify attributes persisted (with retry)
                if attributes:
                    await self._verify_and_fix_user_attributes(realm, user_id, attributes)
                
                return user_id
            
            elif response.status_code == 409:
                logger.warning(f"User already exists: {username}")
                raise KeycloakUserExistsError(f"User {username} already exists in realm {realm}")
            
            else:
                error_msg = response.text
                logger.error(f"Failed to create user: {response.status_code} - {error_msg}")
                raise KeycloakAPIError(f"User creation failed: {response.status_code} - {error_msg}")
                
        except (KeycloakUserExistsError, KeycloakAttributePersistenceError):
            raise
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise KeycloakAPIError(f"User creation error: {str(e)}")
    
    async def _verify_and_fix_user_attributes(
        self,
        realm: str,
        user_id: str,
        expected_attributes: Dict[str, List[str]],
        max_retries: int = 3
    ) -> None:
        """
        Verify user attributes persisted correctly.
        
        If attributes didn't persist, retry with exponential backoff.
        This handles Keycloak v25.0 attribute persistence issues.
        
        Args:
            realm: Realm name
            user_id: User ID
            expected_attributes: Expected attributes
            max_retries: Maximum retry attempts
        
        Raises:
            KeycloakAttributePersistenceError: If attributes don't persist after retries
        """
        logger.debug(f"Verifying attributes for user {user_id}")
        
        for attempt in range(max_retries):
            # Brief delay for Keycloak to persist (especially on first attempt)
            if attempt > 0:
                wait_time = 0.5 * (2 ** attempt)  # 0.5s, 1s, 2s
                logger.warning(f"Retrying attribute verification (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
            else:
                # Even first check needs a small delay
                await asyncio.sleep(0.1)
            
            # Get current user attributes
            user = await self.get_user(realm, user_id)
            actual_attributes = user.get("attributes", {})
            
            # Check each expected attribute
            all_match = True
            missing_or_wrong = {}
            
            for key, expected_value in expected_attributes.items():
                actual_value = actual_attributes.get(key)
                if actual_value != expected_value:
                    all_match = False
                    missing_or_wrong[key] = {
                        "expected": expected_value,
                        "actual": actual_value
                    }
            
            if all_match:
                logger.info(f"✅ User attributes verified: {user_id}")
                return
            
            # Attributes don't match - log and retry
            logger.warning(
                f"Attribute mismatch for user {user_id}: {missing_or_wrong}"
            )
            
            # Update attributes for next attempt (if not last attempt)
            if attempt < max_retries - 1:
                await self.update_user_attributes(realm, user_id, expected_attributes)
        
        # After max_retries, still failed
        error_msg = f"User attributes did not persist after {max_retries} attempts: {user_id}"
        logger.error(error_msg)
        raise KeycloakAttributePersistenceError(error_msg)
    
    async def get_user(self, realm: str, user_id: str) -> Dict[str, Any]:
        """
        Get user by ID.
        
        Args:
            realm: Realm name
            user_id: User ID (UUID)
        
        Returns:
            User data dictionary
        """
        response = await self._make_request("GET", f"/realms/{realm}/users/{user_id}")
        response.raise_for_status()
        return response.json()
    
    async def get_user_by_username(
        self,
        realm: str,
        username: str,
        exact: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get user by username.
        
        Args:
            realm: Realm name
            username: Username to search
            exact: Exact match (default True)
        
        Returns:
            User data or None if not found
        """
        params = {"username": username}
        if exact:
            params["exact"] = "true"
        
        response = await self._make_request("GET", f"/realms/{realm}/users", params=params)
        response.raise_for_status()
        
        users = response.json()
        if users:
            return users[0]
        return None
    
    async def update_user_attributes(
        self,
        realm: str,
        user_id: str,
        attributes: Dict[str, List[str]],
        merge: bool = True
    ) -> None:
        """
        Update user attributes.
        
        Args:
            realm: Realm name
            user_id: User ID
            attributes: Attributes to update
            merge: If True, merge with existing attributes; if False, replace all
        """
        if merge:
            # Get current attributes and merge
            user = await self.get_user(realm, user_id)
            current_attrs = user.get("attributes", {})
            current_attrs.update(attributes)
            attributes = current_attrs
        
        response = await self._make_request(
            "PUT",
            f"/realms/{realm}/users/{user_id}",
            json_data={"attributes": attributes}
        )
        response.raise_for_status()
        logger.info(f"✅ Updated attributes for user {user_id}")
    
    async def set_user_password(
        self,
        realm: str,
        user_id: str,
        password: str,
        temporary: bool = False
    ) -> None:
        """
        Set user password.
        
        Args:
            realm: Realm name
            user_id: User ID
            password: New password
            temporary: If True, user must change password on next login
        """
        response = await self._make_request(
            "PUT",
            f"/realms/{realm}/users/{user_id}/reset-password",
            json_data={
                "type": "password",
                "value": password,
                "temporary": temporary
            }
        )
        
        if response.status_code not in [200, 204]:
            raise KeycloakAPIError(f"Failed to set password: {response.status_code}")
        
        logger.info(f"✅ Password set for user {user_id}")
    
    async def delete_user(self, realm: str, user_id: str) -> None:
        """
        Delete user.
        
        Args:
            realm: Realm name
            user_id: User ID
        """
        response = await self._make_request("DELETE", f"/realms/{realm}/users/{user_id}")
        
        if response.status_code == 204:
            logger.info(f"✅ User deleted: {user_id}")
        else:
            raise KeycloakAPIError(f"Failed to delete user: {response.status_code}")
    
    # ========================================================================
    # Role Management Methods
    # ========================================================================
    
    async def get_realm_roles(self, realm: str) -> List[Dict[str, Any]]:
        """Get all realm roles."""
        response = await self._make_request("GET", f"/realms/{realm}/roles")
        response.raise_for_status()
        return response.json()
    
    async def get_realm_role(self, realm: str, role_name: str) -> Optional[Dict[str, Any]]:
        """Get realm role by name."""
        try:
            response = await self._make_request("GET", f"/realms/{realm}/roles/{role_name}")
            response.raise_for_status()
            return response.json()
        except:
            return None
    
    async def assign_realm_role(self, realm: str, user_id: str, role_name: str) -> None:
        """
        Assign realm role to user.
        
        Args:
            realm: Realm name
            user_id: User ID
            role_name: Role name (e.g., "TENANT_ADMIN")
        """
        role = await self.get_realm_role(realm, role_name)
        if not role:
            raise KeycloakAPIError(f"Role not found: {role_name}")
        
        response = await self._make_request(
            "POST",
            f"/realms/{realm}/users/{user_id}/role-mappings/realm",
            json_data=[role]
        )
        
        if response.status_code in [200, 204]:
            logger.info(f"✅ Assigned role {role_name} to user {user_id}")
        else:
            raise KeycloakAPIError(f"Failed to assign role: {response.status_code}")
    
    async def get_user_realm_roles(self, realm: str, user_id: str) -> List[Dict[str, Any]]:
        """Get user's realm roles."""
        response = await self._make_request(
            "GET",
            f"/realms/{realm}/users/{user_id}/role-mappings/realm"
        )
        response.raise_for_status()
        return response.json()

    async def exchange_token_for_user(
        self,
        realm: str,
        user_id: str,
        client_id: str,
        scope: str = "openid offline_access"
    ) -> Optional[Dict[str, Any]]:
        """
        Exchange admin token for a user access/refresh token (Keycloak token exchange).
        Requires the calling client to have impersonation/token-exchange permissions.
        """
        try:
            subject_token = await self._get_admin_token()
            if not subject_token:
                logger.error("No admin token available for token exchange")
                return None

            client = self._get_client()
            token_url = f"{self.server_url}/realms/{realm}/protocol/openid-connect/token"
            data = {
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "client_id": client_id,
                "subject_token": subject_token,
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "requested_subject": user_id,
                "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "scope": scope,
            }

            response = await client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            token_data = response.json()
            logger.info(
                "Token exchange succeeded for realm %s",
                realm,
            )
            return token_data
        except Exception as exc:
            logger.error(f"Token exchange failed for user {user_id} in realm {realm}: {exc}", exc_info=True)
            return None
    
    # ========================================================================
    # Health & Utility Methods
    # ========================================================================
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check Keycloak connectivity and admin access.
        
        Returns:
            Health status dictionary
        """
        try:
            token = await self._get_admin_token()
            return {
                "status": "healthy",
                "keycloak_url": self.server_url,
                "admin_authenticated": True,
                "token_cached": self._admin_token is not None
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "keycloak_url": self.server_url,
                "admin_authenticated": False,
                "error": str(e)
            }
    
    async def close(self):
        """Close connection pool. Call when done using client."""
        if self._client:
            await self._client.aclose()
            self._client = None
