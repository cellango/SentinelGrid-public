"""Governance API endpoints for audit campaigns and certifications."""

from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict

from app.api.request_context import (
    RequestContext,
    ensure_request_tenant_matches,
    get_current_request_context,
    get_tenant_session,
)
from app.core.tenant_isolation import TenantIsolationValidator
from app.models.audit_campaign import AuditCampaign
from app.models.certification import Certification
from app.models.entitlement import Entitlement
from app.services.audit_logger import AuditLogger

router = APIRouter(prefix="/api/v1/governance", tags=["governance"])


# ============================================================================
# Campaign Management Schemas
# ============================================================================

class CampaignCreate(BaseModel):
    """Schema for creating a campaign."""
    tenant_id: UUID
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    reviewer_type: str = Field(..., pattern="^(self|manager|admin)$")
    auto_revoke_days: Optional[int] = Field(None, ge=0, description="Days after end_date to auto-revoke uncertified")
    entitlement_patterns: Optional[List[str]] = Field(default_factory=list, description="Entitlement patterns to include (e.g., 'incident:*:write')")


class CampaignResponse(BaseModel):
    """Schema for campaign response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    name: str
    description: Optional[str]
    start_date: datetime
    end_date: datetime
    status: str
    reviewer_type: str
    auto_revoke_days: Optional[int]
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign."""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed|cancelled)$")
    reviewer_type: Optional[str] = Field(None, pattern="^(self|manager|admin)$")
    auto_revoke_days: Optional[int] = Field(None, ge=0)


# ============================================================================
# Certification Schemas
# ============================================================================

