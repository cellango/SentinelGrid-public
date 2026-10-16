"""Framework mapping module - NIST/MITRE mapping."""

import logging
from typing import Dict, Any, List, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class FrameworkMappingModule:
    """Enriches tickets with framework mappings (NIST/MITRE)."""
    
    def __init__(self):
        self.framework_service_url = settings.FRAMEWORK_SERVICE_URL
        self.internal_token = settings.INTERNAL_SERVICE_TOKEN
    
    async def enrich(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich ticket with framework mappings.
        
        Args:
            ticket_data: Ticket data dictionary
        
        Returns:
            Framework enrichment data
        """
        # If framework mappings already exist, return them
        if ticket_data.get("nist_controls") or ticket_data.get("mitre_tactics"):
            return {
                "nist_controls": ticket_data.get("nist_controls", []),
                "mitre_tactics": ticket_data.get("mitre_tactics", []),
                "mitre_techniques": ticket_data.get("mitre_techniques", [])
            }
        
        # Otherwise, map using Framework Service
        try:
            mapping = await self._map_to_frameworks(ticket_data)
            return {
                "nist_controls": mapping.get("nist_controls", []),
                "mitre_tactics": mapping.get("mitre_tactics", []),
                "mitre_techniques": mapping.get("mitre_techniques", [])
            }
        except Exception as e:
            logger.error(f"Error mapping frameworks: {e}")
            return {
                "nist_controls": [],
                "mitre_tactics": [],
                "mitre_techniques": []
            }
    
    async def _map_to_frameworks(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map ticket to NIST/MITRE frameworks using Framework Service."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                tenant_id = ticket_data.get("tenant_id")
                headers = {
                    "Authorization": f"Bearer {self.internal_token}",
                    "Content-Type": "application/json",
                }
                if tenant_id:
                    headers["X-Tenant-ID"] = str(tenant_id)
                url = f"{self.framework_service_url}/api/v1/framework/map"
                payload = {
                    "ticket_data": ticket_data,
                    "tenant_id": tenant_id
                }
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning(f"Could not map to frameworks: {e}")
            # Return empty mappings if service unavailable
            return {
                "nist_controls": [],
                "mitre_tactics": [],
                "mitre_techniques": []
            }
