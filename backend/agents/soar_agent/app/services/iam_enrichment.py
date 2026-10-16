"""IAM enrichment module - User, supervisor, groups, permissions."""

import logging
from typing import Dict, Any, List, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class IAMEnrichmentModule:
    """Enriches tickets with IAM-related data."""
    
    def __init__(self):
        self.iam_agent_url = settings.IAM_AGENT_URL
        self.internal_token = settings.INTERNAL_SERVICE_TOKEN
    
    async def enrich(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich ticket with IAM data.
        
        Args:
            ticket_data: Ticket data dictionary
        
        Returns:
            IAM enrichment data
        """
        # Extract user identifiers from ticket
        user_identifiers = self._extract_user_identifiers(ticket_data)
        
        if not user_identifiers:
            return {
                "users": [],
                "supervisors": [],
                "groups": [],
                "permissions": [],
                "access_history": []
            }
        
        enrichment_data = {
            "users": [],
            "supervisors": [],
            "groups": [],
            "permissions": [],
            "access_history": []
        }
        
        for user_id in user_identifiers:
            try:
                # Fetch user data from IAM Agent
                user_data = await self._get_user_details(user_id)
                
                if user_data:
                    enrichment_data["users"].append({
                        "user_id": user_data.get("id"),
                        "username": user_data.get("username"),
                        "email": user_data.get("email"),
                        "display_name": user_data.get("display_name"),
                        "department": user_data.get("department"),
                        "title": user_data.get("title"),
                        "status": user_data.get("status"),  # active, disabled, etc.
                        "last_login": user_data.get("last_login"),
                        "risk_score": user_data.get("risk_score")
                    })
                    
                    # Fetch supervisor data
                    if user_data.get("supervisor_id"):
                        supervisor = await self._get_user_details(user_data["supervisor_id"])
                        if supervisor:
                            enrichment_data["supervisors"].append({
                                "supervisor_id": supervisor.get("id"),
                                "username": supervisor.get("username"),
                                "email": supervisor.get("email"),
                                "display_name": supervisor.get("display_name")
                            })
                    
                    # Fetch group memberships
                    groups = await self._get_user_groups(user_id)
                    enrichment_data["groups"].extend(groups)
                    
                    # Fetch permissions
                    permissions = await self._get_user_permissions(user_id)
                    enrichment_data["permissions"].extend(permissions)
                    
                    # Fetch access history
                    access_history = await self._get_user_access_history(user_id, limit=10)
                    enrichment_data["access_history"].extend(access_history)
            
            except Exception as e:
                logger.error(f"Error enriching IAM data for user {user_id}: {e}")
                continue
        
        return enrichment_data
    
    def _extract_user_identifiers(self, ticket_data: Dict[str, Any]) -> List[str]:
        """Extract user identifiers from ticket data."""
        identifiers = []
        
        # Check ticket fields
        if ticket_data.get("user_identifier"):
            identifiers.append(ticket_data["user_identifier"])
        
        # Check linked alerts
        if ticket_data.get("alerts"):
            for alert in ticket_data["alerts"]:
                if alert.get("user_identifier"):
                    identifiers.append(alert["user_identifier"])
        
        # Check IAM data if already present
        if ticket_data.get("iam_data", {}).get("users"):
            for user in ticket_data["iam_data"]["users"]:
                if user.get("user_id"):
                    identifiers.append(user["user_id"])
        
        # Remove duplicates
        return list(set(identifiers))
    
    async def _get_user_details(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch user details from IAM Agent."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.internal_token}",
                    "Content-Type": "application/json"
                }
                # Note: This endpoint needs to be implemented in IAM Agent
                url = f"{self.iam_agent_url}/api/v1/users/{user_id}"
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning(f"Could not fetch user details for {user_id}: {e}")
            return None
    
    async def _get_user_groups(self, user_id: str) -> List[Dict[str, Any]]:
        """Fetch user groups from IAM Agent."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.internal_token}",
                    "Content-Type": "application/json"
                }
                url = f"{self.iam_agent_url}/api/v1/users/{user_id}/groups"
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning(f"Could not fetch groups for user {user_id}: {e}")
            return []
    
    async def _get_user_permissions(self, user_id: str) -> List[Dict[str, Any]]:
        """Fetch user permissions from IAM Agent."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.internal_token}",
                    "Content-Type": "application/json"
                }
                url = f"{self.iam_agent_url}/api/v1/users/{user_id}/permissions"
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning(f"Could not fetch permissions for user {user_id}: {e}")
            return []
    
    async def _get_user_access_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch user access history from IAM Agent."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.internal_token}",
                    "Content-Type": "application/json"
                }
                url = f"{self.iam_agent_url}/api/v1/users/{user_id}/access-history?limit={limit}"
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning(f"Could not fetch access history for user {user_id}: {e}")
            return []

