"""
User Management API endpoints.

All endpoints enforce strict tenant isolation - users can only access
and manage users within their own tenant.

Security: Every endpoint validates tenant_id from JWT token and ensures
resources belong to the authenticated user's tenant.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

from app.services.keycloak_admin_client import KeycloakAdminClient, KeycloakUserExistsError, KeycloakAPIError
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/users", tags=["users"])


# ============================================================================
# Request/Response Models
# ============================================================================

class UserResponse(BaseModel):
    """User response model."""
    id: str
    username: str
    email: Optional[str]
    firstName: Optional[str]
    lastName: Optional[str]
    enabled: bool
    emailVerified: bool
    tenant_id: Optional[str]
    customer_id: Optional[str]
    createdTimestamp: Optional[int]


class UserListResponse(BaseModel):
    """Paginated user list response."""
    items: List[UserResponse]
    total: int
    page: int
    limit: int
    pages: int


class UserUpdateRequest(BaseModel):
    """User update request."""
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[EmailStr] = None
    enabled: Optional[bool] = None


class UserSearchRequest(BaseModel):
    """User search request."""
    query: str = Field(..., min_length=1, description="Search query (email, name, username)")
    role: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(enabled|disabled)$")


# ============================================================================
# Helper Functions
# ============================================================================

async def get_token_data(credentials: str) -> dict:
    """Extract and validate token, return token data with tenant_id."""
    from app.services.token_validator import TokenValidator
    from app.services.keycloak_client import KeycloakClient
    
    # Validate token
    keycloak_client = KeycloakClient()
    validator = TokenValidator(keycloak_client)
    result = validator.validate_token(credentials)
    
    if not result.get("valid"):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    if not result.get("tenant_id"):
        raise HTTPException(status_code=403, detail="No tenant_id in token")
    
    return result


def get_realm_for_tenant(tenant_id: str) -> str:
    """
    Get Keycloak realm name for tenant.
    
    For now, returns 'sentinelgrid' (shared realm).
    In future, may query database for dedicated realm mapping.
    """
    # TODO: Query database for tenant → realm mapping
    return settings.KEYCLOAK_REALM


def extract_tenant_id_from_user(user: dict) -> Optional[str]:
    """Extract tenant_id from Keycloak user attributes."""
    attributes = user.get("attributes", {})
    tenant_id = attributes.get("tenant_id")
    
    if isinstance(tenant_id, list):
        return tenant_id[0] if tenant_id else None
    
    return tenant_id


def user_belongs_to_tenant(user: dict, tenant_id: str) -> bool:
    """Check if user belongs to the specified tenant."""
    user_tenant_id = extract_tenant_id_from_user(user)
    return user_tenant_id == tenant_id


# ============================================================================
# User Management Endpoints
# ============================================================================

@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by email, name, or username"),
    role: Optional[str] = Query(None, description="Filter by role"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    List users with pagination and filtering.
    
    SECURITY: Only returns users belonging to the authenticated user's tenant.
    """
    # Validate token and extract tenant_id
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    logger.info(f"Listing users for tenant {tenant_id}, page {page}, limit {limit}")
    
    try:
        async with KeycloakAdminClient() as kc:
            # Get all users in realm
            # Build query parameters
            params = {}
            if search:
                params["search"] = search
            if enabled is not None:
                params["enabled"] = enabled
            
            # Get users from Keycloak
            response = await kc._make_request(
                "GET",
                f"/realms/{realm}/users",
                params=params
            )
            response.raise_for_status()
            all_users = response.json()
            
            # CRITICAL: Filter to only this tenant's users
            tenant_users = [
                user for user in all_users
                if user_belongs_to_tenant(user, tenant_id)
            ]
            
            # Additional role filtering if requested
            if role:
                filtered_users = []
                for user in tenant_users:
                    user_roles = await kc.get_user_realm_roles(realm, user["id"])
                    role_names = [r.get("name") for r in user_roles]
                    if role in role_names:
                        filtered_users.append(user)
                tenant_users = filtered_users
            
            # Calculate pagination
            total = len(tenant_users)
            pages = (total + limit - 1) // limit
            start = (page - 1) * limit
            end = start + limit
            paginated_users = tenant_users[start:end]
            
            # Convert to response model
            user_responses = []
            for user in paginated_users:
                user_responses.append(UserResponse(
                    id=user["id"],
                    username=user["username"],
                    email=user.get("email"),
                    firstName=user.get("firstName"),
                    lastName=user.get("lastName"),
                    enabled=user.get("enabled", False),
                    emailVerified=user.get("emailVerified", False),
                    tenant_id=extract_tenant_id_from_user(user),
                    customer_id=user.get("attributes", {}).get("customer_id", [None])[0] if isinstance(user.get("attributes", {}).get("customer_id"), list) else None,
                    createdTimestamp=user.get("createdTimestamp")
                ))
            
            logger.info(f"Returning {len(user_responses)} users for tenant {tenant_id}")
            
            return UserListResponse(
                items=user_responses,
                total=total,
                page=page,
                limit=limit,
                pages=pages
            )
            
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list users: {str(e)}")


