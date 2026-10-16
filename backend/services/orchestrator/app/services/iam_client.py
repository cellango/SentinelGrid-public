"""IAM Agent client for orchestrator."""

import logging
import httpx
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class IAMClient:
    """Client for interacting with IAM Agent."""
    
    def __init__(self):
        self.base_url = settings.IAM_AGENT_URL
        self.token = settings.INTERNAL_SERVICE_TOKEN
        self.timeout = settings.SERVICE_TIMEOUT
    
    async def get_identity_stats(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get identity statistics for a tenant.
        
        Args:
            tenant_id: Tenant ID
        
        Returns:
            Identity statistics dictionary
        """
        try:
            # For now, we'll need to implement a stats endpoint in IAM Agent
            # Or query Keycloak directly. Let's try a generic stats endpoint first.
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Try stats endpoint (may not exist yet)
                try:
                    response = await client.get(
                        f"{self.base_url}/internal/iam/stats/{tenant_id}",
                        headers={
                            "Authorization": f"Bearer {self.token}",
                        },
                    )
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        # Stats endpoint doesn't exist yet, return defaults
                        logger.warning("IAM stats endpoint not available, using defaults")
                        return self._get_default_stats()
                    raise
        
        except Exception as e:
            logger.error(f"Error getting IAM stats: {e}")
            return self._get_default_stats()
    
    def _get_default_stats(self) -> Dict[str, Any]:
        """Return default identity statistics."""
        return {
            "users_count": 0,
            "active_users_count": 0,
            "roles_count": 0,
            "groups_count": 0,
            "last_sync_at": None,
        }
