"""Wazuh Manager API client."""

import logging
import httpx
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class WazuhAPIClient:
    """
    Client for Wazuh Manager REST API.
    
    Provides methods to interact with Wazuh Manager for agent management.
    API Documentation: https://documentation.wazuh.com/current/user-manual/api/
    """
    
    def __init__(self, base_url: str, username: str, password: str, verify_tls: bool):
        """
        Initialize Wazuh API client.
        
        Args:
            base_url: Wazuh Manager API URL (e.g., http://wazuh-manager:55000)
            username: API username
            password: API password
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.verify_tls = verify_tls
        self.token = None
        self.token_expiry = None
    
    async def _get_token(self) -> str:
        """Get or refresh JWT token from Wazuh API."""
        # TODO: Add token expiry check and refresh logic
        if self.token:
            return self.token
        
        async with httpx.AsyncClient(verify=self.verify_tls) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/security/user/authenticate",
                    auth=(self.username, self.password),
                    headers={"Content-Type": "application/json"},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                self.token = data["data"]["token"]
                logger.info("Successfully authenticated with Wazuh Manager API")
                return self.token
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error during Wazuh authentication: {e.response.status_code} - {e.response.text}")
                raise Exception(f"Failed to authenticate with Wazuh Manager: {e}")
            except Exception as e:
                logger.error(f"Failed to authenticate with Wazuh Manager: {e}")
                raise
    
    async def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """
        Make authenticated request to Wazuh API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (e.g., /agents)
            **kwargs: Additional arguments for httpx request
        
        Returns:
            JSON response from Wazuh API
        """
        token = await self._get_token()
        
        # Ensure path starts with /
        if not path.startswith('/'):
            path = f'/{path}'
        
        async with httpx.AsyncClient(verify=self.verify_tls) as client:
            try:
                response = await client.request(
                    method,
                    f"{self.base_url}{path}",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=30.0,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Wazuh API error: {method} {path} - {e.response.status_code} - {e.response.text}")
                raise Exception(f"Wazuh API request failed: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Request to Wazuh API failed: {method} {path} - {e}")
                raise
    
    async def create_agent(self, name: str, ip: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new agent in Wazuh Manager.
        
        Args:
            name: Agent name (typically hostname)
            ip: Agent IP address (optional)
        
        Returns:
            Agent creation response with agent ID
        """
        payload = {"name": name}
        if ip:
            payload["ip"] = ip
        
        logger.info(f"Creating agent in Wazuh Manager: {name}")
        return await self._request("POST", "/agents", json=payload)
    
    async def update_agent_labels(self, agent_id: str, labels: Dict[str, str]) -> Dict[str, Any]:
        """
        Update agent labels - CRITICAL for tenant_id isolation.
        
        Labels are stored server-side in Wazuh Manager and automatically
        injected into every event from this agent.
        
        Args:
            agent_id: Wazuh agent ID (e.g., "001")
            labels: Dictionary of labels (e.g., {"tenant_id": "uuid", ...})
        
        Returns:
            Update response
        """
        logger.info(f"Updating labels for agent {agent_id}: {labels}")
        return await self._request(
            "PUT",
            f"/agents/{agent_id}/labels",
            json=labels
        )
    
    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Get agent details including status and labels.
        
        Args:
            agent_id: Wazuh agent ID
        
        Returns:
            Agent details
        """
        return await self._request("GET", f"/agents/{agent_id}")
    
    async def get_agent_key(self, agent_id: str) -> Dict[str, Any]:
        """
        Get agent authentication key.
        
        This key is used to authenticate the agent with the manager.
        
        Args:
            agent_id: Wazuh agent ID
        
        Returns:
            Agent key response
        """
        return await self._request("GET", f"/agents/{agent_id}/key")
    
    async def delete_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Delete an agent from Wazuh Manager.
        
        Args:
            agent_id: Wazuh agent ID
        
        Returns:
            Deletion response
        """
        logger.info(f"Deleting agent {agent_id} from Wazuh Manager")
        return await self._request("DELETE", f"/agents?agents_list={agent_id}")
    
    async def list_agents(self, limit: int = 500, offset: int = 0) -> Dict[str, Any]:
        """
        List all agents in Wazuh Manager.
        
        Args:
            limit: Maximum number of agents to return
            offset: Offset for pagination
        
        Returns:
            List of agents
        """
        return await self._request(
            "GET",
            f"/agents?limit={limit}&offset={offset}"
        )
    
    async def restart_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Restart an agent.
        
        Args:
            agent_id: Wazuh agent ID
        
        Returns:
            Restart response
        """
        logger.info(f"Restarting agent {agent_id}")
        return await self._request("PUT", f"/agents/restart?agents_list={agent_id}")
    
    async def get_agent_config(self, agent_id: str) -> Dict[str, Any]:
        """
        Get agent configuration.
        
        Args:
            agent_id: Wazuh agent ID
        
        Returns:
            Agent configuration
        """
        return await self._request("GET", f"/agents/{agent_id}/config")
    
    async def upgrade_agent(self, agent_id: str, version: Optional[str] = None) -> Dict[str, Any]:
        """
        Upgrade agent to a newer version.
        
        Args:
            agent_id: Wazuh agent ID
            version: Target version (optional, uses latest if not specified)
        
        Returns:
            Upgrade response
        """
        payload = {}
        if version:
            payload["version"] = version
        
        logger.info(f"Upgrading agent {agent_id} to version {version or 'latest'}")
        return await self._request("PUT", f"/agents/upgrade?agents_list={agent_id}", json=payload)
