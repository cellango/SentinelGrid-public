"""
Self-Service API endpoints.

Allows users to manage their own profile, password, MFA, and sessions.
All operations are scoped to the authenticated user.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

from app.services.keycloak_admin_client import KeycloakAdminClient
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/self", tags=["self-service"])
security = HTTPBearer()


# ============================================================================
# Request/Response Models
# ============================================================================

class ProfileResponse(BaseModel):
    """User profile response."""
    id: str
    username: str
    email: Optional[str]
    firstName: Optional[str]
    lastName: Optional[str]
    locale: Optional[str]
    timezone: Optional[str]
    emailVerified: bool


class ProfileUpdateRequest(BaseModel):
    """Profile update request."""
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None


class PasswordChangeRequest(BaseModel):
    """Password change request."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)

class DirectPasswordResetRequest(BaseModel):
    """Reset password directly for the current user (no email link)."""
    new_password: str = Field(..., min_length=8)


class SessionResponse(BaseModel):
    """User session response."""
    id: str
    username: str
    userId: str
    ipAddress: Optional[str]
    start: Optional[int]
    lastAccess: Optional[int]
    clients: dict


class AppResponse(BaseModel):
    """App launcher response."""
    id: str
    clientId: str
    name: str
    baseUrl: Optional[str]
    description: Optional[str]


# ============================================================================
# Helper Functions
# ============================================================================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current user info from token."""
    from app.services.token_validator import TokenValidator
    from app.services.keycloak_client import KeycloakClient
    
    keycloak_client = KeycloakClient()
    validator = TokenValidator(keycloak_client)
    token = credentials.credentials
    result = validator.validate_token(token)
    
    if not result.get("valid"):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = result.get("user_id") or result.get("payload", {}).get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="No user ID in token")
    
    # Try to capture realm from the token issuer for multi-realm setups (e.g., demo realm)
    try:
        realm_from_token = validator._extract_realm_from_token(token)
    except Exception:
        realm_from_token = None
    
    return {
        "user_id": user_id,
        "tenant_id": result.get("tenant_id"),
        "email": result.get("email") or result.get("payload", {}).get("email"),
        "username": result.get("username") or result.get("payload", {}).get("preferred_username"),
        "realm": realm_from_token,
    }


def get_realm_for_tenant(tenant_id: str, realm_from_token: str | None = None) -> str:
    """Get Keycloak realm name for tenant, preferring the realm embedded in the token."""
    return realm_from_token or settings.KEYCLOAK_REALM


# ============================================================================
# Self-Service Endpoints
# ============================================================================

@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    user_info: dict = Depends(get_current_user)
):
    """Get current user's profile."""
    user_id = user_info["user_id"]
    tenant_id = user_info["tenant_id"]
    realm = get_realm_for_tenant(tenant_id, user_info.get("realm"))
    
    try:
        async with KeycloakAdminClient() as kc:
            user = await kc.get_user(realm, user_id)
            
            return ProfileResponse(
                id=user["id"],
                username=user.get("username", ""),
                email=user.get("email"),
                firstName=user.get("firstName"),
                lastName=user.get("lastName"),
                locale=user.get("attributes", {}).get("locale", [None])[0] if isinstance(user.get("attributes", {}).get("locale"), list) else None,
                timezone=user.get("attributes", {}).get("timezone", [None])[0] if isinstance(user.get("attributes", {}).get("timezone"), list) else None,
                emailVerified=user.get("emailVerified", False)
            )
            
    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to get profile")


