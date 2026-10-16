"""Statistics API endpoints."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
import logging
from app.core.opensearch import OpenSearchClient
from app.core.security import get_current_tenant
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/siem/stats", tags=["stats"])


def get_cache_service() -> CacheService:
    """Dependency to get CacheService instance."""
    return CacheService()


@router.get("")
def get_stats(
    metric: str = Query(
        None,
        description="Specific metric: alerts_count, events_count, top_users, top_ips, by_severity, by_status"
    ),
    start_time: Optional[datetime] = Query(None, description="Start of time range (ISO 8601)"),
    end_time: Optional[datetime] = Query(None, description="End of time range (ISO 8601)"),
    tenant_id: str = Depends(get_current_tenant),
    cache_service: CacheService = Depends(get_cache_service)
):
    """
    Get statistics and aggregations.
    
    Returns various metrics and counts for the tenant.
    Results are cached for performance.
    """
    from datetime import timedelta
    from opensearchpy import Search
    
    opensearch_client = OpenSearchClient()
    
    # Default time range: last 24 hours
    if start_time is None:
        start_time = datetime.utcnow() - timedelta(days=1)
    if end_time is None:
        end_time = datetime.utcnow()
    
    # Check cache
    cache_key = cache_service.get_stats_cache_key(tenant_id, metric or "all")
    if metric:
        cached = cache_service.get(cache_key)
        if cached:
            return cached
    
    try:
        # Get indices
        alerts_indices = opensearch_client.search_indices(
            tenant_id, "alerts", start_time, end_time
        )
        logs_indices = opensearch_client.search_indices(
            tenant_id, "logs", start_time, end_time
        )
        
        result = {}
        
        # Alerts count
        if not metric or metric == "alerts_count":
            if alerts_indices:
                s = Search(using=opensearch_client.client, index=alerts_indices)
                s = s.filter("term", tenant_id=tenant_id)
                s = s.filter("range", timestamp={
                    "gte": start_time.isoformat(),
                    "lte": end_time.isoformat()
                })
                response = s.execute()
                result["alerts_count"] = response.hits.total.value
            else:
                result["alerts_count"] = 0
        
        # Events count
        if not metric or metric == "events_count":
            if logs_indices:
                s = Search(using=opensearch_client.client, index=logs_indices)
                s = s.filter("term", tenant_id=tenant_id)
                s = s.filter("range", timestamp={
                    "gte": start_time.isoformat(),
                    "lte": end_time.isoformat()
                })
                response = s.execute()
                result["events_count"] = response.hits.total.value
            else:
                result["events_count"] = 0
        
        # Alerts by severity
        if not metric or metric == "by_severity":
            if alerts_indices:
                s = Search(using=opensearch_client.client, index=alerts_indices)
                s = s.filter("term", tenant_id=tenant_id)
                s = s.filter("range", timestamp={
                    "gte": start_time.isoformat(),
                    "lte": end_time.isoformat()
                })
                s.aggs.bucket("by_severity", "terms", field="severity", size=10)
                response = s.execute()
                result["by_severity"] = {
                    bucket.key: bucket.doc_count
                    for bucket in response.aggregations.by_severity.buckets
                }
            else:
                result["by_severity"] = {}
        
        # Alerts by status
        if not metric or metric == "by_status":
            if alerts_indices:
                s = Search(using=opensearch_client.client, index=alerts_indices)
                s = s.filter("term", tenant_id=tenant_id)
                s = s.filter("range", timestamp={
                    "gte": start_time.isoformat(),
                    "lte": end_time.isoformat()
                })
                s.aggs.bucket("by_status", "terms", field="status", size=10)
                response = s.execute()
                result["by_status"] = {
                    bucket.key: bucket.doc_count
                    for bucket in response.aggregations.by_status.buckets
                }
            else:
                result["by_status"] = {}
        
        # Top users (if logs available)
        if not metric or metric == "top_users":
            if logs_indices:
                s = Search(using=opensearch_client.client, index=logs_indices)
                s = s.filter("term", tenant_id=tenant_id)
                s = s.filter("range", timestamp={
                    "gte": start_time.isoformat(),
                    "lte": end_time.isoformat()
                })
                s = s.filter("exists", field="user.email")
                s.aggs.bucket("top_users", "terms", field="user.email", size=10)
                response = s.execute()
                result["top_users"] = [
                    {"user": bucket.key, "event_count": bucket.doc_count}
                    for bucket in response.aggregations.top_users.buckets
                ]
            else:
                result["top_users"] = []
        
        # Top IPs (if logs available)
        if not metric or metric == "top_ips":
            if logs_indices:
                s = Search(using=opensearch_client.client, index=logs_indices)
                s = s.filter("term", tenant_id=tenant_id)
                s = s.filter("range", timestamp={
                    "gte": start_time.isoformat(),
                    "lte": end_time.isoformat()
                })
                s = s.filter("exists", field="source.ip")
                s.aggs.bucket("top_ips", "terms", field="source.ip", size=10)
                response = s.execute()
                result["top_ips"] = [
                    {"ip": bucket.key, "event_count": bucket.doc_count}
                    for bucket in response.aggregations.top_ips.buckets
                ]
            else:
                result["top_ips"] = []
        
        # Cache result (5 minute TTL)
        if metric:
            cache_service.set(cache_key, result, ttl_seconds=300)
        
        return result
        
    except Exception as e:
        logger.error(f"Stats query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )

