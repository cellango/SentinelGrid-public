"""Entity timeline API endpoints."""

from fastapi import APIRouter, Depends, Query
from app.models.event import EntityTimelineRequest, EntityTimelineResponse
from app.services.timeline_service import TimelineService
from app.core.opensearch import OpenSearchClient
from app.core.security import get_current_tenant

router = APIRouter(prefix="/siem", tags=["timeline"])


def get_timeline_service() -> TimelineService:
    """Dependency to get TimelineService instance."""
    opensearch_client = OpenSearchClient()
    return TimelineService(opensearch_client)


@router.get("/entity-timeline", response_model=EntityTimelineResponse)
def get_entity_timeline(
    entity_type: str = Query(..., regex="^(user|host|ip|domain|file_hash)$", description="Type of entity"),
    entity_id: str = Query(..., description="Entity identifier"),
    start_time: str = Query(None, description="Start of time range (ISO 8601)"),
    end_time: str = Query(None, description="End of time range (ISO 8601)"),
    event_types: str = Query(None, description="Comma-separated event types to include"),
    limit: int = Query(1000, ge=1, le=10000, description="Max events to return"),
    tenant_id: str = Depends(get_current_tenant),
    timeline_service: TimelineService = Depends(get_timeline_service)
):
    """
    Get timeline of events for a specific entity.
    
    Supported entity types:
    - user: User ID or email
    - host: Hostname
    - ip: IP address
    - domain: Domain name
    - file_hash: File hash (MD5, SHA1, or SHA256)
    
    Returns events in chronological order with summary statistics.
    """
    from datetime import datetime
    
    # Parse optional parameters
    start_time_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00")) if start_time else None
    end_time_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00")) if end_time else None
    event_types_list = event_types.split(",") if event_types else None
    
    request = EntityTimelineRequest(
        entity_type=entity_type,
        entity_id=entity_id,
        start_time=start_time_dt,
        end_time=end_time_dt,
        event_types=event_types_list,
        limit=limit
    )
    
    return timeline_service.get_entity_timeline(
        tenant_id=tenant_id,
        request=request
    )

