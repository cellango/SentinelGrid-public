"""OpenSearch client wrapper for SIEM Agent."""

import logging
from typing import List, Optional
from datetime import datetime, timedelta
from opensearchpy import OpenSearch
try:
    from opensearchpy import RequestsHttpConnection
except ImportError:
    # Fallback if RequestsHttpConnection not available
    RequestsHttpConnection = None
from opensearchpy.exceptions import OpenSearchException
from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenSearchClient:
    """OpenSearch client wrapper with tenant isolation and index management."""
    
    def __init__(self):
        """Initialize OpenSearch client."""
        http_auth = None
        if settings.OPENSEARCH_USER and settings.OPENSEARCH_PASSWORD:
            http_auth = (settings.OPENSEARCH_USER, settings.OPENSEARCH_PASSWORD)
        
        connection_params = {
            "hosts": [settings.OPENSEARCH_URL],
            "http_auth": http_auth,
            "use_ssl": settings.OPENSEARCH_USE_SSL,
            "verify_certs": settings.OPENSEARCH_VERIFY_CERTS,
            "timeout": settings.OPENSEARCH_TIMEOUT,
            "max_retries": settings.OPENSEARCH_MAX_RETRIES,
            "retry_on_timeout": True,
        }
        
        if RequestsHttpConnection:
            connection_params["connection_class"] = RequestsHttpConnection
        
        self.client = OpenSearch(**connection_params)
        
        # Ensure index templates exist
        self._ensure_index_templates()
    
    def _ensure_index_templates(self):
        """Ensure index templates exist for tenant-scoped indices."""
        try:
            # Template for logs indices
            self.client.indices.put_index_template(
                name="sg-logs-template",
                body={
                    "index_patterns": ["sg-*-logs-*"],
                    "template": {
                        "settings": {
                            "number_of_shards": settings.INDEX_SHARDS,
                            "number_of_replicas": settings.INDEX_REPLICAS,
                            "refresh_interval": "30s",
                        },
                        "mappings": {
                            "properties": {
                                "@timestamp": {"type": "date"},
                                "sg": {
                                    "properties": {
                                        "tenant_id": {"type": "keyword"},
                                        "realm": {"type": "keyword"}
                                    }
                                },
                                "tenant_id": {"type": "keyword"},  # Legacy support
                                "event_type": {"type": "keyword"},
                                "source": {
                                "properties": {
                                    "name": {"type": "keyword"},
                                    "type": {"type": "keyword"},
                                    "ip": {"type": "ip"},
                                    "port": {"type": "integer"},
                                    "geo": {
                                        "properties": {
                                            "country": {"type": "keyword"},
                                            "city": {"type": "keyword"}
                                        }
                                    }
                                }
                            },
                            "action": {"type": "keyword"},
                            "outcome": {"type": "keyword"},
                            "user": {
                                "properties": {
                                    "id": {"type": "keyword"},
                                    "email": {"type": "keyword"},
                                    "name": {"type": "text"}
                                }
                            },
                            "host": {
                                "properties": {
                                    "hostname": {"type": "keyword"},
                                    "ip": {"type": "ip"}
                                }
                            },
                            "device": {
                                "properties": {
                                    "id": {"type": "keyword"},
                                    "type": {"type": "keyword"},
                                    "user_agent": {"type": "text"}
                                }
                            },
                            "network": {
                                "properties": {
                                    "protocol": {"type": "keyword"},
                                    "source": {
                                        "properties": {
                                            "ip": {"type": "ip"}
                                        }
                                    },
                                    "destination": {
                                        "properties": {
                                            "ip": {"type": "ip"}
                                        }
                                    }
                                }
                            },
                            "details": {"type": "object"},
                            "raw_data": {"type": "object"}
                        }
                    }
                    }
                }
            )
            
            # Template for alerts indices
            self.client.indices.put_index_template(
                name="sg-alerts-template",
                body={
                    "index_patterns": ["sg-*-alerts-*"],
                    "template": {
                        "settings": {
                            "number_of_shards": settings.INDEX_SHARDS,
                            "number_of_replicas": settings.INDEX_REPLICAS,
                            "refresh_interval": "30s",
                        },
                        "mappings": {
                            "properties": {
                                "@timestamp": {"type": "date"},
                                "sg": {
                                    "properties": {
                                        "tenant_id": {"type": "keyword"},
                                        "realm": {"type": "keyword"}
                                    }
                                },
                                "tenant_id": {"type": "keyword"},  # Legacy support
                                "severity": {"type": "keyword"},
                                "status": {"type": "keyword"},
                                "title": {"type": "text"},
                                "description": {"type": "text"},
                                "tags": {"type": "keyword"},
                                "user_id": {"type": "keyword"},
                                "source_ip": {"type": "ip"},
                                "detection_rule_id": {"type": "keyword"},
                                "events": {"type": "keyword"},  # Array of event IDs
                            }
                        }
                    }
                }
            )
            
            # Template for detection event indices
            self.client.indices.put_index_template(
                name="sg-detection-template",
                body={
                    "index_patterns": ["sg-*-detection-*"],
                    "template": {
                        "settings": {
                            "number_of_shards": settings.INDEX_SHARDS,
                            "number_of_replicas": settings.INDEX_REPLICAS,
                        "refresh_interval": "30s",
                    },
                    "mappings": {
                        "properties": {
                            "@timestamp": {"type": "date"},
                            "event_id": {"type": "keyword"},
                            "sg": {
                                "properties": {
                                    "tenant_id": {"type": "keyword"},
                                    "realm": {"type": "keyword"},
                                    "alert_type": {"type": "keyword"},
                                    "playbook_id": {"type": "keyword"},
                                    "severity": {"type": "keyword"},
                                    "category": {"type": "keyword"}
                                }
                            },
                            "rule": {
                                "properties": {
                                    "id": {"type": "keyword"},
                                    "name": {"type": "text"},
                                    "version": {"type": "keyword"}
                                }
                            },
                            "user": {
                                "properties": {
                                    "id": {"type": "keyword"},
                                    "email": {"type": "keyword"},
                                    "name": {"type": "text"}
                                }
                            },
                            "source": {
                                "properties": {
                                    "ip": {"type": "ip"},
                                    "geo": {"type": "object"},
                                    "port": {"type": "integer"}
                                }
                            },
                            "host": {
                                "properties": {
                                    "name": {"type": "keyword"},
                                    "id": {"type": "keyword"},
                                    "ip": {"type": "ip"},
                                    "asset_criticality": {"type": "keyword"}
                                }
                            },
                            "device": {
                                "properties": {
                                    "id": {"type": "keyword"},
                                    "platform": {"type": "keyword"},
                                    "owner_user_id": {"type": "keyword"},
                                    "owner_email": {"type": "keyword"},
                                    "status": {"type": "keyword"}
                                }
                            },
                            "malware": {
                                "properties": {
                                    "name": {"type": "keyword"},
                                    "family": {"type": "keyword"},
                                    "hash": {"type": "keyword"}
                                }
                            },
                            "email": {
                                "properties": {
                                    "message_id": {"type": "keyword"},
                                    "subject": {"type": "text"},
                                    "from": {"type": "keyword"},
                                    "to": {"type": "keyword"}
                                }
                            },
                            "cloud": {
                                "properties": {
                                    "provider": {"type": "keyword"},
                                    "account_id": {"type": "keyword"},
                                    "region": {"type": "keyword"}
                                }
                            },
                            "resource": {
                                "properties": {
                                    "type": {"type": "keyword"},
                                    "id": {"type": "keyword"},
                                    "tags": {"type": "object"}
                                }
                            },
                            "iam": {
                                "properties": {
                                    "action": {"type": "keyword"},
                                    "role_name": {"type": "keyword"}
                                }
                            },
                            "network": {
                                "properties": {
                                    "bytes_out": {"type": "long"},
                                    "bytes_out_1h": {"type": "long"},
                                    "approx_gb": {"type": "float"}
                                }
                            },
                            "auth": {
                                "properties": {
                                    "failed_count_10m": {"type": "integer"},
                                    "first_failure_at": {"type": "date"},
                                    "success_at": {"type": "date"},
                                    "method": {"type": "keyword"}
                                }
                            },
                            "spray": {
                                "properties": {
                                    "failed_attempts_10m": {"type": "integer"},
                                    "distinct_users": {"type": "integer"}
                                }
                            },
                            "campaign": {
                                "properties": {
                                    "subject_pattern": {"type": "text"},
                                    "approx_recipients": {"type": "integer"}
                                }
                            },
                            "description": {"type": "text"},
                            "metadata": {"type": "object"},
                            "raw_alert": {"type": "object"},
                            "actor": {"type": "object"},
                            "target_user": {
                                "properties": {
                                    "id": {"type": "keyword"},
                                    "email": {"type": "keyword"}
                                }
                            },
                            "report_source": {"type": "keyword"}
                        }
                    }
                    }
                }
            )
            
            logger.info("Index templates configured (logs, alerts, detection)")
            
        except OpenSearchException as e:
            logger.warning(f"Failed to create index templates (may already exist): {e}")
    
    def get_index_name(self, tenant_id: str, index_type: str, date: Optional[datetime] = None) -> str:
        """
        Generate tenant-scoped index name.
        
        Args:
            tenant_id: Tenant UUID
            index_type: logs, alerts, or events
            date: Optional date for time-based index (defaults to today)
        
        Returns:
            Index name in format: sg-{tenant_id}-{index_type}-YYYY.MM.DD
        """
        if date is None:
            date = datetime.utcnow()
        
        date_suffix = date.strftime("%Y.%m.%d")
        return f"sg-{tenant_id}-{index_type}-{date_suffix}"
    
    def search_indices(
        self,
        tenant_id: str,
        index_type: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[str]:
        """
        Get list of indices for time range.
        
        Args:
            tenant_id: Tenant UUID
            index_type: logs, alerts, or events
            start_time: Start of time range (defaults to 30 days ago)
            end_time: End of time range (defaults to now)
        
        Returns:
            List of index names
        """
        if start_time is None:
            start_time = datetime.utcnow() - timedelta(days=settings.INDEX_RETENTION_DAYS)
        if end_time is None:
            end_time = datetime.utcnow()
        
        indices = []
        current = start_time.date()
        end = end_time.date()
        
        while current <= end:
            index_name = f"sg-{tenant_id}-{index_type}-{current.strftime('%Y.%m.%d')}"
            try:
                if self.client.indices.exists(index=index_name):
                    indices.append(index_name)
            except OpenSearchException:
                logger.warning(f"Unable to check index existence for {index_name}")
            current += timedelta(days=1)
        
        # If nothing exists yet, fall back to today's index to avoid 404s
        if not indices:
            today_index = f"sg-{tenant_id}-{index_type}-{datetime.utcnow().strftime('%Y.%m.%d')}"
            try:
                if not self.client.indices.exists(index=today_index):
                    self.client.indices.create(index=today_index)
            except OpenSearchException:
                logger.warning(f"Failed to create fallback index {today_index}")
            else:
                indices.append(today_index)
        
        return indices
    
    def health_check(self) -> dict:
        """
        Check OpenSearch cluster health.
        
        Returns:
            Health status information
        """
        try:
            health = self.client.cluster.health()
            return {
                "status": "healthy",
                "cluster_name": health.get("cluster_name"),
                "cluster_status": health.get("status"),
                "number_of_nodes": health.get("number_of_nodes"),
                "active_primary_shards": health.get("active_primary_shards"),
            }
        except OpenSearchException as e:
            logger.error(f"OpenSearch health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def ensure_index_exists(self, index_name: str):
        """
        Ensure index exists (create if it doesn't).
        
        Args:
            index_name: Name of the index
        """
        if not self.client.indices.exists(index=index_name):
            self.client.indices.create(index=index_name)
            logger.info(f"Created index: {index_name}")
