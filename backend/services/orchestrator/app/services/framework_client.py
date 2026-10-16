"""Client for Framework Service."""

import httpx
import logging
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)


class FrameworkClient:
    """Client for interacting with Framework Service."""
    
    def __init__(self):
        """Initialize framework client."""
        self.base_url = settings.FRAMEWORK_SERVICE_URL
    
    async def map_incident(
        self,
        tenant_id: str,
        incident_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Map incident to MITRE/NIST frameworks.
        
        Args:
            tenant_id: Tenant ID
            incident_data: Incident data dictionary
            
        Returns:
            Framework mapping dictionary
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/framework/map",
                    json={"ticket_data": incident_data, "tenant_id": tenant_id},
                    headers={
                        "X-Tenant-ID": tenant_id,
                        "Authorization": f"Bearer {settings.INTERNAL_SERVICE_TOKEN}"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Framework service returned {response.status_code}: {response.text}")
                    return {}
        except Exception as e:
            logger.error(f"Error calling framework service: {e}")
            return {}
