"""Tenant-scoped role definitions and verified directory reconciliation."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.request_context import (
    RequestContext,
    ensure_request_tenant_matches,
    get_current_request_context,
    get_entitlement_session as get_tenant_session,
)
from app.models.role_entitlement_pattern import RoleEntitlementPattern
from app.schemas.role_mappings import (
    RolePatternCreate,
    RolePatternUpdate,
    RolePatternResponse,
    SyncUserRolesRequest,
    SyncRoleRequest,
)
from app.services.role_sync_service import RoleSyncService, admin, pattern_change

router = APIRouter(prefix="/api/v1/role-mappings", tags=["role-mappings"])


@router.post("", response_model=RolePatternResponse, status_code=201)
async def create_role_pattern(
    pattern: RolePatternCreate,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    ensure_request_tenant_matches(request_context.tenant_id, pattern.tenant_id)
    return pattern_change(db, request_context, pattern)


@router.get("", response_model=list[RolePatternResponse])
async def list_role_patterns(
    role_name: str | None = Query(None),
    tenant_id: UUID | None = Query(None),
    auto_grant: bool | None = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    admin(request_context)
    ensure_request_tenant_matches(request_context.tenant_id, tenant_id)
    query = db.query(RoleEntitlementPattern).filter(
        RoleEntitlementPattern.tenant_id == request_context.tenant_id
    )
    if role_name:
        query = query.filter(RoleEntitlementPattern.role_name == role_name)
    if auto_grant is not None:
        query = query.filter(RoleEntitlementPattern.auto_grant == auto_grant)
    rows = query.order_by(RoleEntitlementPattern.id).limit(501).all()
    if len(rows) > 500:
        raise HTTPException(
            status_code=409, detail="Role inventory exceeds bounded list"
        )
    return [RolePatternResponse.model_validate(row) for row in rows]


@router.get("/{pattern_id}", response_model=RolePatternResponse)
async def get_role_pattern(
    pattern_id: UUID,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    admin(request_context)
    row = (
        db.query(RoleEntitlementPattern)
        .filter(
            RoleEntitlementPattern.id == pattern_id,
            RoleEntitlementPattern.tenant_id == request_context.tenant_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Role pattern not found")
    return RolePatternResponse.model_validate(row)


@router.put("/{pattern_id}", response_model=RolePatternResponse)
async def update_role_pattern(
    pattern_id: UUID,
    pattern_update: RolePatternUpdate,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    return pattern_change(db, request_context, pattern_update, identity=pattern_id)


@router.delete("/{pattern_id}", status_code=204)
async def delete_role_pattern(
    pattern_id: UUID,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    pattern_change(db, request_context, identity=pattern_id, delete=True)


@router.post("/sync/user")
async def sync_user_roles(
    request: SyncUserRolesRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    admin(request_context)
    ensure_request_tenant_matches(request_context.tenant_id, request.tenant_id)
    return await RoleSyncService(db).sync_user_roles_to_entitlements(
        request.user_id, request_context.tenant_id, request_context=request_context
    )


@router.post("/sync/role")
async def sync_role_to_users(
    request: SyncRoleRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    admin(request_context)
    ensure_request_tenant_matches(request_context.tenant_id, request.tenant_id)
    return await RoleSyncService(db).sync_role_to_all_users(
        request.role_name, request_context.tenant_id, request_context=request_context
    )


@router.post("/sync/role/{role_name}/revoke")
async def revoke_role_entitlements(
    role_name: str,
    user_id: UUID = Query(...),
    tenant_id: UUID = Query(...),
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    admin(request_context)
    ensure_request_tenant_matches(request_context.tenant_id, tenant_id)
    return await RoleSyncService(db).revoke_user_entitlements_for_role(
        user_id, role_name, request_context.tenant_id, request_context=request_context
    )
