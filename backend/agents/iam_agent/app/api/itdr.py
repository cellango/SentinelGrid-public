"""Compatibility intake paths for audited proposals, with no enforcement effects."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.request_context import (
    RequestContext,
    get_current_request_context,
    get_entitlement_session,
)
from app.schemas.itdr import ThreatSignal, ThreatSignalBatch, EnforcementResponse
from app.services.itdr_service import ITDRService, require_itdr_admin

router = APIRouter(prefix="/internal/iam/itdr", tags=["itdr"])


def get_itdr_context(context: RequestContext = Depends(get_current_request_context)):
    require_itdr_admin(context)
    return context


@router.post("/enforce", response_model=EnforcementResponse)
async def enforce_threat(
    signal: ThreatSignal,
    context: RequestContext = Depends(get_itdr_context),
    db: Session = Depends(get_entitlement_session),
):
    """Record a response proposal; the legacy path name does not enable execution."""
    return (await ITDRService(db).propose([signal], context))[0]


@router.post(
    "/enforce/batch", response_model=dict[str, list[EnforcementResponse] | int]
)
async def enforce_threats_batch(
    batch: ThreatSignalBatch,
    context: RequestContext = Depends(get_itdr_context),
    db: Session = Depends(get_entitlement_session),
):
    results = await ITDRService(db).propose(batch.signals, context)
    return {"results": results, "count": len(results)}
