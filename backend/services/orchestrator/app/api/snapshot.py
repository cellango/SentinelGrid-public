"""Snapshot API endpoints."""

import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from app.services.snapshot_service import SnapshotService
from app.models.snapshot import SecuritySnapshot
from app.core.security import get_current_tenant, require_orchestrator_request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tenant", tags=["snapshot"], dependencies=[Depends(require_orchestrator_request)])


def get_snapshot_service() -> SnapshotService:
    """Dependency to get snapshot service."""
    return SnapshotService()


@router.get("/{tenant_id}/security-snapshot", response_model=SecuritySnapshot)
async def get_security_snapshot(
    tenant_id: UUID,
    snapshot_service: SnapshotService = Depends(get_snapshot_service),
    authenticated_tenant_id: UUID = Depends(get_current_tenant),
):
    """
    Get comprehensive security snapshot for a tenant.
    
    This endpoint aggregates data from:
    - SIEM Agent (events, alerts, statistics)
    - IAM Agent (identity statistics)
    - Model Gateway (AI analysis)
    
    Returns a complete snapshot with AI-powered insights.
    """
    if tenant_id != authenticated_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Tenant mismatch",
        )

    try:
        snapshot = await snapshot_service.generate_security_snapshot(str(tenant_id))

        # Convert to response model
        return SecuritySnapshot(**snapshot)

    except Exception as e:
        logger.error(f"Error generating security snapshot: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate security snapshot: {str(e)}"
        )
