"""
Invitation Service for user onboarding.

Handles creation, management, and tracking of user invitations.
"""

import logging
import secrets
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.keycloak_admin_client import KeycloakAdminClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class InvitationService:
    """Service for managing user invitations."""
    
    def __init__(self):
        self.keycloak_admin = KeycloakAdminClient()
    
    def _ensure_user_profile_configured(self, realm: str) -> None:
        """
        Fail-safe: Ensure User Profile is configured for the realm.
        
        If User Profile is not configured, attempts to configure it automatically.
        This ensures tenant_id attributes will persist even if realm was created
        outside of the centralized realm creation service.
        """
        try:
            import sys
            # Add /app/libs to path for sg_core imports (mounted at /app/libs in container)
            libs_path = "/app/libs"
            if libs_path not in sys.path:
                sys.path.insert(0, libs_path)
            from sg_core.keycloak_user_profile import verify_user_profile_configured, configure_realm_user_profile
            
            # Check if User Profile is configured
            is_configured = verify_user_profile_configured(realm)
            
            if not is_configured:
                logger.warning(
                    f"⚠️  User Profile not configured for realm '{realm}'. "
                    "Attempting to configure automatically (fail-safe)..."
                )
                
                # Attempt to configure User Profile
                success = configure_realm_user_profile(realm)
                
                if success:
                    logger.info(f"✅ User Profile configured for realm '{realm}' (fail-safe)")
                else:
                    logger.error(
                        f"❌ CRITICAL: Failed to configure User Profile for realm '{realm}'. "
                        "Custom attributes (tenant_id) will NOT persist!"
                    )
        except Exception as e:
            logger.warning(f"Error checking/configuring User Profile (fail-safe): {e}")
    
    async def create_invitation(
        self,
        tenant_id: str,
        realm: str,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        role: Optional[str] = None,
        expires_in_days: int = 7,
        send_email: bool = True
    ) -> Dict:
        """
        Create a user invitation.
        
        Creates a disabled user in Keycloak and generates an invitation token.
        If send_email is True, sends invitation email via Keycloak.
        
        CRITICAL: Verifies User Profile is configured before creating user.
        If not configured, attempts to configure it automatically (fail-safe).
        """
        # Fail-safe: Verify User Profile is configured
        self._ensure_user_profile_configured(realm)
        invitation_id = str(uuid4())
        invitation_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        try:
            async with self.keycloak_admin as kc:
                # Check if user already exists
                existing_users = await kc._make_request(
                    "GET",
                    f"/realms/{realm}/users",
                    params={"email": email, "exact": "true"}
                )
                existing_users.raise_for_status()
                users = existing_users.json()
                
                if users:
                    raise ValueError(f"User with email {email} already exists")
                
                # Create user in Keycloak (disabled initially)
                user_data = {
                    "username": email,
                    "email": email,
                    "firstName": first_name or "",
                    "lastName": last_name or "",
                    "enabled": False,  # Disabled until invitation is accepted
                    "emailVerified": False,
                    "attributes": {
                        "tenant_id": [tenant_id],
                        "invitation_id": [invitation_id],
                        "invitation_token": [invitation_token],
                        "invitation_expires_at": [expires_at.isoformat()]
                    },
                    "requiredActions": ["VERIFY_EMAIL", "UPDATE_PASSWORD"]
                }
                
                response = await kc._make_request(
                    "POST",
                    f"/realms/{realm}/users",
                    json_data=user_data
                )
                response.raise_for_status()
                
                # Get created user ID from Location header
                user_id = response.headers.get("Location", "").split("/")[-1]
                
                # Set temporary password (user will be forced to change it)
                temp_password = secrets.token_urlsafe(16)
                await kc._make_request(
                    "PUT",
                    f"/realms/{realm}/users/{user_id}/reset-password",
                    json_data={
                        "type": "password",
                        "value": temp_password,
                        "temporary": True
                    }
                )
                
                # Assign role if specified
                if role:
                    try:
                        realm_roles = await kc._make_request(
                            "GET",
                            f"/realms/{realm}/roles"
                        )
                        realm_roles.raise_for_status()
                        roles = realm_roles.json()
                        
                        role_obj = next((r for r in roles if r["name"] == role), None)
                        if role_obj:
                            await kc._make_request(
                                "POST",
                                f"/realms/{realm}/users/{user_id}/role-mappings/realm",
                                json_data=[role_obj]
                            )
                    except Exception as e:
                        logger.warning(f"Failed to assign role {role}: {e}")
                
                # Send invitation email if requested
                if send_email:
                    try:
                        await kc._make_request(
                            "PUT",
                            f"/realms/{realm}/users/{user_id}/execute-actions-email",
                            json_data=["VERIFY_EMAIL"],
                            params={
                                "client_id": settings.KEYCLOAK_CLIENT_ID,
                                "redirect_uri": f"{settings.KEYCLOAK_URL}/realms/{realm}/account"
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send invitation email: {e}")
                
                return {
                    "invitation_id": invitation_id,
                    "user_id": user_id,
                    "email": email,
                    "invitation_token": invitation_token,
                    "expires_at": expires_at,
                    "status": "pending"
                }
                
        except Exception as e:
            logger.error(f"Error creating invitation: {e}", exc_info=True)
            raise
    
    async def list_invitations(
        self,
        tenant_id: str,
        realm: str,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict:
        """
        List invitations for a tenant.
        
        Note: This queries Keycloak users with invitation attributes.
        In production, you might want to store invitations in a database.
        """
        invitations = []
        
        try:
            async with self.keycloak_admin as kc:
                # Get all users with invitation attributes
                response = await kc._make_request(
                    "GET",
                    f"/realms/{realm}/users"
                )
                response.raise_for_status()
                users = response.json()
                
                # Filter by tenant_id and invitation attributes
                for user in users:
                    attrs = user.get("attributes", {})
                    user_tenant_id = attrs.get("tenant_id", [None])[0] if isinstance(attrs.get("tenant_id"), list) else None
                    
                    if user_tenant_id != tenant_id:
                        continue
                    
                    invitation_id = attrs.get("invitation_id", [None])[0] if isinstance(attrs.get("invitation_id"), list) else None
                    if not invitation_id:
                        continue
                    
                    invitation_token = attrs.get("invitation_token", [None])[0] if isinstance(attrs.get("invitation_token"), list) else None
                    expires_at_str = attrs.get("invitation_expires_at", [None])[0] if isinstance(attrs.get("invitation_expires_at"), list) else None
                    
                    # Determine status
                    inv_status = "pending"
                    if user.get("enabled"):
                        inv_status = "accepted"
                    elif expires_at_str:
                        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                        if datetime.utcnow() > expires_at:
                            inv_status = "expired"
                    
                    if status and inv_status != status:
                        continue
                    
                    invitations.append({
                        "invitation_id": invitation_id,
                        "user_id": user["id"],
                        "email": user.get("email"),
                        "invitation_token": invitation_token,
                        "expires_at": datetime.fromisoformat(expires_at_str.replace("Z", "+00:00")) if expires_at_str else None,
                        "status": inv_status
                    })
                
                # Paginate
                total = len(invitations)
                start = (page - 1) * limit
                end = start + limit
                paginated = invitations[start:end]
                
                return {
                    "items": paginated,
                    "total": total,
                    "page": page,
                    "limit": limit
                }
                
        except Exception as e:
            logger.error(f"Error listing invitations: {e}", exc_info=True)
            raise
    
    async def cancel_invitation(self, tenant_id: str, invitation_id: str, realm: str) -> None:
        """Cancel an invitation by deleting the user account."""
        
        try:
            async with self.keycloak_admin as kc:
                # Find user by invitation_id
                response = await kc._make_request(
                    "GET",
                    f"/realms/{realm}/users"
                )
                response.raise_for_status()
                users = response.json()
                
                for user in users:
                    attrs = user.get("attributes", {})
                    user_tenant_id = attrs.get("tenant_id", [None])[0] if isinstance(attrs.get("tenant_id"), list) else None
                    user_invitation_id = attrs.get("invitation_id", [None])[0] if isinstance(attrs.get("invitation_id"), list) else None
                    
                    if user_tenant_id == tenant_id and user_invitation_id == invitation_id:
                        # Delete user
                        await kc._make_request(
                            "DELETE",
                            f"/realms/{realm}/users/{user['id']}"
                        )
                        logger.info(f"Cancelled invitation {invitation_id}")
                        return
                
                raise ValueError(f"Invitation {invitation_id} not found")
                
        except Exception as e:
            logger.error(f"Error cancelling invitation: {e}", exc_info=True)
            raise
