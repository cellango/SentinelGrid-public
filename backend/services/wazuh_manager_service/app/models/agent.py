"""Agent data models."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class AgentRegisterRequest(BaseModel):
    """Request to register a new endpoint agent."""
    hostname: str = Field(..., description="Agent hostname", min_length=1, max_length=255)
    ip_address: Optional[str] = Field(None, description="Agent IP address")
    os_platform: Optional[str] = Field(None, description="Operating system: linux, windows, macos")
    os_version: Optional[str] = Field(None, description="OS version (e.g., Ubuntu 22.04, Windows Server 2022)")


class AgentRegisterResponse(BaseModel):
    """Response for agent registration."""
    success: bool
    agent_id: str
    agent_key: str
    manager_address: str
    manager_port: int
    tenant_id: str
    instructions: Dict[str, str]


class AgentListItem(BaseModel):
    """Agent list item."""
    id: str
    wazuh_agent_id: str
    name: str
    ip: Optional[str]
    os: Optional[str]
    status: str  # active, disconnected, never_connected, pending
    last_seen: Optional[str]
    registered: str
    version: Optional[str]


class AgentListResponse(BaseModel):
    """Response for listing agents."""
    agents: list[AgentListItem]
    count: int


class AgentDetailsResponse(BaseModel):
    """Detailed agent information."""
    id: str
    wazuh_agent_id: str
    name: str
    ip: Optional[str]
    os: Optional[Dict[str, Any]]
    version: Optional[str]
    status: str
    last_keepalive: Optional[str]
    registration_date: str
    labels: Dict[str, str]
    groups: list[str]


class AgentRestartResponse(BaseModel):
    """Response for agent restart."""
    success: bool
    agent_id: str
    message: str


class AgentDeleteResponse(BaseModel):
    """Response for agent deletion."""
    success: bool
    agent_id: str
    message: str