@router.get("/search")
async def search_users(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Search users by email, name, or username.
    
    SECURITY: Only searches within authenticated user's tenant.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    logger.info(f"Searching users for tenant {tenant_id}, query: {q}")
    
    try:
        async with KeycloakAdminClient() as kc:
            # Search in Keycloak
            response = await kc._make_request(
                "GET",
                f"/realms/{realm}/users",
                params={"search": q}
            )
            response.raise_for_status()
            all_users = response.json()
            
            # CRITICAL: Filter to tenant
            tenant_users = [
                user for user in all_users
                if user_belongs_to_tenant(user, tenant_id)
            ]
            
            # Paginate
            total = len(tenant_users)
            pages = (total + limit - 1) // limit
            start = (page - 1) * limit
            end = start + limit
            paginated_users = tenant_users[start:end]
            
            # Convert to response
            user_responses = []
            for user in paginated_users:
                user_responses.append(UserResponse(
                    id=user["id"],
                    username=user["username"],
                    email=user.get("email"),
                    firstName=user.get("firstName"),
                    lastName=user.get("lastName"),
                    enabled=user.get("enabled", False),
                    emailVerified=user.get("emailVerified", False),
                    tenant_id=extract_tenant_id_from_user(user),
                    customer_id=user.get("attributes", {}).get("customer_id", [None])[0] if isinstance(user.get("attributes", {}).get("customer_id"), list) else None,
                    createdTimestamp=user.get("createdTimestamp")
                ))
            
            return UserListResponse(
                items=user_responses,
                total=total,
                page=page,
                limit=limit,
                pages=pages
            )
            
    except Exception as e:
        logger.error(f"Error searching users: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Get user details by ID.
    
    SECURITY: Only returns user if they belong to authenticated user's tenant.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Get user from Keycloak
            user = await kc.get_user(realm, user_id)
            
            # CRITICAL: Verify user belongs to this tenant
            user_tenant_id = extract_tenant_id_from_user(user)
            
            if user_tenant_id != tenant_id:
                logger.warning(
                    f"Tenant isolation violation attempt: "
                    f"Tenant {tenant_id} tried to access user from tenant {user_tenant_id}"
                )
                raise HTTPException(status_code=404, detail="User not found")
            
            # Return user
            return UserResponse(
                id=user["id"],
                username=user["username"],
                email=user.get("email"),
                firstName=user.get("firstName"),
                lastName=user.get("lastName"),
                enabled=user.get("enabled", False),
                emailVerified=user.get("emailVerified", False),
                tenant_id=user_tenant_id,
                customer_id=user.get("attributes", {}).get("customer_id", [None])[0] if isinstance(user.get("attributes", {}).get("customer_id"), list) else None,
                createdTimestamp=user.get("createdTimestamp")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user")


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    update_data: UserUpdateRequest,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Update user information.
    
    SECURITY: Only allows updating users in authenticated user's tenant.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Get user first to verify tenant
            user = await kc.get_user(realm, user_id)
            user_tenant_id = extract_tenant_id_from_user(user)
            
            # CRITICAL: Enforce tenant isolation
            if user_tenant_id != tenant_id:
                logger.warning(
                    f"Tenant isolation violation: "
                    f"Tenant {tenant_id} tried to update user in tenant {user_tenant_id}"
                )
                raise HTTPException(status_code=404, detail="User not found")
            
            # Build update payload
            update_payload = {}
            if update_data.firstName is not None:
                update_payload["firstName"] = update_data.firstName
            if update_data.lastName is not None:
                update_payload["lastName"] = update_data.lastName
            if update_data.email is not None:
                update_payload["email"] = update_data.email
            if update_data.enabled is not None:
                update_payload["enabled"] = update_data.enabled
            
            # Update user
            response = await kc._make_request(
                "PUT",
                f"/realms/{realm}/users/{user_id}",
                json_data=update_payload
            )
            response.raise_for_status()
            
            logger.info(f"User {user_id} updated by tenant {tenant_id}")
            
            return {"success": True, "message": "User updated successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user")


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Delete user (soft delete - disable account).
    
    SECURITY: Only allows deleting users in authenticated user's tenant.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Get user first to verify tenant
            user = await kc.get_user(realm, user_id)
            user_tenant_id = extract_tenant_id_from_user(user)
            
            # CRITICAL: Enforce tenant isolation
            if user_tenant_id != tenant_id:
                logger.warning(
                    f"Tenant isolation violation: "
                    f"Tenant {tenant_id} tried to delete user in tenant {user_tenant_id}"
                )
                raise HTTPException(status_code=404, detail="User not found")
            
            # Soft delete: disable user instead of hard delete
            await kc._make_request(
                "PUT",
                f"/realms/{realm}/users/{user_id}",
                json_data={"enabled": False}
            )
            
            logger.info(f"User {user_id} deleted (disabled) by tenant {tenant_id}")
            
            return {"success": True, "message": "User deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete user")


@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Deactivate user account.
    
    SECURITY: Only allows deactivating users in authenticated user's tenant.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Verify tenant ownership
            user = await kc.get_user(realm, user_id)
            user_tenant_id = extract_tenant_id_from_user(user)
            
            if user_tenant_id != tenant_id:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Deactivate
            await kc._make_request(
                "PUT",
                f"/realms/{realm}/users/{user_id}",
                json_data={"enabled": False}
            )
            
            logger.info(f"User {user_id} deactivated by tenant {tenant_id}")
            
            return {"success": True, "message": "User deactivated"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating user: {e}")
        raise HTTPException(status_code=500, detail="Failed to deactivate user")


@router.post("/{user_id}/reactivate")
async def reactivate_user(
    user_id: str,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Reactivate user account.
    
    SECURITY: Only allows reactivating users in authenticated user's tenant.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Verify tenant ownership
            user = await kc.get_user(realm, user_id)
            user_tenant_id = extract_tenant_id_from_user(user)
            
            if user_tenant_id != tenant_id:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Reactivate
            await kc._make_request(
                "PUT",
                f"/realms/{realm}/users/{user_id}",
                json_data={"enabled": True}
            )
            
            logger.info(f"User {user_id} reactivated by tenant {tenant_id}")
            
            return {"success": True, "message": "User reactivated"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reactivating user: {e}")
        raise HTTPException(status_code=500, detail="Failed to reactivate user")


@router.get("/export/csv")
async def export_users_csv(
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Export users to CSV format.
    
    SECURITY: Only exports users from authenticated user's tenant.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Get all users
            response = await kc._make_request("GET", f"/realms/{realm}/users")
            response.raise_for_status()
            all_users = response.json()
            
            # CRITICAL: Filter to tenant
            tenant_users = [
                user for user in all_users
                if user_belongs_to_tenant(user, tenant_id)
            ]
            
            # Convert to CSV
            import io
            import csv
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=[
                "id", "username", "email", "firstName", "lastName",
                "enabled", "emailVerified", "tenant_id", "createdTimestamp"
            ])
            writer.writeheader()
            
            for user in tenant_users:
                writer.writerow({
                    "id": user["id"],
                    "username": user["username"],
                    "email": user.get("email", ""),
                    "firstName": user.get("firstName", ""),
                    "lastName": user.get("lastName", ""),
                    "enabled": user.get("enabled", False),
                    "emailVerified": user.get("emailVerified", False),
                    "tenant_id": extract_tenant_id_from_user(user),
                    "createdTimestamp": user.get("createdTimestamp", "")
                })
            
            csv_content = output.getvalue()
            
            from fastapi.responses import Response
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=users_{tenant_id}_{datetime.now().strftime('%Y%m%d')}.csv"
                }
            )
            
    except Exception as e:
        logger.error(f"Error exporting users: {e}")
        raise HTTPException(status_code=500, detail="Failed to export users")


@router.post("/{user_id}/offboard")
async def offboard_user(
    user_id: str,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Offboard a user (disable account, revoke sessions, generate report).
    
    SECURITY: Only allows offboarding users in authenticated user's tenant.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Get user first to verify tenant
            user = await kc.get_user(realm, user_id)
            user_tenant_id = extract_tenant_id_from_user(user)
            
            # CRITICAL: Enforce tenant isolation
            if user_tenant_id != tenant_id:
                logger.warning(
                    f"Tenant isolation violation: "
                    f"Tenant {tenant_id} tried to offboard user in tenant {user_tenant_id}"
                )
                raise HTTPException(status_code=404, detail="User not found")
            
            # 1. Revoke all sessions
            try:
                await kc._make_request(
                    "POST",
                    f"/realms/{realm}/users/{user_id}/logout"
                )
            except Exception as e:
                logger.warning(f"Error revoking sessions: {e}")
            
            # 2. Disable account
            await kc._make_request(
                "PUT",
                f"/realms/{realm}/users/{user_id}",
                json_data={"enabled": False}
            )
            
            # 3. Generate offboarding report
            report = {
                "user_id": user_id,
                "username": user.get("username"),
                "email": user.get("email"),
                "offboarded_at": datetime.utcnow().isoformat(),
                "offboarded_by": token_data.get("user_id"),
                "tenant_id": tenant_id,
                "actions_taken": [
                    "Sessions revoked",
                    "Account disabled"
                ]
            }
            
            logger.info(f"User {user_id} offboarded by tenant {tenant_id}")
            
            return {
                "success": True,
                "message": "User offboarded successfully",
                "report": report
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error offboarding user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to offboard user")

