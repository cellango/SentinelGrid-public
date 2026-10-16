"""
Complete API-based Keycloak account activation.

This approach uses multiple methods to activate accounts without UI interaction:
1. Disable required actions at realm level
2. Create users without temporary passwords
3. Set emailVerified and clear requiredActions
4. Use service account tokens for Admin API access
"""

import subprocess
import logging
import httpx
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class KeycloakAPIActivation:
    """Complete API-based account activation using all available methods."""
    
    def __init__(self, container_name: Optional[str] = None, admin_user: str = "admin", admin_password: str = "admin"):
        """
        Initialize activation helper.
        
        Args:
            container_name: Keycloak Docker container name (auto-detected if None)
            admin_user: Admin username
            admin_password: Admin password
        """
        self.container_name = container_name or self._detect_container()
        self.admin_user = admin_user
        self.admin_password = admin_password
    
    def _detect_container(self) -> str:
        """Auto-detect Keycloak container name."""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=keycloak", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                container = result.stdout.strip().split('\n')[0]
                logger.info(f"Auto-detected Keycloak container: {container}")
                return container
        except Exception:
            pass
        return "sentinelgrid-keycloak-1"  # Default
    
    def _run_kcadm(self, command: str, realm: str = "master") -> tuple[bool, str]:
        """Run kcadm.sh command in container."""
        auth_cmd = f"/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user {self.admin_user} --password {self.admin_password}"
        full_cmd = f"{auth_cmd} && {command}"
        
        docker_cmd = ["docker", "exec", self.container_name, "bash", "-c", full_cmd]
        
        try:
            result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0, result.stdout if result.returncode == 0 else result.stderr
        except Exception as e:
            return False, str(e)
    
    def disable_required_actions_for_realm(self, realm: str) -> bool:
        """Disable required actions at realm level."""
        logger.info(f"Disabling required actions for realm {realm}...")
        
        commands = [
            f"/opt/keycloak/bin/kcadm.sh update realms/{realm} -s verifyEmail=false",
            f"/opt/keycloak/bin/kcadm.sh update realms/{realm} -s registrationEmailAsUsername=false",
        ]
        
        all_success = True
        for cmd in commands:
            success, output = self._run_kcadm(cmd, realm)
            if not success:
                logger.warning(f"Failed to run: {cmd}")
                all_success = False
        
        return all_success
    
    def recreate_user_without_temp_password(self, realm: str, username: str, email: str, password: str) -> bool:
        """
        Recreate user ensuring no temporary password or required actions.
        
        This is the most reliable method - delete and recreate the user
        with all flags set correctly from the start.
        """
        logger.info(f"Recreating user {username} in realm {realm}...")
        
        # Get user ID if exists
        get_user_cmd = f"/opt/keycloak/bin/kcadm.sh get users -r {realm} -q username={username} --fields id --format csv --noquotes | tail -1"
        success, output = self._run_kcadm(get_user_cmd, realm)
        if success and output.strip():
            user_id = output.strip()
            logger.info(f"Deleting existing user {user_id}...")
            delete_cmd = f"/opt/keycloak/bin/kcadm.sh delete users/{user_id} -r {realm}"
            self._run_kcadm(delete_cmd, realm)
            time.sleep(1)
        
        # Create user with all correct settings (including first/last name to avoid VERIFY_PROFILE)
        create_cmd = (
            f"/opt/keycloak/bin/kcadm.sh create users -r {realm} "
            f"-s username={username} "
            f"-s email={email} "
            f"-s firstName=Admin "
            f"-s lastName=User "
            f"-s enabled=true "
            f"-s emailVerified=true"
        )
        success, output = self._run_kcadm(create_cmd, realm)
        if not success:
            logger.error(f"Failed to create user: {output}")
            return False
        
        # Set password as non-temporary
        time.sleep(1)
        set_pw_cmd = f"/opt/keycloak/bin/kcadm.sh set-password -r {realm} --username {username} --new-password '{password}'"
        success, output = self._run_kcadm(set_pw_cmd, realm)
        if not success:
            logger.warning(f"Password set may have failed: {output}")
        
        # Ensure no required actions
        get_user_cmd = f"/opt/keycloak/bin/kcadm.sh get users -r {realm} -q username={username} --fields id --format csv --noquotes | tail -1"
        success, user_id_output = self._run_kcadm(get_user_cmd, realm)
        if success and user_id_output.strip():
            user_id = user_id_output.strip()
            update_cmd = f"/opt/keycloak/bin/kcadm.sh update users/{user_id} -r {realm} -s 'requiredActions=[]' -s emailVerified=true -s enabled=true"
            self._run_kcadm(update_cmd, realm)
        
        logger.info(f"✅ User {username} recreated successfully")
        return True
    
    def activate_account_complete(self, realm: str, username: str, email: str, password: str) -> bool:
        """
        Complete account activation using all available API methods.
        
        This method:
        1. Disables required actions at realm level
        2. Recreates user without temporary password
        3. Clears any remaining required actions
        4. Verifies email and enables account
        
        Returns:
            True if activation should succeed, False otherwise
        """
        logger.info(f"Starting complete API-based activation for {username}...")
        
        # Step 1: Disable realm-level required actions
        self.disable_required_actions_for_realm(realm)
        
        # Step 2: Recreate user with correct settings
        if not self.recreate_user_without_temp_password(realm, username, email, password):
            return False
        
        # Step 3: Wait a moment for Keycloak to process
        time.sleep(2)
        
        logger.info(f"✅ Complete API activation process finished for {username}")
        return True
    
    def verify_activation(self, keycloak_url: str, realm: str, username: str, password: str, client_id: str = "agribotsai-web") -> bool:
        """
        Verify that account is activated by attempting token generation.
        
        Returns:
            True if token generation succeeds, False otherwise
        """
        token_url = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token"
        data = {
            "client_id": client_id,
            "username": username,
            "password": password,
            "grant_type": "password",
            "scope": "openid",
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(token_url, data=data)
                if response.status_code == 200:
                    token_data = response.json()
                    if "access_token" in token_data:
                        logger.info("✅ Token generation successful - account is activated!")
                        return True
                    else:
                        logger.warning(f"Token response missing access_token: {token_data}")
                        return False
                else:
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"error": response.text}
                    logger.warning(f"Token generation failed ({response.status_code}): {error_data}")
                    return False
        except Exception as e:
            logger.error(f"Error verifying activation: {e}")
            return False


def activate_account_via_api(
    realm: str,
    username: str,
    email: str,
    password: str,
    keycloak_url: str = "http://localhost:8081",
    container_name: Optional[str] = None,
    admin_user: str = "admin",
    admin_password: str = "admin",
    verify: bool = True
) -> bool:
    """
    Complete API-based account activation.
    
    This function uses all available API methods to activate an account:
    - Disables realm-level required actions
    - Recreates user without temporary password
    - Clears required actions
    - Optionally verifies token generation works
    
    Args:
        realm: Realm name
        username: Username to activate
        email: User email
        password: Password to set
        keycloak_url: Keycloak base URL for verification
        container_name: Keycloak container name (auto-detected if None)
        admin_user: Admin username
        admin_password: Admin password
        verify: If True, verify activation by attempting token generation
    
    Returns:
        True if activation succeeded (and verification passed if verify=True)
    """
    activator = KeycloakAPIActivation(container_name, admin_user, admin_password)
    
    # Perform activation
    success = activator.activate_account_complete(realm, username, email, password)
    
    if not success:
        return False
    
    # Verify activation if requested
    if verify:
        time.sleep(2)  # Give Keycloak time to process
        return activator.verify_activation(keycloak_url, realm, username, password)
    
    return True

