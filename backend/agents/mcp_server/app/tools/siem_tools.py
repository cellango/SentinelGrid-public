"""SIEM tools for MCP server."""

import logging
from typing import Dict, Any, List, Optional

from app.core.service_clients import clients
from app.core.security import security_manager

logger = logging.getLogger(__name__)


async def search_logs(
    query: str,
    time_range: str = "1h",
    source: Optional[str] = None,
    limit: int = 100,
    tenant_id: str = "",
    user_id: str = ""
) -> Dict[str, Any]:
    """
    Search logs in OpenSearch via SIEM agent.
    
    Args:
        query: OpenSearch query string
        time_range: Time range (e.g., "1h", "24h", "7d")
        source: Optional source filter
        limit: Maximum number of results
        tenant_id: Tenant ID
        user_id: User ID making the request
    
    Returns:
        Search results with logs
    """
    # Authorize
    await security_manager.authorize_tool_call(
        "search_logs", tenant_id, user_id,
        {"query": query, "time_range": time_range}
    )
    
    try:
        # Call SIEM agent
        response = await clients.siem_agent.post(
            "/api/v1/logs/search",
            json={
                "query": query,
                "time_range": time_range,
                "source": source,
                "limit": limit
            },
            headers=clients.add_tenant_header(tenant_id)
        )
        response.raise_for_status()
        result = response.json()
        
        # Audit
        await security_manager.audit_tool_call(
            "search_logs", tenant_id, user_id,
            {"query": query, "time_range": time_range},
            result, True
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to search logs: {e}")
        await security_manager.audit_tool_call(
            "search_logs", tenant_id, user_id,
            {"query": query}, None, False, str(e)
        )
        raise


async def get_detections(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    tenant_id: str = "",
    user_id: str = ""
) -> List[Dict[str, Any]]:
    """
    Get detection events from detection service.
    
    Args:
        severity: Filter by severity (critical, high, medium, low)
        status: Filter by status (new, in_progress, resolved)
        limit: Maximum number of results
        tenant_id: Tenant ID
        user_id: User ID
    
    Returns:
        List of detection events
    """
    await security_manager.authorize_tool_call(
        "get_detections", tenant_id, user_id,
        {"severity": severity, "status": status}
    )
    
    try:
        params = {"limit": limit}
        if severity:
            params["severity"] = severity
        if status:
            params["status"] = status
        
        response = await clients.detection_service.get(
            "/api/v1/detections",
            params=params,
            headers=clients.add_tenant_header(tenant_id)
        )
        response.raise_for_status()
        result = response.json()
        
        await security_manager.audit_tool_call(
            "get_detections", tenant_id, user_id,
            params, result, True
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to get detections: {e}")
        await security_manager.audit_tool_call(
            "get_detections", tenant_id, user_id,
            {"severity": severity}, None, False, str(e)
        )
        raise


async def get_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    assignee: Optional[str] = None,
    limit: int = 50,
    tenant_id: str = "",
    user_id: str = ""
) -> List[Dict[str, Any]]:
    """
    List security incidents.
    
    Args:
        status: Filter by status
        severity: Filter by severity
        assignee: Filter by assignee
        limit: Maximum results
        tenant_id: Tenant ID
        user_id: User ID
    
    Returns:
        List of incidents
    """
    await security_manager.authorize_tool_call(
        "get_incidents", tenant_id, user_id,
        {"status": status, "severity": severity}
    )
    
    try:
        params = {"limit": limit}
        if status:
            params["status"] = status
        if severity:
            params["severity"] = severity
        if assignee:
            params["assignee"] = assignee
        
        response = await clients.ticketing_agent.get(
            "/api/v1/incidents",
            params=params,
            headers=clients.add_tenant_header(tenant_id)
        )
        response.raise_for_status()
        result = response.json()
        
        await security_manager.audit_tool_call(
            "get_incidents", tenant_id, user_id,
            params, result, True
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to get incidents: {e}")
        await security_manager.audit_tool_call(
            "get_incidents", tenant_id, user_id,
            params, None, False, str(e)
        )
        raise


async def create_incident(
    title: str,
    description: str,
    severity: str,
    observables: Optional[List[str]] = None,
    tenant_id: str = "",
    user_id: str = ""
) -> Dict[str, Any]:
    """
    Create a new security incident.
    
    Args:
        title: Incident title
        description: Incident description
        severity: Severity level
        observables: List of observable IDs to attach
        tenant_id: Tenant ID
        user_id: User ID
    
    Returns:
        Created incident
    """
    await security_manager.authorize_tool_call(
        "create_incident", tenant_id, user_id,
        {"title": title, "severity": severity}
    )
    
    try:
        incident_data = {
            "title": title,
            "description": description,
            "severity": severity,
            "observables": observables or []
        }
        
        response = await clients.ticketing_agent.post(
            "/api/v1/incidents",
            json=incident_data,
            headers=clients.add_tenant_header(tenant_id)
        )
        response.raise_for_status()
        result = response.json()
        
        await security_manager.audit_tool_call(
            "create_incident", tenant_id, user_id,
            incident_data, result, True
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to create incident: {e}")
        await security_manager.audit_tool_call(
            "create_incident", tenant_id, user_id,
            {"title": title}, None, False, str(e)
        )
        raise

