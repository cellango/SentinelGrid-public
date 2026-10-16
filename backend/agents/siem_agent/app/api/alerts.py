"""Alert API endpoints."""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.models.alert import Alert, AlertListResponse, AlertUpdate
from app.services.alert_service import AlertService
from app.core.opensearch import OpenSearchClient
from app.core.security import get_current_tenant

router = APIRouter(prefix="/siem/alerts", tags=["alerts"])


def get_alert_service() -> AlertService:
    """Dependency to get AlertService instance."""
    opensearch_client = OpenSearchClient()
    return AlertService(opensearch_client)


@router.get("", response_model=AlertListResponse)
def list_alerts(
    severity: Optional[str] = Query(None, regex="^(low|medium|high|critical)$"),
    status: Optional[str] = Query(None, regex="^(open|acknowledged|resolved|false_positive)$"),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    sort: str = Query("timestamp:desc", regex="^\\w+:(asc|desc)$"),
    tenant_id: str = Depends(get_current_tenant),
    alert_service: AlertService = Depends(get_alert_service)
):
    """
    List alerts for the current tenant with filtering and pagination.
    
    Query Parameters:
    - severity: Filter by severity (low, medium, high, critical)
    - status: Filter by status (open, acknowledged, resolved, false_positive)
    - start_time: Start of time range (ISO 8601)
    - end_time: End of time range (ISO 8601)
    - limit: Results per page (1-1000, default: 50)
    - offset: Pagination offset (default: 0)
    - sort: Sort field and direction (default: timestamp:desc)
    """
    return alert_service.list_alerts(
        tenant_id=tenant_id,
        severity=severity,
        status=status,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
        sort=sort
    )


@router.get("/{alert_id}", response_model=Alert)
def get_alert(
    alert_id: str,
    tenant_id: str = Depends(get_current_tenant),
    alert_service: AlertService = Depends(get_alert_service)
):
    """
    Get alert by ID.
    
    Returns 404 if alert not found or doesn't belong to tenant.
    """
    alert = alert_service.get_alert(tenant_id, alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found"
        )
    return alert


@router.put("/{alert_id}", response_model=Alert)
def update_alert(
    alert_id: str,
    alert_update: AlertUpdate,
    tenant_id: str = Depends(get_current_tenant),
    alert_service: AlertService = Depends(get_alert_service)
):
    """
    Update alert status, assignment, or comments.
    
    Only fields provided in the request body will be updated.
    """
    alert = alert_service.update_alert(
        tenant_id=tenant_id,
        alert_id=alert_id,
        status=alert_update.status,
        assigned_to=alert_update.assigned_to,
        comments=alert_update.comments
    )
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found"
        )
    
    return alert


@router.post("/{alert_id}/events")
def add_events_to_alert(
    alert_id: str,
    event_ids: List[str],
    tenant_id: str = Depends(get_current_tenant),
    alert_service: AlertService = Depends(get_alert_service)
):
    """
    Add events to an existing alert (alert enrichment).
    
    This links related events to an alert for context.
    """
    result = alert_service.add_events_to_alert(
        tenant_id=tenant_id,
        alert_id=alert_id,
        event_ids=event_ids
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found"
        )
    
    return result

