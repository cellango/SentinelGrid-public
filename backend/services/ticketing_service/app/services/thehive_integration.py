"""TheHive integration service."""

import logging
from typing import Dict, Any, Optional, List
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class TheHiveIntegration:
    """Service for integrating with TheHive."""
    
    def __init__(self):
        self.base_url = settings.THEHIVE_URL
        self.api_key = settings.THEHIVE_API_KEY
        self.headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
    
    async def create_case_from_ticket(
        self,
        ticket_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create a case in TheHive from a ticket.
        
        Args:
            ticket_data: Ticket data dictionary
        
        Returns:
            TheHive case data or None
        """
        if not self.base_url:
            logger.warning("TheHive URL not configured, skipping case creation")
            return None
        
        try:
            case_data = {
                "title": ticket_data["title"],
                "description": ticket_data.get("description", ""),
                "severity": self._map_severity(ticket_data.get("severity")),
                "status": self._map_status(ticket_data.get("status", "open")),
                "tags": self._generate_tags(ticket_data)
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/v1/case"
                response = await client.post(url, json=case_data, headers=self.headers)
                response.raise_for_status()
                case = response.json()
                
                logger.info(f"Created TheHive case {case.get('id')} for ticket {ticket_data.get('id')}")
                return case
        
        except Exception as e:
            logger.error(f"Error creating TheHive case: {e}")
            return None
    
    async def sync_case_status(
        self,
        case_id: str,
        status: str
    ) -> bool:
        """
        Sync case status to TheHive.
        
        Args:
            case_id: TheHive case ID
            status: New status
        
        Returns:
            True if successful
        """
        if not self.base_url:
            return False
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/v1/case/{case_id}"
                payload = {"status": self._map_status(status)}
                response = await client.patch(url, json=payload, headers=self.headers)
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Error syncing case status: {e}")
            return False
    
    def _map_severity(self, severity: Optional[str]) -> int:
        """Map severity to TheHive severity (1-4)."""
        mapping = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1
        }
        return mapping.get(severity or "medium", 2)
    
    def _map_status(self, status: str) -> str:
        """Map status to TheHive status."""
        mapping = {
            "open": "Open",
            "in_progress": "InProgress",
            "resolved": "Resolved",
            "closed": "Resolved"
        }
        return mapping.get(status, "Open")
    
    def _generate_tags(self, ticket_data: Dict[str, Any]) -> List[str]:
        """Generate tags for TheHive case."""
        tags = []
        
        if ticket_data.get("category"):
            tags.append(ticket_data["category"])
        
        if ticket_data.get("tenant_id"):
            tags.append(f"tenant:{ticket_data['tenant_id']}")
        
        if ticket_data.get("cve_ids"):
            tags.extend([f"cve:{cve}" for cve in ticket_data["cve_ids"][:5]])  # Limit tags
        
        return tags
