"""Timeline service for entity event timelines."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from opensearchpy import Search
from opensearchpy.exceptions import OpenSearchException
from fastapi import HTTPException
from app.core.opensearch import OpenSearchClient
from app.models.event import EntityTimelineRequest, EntityTimelineResponse, Event
from app.core.config import settings

logger = logging.getLogger(__name__)


class TimelineService:
    """Service for entity timeline queries."""
    
    def __init__(self, opensearch: OpenSearchClient):
        self.opensearch = opensearch
    
    def get_entity_timeline(
        self,
        tenant_id: str,
        request: EntityTimelineRequest
    ) -> EntityTimelineResponse:
        """
        Get timeline of events for a specific entity.
        
        Args:
            tenant_id: Tenant ID
            request: Timeline request with entity info
        
        Returns:
            EntityTimelineResponse with events and summary
        """
        # Default time range: last 24 hours
        start_time = request.start_time or (datetime.utcnow() - timedelta(days=1))
        end_time = request.end_time or datetime.utcnow()
        
        # Get indices
        indices = self.opensearch.search_indices(
            tenant_id, "logs", start_time, end_time
        )
        
        if not indices:
            return EntityTimelineResponse(
                entity={"type": request.entity_type, "id": request.entity_id},
                time_range={"start": start_time, "end": end_time},
                events=[],
                summary={
                    "total_events": 0,
                    "unique_ips": 0,
                    "unique_locations": 0,
                    "first_seen": None,
                    "last_seen": None
                }
            )
        
        try:
            s = Search(using=self.opensearch.client, index=indices)
            
            # CRITICAL: Tenant isolation
            s = s.filter("term", tenant_id=tenant_id)
            
            # Build entity filter based on entity type
            entity_filter = self._build_entity_filter(request.entity_type, request.entity_id)
            s = s.filter(entity_filter)
            
            # Event type filter
            if request.event_types:
                s = s.filter("terms", event_type=request.event_types)
            
            # Time range
            s = s.filter("range", timestamp={
                "gte": start_time.isoformat(),
                "lte": end_time.isoformat()
            })
            
            # Sort by timestamp
            s = s.sort("@timestamp")
            
            # Limit results
            s = s[0:request.limit]
            
            # Execute query
            response = s.execute()
            
            # Convert to events
            events = []
            unique_ips = set()
            unique_locations = set()
            
            for hit in response:
                event_dict = hit.to_dict()
                event_dict["id"] = hit.meta.id
                if "@timestamp" in event_dict:
                    event_dict["timestamp"] = event_dict["@timestamp"]
                
                event = Event(**event_dict)
                events.append(event)
                
                # Extract IPs and locations for summary
                if event.source and isinstance(event.source, dict):
                    if "ip" in event.source:
                        unique_ips.add(event.source["ip"])
                    if "geo" in event.source and isinstance(event.source["geo"], dict):
                        location = f"{event.source['geo'].get('country', '')}-{event.source['geo'].get('city', '')}"
                        if location:
                            unique_locations.add(location)
            
            # Calculate summary
            first_seen = events[0].timestamp if events else None
            last_seen = events[-1].timestamp if events else None
            
            summary = {
                "total_events": len(events),
                "unique_ips": len(unique_ips),
                "unique_locations": len(unique_locations),
                "first_seen": first_seen.isoformat() if first_seen else None,
                "last_seen": last_seen.isoformat() if last_seen else None
            }
            
            return EntityTimelineResponse(
                entity={
                    "type": request.entity_type,
                    "id": request.entity_id,
                    "identifier": request.entity_id
                },
                time_range={
                    "start": start_time,
                    "end": end_time
                },
                events=events,
                summary=summary
            )
            
        except OpenSearchException as e:
            logger.error(f"Timeline query failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get entity timeline: {str(e)}"
            )
    
    def _build_entity_filter(self, entity_type: str, entity_id: str) -> Dict[str, Any]:
        """
        Build OpenSearch filter for entity type.
        
        Args:
            entity_type: user, host, ip, domain, file_hash
            entity_id: Entity identifier
        
        Returns:
            OpenSearch filter dictionary
        """
        if entity_type == "user":
            return {
                "bool": {
                    "should": [
                        {"term": {"user.id": entity_id}},
                        {"term": {"user.email": entity_id}},
                    ],
                    "minimum_should_match": 1
                }
            }
        elif entity_type == "host":
            return {"term": {"host.hostname": entity_id}}
        elif entity_type == "ip":
            return {
                "bool": {
                    "should": [
                        {"term": {"source.ip": entity_id}},
                        {"term": {"destination.ip": entity_id}},
                    ],
                    "minimum_should_match": 1
                }
            }
        elif entity_type == "domain":
            return {
                "bool": {
                    "should": [
                        {"term": {"source.domain": entity_id}},
                        {"term": {"destination.domain": entity_id}},
                    ],
                    "minimum_should_match": 1
                }
            }
        elif entity_type == "file_hash":
            return {
                "bool": {
                    "should": [
                        {"term": {"file.hash.md5": entity_id}},
                        {"term": {"file.hash.sha1": entity_id}},
                        {"term": {"file.hash.sha256": entity_id}},
                    ],
                    "minimum_should_match": 1
                }
            }
        else:
            raise ValueError(f"Unsupported entity type: {entity_type}")

