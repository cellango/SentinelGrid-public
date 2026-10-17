"""Governance adapters over verified context and the separate IAM database."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.api.request_context import (
    RequestContext,
    ensure_request_tenant_matches,
    get_current_request_context,
    get_entitlement_session as get_tenant_session,
)
from app.models.audit_campaign import AuditCampaign
from app.models.certification import Certification
from app.models.entitlement import Entitlement
from app.schemas.governance import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CertificationResponse,
    CertificationDecision,
    BulkCertificationDecision,
)
from app.services import governance_service as service

router = APIRouter(prefix="/api/v1/governance", tags=["governance"])


@router.post("/campaigns", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    campaign: CampaignCreate,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    ensure_request_tenant_matches(request_context.tenant_id, campaign.tenant_id)
    return service.create_campaign(db, request_context, campaign)


@router.get("/campaigns", response_model=list[CampaignResponse])
async def list_campaigns(
    tenant_id: UUID | None = Query(None),
    campaign_status: str | None = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    service.admin(request_context)
    ensure_request_tenant_matches(request_context.tenant_id, tenant_id)
    query = db.query(AuditCampaign).filter(
        AuditCampaign.tenant_id == request_context.tenant_id,
        AuditCampaign.scope["api_contract"].astext == service.CONTRACT,
    )
    if campaign_status:
        stored = {v: k for k, v in service.WIRE_STATUS.items()}.get(campaign_status)
        if stored is None:
            raise HTTPException(status_code=422, detail="Unsupported campaign status")
        query = query.filter(AuditCampaign.status == stored)
    return [
        service.campaign_response(c)
        for c in query.order_by(AuditCampaign.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    ]


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    service.admin(request_context)
    row = (
        db.query(AuditCampaign)
        .filter(
            AuditCampaign.id == campaign_id,
            AuditCampaign.tenant_id == request_context.tenant_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return service.campaign_response(row)


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: UUID,
    campaign_update: CampaignUpdate,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    return service.update_campaign(db, request_context, campaign_id, campaign_update)


@router.post("/campaigns/{campaign_id}/start", response_model=CampaignResponse)
async def start_campaign(
    campaign_id: UUID,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    return service.start_campaign(db, request_context, campaign_id)


@router.post("/campaigns/{campaign_id}/complete", response_model=CampaignResponse)
async def complete_campaign(
    campaign_id: UUID,
    auto_revoke: bool = Query(True),
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    return service.complete_campaign(db, request_context, campaign_id, auto_revoke)


def _cert_responses(rows, db, tenant):
    result = []
    for row in rows:
        grant = (
            db.query(Entitlement)
            .filter(
                Entitlement.id == row.entitlement_id, Entitlement.tenant_id == tenant
            )
            .first()
        )
        if grant is None or grant.granted_to_type != "user":
            raise HTTPException(
                status_code=409, detail="Unsupported certification subject"
            )
        result.append(service.cert_response(row, grant))
    return result


@router.get("/certifications/pending", response_model=list[CertificationResponse])
async def get_pending_certifications(
    user_id: UUID | None = Query(None),
    campaign_id: UUID | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    user = service.actor(request_context)
    if (
        user_id is not None
        and user_id != user
        and not service.is_admin(request_context)
    ):
        raise HTTPException(status_code=403, detail="Access denied")
    query = service.cert_query(db, request_context.tenant_id).filter(
        Certification.status == "pending",
        AuditCampaign.status == "active",
        Certification.certifier_id == (user_id or user),
        Certification.metadata_json["api_contract"].astext == service.CONTRACT,
    )
    if campaign_id:
        query = query.filter(Certification.campaign_id == campaign_id)
    return _cert_responses(
        query.order_by(Certification.created_at).offset(offset).limit(limit).all(),
        db,
        request_context.tenant_id,
    )


@router.get("/certifications", response_model=list[CertificationResponse])
async def list_certifications(
    campaign_id: UUID | None = Query(None),
    user_id: UUID | None = Query(None),
    review_status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    user = service.actor(request_context)
    query = service.cert_query(db, request_context.tenant_id).filter(
        Certification.metadata_json["api_contract"].astext == service.CONTRACT
    )
    if not service.is_admin(request_context):
        query = query.filter(
            or_(Certification.certifier_id == user, Entitlement.granted_to_id == user)
        )
    if campaign_id:
        query = query.filter(Certification.campaign_id == campaign_id)
    if user_id:
        query = query.filter(Entitlement.granted_to_id == user_id)
    if review_status:
        if review_status not in {"pending", "approved", "revoked", "retained"}:
            raise HTTPException(status_code=422, detail="Unsupported review status")
        query = query.filter(
            Certification.status
            == ("approved" if review_status == "retained" else review_status)
        )
        if review_status in {"approved", "retained"}:
            query = query.filter(
                Certification.metadata_json["review_outcome"].astext == review_status
            )
    return _cert_responses(
        query.order_by(Certification.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all(),
        db,
        request_context.tenant_id,
    )


@router.post("/certifications/bulk-certify", response_model=dict)
async def bulk_certify(
    bulk_decision: BulkCertificationDecision,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    return service.certify(
        db,
        request_context,
        bulk_decision.certification_ids,
        bulk_decision.decision,
        bulk_decision.comments,
        bulk=True,
    )


@router.post(
    "/certifications/{certification_id}/certify", response_model=CertificationResponse
)
async def certify_entitlement(
    certification_id: UUID,
    decision: CertificationDecision,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    return service.certify(
        db, request_context, [certification_id], decision.decision, decision.comments
    )
