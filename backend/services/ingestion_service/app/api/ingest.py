"""Ingestion API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import Optional
from app.models.event import IngestBatchRequest, IngestResponse
from app.services.ingestion_service import IngestionService
from app.core.security import get_current_tenant, require_ingestion_request

router = APIRouter(prefix="/ingest", tags=["ingestion"], dependencies=[Depends(require_ingestion_request)])


def get_ingestion_service() -> IngestionService:
    """Dependency to get ingestion service."""
    from app.services.ingestion_service import IngestionService
    return IngestionService()


@router.post("/events", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_events(
    request: IngestBatchRequest,
    tenant_id: str = Depends(get_current_tenant),
    service: IngestionService = Depends(get_ingestion_service)
):
    """
    Ingest a batch of events.
    
    Events are validated, normalized to ECS format, and queued for batch processing.
    Returns immediately after validation (async processing).
    """
    try:
        response = await service.ingest_batch(request, tenant_id)
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest events: {str(e)}"
        )


@router.post("/events/flush")
async def flush_events(
    tenant_id: str = Depends(get_current_tenant),
    service: IngestionService = Depends(get_ingestion_service)
):
    """
    Force flush pending events for current tenant.
    
    This endpoint forces immediate processing of queued events.
    """
    try:
        await service.flush_tenant_batch(tenant_id)
        return {"status": "flushed", "tenant_id": tenant_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to flush events: {str(e)}"
        )

