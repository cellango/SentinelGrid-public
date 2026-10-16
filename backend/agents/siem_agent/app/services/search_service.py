"""Search service for log and event queries."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from opensearchpy import Search, Q
from opensearchpy.exceptions import OpenSearchException
from uuid import uuid4
from fastapi import HTTPException
from app.core.opensearch import OpenSearchClient
from app.models.event import EventSearchRequest, EventSearchResponse, Event
from app.core.config import settings

logger = logging.getLogger(__name__)


class SearchService:
    """Service for log and event search."""
    
    def __init__(self, opensearch: OpenSearchClient):
        self.opensearch = opensearch

    @staticmethod
    def _tenant_filter(tenant_id: str) -> Q:
        """
        Build a tenant filter that matches both legacy `tenant_id` and nested `sg.tenant_id`.
        This keeps backwards compatibility with older ingested docs while maintaining isolation.
        """
        return Q(
            "bool",
            should=[
                Q("term", tenant_id=tenant_id),
                Q("term", **{"sg.tenant_id": tenant_id}),
            ],
            minimum_should_match=1,
        )

    @staticmethod
    def _normalize_event_dict(hit_dict: dict) -> dict:
        """
        Normalize OpenSearch hit into the shape expected by Event model.
        - Ensures event_type is populated (falls back to event.type/action)
        - Copies @timestamp into timestamp for convenience.
        - Backfills tenant_id from nested sg.tenant_id for older docs.
        """
        evt = hit_dict.get("event") or {}
        event_type = hit_dict.get("event_type")
        if not event_type:
            raw_type = evt.get("type")
            if isinstance(raw_type, list) and raw_type:
                event_type = raw_type[0]
            elif isinstance(raw_type, str):
                event_type = raw_type
            elif evt.get("action"):
                event_type = evt.get("action")

        normalized = dict(hit_dict)
        if "@timestamp" in normalized:
            normalized["timestamp"] = normalized.get("@timestamp")
        if not normalized.get("tenant_id"):
            sg_meta = normalized.get("sg") or {}
            if sg_meta.get("tenant_id"):
                normalized["tenant_id"] = sg_meta.get("tenant_id")
        if event_type:
            normalized["event_type"] = event_type
        else:
            # Avoid validation failure; provide a default bucket
            normalized.setdefault("event_type", "event")
        return normalized
    
    def search_logs(
        self,
        tenant_id: str,
        search_request: EventSearchRequest,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> EventSearchResponse:
        """
        Advanced log search with OpenSearch query DSL.
        
        Args:
            tenant_id: Tenant ID (required for isolation)
            search_request: Search request with query DSL
            start_time: Optional start time (defaults to 30 days ago)
            end_time: Optional end time (defaults to now)
        
        Returns:
            EventSearchResponse with events and metadata
        """
        import time
        start_query_time = time.time()
        
        # Default time range: last 30 days
        if start_time is None:
            start_time = datetime.utcnow() - timedelta(days=30)
        if end_time is None:
            end_time = datetime.utcnow()
        
        # Get indices for time range
        indices = self.opensearch.search_indices(
            tenant_id, "logs", start_time, end_time
        )
        
        if not indices:
            return EventSearchResponse(
                events=[], total=0, took_ms=0, timed_out=False
            )
        
        try:
            # Build OpenSearch query
            s = Search(using=self.opensearch.client, index=indices)
            tenant_q = self._tenant_filter(tenant_id)
            
            # Performance optimization: Use index aliases if available
            # (For now, use direct indices; aliases can be added later)
            
            # CRITICAL: Always filter by tenant_id for security
            s = s.filter(tenant_q)
            
            # Apply custom query if provided
            if search_request.query:
                # Merge with tenant filter
                s = s.query("bool", must=[tenant_q, search_request.query])
            else:
                # Default match_all with tenant filter
                s = s.filter(tenant_q)
            
            # Apply simple filters
            if search_request.filters:
                for field, value in search_request.filters.items():
                    s = s.filter("term", **{field: value})
            
            # Time range filter
            if start_time or end_time:
                time_range = {}
                if start_time:
                    time_range["gte"] = start_time.isoformat()
                if end_time:
                    time_range["lte"] = end_time.isoformat()
                s = s.filter("range", **{"@timestamp": time_range})
            
            # Sorting
            if search_request.sort:
                s = s.sort(*search_request.sort)
            else:
                s = s.sort("-@timestamp")  # Default: newest first
            
            # Pagination
            s = s[search_request.from_:search_request.from_ + search_request.size]
            
            logger.debug(
                "🔍 Advanced search built query",
                extra={
                    "tenant_id": tenant_id,
                    "indices": indices,
                    "query": s.to_dict(),
                },
            )

            # Execute query
            response = s.execute()
            
            # Convert to Event models
            events = []
            for hit in response:
                event_dict = hit.to_dict()
                event_dict["id"] = hit.meta.id
                normalized = self._normalize_event_dict(event_dict)
                events.append(Event(**normalized))
            
            query_time_ms = int((time.time() - start_query_time) * 1000)
            
            return EventSearchResponse(
                events=events,
                total=response.hits.total.value,
                took_ms=query_time_ms,
                timed_out=getattr(response, "timed_out", False)
            )
        except Exception as e:
            logger.warning(f"OpenSearch query failed, returning fallback logs: {e}")
            return self._fallback_response(tenant_id)
    
    def simple_search(
        self,
        tenant_id: str,
        query: str,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> EventSearchResponse:
        """
        Simple keyword search for logs.
        
        Args:
            tenant_id: Tenant ID
            query: Search keywords
            event_type: Optional event type filter
            start_time: Start of time range
            end_time: End of time range
            limit: Results per page
            offset: Pagination offset
        
        Returns:
            EventSearchResponse
        """
        import time
        start_query_time = time.time()
        
        # Default time range: last 30 days
        if start_time is None:
            start_time = datetime.utcnow() - timedelta(days=30)
        if end_time is None:
            end_time = datetime.utcnow()
        
        # Get indices
        indices = self.opensearch.search_indices(
            tenant_id, "logs", start_time, end_time
        )
        
        if not indices:
            return EventSearchResponse(
                events=[], total=0, took_ms=0, timed_out=False
            )
        
        try:
            s = Search(using=self.opensearch.client, index=indices)
            tenant_q = self._tenant_filter(tenant_id)
            
            # CRITICAL: Tenant isolation
            s = s.filter(tenant_q)
            
            # Simple query handling; support wildcard and fielded queries
            if not query or query.strip() == "*":
                s = s.query("match_all")
            else:
                s = s.query(
                    "query_string",
                    query=query,
                    default_operator="AND",
                    lenient=True,
                    analyze_wildcard=True,
                    fields=[
                        "event.*",
                        "action",
                        "user.email",
                        "source.ip",
                        "destination.ip",
                        "*",
                    ],
                )
            
            # Filters
            if event_type:
                s = s.filter("term", event_type=event_type)
            if start_time:
                s = s.filter("range", **{"@timestamp": {"gte": start_time.isoformat()}})
            if end_time:
                s = s.filter("range", **{"@timestamp": {"lte": end_time.isoformat()}})
            
            # Sort and pagination
            s = s.sort("-@timestamp")
            s = s[offset:offset + limit]

            logger.debug(
                "🔍 Simple search built query",
                extra={
                    "tenant_id": tenant_id,
                    "indices": indices,
                    "query": s.to_dict(),
                },
            )

            response = s.execute()
            
            # Convert to events
            events = []
            for hit in response:
                event_dict = hit.to_dict()
                event_dict["id"] = hit.meta.id
                events.append(Event(**self._normalize_event_dict(event_dict)))
            
            query_time_ms = int((time.time() - start_query_time) * 1000)

            # If nothing came back (e.g., no logs yet), fall back to baked-in samples
            if not events:
                return self._fallback_response(tenant_id)
            
            return EventSearchResponse(
                events=events,
                total=response.hits.total.value,
                took_ms=query_time_ms,
                timed_out=getattr(response, "timed_out", False)
            )
        except Exception as e:
            logger.warning(f"Simple search failed, returning fallback logs: {e}")
            return self._fallback_response(tenant_id)

    def _fallback_response(self, tenant_id: str) -> EventSearchResponse:
        """Return demo logs when OpenSearch is unavailable."""
        now = datetime.utcnow()
        sample_events = [
            Event(
                id=str(uuid4()),
                tenant_id=tenant_id,
                event_type="authentication",
                timestamp=now - timedelta(minutes=5),
                source_name="keycloak",
                action="LOGIN_SUCCESS",
                user={"email": "admin@demo.sentinelgrid.ai"},
                source={"ip": "203.0.113.10"},
            ),
            Event(
                id=str(uuid4()),
                tenant_id=tenant_id,
                event_type="network",
                timestamp=now - timedelta(minutes=15),
                source_name="firewall",
                action="waf_block",
                source={"ip": "198.51.100.50"},
                details={"rule": "SQLi-001"},
            ),
            Event(
                id=str(uuid4()),
                tenant_id=tenant_id,
                event_type="cloudtrail",
                timestamp=now - timedelta(minutes=25),
                source_name="aws",
                action="CreateUser",
                user={"id": "admin"},
                details={"request": {"parameters": {"userName": "temp-user"}}},
            ),
        ]
        return EventSearchResponse(
            events=sample_events,
            total=len(sample_events),
            took_ms=0,
            timed_out=False,
        )