class CertificationResponse(BaseModel):
    """Schema for certification response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    campaign_id: UUID
    entitlement_id: UUID
    user_id: UUID
    reviewer_id: UUID
    review_status: str
    review_date: Optional[datetime]
    comments: Optional[str]
    created_at: datetime
    updated_at: datetime


class CertificationDecision(BaseModel):
    """Schema for certification decision."""
    decision: str = Field(..., pattern="^(approved|revoked|retained)$")
    comments: Optional[str] = None


class BulkCertificationDecision(BaseModel):
    """Schema for bulk certification."""
    certification_ids: List[UUID]
    decision: str = Field(..., pattern="^(approved|revoked|retained)$")
    comments: Optional[str] = None


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


# ============================================================================
# Campaign Management Endpoints
# ============================================================================

@router.post("/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign: CampaignCreate,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    """Create a new audit campaign."""
    current_user_id = _current_user_uuid(request_context)
    ensure_request_tenant_matches(request_context.tenant_id, campaign.tenant_id)
    TenantIsolationValidator.validate_tenant_id(request_context.tenant_id)
    
    # Validate dates
    if campaign.end_date <= campaign.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date"
        )
    
    # Create campaign
    db_campaign = AuditCampaign(
        tenant_id=request_context.tenant_id,
        name=campaign.name,
        description=campaign.description,
        start_date=campaign.start_date,
        end_date=campaign.end_date,
        status='pending',
        reviewer_type=campaign.reviewer_type,
        auto_revoke_days=campaign.auto_revoke_days,
        created_by=current_user_id
    )
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)
    
    # Log audit event
    audit_logger = AuditLogger(db)
    audit_logger.log_entitlement_event(
        event_type="campaign_created",
        entitlement_id=None,  # Campaign-level event
        tenant_id=request_context.tenant_id,
        performed_by=current_user_id,
        changes={"campaign_id": str(db_campaign.id), "name": db_campaign.name},
        reason="Campaign created",
    )
    
    return db_campaign


@router.get("/campaigns", response_model=List[CampaignResponse])
async def list_campaigns(
    tenant_id: Optional[UUID] = Query(None, description="Filter by tenant ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    """List campaigns with optional filters."""
    ensure_request_tenant_matches(request_context.tenant_id, tenant_id)
    query_tenant_id = request_context.tenant_id

    query = db.query(AuditCampaign).filter(AuditCampaign.tenant_id == query_tenant_id)
    
    if status:
        query = query.filter(AuditCampaign.status == status)
    
    campaigns = query.order_by(AuditCampaign.created_at.desc()).offset(offset).limit(limit).all()
    return campaigns


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    """Get campaign details."""
    campaign = db.query(AuditCampaign).filter(
        AuditCampaign.id == campaign_id,
        AuditCampaign.tenant_id == request_context.tenant_id,
    ).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    
    return campaign


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: UUID,
    campaign_update: CampaignUpdate,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    """Update a campaign."""
    current_user_id = _current_user_uuid(request_context)
    campaign = db.query(AuditCampaign).filter(
        AuditCampaign.id == campaign_id,
        AuditCampaign.tenant_id == request_context.tenant_id,
    ).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    
    old_value = {
        "status": campaign.status,
        "name": campaign.name,
        "end_date": campaign.end_date.isoformat() if campaign.end_date else None
    }
    
    # Update fields
    update_data = campaign_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(campaign, key, value)
    
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    
    # Log audit event
    audit_logger = AuditLogger(db)
    audit_logger.log_entitlement_event(
        event_type="campaign_updated",
        entitlement_id=None,
        tenant_id=campaign.tenant_id,
        performed_by=current_user_id,
        changes={
            "status": {"old": old_value["status"], "new": campaign.status},
            "name": {"old": old_value["name"], "new": campaign.name},
        },
        reason="Campaign updated",
    )
    
    return campaign


@router.post("/campaigns/{campaign_id}/start", response_model=CampaignResponse)
async def start_campaign(
    campaign_id: UUID,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    """Start a campaign and generate certifications."""
    current_user_id = _current_user_uuid(request_context)
    campaign = db.query(AuditCampaign).filter(
        AuditCampaign.id == campaign_id,
        AuditCampaign.tenant_id == request_context.tenant_id,
    ).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    
    if campaign.status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start campaign with status '{campaign.status}'"
        )
    
    # Change status to in_progress
    campaign.status = 'in_progress'
    
    # Generate certifications for entitlements
    # Filter entitlements based on campaign scope (entitlement patterns would be stored)
    # For now, get all active entitlements for the tenant
    entitlements = db.query(Entitlement).filter(
        Entitlement.tenant_id == campaign.tenant_id,
        Entitlement.status == 'active'
    ).all()
    
    # Create certifications for each entitlement
    certifications_created = 0
    for entitlement in entitlements:
        # Determine reviewer_id based on reviewer_type
        reviewer_id = entitlement.granted_to_id  # Default to self
        # TODO: Implement manager/admin reviewer lookup
        
        certification = Certification(
            campaign_id=campaign.id,
            entitlement_id=entitlement.id,
            user_id=entitlement.granted_to_id,
            reviewer_id=reviewer_id,
            review_status='pending'
        )
        db.add(certification)
        certifications_created += 1
    
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    
    # Log audit event
    audit_logger = AuditLogger(db)
    audit_logger.log_entitlement_event(
        event_type="campaign_started",
        entitlement_id=None,
        tenant_id=campaign.tenant_id,
        performed_by=current_user_id,
        changes={
            "campaign_id": str(campaign.id),
            "certifications_created": certifications_created
        },
        reason="Campaign started",
    )
    
    return campaign


@router.post("/campaigns/{campaign_id}/complete", response_model=CampaignResponse)
async def complete_campaign(
    campaign_id: UUID,
    auto_revoke: bool = Query(True, description="Auto-revoke uncertified entitlements"),
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    """Complete a campaign and optionally auto-revoke uncertified entitlements."""
    current_user_id = _current_user_uuid(request_context)
    campaign = db.query(AuditCampaign).filter(
        AuditCampaign.id == campaign_id,
        AuditCampaign.tenant_id == request_context.tenant_id,
    ).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    
    if campaign.status != 'in_progress':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete campaign with status '{campaign.status}'"
        )
    
    # Auto-revoke uncertified entitlements if requested
    revoked_count = 0
    if auto_revoke:
        pending_certs = db.query(Certification).filter(
            Certification.campaign_id == campaign.id,
            Certification.review_status == 'pending'
        ).all()
        
        for cert in pending_certs:
            entitlement = db.query(Entitlement).filter(Entitlement.id == cert.entitlement_id).first()
            if entitlement:
                entitlement.status = 'revoked'
                cert.review_status = 'revoked'
                cert.review_date = datetime.utcnow()
                revoked_count += 1
    
    campaign.status = 'completed'
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    
    # Log audit event
    audit_logger = AuditLogger(db)
    audit_logger.log_entitlement_event(
        event_type="campaign_completed",
        entitlement_id=None,
        tenant_id=campaign.tenant_id,
        performed_by=current_user_id,
        changes={
            "campaign_id": str(campaign.id),
            "auto_revoked": revoked_count
        },
        reason="Campaign completed",
    )
    
    return campaign


# ============================================================================
# Certification Endpoints
# ============================================================================

@router.get("/certifications/pending", response_model=List[CertificationResponse])
async def get_pending_certifications(
    user_id: Optional[UUID] = Query(None, description="Filter by user ID (for self-certification)"),
    campaign_id: Optional[UUID] = Query(None, description="Filter by campaign ID"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    """Get pending certifications for the current user or specified user."""
    current_user_id = _current_user_uuid(request_context)
    query = db.query(Certification).join(
        AuditCampaign,
        Certification.campaign_id == AuditCampaign.id,
    ).filter(
        Certification.review_status == 'pending',
        AuditCampaign.tenant_id == request_context.tenant_id,
    )
    
    # Filter by reviewer (current user or specified user)
    reviewer_filter = user_id if user_id else current_user_id
    query = query.filter(Certification.reviewer_id == reviewer_filter)
    
    if campaign_id:
        query = query.filter(Certification.campaign_id == campaign_id)
    
    certifications = query.order_by(Certification.created_at.asc()).offset(offset).limit(limit).all()
    return certifications


@router.get("/certifications", response_model=List[CertificationResponse])
async def list_certifications(
    campaign_id: Optional[UUID] = Query(None, description="Filter by campaign ID"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    review_status: Optional[str] = Query(None, description="Filter by review status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    """List certifications with optional filters."""
    query = db.query(Certification).join(
        AuditCampaign,
        Certification.campaign_id == AuditCampaign.id,
    ).filter(
        AuditCampaign.tenant_id == request_context.tenant_id,
    )
    
    if campaign_id:
        query = query.filter(Certification.campaign_id == campaign_id)
    if user_id:
        query = query.filter(Certification.user_id == user_id)
    if review_status:
        query = query.filter(Certification.review_status == review_status)
    
    certifications = query.order_by(Certification.created_at.desc()).offset(offset).limit(limit).all()
    return certifications


@router.post("/certifications/{certification_id}/certify", response_model=CertificationResponse)
async def certify_entitlement(
    certification_id: UUID,
    decision: CertificationDecision,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    """Submit a certification decision for an entitlement."""
    current_user_id = _current_user_uuid(request_context)
    certification = db.query(Certification).join(
        AuditCampaign,
        Certification.campaign_id == AuditCampaign.id,
    ).filter(
        Certification.id == certification_id,
        AuditCampaign.tenant_id == request_context.tenant_id,
    ).first()
    if not certification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certification not found")
    
    # Verify reviewer is the current user
    if certification.reviewer_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to certify this entitlement"
        )
    
    if certification.review_status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Certification already completed with status '{certification.review_status}'"
        )
    
    old_status = certification.review_status
    
    # Update certification
    certification.review_status = decision.decision
    certification.review_date = datetime.utcnow()
    certification.comments = decision.comments
    
    # Update entitlement status if revoked
    if decision.decision == 'revoked':
        entitlement = db.query(Entitlement).filter(Entitlement.id == certification.entitlement_id).first()
        if entitlement:
            entitlement.status = 'revoked'
    
    db.add(certification)
    db.commit()
    db.refresh(certification)
    
    # Get campaign for tenant_id
    campaign = db.query(AuditCampaign).filter(
        AuditCampaign.id == certification.campaign_id,
        AuditCampaign.tenant_id == request_context.tenant_id,
    ).first()
    
    # Log audit event
    audit_logger = AuditLogger(db)
    audit_logger.log_entitlement_event(
        event_type="certified",
        entitlement_id=certification.entitlement_id,
        tenant_id=campaign.tenant_id if campaign else request_context.tenant_id,
        performed_by=current_user_id,
        changes={
            "review_status": {"old": old_status, "new": decision.decision},
            "comments": {"old": None, "new": decision.comments},
        },
        reason="Certification decision submitted",
        campaign_id=campaign.id if campaign else None,
        certification_id=certification.id,
    )
    
    return certification


@router.post("/certifications/bulk-certify", response_model=dict)
async def bulk_certify(
    bulk_decision: BulkCertificationDecision,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    """Bulk certify multiple entitlements."""
    current_user_id = _current_user_uuid(request_context)
    certifications = db.query(Certification).join(
        AuditCampaign,
        Certification.campaign_id == AuditCampaign.id,
    ).filter(
        Certification.id.in_(bulk_decision.certification_ids),
        Certification.reviewer_id == current_user_id,
        Certification.review_status == 'pending',
        AuditCampaign.tenant_id == request_context.tenant_id,
    ).all()
    
    if len(certifications) != len(bulk_decision.certification_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some certifications not found or already completed"
        )
    
    updated_count = 0
    for certification in certifications:
        certification.review_status = bulk_decision.decision
        certification.review_date = datetime.utcnow()
        certification.comments = bulk_decision.comments
        
        if bulk_decision.decision == 'revoked':
            entitlement = db.query(Entitlement).filter(Entitlement.id == certification.entitlement_id).first()
            if entitlement:
                entitlement.status = 'revoked'
        
        updated_count += 1
    
    db.commit()
    
    return {
        "certified_count": updated_count,
        "decision": bulk_decision.decision
    }
