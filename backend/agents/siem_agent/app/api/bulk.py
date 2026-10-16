"""Bulk operations API endpoints."""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from app.services.performance_service import PerformanceService
from app.core.opensearch import OpenSearchClient
from app.core.security import get_current_tenant

router = APIRouter(prefix="/siem/alerts/bulk", tags=["bulk"])


def get_performance_service() -> PerformanceService:
    """Dependency to get PerformanceService instance."""
    opensearch_client = OpenSearchClient()
    return PerformanceService(opensearch_client)


@router.post("/update")
def bulk_update_alerts(
    updates: List[Dict[str, Any]],
    tenant_id: str = Depends(get_current_tenant),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """
    Bulk update multiple alerts.
    
    Request body format:
    [
        {
            "alert_id": "alert-uuid-1",
            "updates": {
                "status": "acknowledged",
                "assigned_to": "user-id"
            }
        },
        {
            "alert_id": "alert-uuid-2",
            "updates": {
                "status": "resolved"
            }
        }
    ]
    
    Returns counts of successful and failed updates.
    """
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No updates provided"
        )
    
    # Validate format
    for update_item in updates:
        if "alert_id" not in update_item or "updates" not in update_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each update must have 'alert_id' and 'updates' fields"
            )
    
    result = performance_service.bulk_update_alerts(
        tenant_id=tenant_id,
        updates=updates
    )
    
    return result

