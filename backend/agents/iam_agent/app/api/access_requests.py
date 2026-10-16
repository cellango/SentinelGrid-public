"""Access Requests API endpoints."""

from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel, Field, ConfigDict

from app.api.request_context import (
    RequestContext,
    ensure_request_tenant_matches,
    get_current_request_context,
    get_tenant_session,
)
from app.core.tenant_isolation import TenantIsolationValidator
from app.models.access_request import AccessRequest, AccessRequestHistory
from app.models.entitlement import Entitlement
from app.services.audit_logger import AuditLogger

router = APIRouter(prefix="/api/v1/access-requests", tags=["access-requests"])
REQUEST_ADMIN_ROLES = {"TENANT_ADMIN", "SOC_MANAGER", "PLATFORM_ADMIN"}


# ============================================================================
# Access Request Schemas
# ============================================================================

class AccessRequestCreate(BaseModel):
    """Schema for creating an access request."""
    tenant_id: UUID
    requested_for: Optional[UUID] = None  # If None, defaults to requested_by
    resource_type: str = Field(..., max_length=100)
    resource_id: str = Field(..., max_length=255)
    action: str = Field(..., max_length=50)
    justification: str = Field(..., min_length=10, description="Why access is needed")
    expires_at: Optional[datetime] = None  # Optional expiration for requested access


class AccessRequestResponse(BaseModel):
    """Schema for access request response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    requested_by: UUID
    requested_for: UUID
    resource_type: str
    resource_id: str
    action: str
    justification: str
    status: str
    reviewer_id: Optional[UUID]
    reviewed_at: Optional[datetime]
    review_comments: Optional[str]
    expires_at: Optional[datetime]
    entitlement_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime


class AccessRequestReview(BaseModel):
    """Schema for reviewing an access request."""
    decision: str = Field(..., pattern="^(approve|deny)$")
    comments: Optional[str] = None


class AccessRequestHistoryResponse(BaseModel):
    """Schema for access request history."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    request_id: UUID
    event_type: str
    performed_by: UUID
    performed_at: datetime
    comments: Optional[str]
    old_status: Optional[str]
    new_status: Optional[str]


