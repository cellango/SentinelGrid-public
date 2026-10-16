"""Role-to-Entitlement mapping API endpoints."""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.request_context import (
    RequestContext,
    ensure_request_tenant_matches,
    get_current_request_context,
    get_entitlement_session as get_tenant_session,
)
from app.models.role_entitlement_pattern import RoleEntitlementPattern
from app.services.role_sync_service import RoleSyncService

router = APIRouter(prefix="/api/v1/role-mappings", tags=["role-mappings"])


class RolePatternCreate(BaseModel):
    """Schema for creating a role-to-entitlement pattern."""
    role_name: str = Field(..., max_length=255)
    tenant_id: Optional[UUID] = None  # NULL for global patterns
    entitlement_pattern: str = Field(..., description="Pattern: resource_type:resource_id:action")
    auto_grant: bool = Field(True, description="Auto-grant when role is assigned")
    created_by: UUID


class RolePatternResponse(BaseModel):
    """Schema for role pattern response."""
    id: UUID
    role_name: str
    tenant_id: Optional[UUID]
    entitlement_pattern: str
    auto_grant: bool
    created_by: UUID
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class RolePatternUpdate(BaseModel):
    """Schema for updating a role pattern."""
    entitlement_pattern: Optional[str] = None
    auto_grant: Optional[bool] = None


class SyncUserRolesRequest(BaseModel):
    """Schema for syncing user roles to entitlements."""
    user_id: str
    tenant_id: UUID
    granted_by: UUID


class SyncRoleRequest(BaseModel):
    """Schema for syncing a role to all users."""
    role_name: str
    tenant_id: Optional[UUID] = None
    granted_by: UUID


@router.post("", response_model=RolePatternResponse, status_code=201)
async def create_role_pattern(
    pattern: RolePatternCreate,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """Create a role-to-entitlement pattern mapping."""
    ensure_request_tenant_matches(request_context.tenant_id, pattern.tenant_id)

    # Validate entitlement pattern format
    parts = pattern.entitlement_pattern.split(":")
    if len(parts) != 3:
        raise HTTPException(
            status_code=400,
            detail="Invalid entitlement pattern. Expected format: resource_type:resource_id:action"
        )
    
    # Check for duplicate
    existing = db.query(RoleEntitlementPattern).filter(
        RoleEntitlementPattern.role_name == pattern.role_name,
        RoleEntitlementPattern.tenant_id == request_context.tenant_id,
        RoleEntitlementPattern.entitlement_pattern == pattern.entitlement_pattern
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Role pattern already exists"
        )
    
    # Create pattern
    pattern_payload = pattern.model_dump()
    pattern_payload["tenant_id"] = request_context.tenant_id
    db_pattern = RoleEntitlementPattern(**pattern_payload)
    db.add(db_pattern)
    db.commit()
    db.refresh(db_pattern)
    
    return db_pattern


@router.get("", response_model=List[RolePatternResponse])
async def list_role_patterns(
    role_name: Optional[str] = Query(None, description="Filter by role name"),
    tenant_id: Optional[UUID] = Query(None, description="Filter by tenant ID"),
    auto_grant: Optional[bool] = Query(None, description="Filter by auto_grant"),
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """List role-to-entitlement patterns."""
    ensure_request_tenant_matches(request_context.tenant_id, tenant_id)
    query = db.query(RoleEntitlementPattern).filter(
        RoleEntitlementPattern.tenant_id == request_context.tenant_id
    )
    
    if role_name:
        query = query.filter(RoleEntitlementPattern.role_name == role_name)
    if auto_grant is not None:
        query = query.filter(RoleEntitlementPattern.auto_grant == auto_grant)
    
    patterns = query.all()
    return patterns


@router.get("/{pattern_id}", response_model=RolePatternResponse)
async def get_role_pattern(
    pattern_id: UUID,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """Get a role pattern by ID."""
    pattern = db.query(RoleEntitlementPattern).filter(
        RoleEntitlementPattern.id == pattern_id,
        RoleEntitlementPattern.tenant_id == request_context.tenant_id,
    ).first()
    
    if not pattern:
        raise HTTPException(status_code=404, detail="Role pattern not found")
    
    return pattern


@router.put("/{pattern_id}", response_model=RolePatternResponse)
async def update_role_pattern(
    pattern_id: UUID,
    pattern_update: RolePatternUpdate,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """Update a role pattern."""
    pattern = db.query(RoleEntitlementPattern).filter(
        RoleEntitlementPattern.id == pattern_id,
        RoleEntitlementPattern.tenant_id == request_context.tenant_id,
    ).first()
    
    if not pattern:
        raise HTTPException(status_code=404, detail="Role pattern not found")
    
    if pattern_update.entitlement_pattern is not None:
        # Validate format
        parts = pattern_update.entitlement_pattern.split(":")
        if len(parts) != 3:
            raise HTTPException(
                status_code=400,
                detail="Invalid entitlement pattern. Expected format: resource_type:resource_id:action"
            )
        pattern.entitlement_pattern = pattern_update.entitlement_pattern
    
    if pattern_update.auto_grant is not None:
        pattern.auto_grant = pattern_update.auto_grant
    
    db.commit()
    db.refresh(pattern)
    
    return pattern


@router.delete("/{pattern_id}", status_code=204)
async def delete_role_pattern(
    pattern_id: UUID,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """Delete a role pattern."""
    pattern = db.query(RoleEntitlementPattern).filter(
        RoleEntitlementPattern.id == pattern_id,
        RoleEntitlementPattern.tenant_id == request_context.tenant_id,
    ).first()
    
    if not pattern:
        raise HTTPException(status_code=404, detail="Role pattern not found")
    
    db.delete(pattern)
    db.commit()
    
    return None


@router.post("/sync/user", status_code=200)
async def sync_user_roles(
    request: SyncUserRolesRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """Sync a user's Keycloak roles to entitlements."""
    ensure_request_tenant_matches(request_context.tenant_id, request.tenant_id)
    sync_service = RoleSyncService(db)
    result = await sync_service.sync_user_roles_to_entitlements(
        request.user_id,
        request_context.tenant_id,
        request.granted_by
    )
    return result


@router.post("/sync/role", status_code=200)
async def sync_role_to_users(
    request: SyncRoleRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """Sync a role's entitlements to all users who have that role."""
    ensure_request_tenant_matches(request_context.tenant_id, request.tenant_id)
    sync_service = RoleSyncService(db)
    result = await sync_service.sync_role_to_all_users(
        request.role_name,
        request.tenant_id or request_context.tenant_id,
        request.granted_by
    )
    return result


@router.post("/sync/role/{role_name}/revoke", status_code=200)
async def revoke_role_entitlements(
    role_name: str,
    user_id: str = Query(..., description="User ID"),
    tenant_id: UUID = Query(..., description="Tenant ID"),
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """Revoke entitlements granted by a role when the role is removed."""
    ensure_request_tenant_matches(request_context.tenant_id, tenant_id)
    sync_service = RoleSyncService(db)
    result = await sync_service.revoke_user_entitlements_for_role(
        user_id,
        role_name,
        request_context.tenant_id
    )
    return result
