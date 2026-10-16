"""
SCIM 2.0 API endpoints.

Provides SCIM 2.0 compliant endpoints for user provisioning.
Integrates with Keycloak user federation.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Response
from pydantic import BaseModel

from app.services.keycloak_admin_client import KeycloakAdminClient
from app.services.audit_service import AuditService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scim/v2", tags=["scim"])


# ============================================================================
# SCIM 2.0 Models
# ============================================================================

class SCIMUser(BaseModel):
    """SCIM 2.0 User resource."""
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    id: Optional[str] = None
    externalId: Optional[str] = None
    userName: str
    name: Optional[dict] = None
    displayName: Optional[str] = None
    emails: List[dict]
    active: bool = True
    meta: Optional[dict] = None


class SCIMListResponse(BaseModel):
    """SCIM 2.0 List response."""
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
    totalResults: int
    itemsPerPage: int
    startIndex: int
    Resources: List[SCIMUser]


# ============================================================================
# Helper Functions
# ============================================================================

_rate_limit_state: Dict[str, Dict[str, float]] = {}


def _parse_token_map() -> Dict[str, str]:
    """Load SCIM bearer token map from env (tenant_id -> token)."""
    token_map: Dict[str, str] = {}
    if settings.SCIM_TENANT_TOKENS:
        try:
            token_map = json.loads(settings.SCIM_TENANT_TOKENS)
        except json.JSONDecodeError:
            # fallback: comma-separated tenant:token pairs
            entries = [p.strip() for p in settings.SCIM_TENANT_TOKENS.split(",") if p.strip()]
            for entry in entries:
                if ":" in entry:
                    tenant, tok = entry.split(":", 1)
                    token_map[tenant.strip()] = tok.strip()
    elif settings.SCIM_BEARER_TOKEN:
        token_map[settings.SCIM_DEFAULT_TENANT_ID] = settings.SCIM_BEARER_TOKEN
    return token_map


def _rate_limit(token: str):
    """Basic per-token rate limit (per minute)."""
    if not token:
        return
    now = time.time()
    window = int(now // 60)
    state = _rate_limit_state.get(token, {"window": window, "count": 0})
    if state["window"] != window:
        state = {"window": window, "count": 0}
    state["count"] += 1
    _rate_limit_state[token] = state
    if state["count"] > settings.SCIM_RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="SCIM rate limit exceeded")


def verify_scim_token(authorization: Optional[str] = Header(None)) -> str:
    """Verify SCIM bearer token against configured map and enforce rate limit."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.replace("Bearer ", "", 1).strip()
    token_map = _parse_token_map()
    if not token_map:
        logger.error("SCIM token map not configured; deny request")
        raise HTTPException(status_code=401, detail="SCIM token not configured")

    _rate_limit(token)

    # Find matching tenant
    for tenant_id, expected in token_map.items():
        if token == expected:
            return tenant_id

    raise HTTPException(status_code=401, detail="Invalid SCIM token")


def get_tenant_from_token(token: str) -> str:
    """Extract tenant_id from SCIM token."""
    return token  # token value maps to tenant_id after verify


def get_realm_for_tenant(tenant_id: str) -> str:
    """Get Keycloak realm name for tenant."""
    return settings.KEYCLOAK_REALM


def audit_scim(action: str, tenant_id: str, resource_id: Optional[str] = None, details: Optional[dict] = None):
    """Log SCIM operation to audit log."""
    try:
        AuditService.log_auth_event(
            realm_name=get_realm_for_tenant(tenant_id),
            action=action,
            actor_user_id=None,
            actor_email="scim",
            customer_id=None,
            organization_id=None,
            details=details or {},
            ip_address=None,
            user_agent="scim-client",
        )
    except Exception as exc:
        logger.warning("Failed to write SCIM audit event: %s", exc)


# ============================================================================
# SCIM 2.0 Endpoints
# ============================================================================

