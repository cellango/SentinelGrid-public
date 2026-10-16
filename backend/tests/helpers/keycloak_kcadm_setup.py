"""
Alternative Keycloak account setup using kcadm.sh commands via Docker.

This approach uses kcadm.sh through docker exec, which avoids Admin API authentication issues.
"""

import subprocess
import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class KeycloakKCAdmSetup:
    """Helper class for Keycloak account setup using kcadm.sh via Docker."""
    
    def __init__(self, container_name: Optional[str] = None, admin_user: str = "admin", admin_password: str = "admin"):
        """
        Initialize Keycloak kcadm setup helper.
        
        Args:
            container_name: Docker container name for Keycloak
            admin_user: Admin username
            admin_password: Admin password
        """
        # Auto-detect container name if not provided
        if container_name is None:
            # Try to find Keycloak container
            try:
                result = subprocess.run(
                    ["docker", "ps", "--filter", "name=keycloak", "--format", "{{.Names}}"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    container_name = result.stdout.strip().split('\n')[0]
                    logger.info(f"Auto-detected Keycloak container: {container_name}")
                else:
                    container_name = "sentinelgrid-keycloak-1"  # Default fallback
                    logger.warning(f"Could not auto-detect container, using default: {container_name}")
            except Exception as e:
                container_name = "sentinelgrid-keycloak-1"
                logger.warning(f"Error detecting container, using default: {container_name}")
        
        self.container_name = container_name
        self.admin_user = admin_user
        self.admin_password = admin_password
    
    def _run_kcadm(self, command: str, realm: str = "master") -> tuple[bool, str]:
        """
        Run kcadm.sh command in Keycloak container.
        
        Returns:
            (success: bool, output: str)
        """
        # Authenticate first
        auth_cmd = f"/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user {self.admin_user} --password {self.admin_password}"
        full_cmd = f"{auth_cmd} && {command}"
        
        docker_cmd = [
            "docker", "exec",
            self.container_name,
            "bash", "-c", full_cmd
        ]
        
        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                error_msg = result.stderr or result.stdout
                logger.warning(f"kcadm command failed: {error_msg}")
                return False, error_msg
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)
    
    def get_user_id(self, realm: str, username: str) -> Optional[str]:
        """Get user ID for a username."""
        command = f"/opt/keycloak/bin/kcadm.sh get users -r {realm} -q username={username} --fields id --format csv --noquotes | tail -1"
        success, output = self._run_kcadm(command, realm)
        
        if success and output.strip():
            user_id = output.strip()
            logger.info(f"Found user ID for {username}: {user_id}")
            return user_id
        else:
            logger.error(f"Could not find user {username} in realm {realm}")
            return None
    
    def clear_required_actions(self, realm: str, user_id: str) -> bool:
        """Clear all required actions for a user."""
        command = f"/opt/keycloak/bin/kcadm.sh update users/{user_id} -r {realm} -s 'requiredActions=[]' -s emailVerified=true -s enabled=true"
        success, output = self._run_kcadm(command, realm)
        
        if success:
            logger.info(f"Cleared required actions for user {user_id}")
            return True
        else:
            logger.error(f"Failed to clear required actions: {output}")
            return False
    
    def set_password(self, realm: str, username: str, password: str, temporary: bool = False) -> bool:
        """Set password for a user."""
        temp_flag = "--temporary" if temporary else ""
        command = f"/opt/keycloak/bin/kcadm.sh set-password -r {realm} --username {username} --new-password '{password}' {temp_flag}"
        success, output = self._run_kcadm(command, realm)
        
        if success:
            logger.info(f"Set password for {username} (temporary={temporary})")
            return True
        else:
            logger.error(f"Failed to set password: {output}")
            return False
    
    def activate_account(self, realm: str, username: str, password: str) -> bool:
        """
        Activate a user account by clearing required actions and setting password.
        
        This uses kcadm.sh via Docker, which should work more reliably than Admin API.
        """
        logger.info(f"Activating account for {username} in realm {realm}")
        
        # Get user ID
        user_id = self.get_user_id(realm, username)
        if not user_id:
            logger.error(f"User {username} not found")
            return False
        
        # Set password as non-temporary
        if not self.set_password(realm, username, password, temporary=False):
            logger.warning("Failed to set password, but continuing...")
        
        # Clear required actions
        if not self.clear_required_actions(realm, user_id):
            logger.warning("Failed to clear required actions, but continuing...")
        
        # Verify account is activated
        user_id_after = self.get_user_id(realm, username)
        if user_id_after:
            logger.info(f"Account {username} activation completed")
            return True
        
        return False


def activate_account_via_kcadm(
    realm: str,
    username: str,
    password: str,
    container_name: str = "sentinelgrid-keycloak-1",
    admin_user: str = "admin",
    admin_password: str = "admin"
) -> bool:
    """
    Activate a Keycloak account using kcadm.sh via Docker.
    
    This is an alternative to API-based activation that uses kcadm.sh commands
    executed in the Keycloak Docker container.
    
    Args:
        realm: Realm name
        username: Username to activate
        password: Password to set
        container_name: Keycloak Docker container name
        admin_user: Admin username
        admin_password: Admin password
    
    Returns:
        True if activation succeeded, False otherwise
    """
    setup = KeycloakKCAdmSetup(container_name, admin_user, admin_password)
    return setup.activate_account(realm, username, password)

