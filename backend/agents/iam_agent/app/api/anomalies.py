"""
Security Anomalies API endpoints.

Provides access to detected security anomalies and threat intelligence.
"""

from datetime import datetime
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.request_context import RequestContext, get_current_request_context
from app.services.anomaly_store import AnomalyStore
from app.services.anomaly_detection import AnomalyDetectionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/security/anomalies", tags=["anomalies"])


# ============================================================================
# Request/Response Models
# ============================================================================

class AnomalyResponse(BaseModel):
    """Anomaly response model."""
    id: Optional[str] = None
    tenant_id: str
    user_id: Optional[str]
    anomaly_type: str
    severity: str
    title: str
    description: Optional[str]
    risk_score: float
    metadata: Optional[dict]
    status: str
    detected_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class AnomalyListResponse(BaseModel):
    """Paginated anomaly list response."""
    items: List[AnomalyResponse]
    total: int
    page: int
    limit: int
    pages: int


class AcknowledgeAnomalyRequest(BaseModel):
    """Acknowledge anomaly request."""
    notes: Optional[str] = None


# ============================================================================
# Helper Functions
# ============================================================================

# ============================================================================
# Anomaly Endpoints
# ============================================================================

@router.get("", response_model=AnomalyListResponse)
async def list_anomalies(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    anomaly_type: Optional[str] = Query(None, description="Filter by anomaly type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    request_context: RequestContext = Depends(get_current_request_context)
):
    """
    List detected security anomalies.
    
    Can filter by user, type, severity, and status.
    """
    tenant_id = str(request_context.tenant_id)
    
    try:
        detection_service = AnomalyDetectionService()
        # Refresh anomalies for this tenant/user, then return persisted view
        await detection_service.detect_anomalies(
            tenant_id=tenant_id,
            user_id=user_id,
            time_window_hours=24,
        )

        store = detection_service.store
        result = store.list_anomalies(
            tenant_id=tenant_id,
            user_id=user_id,
            anomaly_type=anomaly_type,
            severity=severity,
            status=status,
            page=page,
            limit=limit,
        )

        total = result.get("total", 0)
        items = [
            AnomalyResponse(
                id=str(item.get("id")) if item.get("id") else None,
                tenant_id=item.get("tenant_id", tenant_id),
                user_id=item.get("user_id"),
                anomaly_type=item.get("anomaly_type", ""),
                severity=item.get("severity", "medium"),
                title=item.get("title", ""),
                description=item.get("description"),
                risk_score=item.get("risk_score", 0),
                metadata=item.get("metadata"),
                status=item.get("status", "open"),
                detected_at=item.get("detected_at", datetime.utcnow()),
                acknowledged_at=item.get("acknowledged_at"),
                resolved_at=item.get("resolved_at"),
            )
            for item in result.get("items", [])
        ]

        return AnomalyListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=(total + limit - 1) // limit
        )
        
    except Exception as e:
        logger.error(f"Error listing anomalies: {e}")
        raise HTTPException(status_code=500, detail="Failed to list anomalies")


@router.post("/{anomaly_id}/acknowledge")
async def acknowledge_anomaly(
    anomaly_id: str,
    request: AcknowledgeAnomalyRequest,
    request_context: RequestContext = Depends(get_current_request_context)
):
    """
    Acknowledge a security anomaly.
    
    Marks anomaly as acknowledged and optionally adds notes.
    """
    tenant_id = str(request_context.tenant_id)
    user_id = request_context.user_id
    
    try:
        store = AnomalyStore()
        success = store.acknowledge(tenant_id=tenant_id, anomaly_id=anomaly_id, actor=user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Anomaly not found")
        logger.info("Anomaly %s acknowledged by user %s in tenant %s", anomaly_id, user_id, tenant_id)
        return {"success": True, "anomaly_id": anomaly_id}
        
    except Exception as e:
        logger.error(f"Error acknowledging anomaly: {e}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge anomaly")


@router.post("/detect")
async def trigger_anomaly_detection(
    user_id: Optional[str] = None,
    time_window_hours: int = 24,
    request_context: RequestContext = Depends(get_current_request_context)
):
    """
    Manually trigger anomaly detection.
    
    Useful for on-demand security scans.
    """
    tenant_id = str(request_context.tenant_id)
    
    logger.info(f"Manual anomaly detection triggered for tenant {tenant_id}")
    
    try:
        detection_service = AnomalyDetectionService()
        new_anomalies = await detection_service.detect_anomalies(
            tenant_id=tenant_id,
            user_id=user_id,
            time_window_hours=time_window_hours
        )

        # Detection does not authorize response effects. Submit selected assertions
        # through the authenticated, audited ITDR proposal intake separately.
        actions_taken = []

        return {
            "success": True,
            "anomalies_detected": len(new_anomalies),
            "anomalies": new_anomalies,
            "actions_taken": actions_taken,
            "response_status": "blocked",
        }
        
    except Exception as e:
        logger.error(f"Error in anomaly detection: {e}")
        raise HTTPException(status_code=500, detail="Failed to detect anomalies")
