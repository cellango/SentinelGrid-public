"""Detection event manager - handles ingestion and processing of detection events."""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from app.core.opensearch import OpenSearchClient
from app.core.ingest_client import IngestClient
from app.models.detection_event import DetectionEvent, DetectionEventCreate, DetectionEventResponse
from opensearchpy.exceptions import OpenSearchException

logger = logging.getLogger(__name__)


class DetectionManager:
    """Manages detection events - ingestion, indexing, and retrieval."""
    
    def __init__(
        self,
        opensearch_client: Optional[OpenSearchClient] = None,
        ingest_client: Optional[IngestClient] = None,
        ingest_agent_id: str = "siem-agent",
    ):
        """
        Initialize detection manager.
        
        Args:
            opensearch_client: Optional OpenSearch client instance
            ingest_client: Optional ingest client (SentinelGuard /ingest)
            ingest_agent_id: Agent identifier used when calling ingest
        """
        self.opensearch = opensearch_client or OpenSearchClient()
        self.ingest = ingest_client or IngestClient()
        self.ingest_agent_id = ingest_agent_id
    
    def get_detection_index_name(self, tenant_id: str, date: Optional[datetime] = None) -> str:
        """
        Get detection index name for tenant.
        
        Args:
            tenant_id: Tenant UUID
            date: Optional date (defaults to today)
        
        Returns:
            Index name: sg-{tenant_id}-detection-YYYY.MM.DD
        """
        return self.opensearch.get_index_name(tenant_id, "detection", date)
    
    async def ingest_detection_event(
        self,
        event: DetectionEventCreate,
        tenant_id: str,
        realm: str
    ) -> DetectionEventResponse:
        """
        Ingest a detection event via the unified SentinelGuard ingest service.
        
        Args:
            event: Detection event data
            tenant_id: Tenant UUID
            realm: Keycloak realm
        
        Returns:
            DetectionEventResponse with indexing status
        """
        try:
            # Validate tenant context matches
            if event.sg.tenant_id != tenant_id:
                raise ValueError(f"Tenant ID mismatch: event={event.sg.tenant_id}, header={tenant_id}")
            
            if event.sg.realm != realm:
                raise ValueError(f"Realm mismatch: event={event.sg.realm}, header={realm}")
            
            # Create full detection event
            detection_event = DetectionEvent(
                timestamp=datetime.utcnow(),
                sg=event.sg,
                rule=event.rule,
                user=event.user,
                source=event.source,
                host=event.host,
                device=event.device,
                malware=event.malware,
                email=event.email,
                cloud=event.cloud,
                resource=event.resource,
                iam=event.iam,
                network=event.network,
                auth=event.auth,
                spray=event.spray,
                campaign=event.campaign,
                description=event.description,
                metadata=event.metadata,
                raw_alert=event.raw_alert,
                actor=event.actor,
                target_user=event.target_user,
                report_source=event.report_source
            )
            
            # Convert to dict for ingest
            event_dict = detection_event.model_dump(by_alias=True, exclude_none=True)
            
            ingest_resp = self.ingest.send_batch(
                tenant_id=tenant_id,
                agent_id=self.ingest_agent_id,
                events=[event_dict],
            )
            
            logger.info(
                f"Ingested detection event {detection_event.event_id} "
                f"for tenant {tenant_id} via SentinelGuard ingest"
            )
            
            return DetectionEventResponse(
                event_id=detection_event.event_id,
                indexed=True,
                index_name="sentinelguard-events",
                message="Detection event routed via ingest",
                metadata={"ingest_response": ingest_resp},
            )
            
        except ValueError as e:
            logger.error(f"Validation error ingesting detection event: {e}")
            raise
        except OpenSearchException as e:
            logger.error(f"OpenSearch error ingesting detection event: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error ingesting detection event: {e}")
            raise
    
    async def get_detection_event(
        self,
        event_id: str,
        tenant_id: str,
        date: Optional[datetime] = None
    ) -> Optional[DetectionEvent]:
        """
        Retrieve a detection event by ID.
        
        Args:
            event_id: Detection event ID
            tenant_id: Tenant UUID
            date: Optional date to narrow down index search
        
        Returns:
            DetectionEvent if found, None otherwise
        """
        try:
            result = self.opensearch.client.search(
                index="sentinelguard-events",
                body={
                    "query": {
                        "bool": {
                            "filter": [
                                {"term": {"sg.tenant_id": tenant_id}},
                                {"term": {"event_id": event_id}}
                            ]
                        }
                    },
                    "size": 1
                }
            )
            
            hits = result.get("hits", {}).get("hits", [])
            if hits:
                event_data = hits[0].get("_source", {})
                return DetectionEvent(**event_data)
            return None
            
        except OpenSearchException as e:
            if e.status_code == 404:
                logger.warning(f"Detection event {event_id} not found for tenant {tenant_id}")
                return None
            logger.error(f"Error retrieving detection event: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving detection event: {e}")
            raise
    
    async def search_detection_events(
        self,
        tenant_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        alert_types: Optional[list[str]] = None,
        severities: Optional[list[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search detection events for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            start_time: Start of time range
            end_time: End of time range
            alert_types: Filter by alert types
            severities: Filter by severities
            limit: Maximum results to return
            offset: Result offset for pagination
        
        Returns:
            Dict with hits and total count
        """
        try:
            # Build query against unified ingest index
            query = {
                "bool": {
                    "filter": [
                        {"term": {"sg.tenant_id": tenant_id}}
                    ]
                }
            }
            
            # Add time range filter
            if start_time or end_time:
                time_range = {}
                if start_time:
                    time_range["gte"] = start_time.isoformat()
                if end_time:
                    time_range["lte"] = end_time.isoformat()
                query["bool"]["filter"].append({
                    "range": {"@timestamp": time_range}
                })
            
            # Add alert type filter
            if alert_types:
                query["bool"]["filter"].append({
                    "terms": {"sg.alert_type": alert_types}
                })
            
            # Add severity filter
            if severities:
                query["bool"]["filter"].append({
                    "terms": {"sg.severity": severities}
                })
            
            # Execute search
            result = self.opensearch.client.search(
                index="sentinelguard-events",
                body={
                    "query": query,
                    "sort": [{"@timestamp": {"order": "desc"}}],
                    "from": offset,
                    "size": limit
                }
            )
            
            hits = result.get("hits", {})
            events = [
                DetectionEvent(**hit["_source"])
                for hit in hits.get("hits", [])
            ]
            
            return {
                "events": events,
                "total": hits.get("total", {}).get("value", 0),
                "limit": limit,
                "offset": offset
            }
            
        except OpenSearchException as e:
            logger.error(f"Error searching detection events: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error searching detection events: {e}")
            raise
    
    async def get_detection_stats(
        self,
        tenant_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get detection event statistics for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            start_time: Start of time range
            end_time: End of time range
        
        Returns:
            Dict with statistics
        """
        try:
            # Build query with aggregations
            query = {
                "bool": {
                    "filter": [{"term": {"sg.tenant_id": tenant_id}}]
                }
            }
            
            if start_time or end_time:
                time_range = {}
                if start_time:
                    time_range["gte"] = start_time.isoformat()
                if end_time:
                    time_range["lte"] = end_time.isoformat()
                query["bool"]["filter"].append({
                    "range": {"@timestamp": time_range}
                })
            
            result = self.opensearch.client.search(
                index="sentinelguard-events",
                body={
                    "query": query,
                    "size": 0,
                    "aggs": {
                        "by_alert_type": {
                            "terms": {"field": "sg.alert_type", "size": 20}
                        },
                        "by_severity": {
                            "terms": {"field": "sg.severity", "size": 10}
                        },
                        "by_category": {
                            "terms": {"field": "sg.category", "size": 20}
                        },
                        "timeline": {
                            "date_histogram": {
                                "field": "@timestamp",
                                "fixed_interval": "1h"
                            }
                        }
                    }
                }
            )
            
            aggs = result.get("aggregations", {})
            
            return {
                "total_events": result.get("hits", {}).get("total", {}).get("value", 0),
                "by_alert_type": {
                    bucket["key"]: bucket["doc_count"]
                    for bucket in aggs.get("by_alert_type", {}).get("buckets", [])
                },
                "by_severity": {
                    bucket["key"]: bucket["doc_count"]
                    for bucket in aggs.get("by_severity", {}).get("buckets", [])
                },
                "by_category": {
                    bucket["key"]: bucket["doc_count"]
                    for bucket in aggs.get("by_category", {}).get("buckets", [])
                },
                "timeline": [
                    {
                        "timestamp": bucket["key_as_string"],
                        "count": bucket["doc_count"]
                    }
                    for bucket in aggs.get("timeline", {}).get("buckets", [])
                ]
            }
            
        except OpenSearchException as e:
            logger.error(f"Error getting detection stats: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting detection stats: {e}")
            raise
