"""Internal API endpoints for service-to-service communication."""

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Header
from app.services.alert_service import AlertService
from app.services.search_service import SearchService
from app.services.timeline_service import TimelineService
from app.core.opensearch import OpenSearchClient
from app.models.alert import Alert, AlertCreate, AlertListResponse
from app.models.event import EventSearchResponse
from sg_core.service_security import verify_internal_service_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/siem", tags=["internal"])

from app.core.config import settings

# Service-to-service authentication token
INTERNAL_SERVICE_TOKEN = settings.INTERNAL_SERVICE_TOKEN


def verify_internal_token(
    authorization: Optional[str] = Header(None),
    x_internal_service_token: Optional[str] = Header(None, alias="X-Internal-Service-Token"),
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token"),
) -> bool:
    """
    Verify internal service token for service-to-service calls.
    
    In production, this should use proper mTLS or service mesh authentication.
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


def get_alert_service() -> AlertService:
    """Dependency to get AlertService instance."""
    opensearch_client = OpenSearchClient()
    db = None  # Internal endpoints may not need DB for some operations
    return AlertService(opensearch_client, db)


def get_search_service() -> SearchService:
    """Dependency to get SearchService instance."""
    opensearch_client = OpenSearchClient()
    return SearchService(opensearch_client)


def get_timeline_service() -> TimelineService:
    """Dependency to get TimelineService instance."""
    opensearch_client = OpenSearchClient()
    return TimelineService(opensearch_client)


@router.post("/alerts/create", response_model=Alert)
def create_alert_internal(
    alert_data: AlertCreate,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    _verified: bool = Depends(verify_internal_token),
    alert_service: AlertService = Depends(get_alert_service)
):
    """
    Internal endpoint for SOC Agent to create alerts.
    
    This bypasses normal JWT authentication and uses service-to-service auth.
    The tenant_id must be provided in the X-Tenant-ID header.
    """
    from uuid import UUID
    
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant_id format"
        )
    
    return alert_service.create_alert(tenant_uuid, alert_data)


@router.get("/alerts/{alert_id}", response_model=Alert)
def get_alert_internal(
    alert_id: str,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    _verified: bool = Depends(verify_internal_token),
    alert_service: AlertService = Depends(get_alert_service)
):
    """Internal endpoint to get alert by ID."""
    from uuid import UUID
    
    try:
        tenant_uuid = UUID(tenant_id)
        alert_uuid = UUID(alert_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID format"
        )
    
    alert = alert_service.get_alert(tenant_uuid, alert_uuid)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found"
        )
    
    return alert


@router.post("/alerts/{alert_id}/events")
def add_events_to_alert_internal(
    alert_id: str,
    event_ids: List[str],
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    _verified: bool = Depends(verify_internal_token),
    alert_service: AlertService = Depends(get_alert_service)
):
    """Internal endpoint for SOC Agent to enrich alerts with events."""
    from uuid import UUID
    
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant_id format"
        )
    
    result = alert_service.add_events_to_alert(tenant_uuid, alert_id, event_ids)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found"
        )
    
    return result


@router.get("/search/events")
def search_events_internal(
    query: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    _verified: bool = Depends(verify_internal_token),
    search_service: SearchService = Depends(get_search_service)
):
    """
    Internal endpoint for SOC Agent to search events.
    
    Simplified search interface for service-to-service calls.
    """
    from uuid import UUID
    
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant_id format"
        )
    
    response = search_service.simple_search(
        tenant_id=tenant_uuid,
        query=query,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=0
    )
    
    return response


@router.get("/timeline/entity")
def get_entity_timeline_internal(
    entity_type: str,
    entity_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 1000,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    _verified: bool = Depends(verify_internal_token),
    timeline_service: TimelineService = Depends(get_timeline_service)
):
    """
    Internal endpoint for SOC Agent to get entity timelines.
    
    Used for investigation workflows.
    """
    from uuid import UUID
    from app.models.event import EntityTimelineRequest
    
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant_id format"
        )
    
    request = EntityTimelineRequest(
        entity_type=entity_type,
        entity_id=entity_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit
    )
    
    return timeline_service.get_entity_timeline(tenant_uuid, request)
