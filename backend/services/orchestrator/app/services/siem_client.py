"""SIEM Agent client for orchestrator."""

import logging
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)


class SIEMClient:
    """Client for interacting with SIEM Agent."""
    
    def __init__(self):
        self.base_url = settings.SIEM_AGENT_URL
        self.token = settings.INTERNAL_SERVICE_TOKEN
        self.timeout = settings.SERVICE_TIMEOUT
    
    async def get_stats(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get SIEM statistics for a tenant.
        
        Args:
            tenant_id: Tenant ID
        
        Returns:
            SIEM statistics dictionary
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/siem/stats",
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "X-Tenant-ID": tenant_id,
                    },
                )
                response.raise_for_status()
                return response.json()
        
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get SIEM stats: {e.response.status_code} - {e.response.text}")
            # Return default stats on error
            return {
                "events_count": 0,
                "alerts_count": 0,
                "alerts_by_severity": {},
                "alerts_by_status": {},
            }
        except Exception as e:
            logger.error(f"Error getting SIEM stats: {e}")
            return {
                "events_count": 0,
                "alerts_count": 0,
                "alerts_by_severity": {},
                "alerts_by_status": {},
            }
    
    async def list_alerts(
        self,
        tenant_id: str,
        limit: int = 10,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List alerts for a tenant.
        
        Args:
            tenant_id: Tenant ID
            limit: Maximum number of alerts to return
            status: Optional alert status filter
        
        Returns:
            List of alert dictionaries
        """
        try:
            params = {"limit": limit, "offset": 0}
            if status:
                params["status"] = status
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/siem/alerts",
                    params=params,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "X-Tenant-ID": tenant_id,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("items", [])
        
        except Exception as e:
            logger.error(f"Error listing alerts: {e}")
            return []

