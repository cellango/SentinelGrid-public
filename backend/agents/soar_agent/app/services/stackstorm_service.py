"""StackStorm API client for workflow automation."""

import logging
from typing import List, Dict, Any, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class StackStormService:
    """Service for interacting with StackStorm API."""
    
    def __init__(self):
        self.base_url = getattr(settings, 'STACKSTORM_URL', 'http://stackstorm:9101')
        self.api_key = getattr(settings, 'STACKSTORM_API_KEY', None)
        self.headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            self.headers["St2-Api-Key"] = self.api_key
    
    async def list_actions(self, pack: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available StackStorm actions.
        
        Args:
            pack: Optional filter by pack name
        
        Returns:
            List of action definitions
        """
        if not self.base_url:
            logger.warning("StackStorm URL not configured, returning mock actions")
            return [
                {"ref": "core.local", "name": "local", "pack": "core"},
                {"ref": "core.remote", "name": "remote", "pack": "core"},
                {"ref": "core.http", "name": "http", "pack": "core"},
            ]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/v1/actions"
                params = {}
                if pack:
                    params["pack"] = pack
                
                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                return response.json()
        
        except httpx.RequestError as e:
            logger.error(f"Failed to list actions from StackStorm: {e}")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"StackStorm API error: {e.response.status_code} - {e.response.text}")
            return []
    
    async def execute_action(
        self,
        action_ref: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a StackStorm action.
        
        Args:
            action_ref: Action reference (e.g., "core.local")
            parameters: Action parameters
        
        Returns:
            Execution result
        """
        if not self.base_url:
            logger.warning("StackStorm URL not configured, returning mock execution")
            return {
                "id": "mock-execution-1",
                "action": {"ref": action_ref},
                "parameters": parameters or {},
                "status": "succeeded",
                "result": {"stdout": "Mock execution result"},
            }
        
        try:
            execution_data = {
                "action": action_ref,
                "parameters": parameters or {},
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                url = f"{self.base_url}/api/v1/executions"
                response = await client.post(url, json=execution_data, headers=self.headers)
                response.raise_for_status()
                return response.json()
        
        except httpx.RequestError as e:
            logger.error(f"Failed to execute action in StackStorm: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"StackStorm API error: {e.response.status_code} - {e.response.text}")
            raise
    
    async def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """
        Get execution status and results.
        
        Args:
            execution_id: Execution ID
        
        Returns:
            Execution details
        """
        if not self.base_url:
            logger.warning("StackStorm URL not configured, returning mock execution")
            return {
                "id": execution_id,
                "status": "succeeded",
                "result": {"stdout": "Mock execution result"},
            }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/v1/executions/{execution_id}"
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
        
        except httpx.RequestError as e:
            logger.error(f"Failed to get execution from StackStorm: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"StackStorm API error: {e.response.status_code} - {e.response.text}")
            raise
    
    async def wait_for_execution(self, execution_id: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Wait for execution to complete.
        
        Args:
            execution_id: Execution ID to wait for
            timeout: Maximum time to wait in seconds
        
        Returns:
            Completed execution details
        """
        import asyncio
        
        elapsed = 0
        interval = 5
        
        while elapsed < timeout:
            execution = await self.get_execution(execution_id)
            status = execution.get("status")
            
            if status in ["succeeded", "failed", "timeout", "canceled"]:
                return execution
            
            await asyncio.sleep(interval)
            elapsed += interval
        
        raise TimeoutError(f"Execution {execution_id} did not complete within {timeout} seconds")
    
    async def list_workflows(self) -> List[Dict[str, Any]]:
        """
        List available StackStorm workflows.
        
        Returns:
            List of workflow definitions
        """
        if not self.base_url:
            logger.warning("StackStorm URL not configured, returning mock workflows")
            return [
                {"ref": "sentinelgrid.incident_response", "name": "incident_response", "pack": "sentinelgrid"},
                {"ref": "sentinelgrid.alert_triage", "name": "alert_triage", "pack": "sentinelgrid"},
            ]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/v1/actions"
                params = {"action_type": "action-chain,workflow"}
                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                return response.json()
        
        except httpx.RequestError as e:
            logger.error(f"Failed to list workflows from StackStorm: {e}")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"StackStorm API error: {e.response.status_code} - {e.response.text}")
            return []
    
    async def trigger_workflow(
        self,
        workflow_ref: str,
        parameters: Optional[Dict[str, Any]] = None,
        wait: bool = False,
    ) -> Dict[str, Any]:
        """
        Trigger a StackStorm workflow.
        
        Args:
            workflow_ref: Workflow reference
            parameters: Workflow parameters
            wait: Wait for workflow completion
        
        Returns:
            Workflow execution result
        """
        execution = await self.execute_action(workflow_ref, parameters)
        execution_id = execution.get("id")
        
        if wait and execution_id:
            return await self.wait_for_execution(execution_id)
        
        return execution
    
    async def create_rule(
        self,
        name: str,
        trigger: Dict[str, Any],
        criteria: Dict[str, Any],
        action: Dict[str, Any],
        enabled: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a StackStorm rule.
        
        Args:
            name: Rule name
            trigger: Trigger definition
            criteria: Criteria for rule matching
            action: Action to execute
            enabled: Whether rule is enabled
        
        Returns:
            Created rule
        """
        if not self.base_url:
            logger.warning("StackStorm URL not configured, returning mock rule")
            return {
                "id": "mock-rule-1",
                "name": name,
                "enabled": enabled,
            }
        
        try:
            rule_data = {
                "name": name,
                "trigger": trigger,
                "criteria": criteria,
                "action": action,
                "enabled": enabled,
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/v1/rules"
                response = await client.post(url, json=rule_data, headers=self.headers)
                response.raise_for_status()
                return response.json()
        
        except httpx.RequestError as e:
            logger.error(f"Failed to create rule in StackStorm: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"StackStorm API error: {e.response.status_code} - {e.response.text}")
            raise

