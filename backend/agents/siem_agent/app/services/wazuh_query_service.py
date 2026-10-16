"""Service to query Wazuh alerts from OpenSearch."""

import logging
from uuid import UUID
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from opensearchpy import OpenSearch, exceptions as opensearch_exceptions

logger = logging.getLogger(__name__)


class WazuhQueryService:
    """
    Query Wazuh (SentinelGrid Endpoint Protection) alerts from SentinelGrid SIEM (OpenSearch).
    
    All queries are automatically tenant-isolated using tenant-specific index patterns.
    """
    
    def __init__(self, opensearch_client: OpenSearch):
        """
        Initialize Wazuh query service.
        
        Args:
            opensearch_client: OpenSearch client instance
        """
        self.os = opensearch_client
    
    async def get_alerts(
        self,
        tenant_id: UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity_min: Optional[int] = None,
        agent_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get Wazuh alerts for a specific tenant.
        
        Queries tenant-specific index pattern ensuring complete isolation:
        wazuh-alerts-{tenant_id}-*
        
        Args:
            tenant_id: Globally unique tenant ID
            start_time: Start of time range (default: 24 hours ago)
            end_time: End of time range (default: now)
            severity_min: Minimum rule level (0-15, default: 3)
            agent_id: Filter by specific agent ID (optional)
            limit: Maximum results to return
            offset: Offset for pagination
        
        Returns:
            Dictionary with alerts and metadata
        """
        # Default time range: last 24 hours
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(days=1)
        
        # Build query filters
        filters = [
            # Time range
            {"range": {"@timestamp": {
                "gte": start_time.isoformat(),
                "lte": end_time.isoformat()
            }}},
            # Double-check tenant_id (redundant with index pattern, but extra safety)
            {"term": {"agent.labels.tenant_id": str(tenant_id)}}
        ]
        
        # Optional filters
        if severity_min is not None:
            filters.append({"range": {"rule.level": {"gte": severity_min}}})
        
        if agent_id:
            filters.append({"term": {"agent.id": agent_id}})
        
        # Build query
        query = {
            "query": {
                "bool": {
                    "filter": filters
                }
            },
            "sort": [{"@timestamp": "desc"}],
            "size": limit,
            "from": offset
        }
        
        # Query tenant-specific index pattern
        index_pattern = f"wazuh-alerts-{tenant_id}-*"
        
        try:
            response = self.os.search(
                index=index_pattern,
                body=query
            )
            
            alerts = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                alerts.append({
                    "id": hit["_id"],
                    "timestamp": source.get("@timestamp"),
                    "agent": {
                        "id": source.get("agent", {}).get("id"),
                        "name": source.get("agent", {}).get("name"),
                        "ip": source.get("agent", {}).get("ip")
                    },
                    "rule": {
                        "id": source.get("rule", {}).get("id"),
                        "level": source.get("rule", {}).get("level"),
                        "description": source.get("rule", {}).get("description"),
                        "mitre": source.get("rule", {}).get("mitre", {})
                    },
                    "data": source.get("data", {}),
                    "full_log": source.get("full_log"),
                    "location": source.get("location")
                })
            
            return {
                "alerts": alerts,
                "total": response["hits"]["total"]["value"],
                "count": len(alerts),
                "query": {
                    "tenant_id": str(tenant_id),
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "severity_min": severity_min,
                    "agent_id": agent_id
                }
            }
            
        except opensearch_exceptions.NotFoundError:
            # No indices exist yet for this tenant
            logger.info(f"No Wazuh alert indices found for tenant {tenant_id}")
            return {
                "alerts": [],
                "total": 0,
                "count": 0,
                "query": {
                    "tenant_id": str(tenant_id),
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Failed to query Wazuh alerts for tenant {tenant_id}: {e}", exc_info=True)
            raise Exception(f"Failed to query alerts: {str(e)}")
    
    async def get_alert_statistics(
        self,
        tenant_id: UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get alert statistics for a tenant.
        
        Args:
            tenant_id: Tenant ID
            start_time: Start of time range
            end_time: End of time range
        
        Returns:
            Statistics including severity breakdown, top rules, etc.
        """
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(days=7)
        
        index_pattern = f"wazuh-alerts-{tenant_id}-*"
        
        # Aggregation query
        query = {
            "query": {
                "bool": {
                    "filter": [
                        {"range": {"@timestamp": {
                            "gte": start_time.isoformat(),
                            "lte": end_time.isoformat()
                        }}},
                        {"term": {"agent.labels.tenant_id": str(tenant_id)}}
                    ]
                }
            },
            "size": 0,
            "aggs": {
                "by_severity": {
                    "range": {
                        "field": "rule.level",
                        "ranges": [
                            {"key": "low", "from": 0, "to": 5},
                            {"key": "medium", "from": 5, "to": 10},
                            {"key": "high", "from": 10, "to": 13},
                            {"key": "critical", "from": 13, "to": 16}
                        ]
                    }
                },
                "by_agent": {
                    "terms": {
                        "field": "agent.name",
                        "size": 10
                    }
                },
                "top_rules": {
                    "terms": {
                        "field": "rule.description.keyword",
                        "size": 10
                    }
                },
                "mitre_tactics": {
                    "terms": {
                        "field": "rule.mitre.tactic",
                        "size": 20
                    }
                }
            }
        }
        
        try:
            response = self.os.search(index=index_pattern, body=query)
            
            # Parse aggregations
            aggs = response.get("aggregations", {})
            
            return {
                "total_alerts": response["hits"]["total"]["value"],
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "severity_breakdown": {
                    bucket["key"]: bucket["doc_count"]
                    for bucket in aggs.get("by_severity", {}).get("buckets", [])
                },
                "top_agents": [
                    {"name": bucket["key"], "count": bucket["doc_count"]}
                    for bucket in aggs.get("by_agent", {}).get("buckets", [])
                ],
                "top_rules": [
                    {"rule": bucket["key"], "count": bucket["doc_count"]}
                    for bucket in aggs.get("top_rules", {}).get("buckets", [])
                ],
                "mitre_tactics": [
                    {"tactic": bucket["key"], "count": bucket["doc_count"]}
                    for bucket in aggs.get("mitre_tactics", {}).get("buckets", [])
                    if bucket["key"]  # Filter out empty values
                ]
            }
            
        except opensearch_exceptions.NotFoundError:
            return {
                "total_alerts": 0,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "severity_breakdown": {},
                "top_agents": [],
                "top_rules": [],
                "mitre_tactics": []
            }
        except Exception as e:
            logger.error(f"Failed to get alert statistics: {e}", exc_info=True)
            raise Exception(f"Failed to get statistics: {str(e)}")

