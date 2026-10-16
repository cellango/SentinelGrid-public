"""SOAR/Playbook tools for MCP server."""

import logging
from typing import Dict, Any, List, Optional

from app.core.service_clients import clients
from app.core.security import security_manager

logger = logging.getLogger(__name__)


async def list_playbooks(
    category: Optional[str] = None,
    tenant_id: str = "",
    user_id: str = ""
) -> List[Dict[str, Any]]:
    """
    List available playbooks.
    
    Args:
        category: Filter by category
        tenant_id: Tenant ID
        user_id: User ID
    
    Returns:
        List of playbooks
    """
    await security_manager.authorize_tool_call(
        "list_playbooks", tenant_id, user_id, {"category": category}
    )
    
    try:
        params = {}
        if category:
            params["category"] = category
        
        response = await clients.soar_agent.get(
            "/api/v1/playbooks",
            params=params,
            headers=clients.add_tenant_header(tenant_id)
        )
        response.raise_for_status()
        result = response.json()
        
        await security_manager.audit_tool_call(
            "list_playbooks", tenant_id, user_id, params, result, True
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to list playbooks: {e}")
        await security_manager.audit_tool_call(
            "list_playbooks", tenant_id, user_id, {}, None, False, str(e)
        )
        raise


async def get_playbook(
    playbook_id: str,
    tenant_id: str = "",
    user_id: str = ""
) -> Dict[str, Any]:
    """
    Get playbook details.
    
    Args:
        playbook_id: Playbook ID
        tenant_id: Tenant ID
        user_id: User ID
    
    Returns:
        Playbook details
    """
    await security_manager.authorize_tool_call(
        "get_playbook", tenant_id, user_id, {"playbook_id": playbook_id}
    )
    
    try:
        response = await clients.soar_agent.get(
            f"/api/v1/playbooks/{playbook_id}",
            headers=clients.add_tenant_header(tenant_id)
        )
        response.raise_for_status()
        result = response.json()
        
        await security_manager.audit_tool_call(
            "get_playbook", tenant_id, user_id,
            {"playbook_id": playbook_id}, result, True
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to get playbook: {e}")
        await security_manager.audit_tool_call(
            "get_playbook", tenant_id, user_id,
            {"playbook_id": playbook_id}, None, False, str(e)
        )
        raise


async def run_playbook(
    playbook_id: str,
    params: Dict[str, Any],
    incident_id: Optional[str] = None,
    tenant_id: str = "",
    user_id: str = ""
) -> Dict[str, Any]:
    """
    Execute a playbook.
    
    Args:
        playbook_id: Playbook ID to execute
        params: Playbook parameters
        incident_id: Optional incident ID to associate
        tenant_id: Tenant ID
        user_id: User ID
    
    Returns:
        Execution result
    """
    await security_manager.authorize_tool_call(
        "run_playbook", tenant_id, user_id,
        {"playbook_id": playbook_id, "params": params}
    )
    
    try:
        execution_data = {
            "playbook_id": playbook_id,
            "params": params,
            "incident_id": incident_id
        }
        
        response = await clients.soar_agent.post(
            "/api/v1/playbooks/execute",
            json=execution_data,
            headers=clients.add_tenant_header(tenant_id)
        )
        response.raise_for_status()
        result = response.json()
        
        await security_manager.audit_tool_call(
            "run_playbook", tenant_id, user_id,
            execution_data, result, True
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to run playbook: {e}")
        await security_manager.audit_tool_call(
            "run_playbook", tenant_id, user_id,
            {"playbook_id": playbook_id}, None, False, str(e)
        )
        raise


async def get_playbook_execution(
    execution_id: str,
    tenant_id: str = "",
    user_id: str = ""
) -> Dict[str, Any]:
    """
    Get playbook execution status.
    
    Args:
        execution_id: Execution ID
        tenant_id: Tenant ID
        user_id: User ID
    
    Returns:
        Execution status and results
    """
    await security_manager.authorize_tool_call(
        "get_playbook_execution", tenant_id, user_id,
        {"execution_id": execution_id}
    )
    
    try:
        response = await clients.soar_agent.get(
            f"/api/v1/playbooks/executions/{execution_id}",
            headers=clients.add_tenant_header(tenant_id)
        )
        response.raise_for_status()
        result = response.json()
        
        await security_manager.audit_tool_call(
            "get_playbook_execution", tenant_id, user_id,
            {"execution_id": execution_id}, result, True
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to get playbook execution: {e}")
        await security_manager.audit_tool_call(
            "get_playbook_execution", tenant_id, user_id,
            {"execution_id": execution_id}, None, False, str(e)
        )
        raise

