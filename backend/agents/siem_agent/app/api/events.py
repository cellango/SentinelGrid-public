"""Event ingestion API endpoints (internal)."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Header
from uuid import UUID
from pydantic import BaseModel
from app.core.ingest_client import IngestClient
from app.core.config import settings
from sg_core.service_security import verify_internal_service_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/siem/events", tags=["events"])

# Service-to-service authentication token
INTERNAL_SERVICE_TOKEN = settings.INTERNAL_SERVICE_TOKEN


class BatchEventRequest(BaseModel):
    """Batch event ingestion request model."""
    events: List[Dict[str, Any]]
    tenant_id: Optional[str] = None


def verify_internal_token(
    authorization: Optional[str] = Header(None),
    x_internal_service_token: Optional[str] = Header(None, alias="X-Internal-Service-Token"),
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token"),
) -> bool:
    """
    Verify internal service token for service-to-service calls.
    """
    verify_internal_service_token(
        INTERNAL_SERVICE_TOKEN,
        authorization=authorization,
        x_internal_service_token=x_internal_service_token,
        x_internal_token=x_internal_token,
        missing_detail="Missing authorization header",
        invalid_detail="Invalid internal service token",
    )
    return True


@router.post("/batch")
async def ingest_event_batch(
    batch_data: BatchEventRequest,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    _verified: bool = Depends(verify_internal_token),
    ingest_client: IngestClient = Depends(lambda: IngestClient())
):
    """
    Internal endpoint for batch event ingestion; routes through SentinelGuard ingest.
    """
    try:
        events = batch_data.events
        if not events:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No events provided in batch"
            )

        # Normalize timestamps and ensure IDs where possible
        normalized: List[Dict[str, Any]] = []
        for event in events:
            ev = dict(event)
            if "@timestamp" not in ev:
                ev["@timestamp"] = datetime.utcnow().isoformat()
            elif isinstance(ev["@timestamp"], datetime):
                ev["@timestamp"] = ev["@timestamp"].isoformat()
            if "id" not in ev:
                ev["id"] = str(UUID())
            normalized.append(ev)

        ingest_client.send_batch(
            tenant_id=tenant_id,
            agent_id=settings.SERVICE_NAME,
            events=normalized,
        )

        logger.info("Routed %d events via SentinelGuard ingest for tenant %s", len(normalized), tenant_id)

        return {
            "indexed": len(normalized),
            "failed": 0,
            "index": "sentinelguard-events",
            "errors": [],
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to ingest event batch: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest events: {str(e)}"
        )
