"""Entitlements API endpoints."""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict

from app.api.request_context import (
    RequestContext,
    ensure_request_tenant_matches,
    get_current_request_context,
    get_tenant_session,
)
from app.core.config import settings
from app.core.tenant_isolation import TenantIsolationValidator
from app.models.entitlement import Entitlement
from app.services.redis_cache import cache
from app.services.audit_logger import AuditLogger

router = APIRouter(prefix="/api/v1/entitlements", tags=["entitlements"])

# Rate limiter will be set from app state
def get_limiter():
    """Get rate limiter from app state."""
    from app.main import app
    return app.state.limiter


# Pydantic schemas
class EntitlementCreate(BaseModel):
    """Schema for creating an entitlement."""
    tenant_id: UUID
    resource_type: str = Field(..., max_length=100)
    resource_id: str = Field(..., max_length=255)
    action: str = Field(..., max_length=50)
    granted_to_type: str = Field(..., pattern="^(user|role|group)$")
    granted_to_id: UUID
    granted_to_name: Optional[str] = Field(None, max_length=255)
    granted_by: UUID
    expires_at: Optional[str] = None
    metadata_json: dict = Field(default_factory=dict, alias="metadata")


class EntitlementResponse(BaseModel):
    """Schema for entitlement response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    resource_type: str
    resource_id: str
    action: str
    granted_to_type: str
    granted_to_id: UUID
    granted_to_name: Optional[str]
    status: str
    granted_by: UUID
    granted_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    usage_count_90d: int
    metadata: dict = Field(serialization_alias="metadata", alias="metadata_json")


class EntitlementUpdate(BaseModel):
    """Schema for updating an entitlement."""
    status: Optional[str] = None
    expires_at: Optional[str] = None
    metadata_json: Optional[dict] = Field(None, alias="metadata")


def _resolve_audit_actor(request_context: RequestContext, fallback_actor: UUID) -> UUID:
    try:
        if request_context.user_id:
            return UUID(str(request_context.user_id))
    except ValueError:
        pass
    return fallback_actor


@router.post("", response_model=EntitlementResponse, status_code=201)
async def create_entitlement(
    entitlement: EntitlementCreate,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """Create a new entitlement."""
    ensure_request_tenant_matches(request_context.tenant_id, entitlement.tenant_id)
    TenantIsolationValidator.validate_tenant_id(request_context.tenant_id)
    
    # Check for duplicate
    existing = db.query(Entitlement).filter(
        Entitlement.tenant_id == request_context.tenant_id,
        Entitlement.resource_type == entitlement.resource_type,
        Entitlement.resource_id == entitlement.resource_id,
        Entitlement.action == entitlement.action,
        Entitlement.granted_to_type == entitlement.granted_to_type,
        Entitlement.granted_to_id == entitlement.granted_to_id,
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Entitlement already exists"
        )
    
    # Create new entitlement
    entitlement_payload = entitlement.model_dump()
    entitlement_payload["tenant_id"] = request_context.tenant_id
    db_entitlement = Entitlement(**entitlement_payload)
    db.add(db_entitlement)
    db.commit()
    db.refresh(db_entitlement)
    
    # Audit log
    audit_logger = AuditLogger(db)
    audit_logger.log_entitlement_created(
        db_entitlement,
        performed_by=_resolve_audit_actor(request_context, entitlement.granted_by),
        reason="Entitlement created via API"
    )
    
    # Invalidate cache
    cache.invalidate_entitlement(str(db_entitlement.id), str(db_entitlement.tenant_id))
    
    return db_entitlement


@router.get("/{entitlement_id}", response_model=EntitlementResponse)
async def get_entitlement(
    entitlement_id: UUID,
    tenant_id: Optional[UUID] = Query(None, description="Tenant ID for isolation validation"),
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """Get a specific entitlement by ID."""
    ensure_request_tenant_matches(request_context.tenant_id, tenant_id)

    # Try cache first
    cache_key = f"entitlement:{entitlement_id}"
    cached_entitlement = cache.get(cache_key)
    if cached_entitlement:
        if cached_entitlement.get("tenant_id") != str(request_context.tenant_id):
            raise HTTPException(status_code=404, detail="Entitlement not found")
        return cached_entitlement
    
    entitlement = db.query(Entitlement).filter(
        Entitlement.id == entitlement_id,
        Entitlement.tenant_id == request_context.tenant_id,
    ).first()
    
    if not entitlement:
        raise HTTPException(status_code=404, detail="Entitlement not found")
    
    return entitlement


@router.get("", response_model=List[EntitlementResponse])
async def list_entitlements(
    tenant_id: Optional[UUID] = Query(None, description="Filter by tenant ID"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    role_name: Optional[str] = Query(None, description="Filter by role name"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    action: Optional[str] = Query(None, description="Filter by action"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """List entitlements with optional filters."""
    ensure_request_tenant_matches(request_context.tenant_id, tenant_id)

    # Generate cache key from filters
    cache_key_parts = ["entitlements"]
    cache_key_parts.append(f"tenant:{request_context.tenant_id}")
    if user_id:
        cache_key_parts.append(f"user:{user_id}")
    if role_name:
        cache_key_parts.append(f"role:{role_name}")
    if resource_type:
        cache_key_parts.append(f"resource:{resource_type}")
    if action:
        cache_key_parts.append(f"action:{action}")
    if status:
        cache_key_parts.append(f"status:{status}")
    cache_key_parts.append(f"limit:{limit}:offset:{offset}")
    cache_key = ":".join(cache_key_parts)
    
    # Try cache
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    query = db.query(Entitlement).filter(Entitlement.tenant_id == request_context.tenant_id)
    if user_id:
        query = query.filter(
            Entitlement.granted_to_type == "user",
            Entitlement.granted_to_id == user_id
        )
    if role_name:
        query = query.filter(
            Entitlement.granted_to_type == "role",
            Entitlement.granted_to_name == role_name
        )
    if resource_type:
        query = query.filter(Entitlement.resource_type == resource_type)
    if action:
        query = query.filter(Entitlement.action == action)
    if status:
        query = query.filter(Entitlement.status == status)
    
    entitlements = query.limit(limit).offset(offset).all()
    
    # Note: Cache handles serialization automatically via json.dumps
    # We return the SQLAlchemy objects directly, FastAPI handles serialization
    return entitlements


@router.put("/{entitlement_id}", response_model=EntitlementResponse)
async def update_entitlement(
    entitlement_id: UUID,
    entitlement_update: EntitlementUpdate,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """Update an entitlement."""
    entitlement = db.query(Entitlement).filter(
        Entitlement.id == entitlement_id,
        Entitlement.tenant_id == request_context.tenant_id,
    ).first()
    
    if not entitlement:
        raise HTTPException(status_code=404, detail="Entitlement not found")
    
    # Track changes for audit log
    old_values = {
        "status": entitlement.status,
        "expires_at": str(entitlement.expires_at) if entitlement.expires_at else None,
        "metadata": entitlement.metadata_json or {}
    }
    
    # Update fields
    new_values = old_values.copy()
    if entitlement_update.status is not None:
        entitlement.status = entitlement_update.status
        new_values["status"] = entitlement_update.status
    if entitlement_update.expires_at is not None:
        entitlement.expires_at = entitlement_update.expires_at
        new_values["expires_at"] = entitlement_update.expires_at
    if entitlement_update.metadata_json is not None:
        entitlement.metadata_json = entitlement_update.metadata_json
        new_values["metadata"] = entitlement_update.metadata_json
    
    db.commit()
    db.refresh(entitlement)
    
    # Audit log
    audit_logger = AuditLogger(db)
    audit_logger.log_entitlement_updated(
        entitlement,
        performed_by=_resolve_audit_actor(request_context, entitlement.granted_by),
        old_values=old_values,
        new_values=new_values,
        reason="Entitlement updated via API"
    )
    
    # Invalidate cache
    cache.invalidate_entitlement(str(entitlement.id), str(entitlement.tenant_id))
    
    return entitlement


@router.delete("/{entitlement_id}", status_code=204)
async def delete_entitlement(
    entitlement_id: UUID,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """Delete (revoke) an entitlement."""
    entitlement = db.query(Entitlement).filter(
        Entitlement.id == entitlement_id,
        Entitlement.tenant_id == request_context.tenant_id,
    ).first()
    
    if not entitlement:
        raise HTTPException(status_code=404, detail="Entitlement not found")
    
    # Soft delete by setting status to 'revoked'
    entitlement.status = "revoked"
    db.commit()
    
    # Audit log
    audit_logger = AuditLogger(db)
    audit_logger.log_entitlement_revoked(
        entitlement,
        performed_by=_resolve_audit_actor(request_context, entitlement.granted_by),
        reason="Entitlement revoked via API"
    )
    
    # Invalidate cache
    cache.invalidate_entitlement(str(entitlement.id), str(entitlement.tenant_id))
    
    return None