@router.get("/Users", response_model=SCIMListResponse)
async def list_users_scim(
    startIndex: int = 1,
    count: int = 100,
    filter: Optional[str] = None,
    authorization: str = Depends(verify_scim_token)
):
    """
    SCIM 2.0: List users.
    
    GET /Users?startIndex=1&count=100
    """
    tenant_id = get_tenant_from_token(authorization)
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Get users from Keycloak
            response = await kc._make_request(
                "GET",
                f"/realms/{realm}/users",
                params={"first": startIndex - 1, "max": count}
            )
            response.raise_for_status()
            users = response.json()
            
            # Convert to SCIM format
            scim_users = []
            for user in users:
                # Filter by tenant_id
                attrs = user.get("attributes", {})
                user_tenant_id = attrs.get("tenant_id", [None])[0] if isinstance(attrs.get("tenant_id"), list) else None
                
                if user_tenant_id != tenant_id:
                    continue
                
                scim_user = SCIMUser(
                    id=user["id"],
                    externalId=user.get("username"),
                    userName=user.get("username", ""),
                    name={
                        "givenName": user.get("firstName", ""),
                        "familyName": user.get("lastName", ""),
                        "formatted": f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()
                    },
                    displayName=f"{user.get('firstName', '')} {user.get('lastName', '')}".strip() or user.get("username", ""),
                    emails=[{"value": user.get("email", ""), "primary": True}],
                    active=user.get("enabled", False),
                    meta={
                        "resourceType": "User",
                        "created": datetime.fromtimestamp(user.get("createdTimestamp", 0) / 1000).isoformat() if user.get("createdTimestamp") else None,
                        "lastModified": datetime.fromtimestamp(user.get("createdTimestamp", 0) / 1000).isoformat() if user.get("createdTimestamp") else None,
                    }
                )
                scim_users.append(scim_user)
            
            audit_scim(action="scim_list_users", tenant_id=tenant_id, details={"count": len(scim_users)})
            
            return SCIMListResponse(
                totalResults=len(scim_users),
                itemsPerPage=count,
                startIndex=startIndex,
                Resources=scim_users
            )
            
    except Exception as e:
        logger.error(f"Error listing SCIM users: {e}")
        raise HTTPException(status_code=500, detail="Failed to list users")


@router.get("/Users/{user_id}", response_model=SCIMUser)
async def get_user_scim(
    user_id: str,
    authorization: str = Depends(verify_scim_token)
):
    """
    SCIM 2.0: Get user by ID.
    
    GET /Users/{id}
    """
    tenant_id = get_tenant_from_token(authorization)
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            user = await kc.get_user(realm, user_id)
            
            # Verify tenant
            attrs = user.get("attributes", {})
            user_tenant_id = attrs.get("tenant_id", [None])[0] if isinstance(attrs.get("tenant_id"), list) else None
            
            if user_tenant_id != tenant_id:
                raise HTTPException(status_code=404, detail="User not found")
            
            scim_user = SCIMUser(
                id=user["id"],
                externalId=user.get("username"),
                userName=user.get("username", ""),
                name={
                    "givenName": user.get("firstName", ""),
                    "familyName": user.get("lastName", ""),
                    "formatted": f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()
                },
                displayName=f"{user.get('firstName', '')} {user.get('lastName', '')}".strip() or user.get("username", ""),
                emails=[{"value": user.get("email", ""), "primary": True}],
                active=user.get("enabled", False),
                meta={
                    "resourceType": "User",
                    "created": datetime.fromtimestamp(user.get("createdTimestamp", 0) / 1000).isoformat() if user.get("createdTimestamp") else None,
                    "lastModified": datetime.fromtimestamp(user.get("createdTimestamp", 0) / 1000).isoformat() if user.get("createdTimestamp") else None,
                }
            )
            audit_scim(action="scim_get_user", tenant_id=tenant_id, resource_id=user_id)
            return scim_user
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting SCIM user: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user")


@router.post("/Users", response_model=SCIMUser, status_code=201)
async def create_user_scim(
    user: SCIMUser,
    authorization: str = Depends(verify_scim_token)
):
    """
    SCIM 2.0: Create user.
    
    POST /Users
    """
    tenant_id = get_tenant_from_token(authorization)
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Create user in Keycloak
            user_data = {
                "username": user.userName,
                "email": user.emails[0]["value"] if user.emails else user.userName,
                "firstName": user.name.get("givenName") if user.name else None,
                "lastName": user.name.get("familyName") if user.name else None,
                "enabled": user.active,
                "emailVerified": False,
                "attributes": {
                    "tenant_id": [tenant_id]
                }
            }
            
            response = await kc._make_request(
                "POST",
                f"/realms/{realm}/users",
                json_data=user_data
            )
            response.raise_for_status()
            
            user_id = response.headers.get("Location", "").split("/")[-1]
            
            # Get created user
            created_user = await kc.get_user(realm, user_id)
            
            scim_user = SCIMUser(
                id=created_user["id"],
                externalId=created_user.get("username"),
                userName=created_user.get("username", ""),
                name={
                    "givenName": created_user.get("firstName", ""),
                    "familyName": created_user.get("lastName", ""),
                    "formatted": f"{created_user.get('firstName', '')} {created_user.get('lastName', '')}".strip()
                },
                displayName=f"{created_user.get('firstName', '')} {created_user.get('lastName', '')}".strip() or created_user.get("username", ""),
                emails=[{"value": created_user.get("email", ""), "primary": True}],
                active=created_user.get("enabled", False),
                meta={
                    "resourceType": "User",
                    "created": datetime.utcnow().isoformat(),
                    "lastModified": datetime.utcnow().isoformat(),
                }
            )
            audit_scim(action="scim_create_user", tenant_id=tenant_id, resource_id=user_id)
            return scim_user
            
    except Exception as e:
        logger.error(f"Error creating SCIM user: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user")