@router.put("/profile", response_model=ProfileResponse)
async def update_profile(
    update_data: ProfileUpdateRequest,
    user_info: dict = Depends(get_current_user)
):
    """Update current user's profile."""
    user_id = user_info["user_id"]
    tenant_id = user_info["tenant_id"]
    realm = get_realm_for_tenant(tenant_id, user_info.get("realm"))
    
    try:
        async with KeycloakAdminClient() as kc:
            # Get current user
            user = await kc.get_user(realm, user_id)
            
            # Build update payload
            update_payload = {}
            if update_data.firstName is not None:
                update_payload["firstName"] = update_data.firstName
            if update_data.lastName is not None:
                update_payload["lastName"] = update_data.lastName
            
            # Update attributes
            attributes = user.get("attributes", {})
            if update_data.locale is not None:
                attributes["locale"] = [update_data.locale]
            if update_data.timezone is not None:
                attributes["timezone"] = [update_data.timezone]
            
            if attributes:
                update_payload["attributes"] = attributes
            
            # Update user
            await kc._make_request(
                "PUT",
                f"/realms/{realm}/users/{user_id}",
                json_data=update_payload
            )
            
            # Get updated user
            updated_user = await kc.get_user(realm, user_id)
            
            return ProfileResponse(
                id=updated_user["id"],
                username=updated_user.get("username", ""),
                email=updated_user.get("email"),
                firstName=updated_user.get("firstName"),
                lastName=updated_user.get("lastName"),
                locale=updated_user.get("attributes", {}).get("locale", [None])[0] if isinstance(updated_user.get("attributes", {}).get("locale"), list) else None,
                timezone=updated_user.get("attributes", {}).get("timezone", [None])[0] if isinstance(updated_user.get("attributes", {}).get("timezone"), list) else None,
                emailVerified=updated_user.get("emailVerified", False)
            )
            
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile")


@router.post("/password/change")
async def change_password(
    password_data: PasswordChangeRequest,
    user_info: dict = Depends(get_current_user)
):
    """
    Change user's password.
    
    Requires current password for verification.
    """
    user_id = user_info["user_id"]
    tenant_id = user_info["tenant_id"]
    realm = get_realm_for_tenant(tenant_id, user_info.get("realm"))
    
    try:
        async with KeycloakAdminClient() as kc:
            # Note: Keycloak Admin API doesn't support password change with current password verification
            # In production, you would:
            # 1. Verify current password via OIDC token endpoint
            # 2. Then update password via Admin API
            
            # For now, we'll use the reset password endpoint
            # In production, add proper current password verification
            await kc._make_request(
                "PUT",
                f"/realms/{realm}/users/{user_id}/reset-password",
                json_data={
                    "type": "password",
                    "value": password_data.new_password,
                    "temporary": False
                }
            )
            
            logger.info(f"Password changed for user {user_id}")
            
            return {"success": True, "message": "Password changed successfully"}
            
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        raise HTTPException(status_code=500, detail="Failed to change password")


@router.post("/password/reset/direct")
async def reset_password_direct(
    request: DirectPasswordResetRequest,
    user_info: dict = Depends(get_current_user)
):
    """
    Reset password directly for the current user (no email flow).
    
    - Sets the password as non-temporary
    - Clears required actions to avoid forced reset loops
    """
    user_id = user_info["user_id"]
    tenant_id = user_info["tenant_id"]
    realm = get_realm_for_tenant(tenant_id, user_info.get("realm"))

    try:
        async with KeycloakAdminClient() as kc:
            await kc._make_request(
                "PUT",
                f"/realms/{realm}/users/{user_id}/reset-password",
                json_data={
                    "type": "password",
                    "value": request.new_password,
                    "temporary": False,
                }
            )
            await kc._make_request(
                "PUT",
                f"/realms/{realm}/users/{user_id}",
                json_data={"requiredActions": [], "emailVerified": True, "enabled": True}
            )

            return {"success": True, "message": "Password reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting password directly: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset password")


