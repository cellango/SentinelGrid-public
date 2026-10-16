"""Bulk operations API endpoints for entitlements."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.request_context import (
    RequestContext,
    ensure_request_tenant_matches,
    get_current_request_context,
    get_tenant_session,
)
from app.models.entitlement import Entitlement
from app.api.entitlements import EntitlementCreate, EntitlementUpdate
from app.services.redis_cache import cache

router = APIRouter(prefix="/api/v1/entitlements", tags=["entitlements"])


class BulkCreateRequest(BaseModel):
    """Schema for bulk create request."""
    entitlements: List[EntitlementCreate]


class BulkUpdateRequest(BaseModel):
    """Schema for bulk update request."""
    updates: List[dict]  # Each dict has "id" and the fields to update


class BulkDeleteRequest(BaseModel):
    """Schema for bulk delete request."""
    entitlement_ids: List[UUID]


class BulkOperationResponse(BaseModel):
    """Schema for bulk operation response."""
    created: int = 0
    updated: int = 0
    deleted: int = 0
    failed: int = 0
    errors: List[str] = []


@router.post("/bulk", response_model=BulkOperationResponse)
async def bulk_create_entitlements(
    request: BulkCreateRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """Bulk create entitlements."""
    response = BulkOperationResponse()
    tenant_ids_to_invalidate = set()
    
    for entitlement_data in request.entitlements:
        ensure_request_tenant_matches(request_context.tenant_id, entitlement_data.tenant_id)
        try:
            # Check for duplicate
            existing = db.query(Entitlement).filter(
                Entitlement.tenant_id == request_context.tenant_id,
                Entitlement.resource_type == entitlement_data.resource_type,
                Entitlement.resource_id == entitlement_data.resource_id,
                Entitlement.action == entitlement_data.action,
                Entitlement.granted_to_type == entitlement_data.granted_to_type,
                Entitlement.granted_to_id == entitlement_data.granted_to_id,
            ).first()
            
            if existing:
                response.failed += 1
                response.errors.append(
                    f"Entitlement already exists: {entitlement_data.resource_type}:{entitlement_data.resource_id}:{entitlement_data.action}"
                )
                continue
            
            # Create new entitlement
            entitlement_payload = entitlement_data.model_dump()
            entitlement_payload["tenant_id"] = request_context.tenant_id
            db_entitlement = Entitlement(**entitlement_payload)
            db.add(db_entitlement)
            response.created += 1
            tenant_ids_to_invalidate.add(str(request_context.tenant_id))
            
        except Exception as e:
            response.failed += 1
            response.errors.append(f"Error creating entitlement: {str(e)}")
    
    try:
        db.commit()
        
        # Invalidate cache for affected tenants
        for tenant_id in tenant_ids_to_invalidate:
            cache.invalidate_tenant_entitlements(tenant_id)
    except Exception as e:
        db.rollback()
        response.failed += response.created
        response.created = 0
        response.errors.append(f"Database error: {str(e)}")
    
    return response


@router.put("/bulk", response_model=BulkOperationResponse)
async def bulk_update_entitlements(
    request: BulkUpdateRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """Bulk update entitlements."""
    response = BulkOperationResponse()
    tenant_ids_to_invalidate = set()
    
    for update_data in request.updates:
        try:
            entitlement_id = update_data.get("id")
            if not entitlement_id:
                response.failed += 1
                response.errors.append("Missing 'id' in update data")
                continue
            
            entitlement = db.query(Entitlement).filter(
                Entitlement.id == entitlement_id,
                Entitlement.tenant_id == request_context.tenant_id,
            ).first()
            if not entitlement:
                response.failed += 1
                response.errors.append(f"Entitlement not found: {entitlement_id}")
                continue
            
            # Update fields
            update_fields = EntitlementUpdate(**{k: v for k, v in update_data.items() if k != "id"})
            if update_fields.status is not None:
                entitlement.status = update_fields.status
            if update_fields.expires_at is not None:
                entitlement.expires_at = update_fields.expires_at
            if update_fields.metadata_json is not None:
                entitlement.metadata_json = update_fields.metadata_json
            
            response.updated += 1
            tenant_ids_to_invalidate.add(str(entitlement.tenant_id))
            
        except Exception as e:
            response.failed += 1
            response.errors.append(f"Error updating entitlement: {str(e)}")
    
    try:
        db.commit()
        
        # Invalidate cache for affected tenants
        for tenant_id in tenant_ids_to_invalidate:
            cache.invalidate_tenant_entitlements(tenant_id)
    except Exception as e:
        db.rollback()
        response.failed += response.updated
        response.updated = 0
        response.errors.append(f"Database error: {str(e)}")
    
    return response


@router.delete("/bulk", response_model=BulkOperationResponse)
async def bulk_delete_entitlements(
    request: BulkDeleteRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """Bulk delete (revoke) entitlements."""
    response = BulkOperationResponse()
    tenant_ids_to_invalidate = set()
    
    for entitlement_id in request.entitlement_ids:
        try:
            entitlement = db.query(Entitlement).filter(
                Entitlement.id == entitlement_id,
                Entitlement.tenant_id == request_context.tenant_id,
            ).first()
            if not entitlement:
                response.failed += 1
                response.errors.append(f"Entitlement not found: {entitlement_id}")
                continue
            
            # Soft delete
            entitlement.status = "revoked"
            response.deleted += 1
            tenant_ids_to_invalidate.add(str(entitlement.tenant_id))
            
        except Exception as e:
            response.failed += 1
            response.errors.append(f"Error deleting entitlement: {str(e)}")
    
    try:
        db.commit()
        
        # Invalidate cache for affected tenants
        for tenant_id in tenant_ids_to_invalidate:
            cache.invalidate_tenant_entitlements(tenant_id)
    except Exception as e:
        db.rollback()
        response.failed += response.deleted
        response.deleted = 0
        response.errors.append(f"Database error: {str(e)}")
    
    return response
