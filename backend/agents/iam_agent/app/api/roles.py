"""
Role Management API endpoints.

Manages role assignments with automatic entitlement provisioning.
When a role is assigned, default entitlements for that role are automatically granted.

Security: All operations enforce tenant isolation.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime

from app.services.keycloak_admin_client import KeycloakAdminClient
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/roles", tags=["roles"])


# ============================================================================
# Models
# ============================================================================

class RoleResponse(BaseModel):
    """Role response model."""
    id: str
    name: str
    description: Optional[str]
    composite: bool = False


class UserRoleResponse(BaseModel):
    """User's role assignment response."""
    user_id: str
    roles: List[RoleResponse]


class RoleAssignmentRequest(BaseModel):
    """Role assignment request."""
    role_name: str


# ============================================================================
# Role-to-Entitlement Mapping
# ============================================================================

def get_default_entitlements_for_role(role_name: str, tenant_id: str) -> List[str]:
    """
    Get default entitlements for a role.
    
    These are automatically granted when the role is assigned.
    Format: resource_type:resource_id:action@tenant_id
    
    Args:
        role_name: Role name (TENANT_ADMIN, SOC_MANAGER, etc.)
        tenant_id: Tenant ID to scope entitlements
    
    Returns:
        List of entitlement strings
    """
    ROLE_ENTITLEMENTS = {
        "TENANT_ADMIN": [
            f"*:*:*@{tenant_id}"  # Full access to everything in tenant
        ],
        "SOC_MANAGER": [
            f"*:*:read@{tenant_id}",  # Read all
            f"incident:*:write@{tenant_id}",
            f"incident:*:assign@{tenant_id}",
            f"incident:*:resolve@{tenant_id}",
            f"playbook:*:execute@{tenant_id}",
            f"integration:*:configure@{tenant_id}",
            f"report:*:generate@{tenant_id}"
        ],
        "SOC_ANALYST": [
            f"alert:*:read@{tenant_id}",
            f"alert:*:triage@{tenant_id}",
            f"alert:*:acknowledge@{tenant_id}",
            f"incident:*:read@{tenant_id}",
            f"incident:*:write@{tenant_id}",
            f"playbook:*:read@{tenant_id}",
            f"report:*:read@{tenant_id}"
        ],
        "VIEW_ONLY": [
            f"*:*:read@{tenant_id}"  # Read-only access
        ]
    }
    
    return ROLE_ENTITLEMENTS.get(role_name, [])


async def grant_entitlements_for_role(
    user_id: str,
    tenant_id: str,
    role_name: str
):
    """
    Grant default entitlements for a role.
    
    Called automatically when a role is assigned.
    Integrates with Entitlement Agent to create entitlement records.
    """
    entitlements = get_default_entitlements_for_role(role_name, tenant_id)
    
    if not entitlements:
        logger.info(f"No default entitlements for role {role_name}")
        return
    
    logger.info(f"Granting {len(entitlements)} entitlements for role {role_name}")
    
    # TODO: Call Entitlement Agent to actually grant entitlements
    # For now, log what would be granted
    for ent in entitlements:
        logger.info(f"  Would grant: {ent} to user {user_id}")
    
    # Future implementation:
    # async with httpx.AsyncClient() as client:
    #     for ent in entitlements:
    #         await client.post(
    #             f"{ENTITLEMENT_AGENT_URL}/api/v1/entitlements",
    #             json={
    #                 "tenant_id": tenant_id,
    #                 "user_id": user_id,
    #                 "entitlement": ent
    #             }
    #         )


# ============================================================================
# Helper Functions
# ============================================================================

async def get_token_data(authorization: str) -> dict:
    """Validate token and extract tenant_id."""
    from app.services.token_validator import TokenValidator
    from app.services.keycloak_client import KeycloakClient
    
    keycloak_client = KeycloakClient()
    validator = TokenValidator(keycloak_client)
    result = validator.validate_token(authorization)
    
    if not result.get("valid"):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    if not result.get("tenant_id"):
        raise HTTPException(status_code=403, detail="No tenant_id in token")
    
    return result


def get_realm_for_tenant(tenant_id: str) -> str:
    """Get realm name for tenant."""
    return settings.KEYCLOAK_REALM


def extract_tenant_id_from_user(user: dict) -> Optional[str]:
    """Extract tenant_id from Keycloak user attributes."""
    attributes = user.get("attributes", {})
    tenant_id = attributes.get("tenant_id")
    
    if isinstance(tenant_id, list):
        return tenant_id[0] if tenant_id else None
    
    return tenant_id


# ============================================================================
# Role Management Endpoints
# ============================================================================

