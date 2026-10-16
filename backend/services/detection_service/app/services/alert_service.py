"""Service for creating alerts from rule evaluation results."""

import logging
import httpx
from typing import List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)


async def create_alerts(tenant_id: str, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create alerts in SIEM Agent.
    
    Args:
        tenant_id: Tenant ID
        alerts: List of alert dictionaries from rule evaluation
    
    Returns:
        Creation results
    """
    if not alerts:
        return {"created": 0, "failed": 0}
    
    url = f"{settings.SIEM_AGENT_URL}/internal/siem/alerts/create"
    
    created = 0
    failed = 0
    
    # Create alerts individually (could be batched in future)
    for alert in alerts:
        try:
            # Convert alert to AlertCreate format expected by SIEM Agent
            from datetime import datetime
            
            alert_create = {
                "title": alert.get("title"),
                "description": alert.get("description"),
                "severity": alert.get("severity", "medium"),
                "status": alert.get("status", "open"),
                "events": alert.get("events", []),
                "metadata": {
                    "detection_rule_id": alert.get("metadata", {}).get("rule_name"),
                    **alert.get("metadata", {}),
                },
            }
            
            # Add optional fields
            if "user_id" in alert:
                alert_create["user_id"] = alert["user_id"]
            if "source_ip" in alert:
                alert_create["source_ip"] = alert["source_ip"]
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=alert_create,
                    headers={
                        "Authorization": f"Bearer {settings.INTERNAL_SERVICE_TOKEN}",
                        "X-Tenant-ID": tenant_id,
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                created += 1
        
        except Exception as e:
            logger.error(f"Failed to create alert: {e}", exc_info=True)
            failed += 1
    
    logger.info(f"Created {created} alerts, {failed} failed for tenant {tenant_id}")
    
    return {
        "created": created,
        "failed": failed,
    }

