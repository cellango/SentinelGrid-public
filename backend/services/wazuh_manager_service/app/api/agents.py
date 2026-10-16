"""Agent management API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.database import get_db, get_tenant_session
from app.core.security import get_current_tenant
from app.core.config import settings
from app.services.agent_service import AgentService
from app.services.wazuh_api_client import WazuhAPIClient
from app.models.agent import (
    AgentRegisterRequest,
    AgentRegisterResponse,
    AgentListResponse,
    AgentDetailsResponse,
    AgentRestartResponse,
    AgentDeleteResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["agents"])


def get_wazuh_client() -> WazuhAPIClient:
    """Get Wazuh API client."""
    return WazuhAPIClient(
        base_url=settings.WAZUH_MANAGER_URL,
        username=settings.WAZUH_API_USERNAME,
        password=settings.WAZUH_API_PASSWORD,
        verify_tls=settings.UPSTREAM_TLS_VERIFY,
    )


def get_agent_service(
    db: Session = Depends(get_tenant_session),
    wazuh_client: WazuhAPIClient = Depends(get_wazuh_client)
) -> AgentService:
    """Get agent service."""
    return AgentService(db, wazuh_client)


@router.post("/agents/register", response_model=AgentRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_agent(
    request: AgentRegisterRequest,
    tenant_id: UUID = Depends(get_current_tenant),
    service: AgentService = Depends(get_agent_service)
):
    """
    Register a new SentinelGrid Endpoint Protection agent.
    
    The tenant_id is automatically extracted from the user's JWT token.
    The agent will be labeled with this tenant_id in the Endpoint Manager,
    ensuring all events are properly isolated.
    
    Returns:
        Agent registration details including authentication key and installation instructions
    """
    try:
        result = await service.register_agent(
            tenant_id=tenant_id,
            hostname=request.hostname,
            ip_address=request.ip_address,
            os_platform=request.os_platform,
            os_version=request.os_version
        )
        return result
    except Exception as e:
        logger.error(f"Agent registration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register agent: {str(e)}"
        )


@router.get("/agents", response_model=AgentListResponse)
async def list_agents(
    tenant_id: UUID = Depends(get_current_tenant),
    service: AgentService = Depends(get_agent_service)
):
    """
    List all endpoint agents for the current tenant.
    
    Only returns agents that belong to the authenticated user's tenant.
    """
    try:
        agents = await service.list_agents(tenant_id)
        return {
            "agents": agents,
            "count": len(agents)
        }
    except Exception as e:
        logger.error(f"Failed to list agents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list agents: {str(e)}"
        )


@router.get("/agents/{agent_id}", response_model=AgentDetailsResponse)
async def get_agent(
    agent_id: str,
    tenant_id: UUID = Depends(get_current_tenant),
    service: AgentService = Depends(get_agent_service)
):
    """
    Get detailed information about a specific agent.
    
    Returns 404 if agent not found or doesn't belong to current tenant.
    """
    try:
        agent = await service.get_agent_details(tenant_id, agent_id)
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
        
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent details: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent details: {str(e)}"
        )


@router.delete("/agents/{agent_id}", response_model=AgentDeleteResponse)
async def delete_agent(
    agent_id: str,
    tenant_id: UUID = Depends(get_current_tenant),
    service: AgentService = Depends(get_agent_service)
):
    """
    Delete an endpoint agent.
    
    Removes the agent from both the Endpoint Manager and the database.
    Only allows deletion of agents belonging to the current tenant.
    """
    try:
        success = await service.delete_agent(tenant_id, agent_id)
        return {
            "success": success,
            "agent_id": agent_id,
            "message": "Agent deleted successfully"
        }
    except Exception as e:
        logger.error(f"Failed to delete agent: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete agent: {str(e)}"
        )


@router.post("/agents/{agent_id}/restart", response_model=AgentRestartResponse)
async def restart_agent(
    agent_id: str,
    tenant_id: UUID = Depends(get_current_tenant),
    service: AgentService = Depends(get_agent_service)
):
    """
    Restart an endpoint agent.
    
    Sends a restart command to the agent via the Endpoint Manager.
    Only allows restarting agents belonging to the current tenant.
    """
    try:
        result = await service.restart_agent(tenant_id, agent_id)
        return result
    except Exception as e:
        logger.error(f"Failed to restart agent: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart agent: {str(e)}"
        )
