"""API endpoints for action execution."""

import logging
from typing import Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel

from app.services.action_executor import ActionExecutor

logger = logging.getLogger(__name__)

router = APIRouter()
action_executor = ActionExecutor()


class ActionRequest(BaseModel):
    """Action execution request."""
    action_type: str
    action_params: Dict[str, Any]
    ticket_id: Optional[str] = None
    requires_approval: Optional[bool] = None


@router.post("/execute")
async def execute_action(
    request: ActionRequest,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    user_id: str = Query(..., description="User ID requesting action")
):
    """
    Execute a security action.
    
    Args:
        request: Action execution request
        tenant_id: Tenant ID
        user_id: User ID requesting action
    
    Returns:
        Action execution result
    """
    try:
        result = await action_executor.execute_action(
            action_type=request.action_type,
            action_params=request.action_params,
            ticket_id=request.ticket_id,
            tenant_id=tenant_id,
            user_id=user_id,
            requires_approval=request.requires_approval
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing action: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/types")
async def get_action_types():
    """Get available action types."""
    return {
        "action_types": [
            {
                "id": "iam_disable_user",
                "name": "Disable User",
                "category": "IAM",
                "description": "Disable a user account",
                "parameters": {"user_id": "string (required)"}
            },
            {
                "id": "iam_reset_password",
                "name": "Reset Password",
                "category": "IAM",
                "description": "Force password reset for a user",
                "parameters": {"user_id": "string (required)"}
            },
            {
                "id": "iam_revoke_sessions",
                "name": "Revoke Sessions",
                "category": "IAM",
                "description": "Revoke all active sessions for a user",
                "parameters": {"user_id": "string (required)"}
            },
            {
                "id": "endpoint_quarantine",
                "name": "Quarantine Endpoint",
                "category": "Endpoint",
                "description": "Quarantine an endpoint",
                "parameters": {"asset_id": "string (required)"}
            },
            {
                "id": "endpoint_isolate",
                "name": "Isolate Endpoint",
                "category": "Endpoint",
                "description": "Isolate an endpoint from the network",
                "parameters": {"asset_id": "string (required)"}
            },
            {
                "id": "network_block_ip",
                "name": "Block IP Address",
                "category": "Network",
                "description": "Block an IP address at the firewall",
                "parameters": {"ip_address": "string (required)"}
            },
            {
                "id": "network_add_firewall_rule",
                "name": "Add Firewall Rule",
                "category": "Network",
                "description": "Add a firewall rule",
                "parameters": {"rule": "object (required)"}
            },
            {
                "id": "email_quarantine",
                "name": "Quarantine Email",
                "category": "Email",
                "description": "Quarantine an email",
                "parameters": {"email": "string (required)"}
            },
            {
                "id": "cloud_stop_instance",
                "name": "Stop Cloud Instance",
                "category": "Cloud",
                "description": "Stop a cloud instance",
                "parameters": {"resource_id": "string (required)"}
            }
        ]
    }