def _current_user_uuid(request_context: RequestContext) -> UUID:
    if not request_context.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No user_id in token",
        )
    try:
        return UUID(str(request_context.user_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user_id in token",
        ) from exc


def _has_access_request_admin_role(request_context: RequestContext) -> bool:
    normalized_roles = {role.upper() for role in request_context.roles}
    return bool(normalized_roles.intersection(REQUEST_ADMIN_ROLES))


def _ensure_can_view_access_request(
    access_request: AccessRequest,
    request_context: RequestContext,
) -> UUID:
    current_user_id = _current_user_uuid(request_context)
    if _has_access_request_admin_role(request_context):
        return current_user_id

    permitted_user_ids = {
        access_request.requested_by,
        access_request.requested_for,
        access_request.reviewer_id,
    }
    if current_user_id not in {user_id for user_id in permitted_user_ids if user_id is not None}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    return current_user_id


# ============================================================================
# Access Request Endpoints
# ============================================================================

@router.post("", response_model=AccessRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_access_request(
    request: AccessRequestCreate,
    db: Session = Depends(get_tenant_session),
    request_context: RequestContext = Depends(get_current_request_context),
):
    """Create a new access request."""
    current_user_id = _current_user_uuid(request_context)
    ensure_request_tenant_matches(request_context.tenant_id, request.tenant_id)
    TenantIsolationValidator.validate_tenant_id(request_context.tenant_id)
    
    # Set requested_for to current user if not specified
    requested_for = request.requested_for or current_user_id
    
    # Check if entitlement already exists
    existing = db.query(Entitlement).filter(
        Entitlement.tenant_id == request_context.tenant_id,
        Entitlement.resource_type == request.resource_type,
        Entitlement.resource_id == request.resource_id,
        Entitlement.action == request.action,
        Entitlement.granted_to_type == 'user',
        Entitlement.granted_to_id == requested_for,
        Entitlement.status == 'active'
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Entitlement already exists for this user"
        )
    
    # Check for duplicate pending request
    duplicate = db.query(AccessRequest).filter(
        AccessRequest.tenant_id == request_context.tenant_id,
        AccessRequest.requested_for == requested_for,
        AccessRequest.resource_type == request.resource_type,
        AccessRequest.resource_id == request.resource_id,
        AccessRequest.action == request.action,
        AccessRequest.status == 'pending'
    ).first()
    
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending request for this access already exists"
        )
    
    # Create access request
    db_request = AccessRequest(
        tenant_id=request_context.tenant_id,
        requested_by=current_user_id,
        requested_for=requested_for,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        action=request.action,
        justification=request.justification,
        expires_at=request.expires_at,
        status='pending'
    )
    db.add(db_request)
    db.flush()
    
    # Create history entry
    history = AccessRequestHistory(
        request_id=db_request.id,
        event_type='created',
        performed_by=current_user_id,
        comments=request.justification
    )
    db.add(history)
    db.commit()
    db.refresh(db_request)
    
    # Log audit event
    audit_logger = AuditLogger(db)
    audit_logger.log_entitlement_event(
        event_type="access_request_created",
        entitlement_id=None,
        tenant_id=request_context.tenant_id,
        performed_by=current_user_id,
        changes={
            "request_id": str(db_request.id),
            "resource_type": request.resource_type,
            "action": request.action,
        },
        reason="Access request created",
    )
    
    return db_request


@router.get("", response_model=List[AccessRequestResponse])
async def list_access_requests(
    tenant_id: Optional[UUID] = Query(None, description="Filter by tenant ID"),
    request_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    requested_by: Optional[UUID] = Query(None, description="Filter by requester"),
    reviewer_id: Optional[UUID] = Query(None, description="Filter by reviewer (for pending reviews)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_tenant_session),
    request_context: RequestContext = Depends(get_current_request_context),
):
    """List access requests with optional filters."""
    ensure_request_tenant_matches(request_context.tenant_id, tenant_id)
    current_user_id = _current_user_uuid(request_context)
    is_request_admin = _has_access_request_admin_role(request_context)
    query_tenant_id = request_context.tenant_id
    
    query = db.query(AccessRequest).filter(AccessRequest.tenant_id == query_tenant_id)
    
    if request_status:
        query = query.filter(AccessRequest.status == request_status)
    if requested_by:
        if not is_request_admin and requested_by != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        query = query.filter(AccessRequest.requested_by == requested_by)
    elif not is_request_admin:
        query = query.filter(
            or_(
                AccessRequest.requested_by == current_user_id,
                AccessRequest.requested_for == current_user_id,
                AccessRequest.reviewer_id == current_user_id,
            )
        )
    if reviewer_id:
        if not is_request_admin and reviewer_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        query = query.filter(AccessRequest.reviewer_id == reviewer_id)
    
    requests = query.order_by(AccessRequest.created_at.desc()).offset(offset).limit(limit).all()
    return requests


@router.get("/{request_id}", response_model=AccessRequestResponse)
async def get_access_request(
    request_id: UUID,
    db: Session = Depends(get_tenant_session),
    request_context: RequestContext = Depends(get_current_request_context),
):
    """Get access request details."""
    access_request = db.query(AccessRequest).filter(
        AccessRequest.id == request_id,
        AccessRequest.tenant_id == request_context.tenant_id,
    ).first()
    if not access_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found")

    _ensure_can_view_access_request(access_request, request_context)
    return access_request


@router.post("/{request_id}/review", response_model=AccessRequestResponse)
async def review_access_request(
    request_id: UUID,
    review: AccessRequestReview,
    db: Session = Depends(get_tenant_session),
    request_context: RequestContext = Depends(get_current_request_context),
):
    """Review (approve or deny) an access request."""
    current_user_id = _current_user_uuid(request_context)
    if not _has_access_request_admin_role(request_context):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    access_request = db.query(AccessRequest).filter(
        AccessRequest.id == request_id,
        AccessRequest.tenant_id == request_context.tenant_id,
    ).first()
    if not access_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found")
    
    if access_request.status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot review request with status '{access_request.status}'"
        )
    
    old_status = access_request.status
    new_status = 'approved' if review.decision == 'approve' else 'denied'
    
    # Update request
    access_request.status = new_status
    access_request.reviewer_id = current_user_id
    access_request.reviewed_at = datetime.now(timezone.utc)
    access_request.review_comments = review.comments
    
    # If approved, create entitlement
    if review.decision == 'approve':
        entitlement = Entitlement(
            tenant_id=access_request.tenant_id,
            resource_type=access_request.resource_type,
            resource_id=access_request.resource_id,
            action=access_request.action,
            granted_to_type='user',
            granted_to_id=access_request.requested_for,
            granted_by=current_user_id,
            expires_at=access_request.expires_at,
            status='active',
            metadata_json={'source': 'access_request', 'request_id': str(access_request.id)}
        )
        db.add(entitlement)
        db.flush()
        access_request.entitlement_id = entitlement.id
        
        # Log audit event
        audit_logger = AuditLogger(db)
        audit_logger.log_entitlement_event(
            event_type="created",
            entitlement_id=entitlement.id,
            tenant_id=access_request.tenant_id,
            performed_by=current_user_id,
            changes={
                "resource_type": access_request.resource_type,
                "action": access_request.action,
                "source": "access_request",
            },
            reason="Access request approved",
        )
    
    # Create history entry
    history = AccessRequestHistory(
        request_id=access_request.id,
        event_type='approved' if review.decision == 'approve' else 'denied',
        performed_by=current_user_id,
        old_status=old_status,
        new_status=new_status,
        comments=review.comments
    )
    db.add(history)
    db.commit()
    db.refresh(access_request)
    
    return access_request


@router.get("/{request_id}/history", response_model=List[AccessRequestHistoryResponse])
async def get_access_request_history(
    request_id: UUID,
    db: Session = Depends(get_tenant_session),
    request_context: RequestContext = Depends(get_current_request_context),
):
    """Get access request history/timeline."""
    access_request = db.query(AccessRequest).filter(
        AccessRequest.id == request_id,
        AccessRequest.tenant_id == request_context.tenant_id,
    ).first()
    if not access_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found")
    _ensure_can_view_access_request(access_request, request_context)

    history = db.query(AccessRequestHistory).filter(
        AccessRequestHistory.request_id == request_id
    ).order_by(AccessRequestHistory.performed_at.desc()).all()
    
    return history


@router.post("/{request_id}/cancel", response_model=AccessRequestResponse)
async def cancel_access_request(
    request_id: UUID,
    db: Session = Depends(get_tenant_session),
    request_context: RequestContext = Depends(get_current_request_context),
):
    """Cancel an access request (only by requester)."""
    current_user_id = _current_user_uuid(request_context)
    access_request = db.query(AccessRequest).filter(
        AccessRequest.id == request_id,
        AccessRequest.tenant_id == request_context.tenant_id,
    ).first()
    if not access_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found")
    
    if access_request.requested_by != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the requester can cancel this request"
        )
    
    if access_request.status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel request with status '{access_request.status}'"
        )
    
    old_status = access_request.status
    access_request.status = 'cancelled'
    
    # Create history entry
    history = AccessRequestHistory(
        request_id=access_request.id,
        event_type='cancelled',
        performed_by=current_user_id,
        old_status=old_status,
        new_status='cancelled'
    )
    db.add(history)
    db.commit()
    db.refresh(access_request)
    
    return access_request
