"""Log search API endpoints."""

from datetime import datetime
from fastapi import APIRouter, Depends, Query
from app.models.event import (
    EventSearchRequest,
    EventSearchResponse,
    SimpleSearchRequest
)
from app.services.search_service import SearchService
from app.core.opensearch import OpenSearchClient
from app.core.security import get_current_tenant

router = APIRouter(prefix="/siem/logs", tags=["logs"])


def get_search_service() -> SearchService:
    """Dependency to get SearchService instance."""
    opensearch_client = OpenSearchClient()
    return SearchService(opensearch_client)


@router.post("/search", response_model=EventSearchResponse)
def search_logs(
    search_request: EventSearchRequest,
    start_time: datetime = Query(None),
    end_time: datetime = Query(None),
    tenant_id: str = Depends(get_current_tenant),
    search_service: SearchService = Depends(get_search_service)
):
    """
    Advanced log search with OpenSearch query DSL.
    
    Allows complex queries using OpenSearch query syntax.
    All queries are automatically scoped to the current tenant.
    """
    return search_service.search_logs(
        tenant_id=tenant_id,
        search_request=search_request,
        start_time=start_time,
        end_time=end_time
    )


@router.get("/search/simple", response_model=EventSearchResponse)
def simple_search(
    q: str = Query(..., description="Search query (keywords)"),
    event_type: str = Query(None, description="Filter by event type"),
    start_time: datetime = Query(None, description="Start of time range (ISO 8601)"),
    end_time: datetime = Query(None, description="End of time range (ISO 8601)"),
    limit: int = Query(100, ge=1, le=1000, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    tenant_id: str = Depends(get_current_tenant),
    search_service: SearchService = Depends(get_search_service)
):
    """
    Simple keyword search for logs.
    
    Searches across common fields (title, description, action, user.email, source.ip).
    User-friendly alternative to advanced query DSL.
    """
    return search_service.simple_search(
        tenant_id=tenant_id,
        query=q,
        event_type=event_type,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset
    )

