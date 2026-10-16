"""Detection event API endpoints."""

import logging
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Header, HTTPException, status, Query

from app.models.detection_event import (
    DetectionEventCreate,
    DetectionEventResponse,
    DetectionEvent
)
from app.services.detection_manager import DetectionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/detection", tags=["detection"])


async def get_tenant_context(
    x_tenant_id: str = Header(..., description="Tenant UUID"),
    x_realm: str = Header(..., description="Keycloak realm")
) -> tuple[str, str]:
    """
    Extract and validate tenant context from headers.
    
    Returns:
        Tuple of (tenant_id, realm)
    """
    if not x_tenant_id or not x_realm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing tenant context headers (X-Tenant-ID, X-Realm)"
        )
    return x_tenant_id, x_realm


@router.post("/events", response_model=DetectionEventResponse, status_code=status.HTTP_201_CREATED)
async def ingest_detection_event(
    event: DetectionEventCreate,
    tenant_context: tuple[str, str] = Depends(get_tenant_context)
):
    """
    Ingest a detection event from OpenSearch monitor or external source.
    
    This endpoint receives detection events, validates tenant context,
    and indexes them into the appropriate OpenSearch index.
    
    Headers:
        X-Tenant-ID: Tenant UUID
        X-Realm: Keycloak realm
    
    Body:
        DetectionEventCreate: Detection event data
    
    Returns:
        DetectionEventResponse: Indexing result with event ID
    """
    tenant_id, realm = tenant_context
    
    try:
        manager = DetectionManager()
        result = await manager.ingest_detection_event(event, tenant_id, realm)
        
        logger.info(
            f"Ingested detection event {result.event_id} "
            f"for tenant {tenant_id}, alert_type={event.sg.alert_type}"
        )
        
        return result
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error ingesting detection event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest detection event: {str(e)}"
        )


@router.get("/events/{event_id}", response_model=DetectionEvent)
async def get_detection_event(
    event_id: str,
    date: Optional[str] = Query(None, description="Event date (YYYY-MM-DD) to narrow search"),
    tenant_context: tuple[str, str] = Depends(get_tenant_context)
):
    """
    Retrieve a detection event by ID.
    
    Headers:
        X-Tenant-ID: Tenant UUID
        X-Realm: Keycloak realm
    
    Args:
        event_id: Detection event ID
        date: Optional event date to narrow search
    
    Returns:
        DetectionEvent: The detection event
    """
    tenant_id, _ = tenant_context
    
    try:
        event_date = None
        if date:
            event_date = datetime.strptime(date, "%Y-%m-%d")
        
        manager = DetectionManager()
        event = await manager.get_detection_event(event_id, tenant_id, event_date)
        
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Detection event {event_id} not found"
            )
        
        return event
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving detection event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve detection event: {str(e)}"
        )


@router.get("/events", response_model=dict)
async def search_detection_events(
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    alert_types: Optional[str] = Query(None, description="Comma-separated alert types"),
    severities: Optional[str] = Query(None, description="Comma-separated severities"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    tenant_context: tuple[str, str] = Depends(get_tenant_context)
):
    """
    Search detection events for the tenant.
    
    Headers:
        X-Tenant-ID: Tenant UUID
        X-Realm: Keycloak realm
    
    Query params:
        start_time: Start time (ISO format)
        end_time: End time (ISO format)
        alert_types: Comma-separated alert types
        severities: Comma-separated severities (critical, high, medium, low)
        limit: Max results (1-1000)
        offset: Result offset
    
    Returns:
        Dict with events, total, limit, offset
    """
    tenant_id, _ = tenant_context
    
    try:
        # Parse time range
        start_dt = None
        end_dt = None
        if start_time:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        if end_time:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        # Default to last 24 hours if no time range specified
        if not start_dt and not end_dt:
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(hours=24)
        
        # Parse filters
        alert_type_list = None
        if alert_types:
            alert_type_list = [t.strip() for t in alert_types.split(',')]
        
        severity_list = None
        if severities:
            severity_list = [s.strip() for s in severities.split(',')]
        
        manager = DetectionManager()
        result = await manager.search_detection_events(
            tenant_id=tenant_id,
            start_time=start_dt,
            end_time=end_dt,
            alert_types=alert_type_list,
            severities=severity_list,
            limit=limit,
            offset=offset
        )
        
        # Convert events to dict for JSON serialization
        result["events"] = [
            event.model_dump(by_alias=True, exclude_none=True)
            for event in result["events"]
        ]
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameter: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error searching detection events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search detection events: {str(e)}"
        )


@router.get("/stats", response_model=dict)
async def get_detection_stats(
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    tenant_context: tuple[str, str] = Depends(get_tenant_context)
):
    """
    Get detection event statistics for the tenant.
    
    Headers:
        X-Tenant-ID: Tenant UUID
        X-Realm: Keycloak realm
    
    Query params:
        start_time: Start time (ISO format)
        end_time: End time (ISO format)
    
    Returns:
        Dict with statistics (counts by type, severity, timeline)
    """
    tenant_id, _ = tenant_context
    
    try:
        # Parse time range
        start_dt = None
        end_dt = None
        if start_time:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        if end_time:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        # Default to last 7 days if no time range specified
        if not start_dt and not end_dt:
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(days=7)
        
        manager = DetectionManager()
        stats = await manager.get_detection_stats(
            tenant_id=tenant_id,
            start_time=start_dt,
            end_time=end_dt
        )
        
        return stats
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameter: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting detection stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get detection stats: {str(e)}"
        )