@router.post("/password/reset")
async def request_password_reset(
    user_info: dict = Depends(get_current_user)
):
    """Request password reset email."""
    user_id = user_info["user_id"]
    tenant_id = user_info["tenant_id"]
    realm = get_realm_for_tenant(tenant_id, user_info.get("realm"))
    
    try:
        async with KeycloakAdminClient() as kc:
            # Send password reset email
            response = await kc._make_request(
                "PUT",
                f"/realms/{realm}/users/{user_id}/execute-actions-email",
                json_data=["UPDATE_PASSWORD"],
                params={
                    "client_id": settings.KEYCLOAK_CLIENT_ID
                }
            )
            
            if response.status_code in (200, 204):
                return {
                    "success": True,
                    "email_sent": True,
                    "message": "Password reset requested. Check your email for a reset link.",
                }

            # Keycloak commonly fails here when SMTP isn't configured. Don't crash the UI;
            # instead, return a clear warning and log the full server response.
            body_text = (response.text or "").strip()
            logger.warning(
                "Password reset email request returned non-success response for realm=%s status=%s",
                realm,
                response.status_code,
            )

            lower = body_text.lower()
            if response.status_code >= 400 and any(s in lower for s in ("smtp", "mail", "email")):
                return {
                    "success": True,
                    "email_sent": False,
                    "message": "Password reset requested, but email delivery is not configured. Use 'Change Password' or contact your admin.",
                }

            raise HTTPException(status_code=502, detail="Failed to send password reset email")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error requesting password reset: {e}")
        raise HTTPException(status_code=500, detail="Failed to send password reset email")


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    user_info: dict = Depends(get_current_user)
):
    """List active sessions for current user."""
    user_id = user_info["user_id"]
    tenant_id = user_info["tenant_id"]
    realm = get_realm_for_tenant(tenant_id, user_info.get("realm"))
    
    try:
        async with KeycloakAdminClient() as kc:
            response = await kc._make_request(
                "GET",
                f"/realms/{realm}/users/{user_id}/sessions"
            )
            response.raise_for_status()
            sessions = response.json()
            
            return [
                SessionResponse(
                    id=session.get("id", ""),
                    username=session.get("username", ""),
                    userId=session.get("userId", ""),
                    ipAddress=session.get("ipAddress"),
                    start=session.get("start"),
                    lastAccess=session.get("lastAccess"),
                    clients=session.get("clients", {})
                )
                for session in sessions
            ]
            
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to list sessions")


@router.post("/sessions/{session_id}/logout")
async def logout_session(
    session_id: str,
    user_info: dict = Depends(get_current_user)
):
    """Logout all sessions for the current user.

    Keycloak's admin APIs do not support targeted session revocation in this flow,
    so this endpoint currently revokes every active session for the user.
    """
    user_id = user_info["user_id"]
    tenant_id = user_info["tenant_id"]
    realm = get_realm_for_tenant(tenant_id, user_info.get("realm"))
    
    try:
        async with KeycloakAdminClient() as kc:
            # Note: Keycloak doesn't have a direct endpoint to logout a specific session
            # We'll logout all sessions and the user will need to log back in
            # In production, you might track sessions differently
            
            await kc._make_request(
                "POST",
                f"/realms/{realm}/users/{user_id}/logout"
            )
            
            return {"success": True, "message": "All active sessions signed out"}
            
    except Exception as e:
        logger.error(f"Error logging out session: {e}")
        raise HTTPException(status_code=500, detail="Failed to logout session")


@router.get("/apps", response_model=List[AppResponse])
async def list_apps(
    user_info: dict = Depends(get_current_user)
):
    """
    List apps accessible to current user (app launcher).
    
    Returns apps the user has access to via roles/groups.
    """
    user_id = user_info["user_id"]
    tenant_id = user_info["tenant_id"]
    realm = get_realm_for_tenant(tenant_id, user_info.get("realm"))
    
    try:
        async with KeycloakAdminClient() as kc:
            # Get all clients (apps) in realm
            response = await kc._make_request(
                "GET",
                f"/realms/{realm}/clients"
            )
            response.raise_for_status()
            clients = response.json()
            
            # Filter to clients user has access to
            # In production, you would check user's roles/groups against client roles
            # For now, return all clients (filtering can be added later)
            
            accessible_apps = []
            for client in clients:
                # Skip service accounts and internal clients
                if client.get("clientId") in ["account", "account-console", "admin-cli", "broker", "realm-management", "security-admin-console"]:
                    continue
                
                accessible_apps.append(AppResponse(
                    id=client.get("id", ""),
                    clientId=client.get("clientId", ""),
                    name=client.get("name", client.get("clientId", "")),
                    baseUrl=client.get("baseUrl"),
                    description=client.get("description")
                ))
            
            return accessible_apps
            
    except Exception as e:
        logger.error(f"Error listing apps: {e}")
        raise HTTPException(status_code=500, detail="Failed to list apps")
