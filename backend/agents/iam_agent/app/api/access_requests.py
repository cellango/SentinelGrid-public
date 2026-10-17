"""Access Requests API endpoints."""

from contextlib import contextmanager
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel, Field, ConfigDict, AwareDatetime, field_validator

from app.api.request_context import (
    RequestContext,
    ensure_request_tenant_matches,
    get_current_request_context,
    get_entitlement_session as get_tenant_session,
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
    resource_type: str = Field(..., min_length=1, max_length=100)
    resource_id: str = Field(..., min_length=1, max_length=255)
    action: str = Field(..., min_length=1, max_length=50)
    justification: str = Field(..., min_length=10, description="Why access is needed")
    expires_at: Optional[AwareDatetime] = None

    @field_validator("resource_type", "resource_id", "action")
    @classmethod
    def nonblank_target(cls, value):
        if not value.strip():
            raise ValueError("A nonblank target is required")
        return value

    @field_validator("expires_at")
    @classmethod
    def future_expiry(cls, value):
        if value is not None and value <= datetime.now(timezone.utc):
            raise ValueError("Requested access must expire in the future")
        return value


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


def _response(row: AccessRequest) -> AccessRequestResponse:
    # V3 allowed NULL requested_for to mean the requester. Preserve that wire
    # behavior without rewriting historical rows or authorizing delegation.
    values = {name: getattr(row, name) for name in AccessRequestResponse.model_fields}
    values["requested_for"] = row.requested_for or row.requested_by
    return AccessRequestResponse.model_validate(values)


@contextmanager
def _request_change(db: Session):
    """The transition, grant, history and audit succeed or roll back together."""
    try:
        yield
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Access request change could not be committed") from exc


def _locked_request(db: Session, request_id: UUID, tenant_id: UUID) -> AccessRequest:
    row = db.query(AccessRequest).filter(
        AccessRequest.id == request_id, AccessRequest.tenant_id == tenant_id,
    ).populate_existing().with_for_update().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found")
    return row


def _record_transition(db: Session, row: AccessRequest, actor: UUID,
                       event: str, old_status: Optional[str], comments: Optional[str] = None):
    db.add(AccessRequestHistory(request_id=row.id, event_type=event, performed_by=actor,
                               old_status=old_status, new_status=row.status, comments=comments))
    AuditLogger(db).log_entitlement_event(
        event_type="access_request_" + event, entitlement_id=row.entitlement_id,
        tenant_id=row.tenant_id, performed_by=actor, subject_id=row.requested_for or row.requested_by,
        changes={"request_id": str(row.id), "resource_type": row.resource_type,
                 "resource_id": row.resource_id, "action": row.action,
                 "requested_by": str(row.requested_by),
                 "requested_for": str(row.requested_for or row.requested_by),
                 "expires_at": row.expires_at, "old_status": old_status, "new_status": row.status},
        reason=comments,
    )


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
    
    # Only the verified caller's tenant membership is established here. A
    # supplied UUID, including one supplied by an admin, is not membership proof.
    requested_for = request.requested_for or current_user_id
    if requested_for != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only self-service access requests are supported")

    with _request_change(db):
        existing = db.query(Entitlement).filter(
            Entitlement.tenant_id == request_context.tenant_id,
            Entitlement.resource_type == request.resource_type,
            Entitlement.resource_id == request.resource_id,
            Entitlement.action == request.action,
            Entitlement.granted_to_type == 'user',
            Entitlement.granted_to_id == requested_for,
            Entitlement.status == 'active',
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Entitlement already exists for this user")
        duplicate = db.query(AccessRequest).filter(
            AccessRequest.tenant_id == request_context.tenant_id,
            or_(AccessRequest.requested_for == requested_for,
                (AccessRequest.requested_for.is_(None)) & (AccessRequest.requested_by == requested_for)),
            AccessRequest.resource_type == request.resource_type,
            AccessRequest.resource_id == request.resource_id,
            AccessRequest.action == request.action, AccessRequest.status == 'pending',
        ).first()
        if duplicate:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="A pending request for this access already exists")
        row = AccessRequest(tenant_id=request_context.tenant_id, requested_by=current_user_id,
            requested_for=requested_for, resource_type=request.resource_type,
            resource_id=request.resource_id, action=request.action,
            justification=request.justification, expires_at=request.expires_at, status='pending')
        db.add(row)
        db.flush()
        _record_transition(db, row, current_user_id, 'created', None, request.justification)
        response = _response(row)
    return response


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
    return [_response(row) for row in requests]


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
    return _response(access_request)


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

    with _request_change(db):
        row = _locked_request(db, request_id, request_context.tenant_id)
        if row.status != 'pending':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Cannot review request with status '{row.status}'")
        beneficiary = row.requested_for or row.requested_by
        if review.decision == 'approve':
            if current_user_id in {row.requested_by, beneficiary}:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="An independent reviewer is required")
            if beneficiary != row.requested_by:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                    detail="Delegated requests need a verified membership path")
            if row.expires_at is not None and (
                row.expires_at.tzinfo is None or row.expires_at <= datetime.now(timezone.utc)
            ):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                    detail="Requested access has expired")
            existing = db.query(Entitlement).filter(
                Entitlement.tenant_id == request_context.tenant_id,
                Entitlement.granted_to_type == 'user', Entitlement.granted_to_id == beneficiary,
                Entitlement.resource_type == row.resource_type, Entitlement.resource_id == row.resource_id,
                Entitlement.action == row.action, Entitlement.status == 'active',
            ).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                    detail="Entitlement already exists for this user")
            entitlement = Entitlement(tenant_id=request_context.tenant_id,
                resource_type=row.resource_type, resource_id=row.resource_id, action=row.action,
                granted_to_type='user', granted_to_id=beneficiary, granted_by=current_user_id,
                expires_at=row.expires_at, status='active',
                metadata_json={'source': 'access_request', 'request_id': str(row.id)})
            db.add(entitlement)
            db.flush()
            row.entitlement_id = entitlement.id
            AuditLogger(db).log_entitlement_created(entitlement, current_user_id,
                                                    reason="Access request approved")
        old_status = row.status
        row.status = 'approved' if review.decision == 'approve' else 'denied'
        row.reviewer_id = current_user_id
        row.reviewed_at = datetime.now(timezone.utc)
        row.review_comments = review.comments
        _record_transition(db, row, current_user_id, row.status, old_status, review.comments)
        response = _response(row)
    return response


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
    with _request_change(db):
        row = _locked_request(db, request_id, request_context.tenant_id)
        if row.requested_by != current_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Only the requester can cancel this request")
        if row.status != 'pending':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Cannot cancel request with status '{row.status}'")
        old_status = row.status
        row.status = 'cancelled'
        _record_transition(db, row, current_user_id, 'cancelled', old_status)
        response = _response(row)
    return response
