"""Observable enrichment tools for MCP server."""

import logging
from typing import Dict, Any, List, Optional

from app.core.service_clients import clients
from app.core.security import security_manager

logger = logging.getLogger(__name__)


async def get_observable(
    observable_id: str,
    tenant_id: str = "",
    user_id: str = ""
) -> Dict[str, Any]:
    """Get enriched observable."""
    await security_manager.authorize_tool_call(
        "get_observable", tenant_id, user_id, {"observable_id": observable_id}
    )
    
    try:
        response = await clients.observables_service.get(
            f"/observables/{observable_id}",
            headers=clients.add_tenant_header(tenant_id)
        )
        response.raise_for_status()
        result = response.json()
        
        await security_manager.audit_tool_call(
            "get_observable", tenant_id, user_id,
            {"observable_id": observable_id}, result, True
        )
        
        return result
    except Exception as e:
        logger.error(f"Failed to get observable: {e}")
        raise


async def search_observables(
    observable_type: Optional[str] = None,
    value: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    tenant_id: str = "",
    user_id: str = ""
) -> List[Dict[str, Any]]:
    """Search observables."""
    await security_manager.authorize_tool_call(
        "search_observables", tenant_id, user_id,
        {"type": observable_type, "value": value}
    )
    
    try:
        search_params = {
            "observable_type": observable_type,
            "value": value,
            "enrichment_status": status,
            "limit": limit
        }
        
        response = await clients.observables_service.post(
            "/observables/search",
            json=search_params,
            headers=clients.add_tenant_header(tenant_id)
        )
        response.raise_for_status()
        result = response.json()
        
        await security_manager.audit_tool_call(
            "search_observables", tenant_id, user_id,
            search_params, result, True
        )
        
        return result
    except Exception as e:
        logger.error(f"Failed to search observables: {e}")
        raise

