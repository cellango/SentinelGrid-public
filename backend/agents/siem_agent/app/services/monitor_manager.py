"""OpenSearch Alerting monitor management service."""

import logging
from typing import Dict, Any, List, Optional
import httpx
from datetime import datetime

from app.config.monitor_definitions import (
    get_all_monitor_definitions,
    get_monitor_definition,
    interpolate_tenant_id
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class MonitorManager:
    """Manages OpenSearch Alerting monitors."""
    
    def __init__(self, opensearch_url: Optional[str] = None):
        """
        Initialize monitor manager.
        
        Args:
            opensearch_url: OpenSearch cluster URL (defaults to settings)
        """
        self.opensearch_url = opensearch_url or settings.OPENSEARCH_URL
        self.auth = None
        self.verify_tls = settings.OPENSEARCH_VERIFY_CERTS
        if settings.OPENSEARCH_USER and settings.OPENSEARCH_PASSWORD:
            self.auth = (settings.OPENSEARCH_USER, settings.OPENSEARCH_PASSWORD)
    
    async def create_monitor(
        self,
        tenant_id: str,
        rule_key: str,
        destination_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an OpenSearch monitor for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            rule_key: Detection rule key (e.g., 'SG-DET-001')
            destination_id: OpenSearch destination ID for webhook (None = no actions)
        
        Returns:
            Dict with monitor_id and creation status
        """
        try:
            # Get monitor definition
            monitor_def = get_monitor_definition(rule_key)
            
            # Interpolate tenant ID
            interpolated = interpolate_tenant_id(monitor_def, tenant_id)
            
            # Build OpenSearch monitor payload
            monitor_payload = {
                "type": "monitor",
                "name": f"{interpolated['name']} - Tenant {tenant_id[:8]}",
                "enabled": True,
                "schedule": interpolated["schedule"],
                "inputs": [
                    {
                        "search": {
                            "indices": [interpolated["index_pattern"]],
                            "query": interpolated["query"]
                        }
                    }
                ],
                "triggers": [
                    {
                        "name": f"{interpolated['alert_type']}_trigger",
                        "severity": self._map_severity_to_level(interpolated["severity"]),
                        "condition": interpolated["trigger_condition"],
                        "actions": (
                            [] if not destination_id else [
                                {
                                    "name": "webhook_to_router",
                                    "destination_id": destination_id,
                                    "message_template": {
                                        "source": self._build_detection_event_payload(
                                            interpolated, tenant_id
                                        )
                                    },
                                    "throttle_enabled": True,
                                    "throttle": {"value": 1, "unit": "MINUTES"}
                                }
                            ]
                        )
                    }
                ]
            }
            
            # Create monitor via OpenSearch Alerting API
            async with httpx.AsyncClient(auth=self.auth, verify=self.verify_tls, timeout=30.0) as client:
                response = await client.post(
                    f"{self.opensearch_url}/_plugins/_alerting/monitors",
                    json=monitor_payload
                )
                response.raise_for_status()
                
                result = response.json()
                monitor_id = result.get("_id")
                
                logger.info(
                    f"Created monitor {monitor_id} for tenant {tenant_id}, "
                    f"rule={rule_key}"
                )
                
                return {
                    "monitor_id": monitor_id,
                    "rule_key": rule_key,
                    "tenant_id": tenant_id,
                    "created_at": datetime.utcnow().isoformat()
                }
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating monitor: {e.response.status_code} - {e.response.text}")
            raise

    async def create_monitor_from_payload(
        self,
        monitor_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create an OpenSearch monitor using an explicit payload.
        """
        try:
            async with httpx.AsyncClient(auth=self.auth, verify=self.verify_tls, timeout=30.0) as client:
                response = await client.post(
                    f"{self.opensearch_url}/_plugins/_alerting/monitors",
                    json=monitor_payload
                )
                response.raise_for_status()

                result = response.json()
                monitor_id = result.get("_id")

                logger.info(
                    f"Created monitor {monitor_id} (custom payload)"
                )

                return {
                    "monitor_id": monitor_id,
                    "created_at": datetime.utcnow().isoformat()
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating monitor: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error creating monitor: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating monitor: {e}")
            raise
    
    async def update_monitor(
        self,
        monitor_id: str,
        enabled: Optional[bool] = None,
        schedule: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing monitor.
        
        Args:
            monitor_id: OpenSearch monitor ID
            enabled: Enable/disable monitor
            schedule: Update schedule
        
        Returns:
            Updated monitor info
        """
        try:
            # Get current monitor
            async with httpx.AsyncClient(auth=self.auth, verify=self.verify_tls, timeout=30.0) as client:
                response = await client.get(
                    f"{self.opensearch_url}/_plugins/_alerting/monitors/{monitor_id}"
                )
                response.raise_for_status()
                
                current_monitor = response.json().get("monitor", {})
                
                # Update fields
                if enabled is not None:
                    current_monitor["enabled"] = enabled
                if schedule is not None:
                    current_monitor["schedule"] = schedule
                
                # Update monitor
                response = await client.put(
                    f"{self.opensearch_url}/_plugins/_alerting/monitors/{monitor_id}",
                    json=current_monitor
                )
                response.raise_for_status()
                
                logger.info(f"Updated monitor {monitor_id}")
                
                return {
                    "monitor_id": monitor_id,
                    "updated_at": datetime.utcnow().isoformat()
                }
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error updating monitor: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error updating monitor: {e}")
            raise
    
    async def delete_monitor(self, monitor_id: str) -> bool:
        """
        Delete a monitor.
        
        Args:
            monitor_id: OpenSearch monitor ID
        
        Returns:
            True if deleted successfully
        """
        try:
            async with httpx.AsyncClient(auth=self.auth, verify=self.verify_tls, timeout=30.0) as client:
                response = await client.delete(
                    f"{self.opensearch_url}/_plugins/_alerting/monitors/{monitor_id}"
                )
                response.raise_for_status()
                
                logger.info(f"Deleted monitor {monitor_id}")
                return True
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Monitor {monitor_id} not found")
                return False
            logger.error(f"HTTP error deleting monitor: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error deleting monitor: {e}")
            raise
    
    async def get_monitor(self, monitor_id: str) -> Dict[str, Any]:
        """
        Get monitor details.
        
        Args:
            monitor_id: OpenSearch monitor ID
        
        Returns:
            Monitor details
        """
        try:
            async with httpx.AsyncClient(auth=self.auth, verify=self.verify_tls, timeout=30.0) as client:
                response = await client.get(
                    f"{self.opensearch_url}/_plugins/_alerting/monitors/{monitor_id}"
                )
                response.raise_for_status()
                
                return response.json()
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting monitor: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting monitor: {e}")
            raise
    
    async def list_monitors(
        self,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all monitors.
        
        Args:
            tenant_id: Optional filter by tenant (checks monitor name)
        
        Returns:
            List of monitors
        """
        try:
            async with httpx.AsyncClient(auth=self.auth, verify=self.verify_tls, timeout=30.0) as client:
                response = await client.post(
                    f"{self.opensearch_url}/_plugins/_alerting/monitors/_search",
                    json={"size": 1000, "query": {"match_all": {}}}
                )
                response.raise_for_status()
                
                hits = response.json().get("hits", {}).get("hits", [])
                monitors = [
                    {"_id": hit.get("_id"), **(hit.get("_source") or {})}
                    for hit in hits
                ]
                
                # Filter by tenant if specified
                if tenant_id:
                    monitors = [
                        m for m in monitors
                        if tenant_id[:8] in m.get("name", "")
                    ]
                
                return monitors
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error listing monitors: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error listing monitors: {e}")
            raise
    
    async def create_webhook_destination(
        self,
        tenant_id: str,
        webhook_url: str,
        auth_token: str,
    ) -> str:
        """
        Create webhook destination in OpenSearch Notifications (prefers Notifications API, falls back to Alerting).
        """
        notifications_payload = {
            "config": {
                "name": f"sentinelgrid-soar-webhook-{tenant_id[:8]}",
                "description": "SentinelGrid SOAR webhook",
                "config_type": "webhook",
                "is_enabled": True,
                "webhook": {
                    "url": webhook_url,
                    "header_params": {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {auth_token}",
                        "X-Tenant-ID": tenant_id,
                    },
                    "method": "POST",
                },
            }
        }

        alerting_payload = {
            "name": f"sentinelgrid-soar-webhook-{tenant_id[:8]}",
            "type": "webhook",
            "is_enabled": True,
            "schema_version": 1,
            "webhook": {
                "url": webhook_url,
                "header_params": {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {auth_token}",
                    "X-Tenant-ID": tenant_id,
                },
                "method": "POST",
            },
        }

        try:
            async with httpx.AsyncClient(auth=self.auth, verify=self.verify_tls, timeout=30.0) as client:
                # Preferred Notifications API (2.6+)
                try:
                    response = await client.post(
                        f"{self.opensearch_url}/_plugins/_notifications/configs",
                        json=notifications_payload,
                    )
                    response.raise_for_status()
                    result = response.json()
                    destination_id = result.get("config_id")
                    if destination_id:
                        logger.info(
                            "Created webhook destination %s for tenant %s via Notifications API",
                            destination_id,
                            tenant_id,
                        )
                        return destination_id
                    logger.warning("Notifications API response missing config_id: %s", result)
                except httpx.HTTPStatusError as e:
                    logger.warning(
                        "Notifications API create failed (%s): %s",
                        e.response.status_code,
                        e.response.text,
                    )
                except Exception:
                    # Fall through to Alerting
                    pass

                # Fallback to Alerting destinations (older clusters)
                response = await client.post(
                    f"{self.opensearch_url}/_plugins/_alerting/destinations",
                    json=alerting_payload,
                )
                response.raise_for_status()
                result = response.json()
                destination_id = result.get("id") or result.get("_id")
                if destination_id:
                    logger.info(
                        "Created webhook destination %s for tenant %s via Alerting API",
                        destination_id,
                        tenant_id,
                    )
                    return destination_id
                logger.error("Alerting API response missing destination id: %s", result)
                raise ValueError("Destination creation did not return an id")

        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error creating destination: %s - %s",
                e.response.status_code,
                e.response.text,
            )
            raise
        except Exception as e:
            logger.error(f"Error creating destination: {e}")
            raise

    async def create_router_destination(self) -> str:
        """
        Create (or reuse) a shared webhook destination pointing to the router endpoint.
        """
        name = "sentinelgrid-router-destination"
        router_url = settings.ROUTER_URL
        payload = {
            "config": {
                "name": name,
                "description": "Shared router destination",
                "config_type": "webhook",
                "is_enabled": True,
                "webhook": {
                    "url": router_url,
                    "header_params": {
                        "Content-Type": "application/json",
                    },
                    "method": "POST",
                },
            }
        }

        try:
            async with httpx.AsyncClient(auth=self.auth, verify=self.verify_tls, timeout=30.0) as client:
                response = await client.post(
                    f"{self.opensearch_url}/_plugins/_notifications/configs",
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()
                dest_id = result.get("config_id") or result.get("_id")
                if dest_id:
                    logger.info("Created router destination: %s", dest_id)
                    return dest_id
                logger.error("Router destination create response missing id: %s", result)
                raise ValueError("Router destination creation did not return an id")
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error creating router destination: %s %s",
                e.response.status_code,
                e.response.text,
            )
            raise
        except Exception as e:
            logger.error(f"Failed to create router destination: {e}")
            raise
    
    async def delete_webhook_destination(self, destination_id: str) -> bool:
        """
        Delete webhook destination.
        
        Args:
            destination_id: Destination ID
        
        Returns:
            True if deleted
        """
        try:
            async with httpx.AsyncClient(auth=self.auth, verify=self.verify_tls, timeout=30.0) as client:
                response = await client.delete(
                    f"{self.opensearch_url}/_plugins/_notifications/configs/{destination_id}"
                )
                response.raise_for_status()
                
                logger.info(f"Deleted destination {destination_id}")
                return True
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Destination {destination_id} not found")
                return False
            logger.error(f"HTTP error deleting destination: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error deleting destination: {e}")
            raise
    
    def _map_severity_to_level(self, severity: str) -> str:
        """Map severity string to OpenSearch level."""
        severity_map = {
            "critical": "1",
            "high": "2",
            "medium": "3",
            "low": "4",
            "informational": "5"
        }
        return severity_map.get(severity.lower(), "3")
    
    def _build_detection_event_payload(
        self,
        monitor_def: Dict[str, Any],
        tenant_id: str
    ) -> str:
        """
        Build detection event payload template for webhook.
        
        This uses Mustache templating that OpenSearch supports.
        """
        return """
{
  "@timestamp": "{{ctx.trigger.triggered_time}}",
  "sg": {
    "tenant_id": \"""" + tenant_id + """\",
    "realm": "sentinelgrid",
    "alert_type": \"""" + monitor_def['alert_type'] + """\",
    "playbook_id": \"""" + monitor_def['playbook_id'] + """\",
    "severity": \"""" + monitor_def['severity'] + """\",
    "category": \"""" + monitor_def['category'] + """\"
  },
  "rule": {
    "id": \"""" + monitor_def['rule_key'] + """\",
    "name": \"""" + monitor_def['name'] + """\",
    "version": \"""" + monitor_def['version'] + """\"
  },
  "description": \"""" + monitor_def['description'] + """\",
  "metadata": """ + str(monitor_def.get('metadata', {})).replace("'", '"') + """,
  "raw_alert": {
    "monitor_id": "{{ctx.monitor.id}}",
    "monitor_name": "{{ctx.monitor.name}}",
    "trigger_id": "{{ctx.trigger.id}}",
    "trigger_name": "{{ctx.trigger.name}}",
    "severity": "{{ctx.trigger.severity}}",
    "period_start": "{{ctx.periodStart}}",
    "period_end": "{{ctx.periodEnd}}",
    "results": "{{ctx.results}}"
  }
}
        """.strip()