@router.put("/Users/{user_id}", response_model=SCIMUser)
async def update_user_scim(
    user_id: str,
    user: SCIMUser,
    authorization: str = Depends(verify_scim_token)
):
    """
    SCIM 2.0: Update user.
    
    PUT /Users/{id}
    """
    tenant_id = get_tenant_from_token(authorization)
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Verify user exists and belongs to tenant
            existing_user = await kc.get_user(realm, user_id)
            attrs = existing_user.get("attributes", {})
            user_tenant_id = attrs.get("tenant_id", [None])[0] if isinstance(attrs.get("tenant_id"), list) else None
            
            if user_tenant_id != tenant_id:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Update user
            user_data = {
                "email": user.emails[0]["value"] if user.emails else existing_user.get("email"),
                "firstName": user.name.get("givenName") if user.name else existing_user.get("firstName"),
                "lastName": user.name.get("familyName") if user.name else existing_user.get("lastName"),
                "enabled": user.active,
            }
            
            await kc._make_request(
                "PUT",
                f"/realms/{realm}/users/{user_id}",
                json_data=user_data
            )
            
            # Get updated user
            updated_user = await kc.get_user(realm, user_id)
            
            scim_user = SCIMUser(
                id=updated_user["id"],
                externalId=updated_user.get("username"),
                userName=updated_user.get("username", ""),
                name={
                    "givenName": updated_user.get("firstName", ""),
                    "familyName": updated_user.get("lastName", ""),
                    "formatted": f"{updated_user.get('firstName', '')} {updated_user.get('lastName', '')}".strip()
                },
                displayName=f"{updated_user.get('firstName', '')} {updated_user.get('lastName', '')}".strip() or updated_user.get("username", ""),
                emails=[{"value": updated_user.get("email", ""), "primary": True}],
                active=updated_user.get("enabled", False),
                meta={
                    "resourceType": "User",
                    "lastModified": datetime.utcnow().isoformat(),
                }
            )
            audit_scim(action="scim_update_user", tenant_id=tenant_id, resource_id=user_id)
            return scim_user
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating SCIM user: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user")


@router.delete("/Users/{user_id}", status_code=204)
async def delete_user_scim(
    user_id: str,
    authorization: str = Depends(verify_scim_token)
):
    """
    SCIM 2.0: Delete user.
    
    DELETE /Users/{id}
    """
    tenant_id = get_tenant_from_token(authorization)
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Verify user belongs to tenant
            user = await kc.get_user(realm, user_id)
            attrs = user.get("attributes", {})
            user_tenant_id = attrs.get("tenant_id", [None])[0] if isinstance(attrs.get("tenant_id"), list) else None
            
            if user_tenant_id != tenant_id:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Delete user
            await kc._make_request(
                "DELETE",
                f"/realms/{realm}/users/{user_id}"
            )
            
            audit_scim(action="scim_delete_user", tenant_id=tenant_id, resource_id=user_id)
            return Response(status_code=204)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting SCIM user: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete user")


@router.get("/ServiceProviderConfig")
async def get_service_provider_config():
    """
    SCIM 2.0: Get service provider configuration.
    
    GET /ServiceProviderConfig
    """
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "patch": {"supported": True},
        "bulk": {"supported": False, "maxOperations": 0, "maxPayloadSize": 0},
        "filter": {"supported": True, "maxResults": 200},
        "changePassword": {"supported": True},
        "sort": {"supported": False},
        "etag": {"supported": False},
        "authenticationSchemes": [
            {
                "type": "oauthbearertoken",
                "name": "OAuth Bearer Token",
                "description": "Authentication using OAuth 2.0 bearer token"
            }
        ]
    }