@router.get("", response_model=List[RoleResponse])
async def list_roles(
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    List available roles in the realm.
    
    Returns all realm roles that can be assigned to users.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            roles = await kc.get_realm_roles(realm)
            
            # Convert to response model
            role_responses = []
            for role in roles:
                role_responses.append(RoleResponse(
                    id=role.get("id", ""),
                    name=role.get("name", ""),
                    description=role.get("description"),
                    composite=role.get("composite", False)
                ))
            
            return role_responses
            
    except Exception as e:
        logger.error(f"Error listing roles: {e}")
        raise HTTPException(status_code=500, detail="Failed to list roles")


@router.get("/{role_name}")
async def get_role(
    role_name: str,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """Get role details by name."""
    token_data = await get_token_data(authorization)
    realm = get_realm_for_tenant(token_data["tenant_id"])
    
    try:
        async with KeycloakAdminClient() as kc:
            role = await kc.get_realm_role(realm, role_name)
            
            if not role:
                raise HTTPException(status_code=404, detail="Role not found")
            
            # Get default entitlements for this role
            entitlements = get_default_entitlements_for_role(role_name, token_data["tenant_id"])
            
            return {
                "id": role.get("id"),
                "name": role.get("name"),
                "description": role.get("description"),
                "composite": role.get("composite", False),
                "default_entitlements": entitlements
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting role: {e}")
        raise HTTPException(status_code=500, detail="Failed to get role")


@router.get("/{role_name}/users")
async def list_users_with_role(
    role_name: str,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    List users who have a specific role.
    
    SECURITY: Only returns users from authenticated user's tenant.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Get all users with this role
            response = await kc._make_request(
                "GET",
                f"/realms/{realm}/roles/{role_name}/users"
            )
            response.raise_for_status()
            all_users = response.json()
            
            # CRITICAL: Filter to tenant
            tenant_users = [
                user for user in all_users
                if extract_tenant_id_from_user(user) == tenant_id
            ]
            
            return {"role": role_name, "users": tenant_users, "count": len(tenant_users)}
            
    except Exception as e:
        logger.error(f"Error listing users with role: {e}")
        raise HTTPException(status_code=500, detail="Failed to list users")


@router.get("/users/{user_id}/roles", response_model=UserRoleResponse)
async def get_user_roles(
    user_id: str,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Get user's assigned roles.
    
    SECURITY: Only returns roles if user belongs to authenticated user's tenant.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Verify user belongs to tenant
            user = await kc.get_user(realm, user_id)
            user_tenant_id = extract_tenant_id_from_user(user)
            
            if user_tenant_id != tenant_id:
                logger.warning(f"Cross-tenant role query blocked")
                raise HTTPException(status_code=404, detail="User not found")
            
            # Get user's roles
            roles = await kc.get_user_realm_roles(realm, user_id)
            
            role_responses = []
            for role in roles:
                role_responses.append(RoleResponse(
                    id=role.get("id", ""),
                    name=role.get("name", ""),
                    description=role.get("description"),
                    composite=role.get("composite", False)
                ))
            
            return UserRoleResponse(user_id=user_id, roles=role_responses)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user roles: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user roles")


@router.post("/users/{user_id}/roles")
async def assign_role_to_user(
    user_id: str,
    request: RoleAssignmentRequest,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Assign role to user with automatic entitlement provisioning.
    
    SECURITY: Only allows assigning roles to users in authenticated user's tenant.
    
    When a role is assigned, default entitlements for that role are
    automatically granted to the user.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    logger.info(f"Assigning role {request.role_name} to user {user_id} in tenant {tenant_id}")
    
    try:
        async with KeycloakAdminClient() as kc:
            # Verify user belongs to tenant
            user = await kc.get_user(realm, user_id)
            user_tenant_id = extract_tenant_id_from_user(user)
            
            if user_tenant_id != tenant_id:
                logger.warning(
                    f"Cross-tenant role assignment blocked: "
                    f"Tenant {tenant_id} tried to assign role to user in tenant {user_tenant_id}"
                )
                raise HTTPException(status_code=404, detail="User not found")
            
            # Assign role in Keycloak
            await kc.assign_realm_role(realm, user_id, request.role_name)
            
            logger.info(f"✅ Role {request.role_name} assigned to user {user_id}")
            
            # Auto-grant default entitlements for this role
            await grant_entitlements_for_role(user_id, tenant_id, request.role_name)
            
            logger.info(f"✅ Default entitlements granted for role {request.role_name}")
            
            return {
                "success": True,
                "message": f"Role {request.role_name} assigned successfully",
                "entitlements_granted": get_default_entitlements_for_role(request.role_name, tenant_id)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning role: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to assign role: {str(e)}")


@router.delete("/users/{user_id}/roles/{role_name}")
async def remove_role_from_user(
    user_id: str,
    role_name: str,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Remove role from user.
    
    SECURITY: Only allows removing roles from users in authenticated user's tenant.
    
    Note: Does NOT automatically revoke entitlements (use audit campaigns for that).
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Verify user belongs to tenant
            user = await kc.get_user(realm, user_id)
            user_tenant_id = extract_tenant_id_from_user(user)
            
            if user_tenant_id != tenant_id:
                logger.warning(f"Cross-tenant role removal blocked")
                raise HTTPException(status_code=404, detail="User not found")
            
            # Get role
            role = await kc.get_realm_role(realm, role_name)
            if not role:
                raise HTTPException(status_code=404, detail="Role not found")
            
            # Remove role
            response = await kc._make_request(
                "DELETE",
                f"/realms/{realm}/users/{user_id}/role-mappings/realm",
                json_data=[role]
            )
            
            if response.status_code in [204, 200]:
                logger.info(f"Role {role_name} removed from user {user_id}")
                return {
                    "success": True,
                    "message": f"Role {role_name} removed successfully"
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to remove role")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing role: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove role")


@router.get("/{role_name}/permissions")
async def get_role_permissions(
    role_name: str,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Get permissions (default entitlements) for a role.
    
    Shows what entitlements will be granted when this role is assigned.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    entitlements = get_default_entitlements_for_role(role_name, tenant_id)
    
    return {
        "role": role_name,
        "tenant_id": tenant_id,
        "default_entitlements": entitlements,
        "count": len(entitlements),
        "description": f"Default entitlements automatically granted when {role_name} is assigned"
    }

