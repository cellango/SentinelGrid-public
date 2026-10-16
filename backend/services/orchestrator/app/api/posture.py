"""Posture score endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException

from app.services.posture_scoring import PostureScoringService
from app.core.config import settings
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tenant", tags=["posture"])

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
async def get_posture_score_history(tenant_id: str, limit: int = 14):
    """Return recent posture score snapshots for trends."""
    try:
        with _history_engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, overall_score, coverage, incident_penalty, computed_at
                    FROM posture_score_snapshot
                    WHERE tenant_id = :tenant_id
                    ORDER BY computed_at DESC
                    LIMIT :limit
                    """
                ),
                {"tenant_id": tenant_id, "limit": limit},
            ).mappings().all()
            return {"items": [dict(r) for r in rows]}
    except Exception as e:
        # For demo environments with no history table/data, return an empty set instead of 500
        logger.warning(f"[posture] Returning empty history for {tenant_id}: {e}")
        return {"items": []}


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
