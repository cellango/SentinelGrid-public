"""Posture score endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query

from app.services.posture_scoring import PostureScoringService
from app.core.config import settings
from app.core.security import require_orchestrator_request
from sqlalchemy import create_engine, text
from uuid import UUID
from app.core.security import get_current_tenant

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tenant", tags=["posture"], dependencies=[Depends(require_orchestrator_request)])

_posture_scorer = PostureScoringService()
_history_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)


@router.get("/{tenant_id}/posture-score")
async def get_posture_score(tenant_id: str):
    """Return posture score + breakdown for a tenant (non-mock)."""
    try:
        return _posture_scorer.score_tenant(tenant_id)
    except Exception as e:
        logger.error(f"Failed to compute posture score for {tenant_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to compute posture score")


@router.get("/{tenant_id}/posture-score/history")
async def get_posture_score_history(
    tenant_id: UUID,
    limit: int = Query(14, ge=1, le=90),
    authenticated_tenant_id: UUID = Depends(get_current_tenant),
):
    """Read only the exact verified tenant's stored history; no score generation."""
    if tenant_id != authenticated_tenant_id:
        raise HTTPException(403, "Access denied: Tenant mismatch")
    try:
        with _history_engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, overall_score, coverage, incident_penalty, computed_at
                    FROM public.posture_score_snapshot
                    WHERE tenant_id = :tenant_id
                    ORDER BY computed_at DESC
                    LIMIT :limit
                    """
                ),
                {"tenant_id": str(authenticated_tenant_id), "limit": limit},
            ).mappings().all()
            return {"items": [dict(r) for r in rows]}
    except Exception:
        logger.warning("Posture history store unavailable")
        raise HTTPException(503, "Posture history unavailable") from None



@router.post("/{tenant_id}/posture-rescore")
async def trigger_posture_rescore(tenant_id: str):
    """
    Event-driven re-score trigger.
    Intended to be called after scan ingestion or incident updates.
    Returns the freshly computed score (also persisted as a snapshot).
    """
    try:
        return _posture_scorer.score_tenant(tenant_id)
    except Exception as e:
        logger.error(f"Failed to rescore posture for {tenant_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to rescore posture")
