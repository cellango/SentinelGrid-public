"""
Helper functions for setting up Keycloak user accounts for testing.

Provides both API-based and UI-based approaches to activate accounts.
"""

import httpx
import logging
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)


class KeycloakAccountSetup:
    """Helper class for Keycloak account setup and activation."""
    
    def __init__(self, keycloak_url: str, realm: str, admin_username: str, admin_password: str):
        """
        Initialize Keycloak account setup helper.
        
        Args:
            keycloak_url: Base URL for Keycloak (e.g., http://localhost:8081)
            realm: Realm name (e.g., 'agribotsai' or 'master' for admin)
            admin_username: Admin username for the master realm
            admin_password: Admin password for the master realm
        """
        self.keycloak_url = keycloak_url.rstrip('/')
        self.realm = realm
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.admin_token: Optional[str] = None
    
    def _get_admin_token(self) -> str:
        """Get admin access token from master realm."""
        if self.admin_token:
            return self.admin_token
        
        # Try admin-cli client first
        token_url = f"{self.keycloak_url}/realms/master/protocol/openid-connect/token"
        data = {
            "client_id": "admin-cli",
            "username": self.admin_username,
            "password": self.admin_password,
            "grant_type": "password",
        }
        
        with httpx.Client(timeout=10.0) as client:
            response = client.post(token_url, data=data)
            if response.status_code != 200:
                # Fallback: Try without client_id (some Keycloak configs)
                logger.warning(f"admin-cli authentication failed ({response.status_code}), trying alternative...")
                data_no_client = {
                    "username": self.admin_username,
                    "password": self.admin_password,
                    "grant_type": "password",
                }
                response = client.post(token_url, data=data_no_client)
            
            response.raise_for_status()
            self.admin_token = response.json()["access_token"]
            return self.admin_token
    
    def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user information from Keycloak Admin API."""
        token = self._get_admin_token()
        users_url = f"{self.keycloak_url}/admin/realms/{self.realm}/users"
        params = {"username": username, "exact": "true"}
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        with httpx.Client(timeout=10.0) as client:
            response = client.get(users_url, headers=headers, params=params)
            response.raise_for_status()
            users = response.json()
            return users[0] if users else None
    
    def clear_required_actions(self, user_id: str) -> bool:
        """Clear all required actions for a user via Admin API."""
        token = self._get_admin_token()
        user_url = f"{self.keycloak_url}/admin/realms/{self.realm}/users/{user_id}"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        # Get current user data
        with httpx.Client(timeout=10.0) as client:
            response = client.get(user_url, headers=headers)
            response.raise_for_status()
            user_data = response.json()
            
            # Update user to clear required actions and verify email
            user_data["requiredActions"] = []
            user_data["emailVerified"] = True
            
            response = client.put(user_url, headers=headers, json=user_data)
            response.raise_for_status()
            logger.info(f"Cleared required actions for user {user_id}")
            return True
    
    def set_password(self, user_id: str, password: str, temporary: bool = False) -> bool:
        """Set password for a user via Admin API."""
        token = self._get_admin_token()
        password_url = f"{self.keycloak_url}/admin/realms/{self.realm}/users/{user_id}/reset-password"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "type": "password",
            "value": password,
            "temporary": temporary,
        }
        
        with httpx.Client(timeout=10.0) as client:
            response = client.put(password_url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info(f"Set password for user {user_id} (temporary={temporary})")
            return True
    
    def complete_password_update_via_api(self, username: str, old_password: str, new_password: str) -> bool:
        """
        Attempt to complete password update via API.
        
        This may not work if Keycloak requires UI interaction.
        """
        # Try to authenticate with old password
        token_url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"
        data = {
            "client_id": "agribotsai-web",
            "username": username,
            "password": old_password,
            "grant_type": "password",
        }
        
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.post(token_url, data=data)
            
            # If we get a redirect or special response, there might be required actions
            if response.status_code == 200:
                token_data = response.json()
                if "access_token" in token_data:
                    # Already working, update password via admin API
                    user_info = self.get_user_info(username)
                    if user_info:
                        self.set_password(user_info["id"], new_password, temporary=False)
                        return True
            
            # Check if there's a required action response
            logger.warning(f"Could not complete password update via API for {username}")
            return False
    
    def activate_account(self, username: str, password: str) -> bool:
        """
        Activate a user account by clearing required actions and setting password.
        
        This is a best-effort attempt to activate the account programmatically.
        """
        user_info = self.get_user_info(username)
        if not user_info:
            logger.error(f"User {username} not found")
            return False
        
        user_id = user_info["id"]
        logger.info(f"Activating account for {username} (ID: {user_id})")
        
        # Set password as non-temporary
        self.set_password(user_id, password, temporary=False)
        
        # Clear required actions
        self.clear_required_actions(user_id)
        
        # Verify account is activated
        user_info_after = self.get_user_info(username)
        if user_info_after:
            required_actions = user_info_after.get("requiredActions", [])
            if len(required_actions) == 0:
                logger.info(f"Account {username} activated successfully")
                return True
            else:
                logger.warning(f"Account {username} still has required actions: {required_actions}")
                return False
        
        return False


def setup_test_user(
    keycloak_url: str,
    realm: str,
    username: str,
    password: str,
    admin_username: str = "admin",
    admin_password: str = "admin"
) -> bool:
    """
    Setup a test user account for testing.
    
    This function attempts to activate the account programmatically.
    If it fails, you may need to use the UI-based activation (Selenium).
    
    Args:
        keycloak_url: Keycloak base URL
        realm: Realm name
        username: Username to activate
        password: Password to set
        admin_username: Admin username for master realm
        admin_password: Admin password for master realm
    
    Returns:
        True if account was activated, False otherwise
    """
    setup = KeycloakAccountSetup(keycloak_url, realm, admin_username, admin_password)
    return setup.activate_account(username, password)

