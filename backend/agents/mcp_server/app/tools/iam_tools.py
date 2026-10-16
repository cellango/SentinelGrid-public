"""IAM tools for MCP server."""

import logging
from typing import Dict, Any, List, Optional

from app.core.service_clients import clients
from app.core.security import security_manager

logger = logging.getLogger(__name__)


async def get_user(
    user_id: str,
    tenant_id: str = "",
    requesting_user_id: str = ""
) -> Dict[str, Any]:
    """Get user details from IAM."""
    await security_manager.authorize_tool_call(
        "get_user", tenant_id, requesting_user_id, {"user_id": user_id}
    )
    
    try:
        response = await clients.iam_agent.get(
            f"/api/v1/users/{user_id}",
            headers=clients.add_tenant_header(tenant_id)
        )
        response.raise_for_status()
        result = response.json()
        
        await security_manager.audit_tool_call(
            "get_user", tenant_id, requesting_user_id,
            {"user_id": user_id}, result, True
        )
        
        return result
    except Exception as e:
        logger.error(f"Failed to get user: {e}")
        await security_manager.audit_tool_call(
            "get_user", tenant_id, requesting_user_id,
            {"user_id": user_id}, None, False, str(e)
        )
        raise


async def lock_account(
    user_id: str,
    reason: str,
    tenant_id: str = "",
    requesting_user_id: str = ""
) -> Dict[str, Any]:
    """Lock user account (HIGH RISK - requires approval)."""
    await security_manager.authorize_tool_call(
        "lock_account", tenant_id, requesting_user_id,
        {"user_id": user_id, "reason": reason}
    )
    
    try:
        response = await clients.iam_agent.post(
            f"/api/v1/users/{user_id}/lock",
            json={"reason": reason},
            headers=clients.add_tenant_header(tenant_id)
        )
        response.raise_for_status()
        result = response.json()
        
        await security_manager.audit_tool_call(
            "lock_account", tenant_id, requesting_user_id,
            {"user_id": user_id, "reason": reason}, result, True
        )
        
        return result
    except Exception as e:
        logger.error(f"Failed to lock account: {e}")
        await security_manager.audit_tool_call(
            "lock_account", tenant_id, requesting_user_id,
            {"user_id": user_id}, None, False, str(e)
        )
        raise

