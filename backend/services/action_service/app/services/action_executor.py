"""Action executor service for automated security actions."""

import logging
from typing import Dict, Any, List, Optional, Union
from uuid import UUID
from datetime import datetime
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class ActionStatus:
    """Action status constants."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionExecutor:
    """Service for executing automated security actions."""
    
    def __init__(self):
        self.iam_agent_url = settings.IAM_AGENT_URL
        self.ticketing_service_url = settings.TICKETING_SERVICE_URL
        self.internal_token = settings.INTERNAL_SERVICE_TOKEN
        self.require_approval = settings.REQUIRE_APPROVAL
    
    async def execute_action(
        self,
        action_type: str,
        action_params: Dict[str, Any],
        ticket_id: Optional[Union[UUID, str]] = None,
        tenant_id: Optional[Union[UUID, str]] = None,
        user_id: Optional[str] = None,
        requires_approval: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Execute a security action.
        
        Args:
            action_type: Type of action (iam_disable_user, endpoint_quarantine, network_block_ip, etc.)
            action_params: Action parameters
            ticket_id: Associated ticket ID
            tenant_id: Tenant ID
            user_id: User requesting the action
            requires_approval: Override default approval requirement
        
        Returns:
            Action execution result
        """
        requires_approval = requires_approval if requires_approval is not None else self.require_approval
        
        # Check if approval is required
        if requires_approval:
            return {
                "status": ActionStatus.PENDING,
                "action_id": f"action-{datetime.utcnow().timestamp()}",
                "message": "Action requires approval",
                "approval_required": True
            }
        
        # Execute action based on type
        try:
            if action_type.startswith("iam_"):
                result = await self._execute_iam_action(action_type, action_params, tenant_id)
            elif action_type.startswith("endpoint_"):
                result = await self._execute_endpoint_action(action_type, action_params, tenant_id)
            elif action_type.startswith("network_"):
                result = await self._execute_network_action(action_type, action_params, tenant_id)
            elif action_type.startswith("email_"):
                result = await self._execute_email_action(action_type, action_params, tenant_id)
            elif action_type.startswith("cloud_"):
                result = await self._execute_cloud_action(action_type, action_params, tenant_id)
            else:
                raise ValueError(f"Unknown action type: {action_type}")
            
            # Update ticket if provided
            if ticket_id and result.get("status") == ActionStatus.COMPLETED:
                await self._update_ticket_with_action(ticket_id, action_type, result, tenant_id)
            
            return result
        
        except Exception as e:
            logger.error(f"Error executing action {action_type}: {e}")
            return {
                "status": ActionStatus.FAILED,
                "error": str(e),
                "action_type": action_type
            }
    
    async def _execute_iam_action(
        self,
        action_type: str,
        action_params: Dict[str, Any],
        tenant_id: Optional[Union[UUID, str]]
    ) -> Dict[str, Any]:
        """Execute IAM-related actions."""
        user_id = action_params.get("user_id")
        
        if not user_id:
            raise ValueError("user_id is required for IAM actions")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.internal_token}",
                    "Content-Type": "application/json"
                }
                
                if action_type == "iam_disable_user":
                    url = f"{self.iam_agent_url}/api/v1/users/{user_id}/disable"
                    response = await client.post(url, headers=headers)
                    response.raise_for_status()
                    return {
                        "status": ActionStatus.COMPLETED,
                        "action_type": action_type,
                        "user_id": user_id,
                        "result": response.json()
                    }
                
                elif action_type == "iam_reset_password":
                    url = f"{self.iam_agent_url}/api/v1/users/{user_id}/reset-password"
                    response = await client.post(url, headers=headers)
                    response.raise_for_status()
                    return {
                        "status": ActionStatus.COMPLETED,
                        "action_type": action_type,
                        "user_id": user_id,
                        "result": response.json()
                    }
                
                elif action_type == "iam_revoke_sessions":
                    url = f"{self.iam_agent_url}/api/v1/users/{user_id}/revoke-sessions"
                    response = await client.post(url, headers=headers)
                    response.raise_for_status()
                    return {
                        "status": ActionStatus.COMPLETED,
                        "action_type": action_type,
                        "user_id": user_id,
                        "result": response.json()
                    }
                
                else:
                    raise ValueError(f"Unknown IAM action type: {action_type}")
        
        except httpx.RequestError as e:
            logger.error(f"Error executing IAM action: {e}")
            raise
    
    async def _execute_endpoint_action(
        self,
        action_type: str,
        action_params: Dict[str, Any],
        tenant_id: Optional[Union[UUID, str]]
    ) -> Dict[str, Any]:
        """Execute endpoint-related actions."""
        # Placeholder - would integrate with endpoint management system
        asset_id = action_params.get("asset_id")
        
        if action_type == "endpoint_quarantine":
            return {
                "status": ActionStatus.COMPLETED,
                "action_type": action_type,
                "asset_id": asset_id,
                "message": "Endpoint quarantined (placeholder)"
            }
        
        elif action_type == "endpoint_isolate":
            return {
                "status": ActionStatus.COMPLETED,
                "action_type": action_type,
                "asset_id": asset_id,
                "message": "Endpoint isolated (placeholder)"
            }
        
        else:
            raise ValueError(f"Unknown endpoint action type: {action_type}")
    
    async def _execute_network_action(
        self,
        action_type: str,
        action_params: Dict[str, Any],
        tenant_id: Optional[Union[UUID, str]]
    ) -> Dict[str, Any]:
        """Execute network-related actions."""
        # Placeholder - would integrate with firewall/network management
        ip_address = action_params.get("ip_address")
        
        if action_type == "network_block_ip":
            return {
                "status": ActionStatus.COMPLETED,
                "action_type": action_type,
                "ip_address": ip_address,
                "message": "IP blocked (placeholder)"
            }
        
        elif action_type == "network_add_firewall_rule":
            return {
                "status": ActionStatus.COMPLETED,
                "action_type": action_type,
                "rule": action_params.get("rule"),
                "message": "Firewall rule added (placeholder)"
            }
        
        else:
            raise ValueError(f"Unknown network action type: {action_type}")
    
    async def _execute_email_action(
        self,
        action_type: str,
        action_params: Dict[str, Any],
        tenant_id: Optional[Union[UUID, str]]
    ) -> Dict[str, Any]:
        """Execute email-related actions."""
        # Placeholder - would integrate with email security system
        email = action_params.get("email")
        
        if action_type == "email_quarantine":
            return {
                "status": ActionStatus.COMPLETED,
                "action_type": action_type,
                "email": email,
                "message": "Email quarantined (placeholder)"
            }
        
        else:
            raise ValueError(f"Unknown email action type: {action_type}")
    
    async def _execute_cloud_action(
        self,
        action_type: str,
        action_params: Dict[str, Any],
        tenant_id: Optional[Union[UUID, str]]
    ) -> Dict[str, Any]:
        """Execute cloud-related actions."""
        # Placeholder - would integrate with cloud provider APIs
        resource_id = action_params.get("resource_id")
        
        if action_type == "cloud_stop_instance":
            return {
                "status": ActionStatus.COMPLETED,
                "action_type": action_type,
                "resource_id": resource_id,
                "message": "Cloud instance stopped (placeholder)"
            }
        
        else:
            raise ValueError(f"Unknown cloud action type: {action_type}")
    
    async def _update_ticket_with_action(
        self,
        ticket_id: Union[UUID, str],
        action_type: str,
        action_result: Dict[str, Any],
        tenant_id: Optional[Union[UUID, str]]
    ):
        """Update ticket with action execution result."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.internal_token}",
                    "Content-Type": "application/json"
                }
                url = f"{self.ticketing_service_url}/api/v1/tickets/{ticket_id}"
                params = {"tenant_id": str(tenant_id)} if tenant_id else {}
                
                # Add action to ticket timeline
                payload = {
                    "timeline_data": {
                        "action": {
                            "type": action_type,
                            "status": action_result.get("status"),
                            "timestamp": datetime.utcnow().isoformat(),
                            "result": action_result
                        }
                    }
                }
                
                response = await client.patch(url, headers=headers, json=payload, params=params)
                response.raise_for_status()
        
        except Exception as e:
            logger.warning(f"Could not update ticket with action: {e}")

