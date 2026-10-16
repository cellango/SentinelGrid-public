"""
Agent Version Management API

Provides endpoints for retrieving agent version information and download URLs.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import date
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

# Database connection
def get_db():
    """Get database session."""
    if not settings.DB_URL:
        return None  # Return None if DB not configured (use hardcoded data)
    
    engine = create_engine(settings.DB_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# Request/Response Models
# ============================================================================

class AgentVersionResponse(BaseModel):
    """Response for agent version information."""
    agent_type: str
    upstream_tool: str
    upstream_version: str
    sentinelgrid_version: str
    release_date: date
    download_urls: Dict[str, str]  # Platform -> URL mapping
    checksums: Dict[str, str]  # Platform -> SHA256 checksum mapping
    changelog: Optional[str] = None
    is_latest: bool
    is_deprecated: bool = False


class AgentVersionsListResponse(BaseModel):
    """Response for listing all agent versions."""
    versions: List[AgentVersionResponse]
    latest_versions: Dict[str, AgentVersionResponse]  # agent_type -> latest version


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/versions", response_model=AgentVersionsListResponse)
async def get_agent_versions(
    agent_type: Optional[str] = None,
    db = None
):
    """
    Get available agent versions.
    
    Args:
        agent_type: Optional filter by agent type (endpoint_protection, cloud_agent, network_sensor)
    """
    try:
        # For now, return hardcoded data until we populate the database
        # In production, query from agent_versions table
        
        # This is a placeholder - in production, query from database
        versions = []
        latest_versions = {}
        
        # Example: Endpoint Protection (Wazuh-based)
        if not agent_type or agent_type == "endpoint_protection":
            endpoint_version = AgentVersionResponse(
                agent_type="endpoint_protection",
                upstream_tool="wazuh",
                upstream_version="4.8.0",
                sentinelgrid_version="1.0.0",
                release_date=date.today(),
                download_urls={
                    "linux_rpm": "https://agents.sentinelgrid.ai/v1.0.0/linux/rpm/sentinelgrid-agent-1.0.0-1.x86_64.rpm",
                    "linux_deb": "https://agents.sentinelgrid.ai/v1.0.0/linux/deb/sentinelgrid-agent_1.0.0-1_amd64.deb",
                    "windows": "https://agents.sentinelgrid.ai/v1.0.0/windows/sentinelgrid-agent-1.0.0-1.msi",
                    "macos": "https://agents.sentinelgrid.ai/v1.0.0/macos/sentinelgrid-agent-1.0.0-1.pkg"
                },
                checksums={
                    "linux_rpm": "sha256:...",  # Placeholder
                    "linux_deb": "sha256:...",  # Placeholder
                    "windows": "sha256:...",    # Placeholder
                    "macos": "sha256:..."       # Placeholder
                },
                changelog="Initial release based on Wazuh 4.8.0",
                is_latest=True,
                is_deprecated=False
            )
            versions.append(endpoint_version)
            latest_versions["endpoint_protection"] = endpoint_version
        
        return AgentVersionsListResponse(
            versions=versions,
            latest_versions=latest_versions
        )
        
    except Exception as e:
        logger.error(f"Error getting agent versions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get agent versions: {str(e)}")


@router.get("/versions/{agent_type}/latest", response_model=AgentVersionResponse)
async def get_latest_agent_version(
    agent_type: str,
    db = None
):
    """
    Get the latest version of a specific agent type.
    
    Args:
        agent_type: Agent type (endpoint_protection, cloud_agent, network_sensor)
    """
    try:
        # Validate agent type
        valid_types = ["endpoint_protection", "cloud_agent", "network_sensor"]
        if agent_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agent_type. Must be one of: {', '.join(valid_types)}"
            )
        
        # For now, return hardcoded data
        # In production, query from agent_versions table where is_latest=true and agent_type=agent_type
        
        if agent_type == "endpoint_protection":
            return AgentVersionResponse(
                agent_type="endpoint_protection",
                upstream_tool="wazuh",
                upstream_version="4.8.0",
                sentinelgrid_version="1.0.0",
                release_date=date.today(),
                download_urls={
                    "linux_rpm": "https://agents.sentinelgrid.ai/v1.0.0/linux/rpm/sentinelgrid-agent-1.0.0-1.x86_64.rpm",
                    "linux_deb": "https://agents.sentinelgrid.ai/v1.0.0/linux/deb/sentinelgrid-agent_1.0.0-1_amd64.deb",
                    "windows": "https://agents.sentinelgrid.ai/v1.0.0/windows/sentinelgrid-agent-1.0.0-1.msi",
                    "macos": "https://agents.sentinelgrid.ai/v1.0.0/macos/sentinelgrid-agent-1.0.0-1.pkg"
                },
                checksums={
                    "linux_rpm": "sha256:...",
                    "linux_deb": "sha256:...",
                    "windows": "sha256:...",
                    "macos": "sha256:..."
                },
                changelog="Initial release based on Wazuh 4.8.0",
                is_latest=True,
                is_deprecated=False
            )
        
        raise HTTPException(status_code=404, detail=f"Agent type '{agent_type}' not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest agent version: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get latest agent version: {str(e)}")


@router.get("/install/{platform}")
async def get_install_script(
    platform: str,
    agent_type: str = "endpoint_protection"
):
    """
    Get installation script for a specific platform.
    
    Args:
        platform: Platform (linux_rpm, linux_deb, windows, macos)
        agent_type: Agent type (default: endpoint_protection)
    """
    try:
        # Validate platform
        valid_platforms = ["linux_rpm", "linux_deb", "windows", "macos"]
        if platform not in valid_platforms:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid platform. Must be one of: {', '.join(valid_platforms)}"
            )
        
        # Get latest version
        # In production, query from database
        version = "1.0.0"
        base_url = "https://agents.sentinelgrid.ai"
        
        # Generate platform-specific install script
        if platform == "linux_rpm":
            script = f"""#!/bin/bash
# SentinelGrid Endpoint Protection Agent Installer (RPM)

set -e

VERSION="{version}"
DOWNLOAD_URL="{base_url}/v${{VERSION}}/linux/rpm/sentinelgrid-agent-${{VERSION}}-1.x86_64.rpm"

echo "Installing SentinelGrid Endpoint Protection Agent..."

# Download
wget -O /tmp/sentinelgrid-agent.rpm "$DOWNLOAD_URL"

# Verify checksum (if available)
# wget -O /tmp/sentinelgrid-agent.rpm.sha256 "$DOWNLOAD_URL.sha256"
# sha256sum -c /tmp/sentinelgrid-agent.rpm.sha256

# Install
sudo rpm -ivh /tmp/sentinelgrid-agent.rpm

# Configure (requires tenant token)
# sudo /var/ossec/bin/agent-auth -m manager.sentinelgrid.ai -A YOUR_TENANT_TOKEN

# Start service
sudo systemctl enable sentinelgrid-agent
sudo systemctl start sentinelgrid-agent

echo "✅ SentinelGrid Endpoint Protection Agent installed successfully!"
"""
        elif platform == "linux_deb":
            script = f"""#!/bin/bash
# SentinelGrid Endpoint Protection Agent Installer (DEB)

set -e

VERSION="{version}"
DOWNLOAD_URL="{base_url}/v${{VERSION}}/linux/deb/sentinelgrid-agent_${{VERSION}}-1_amd64.deb"

echo "Installing SentinelGrid Endpoint Protection Agent..."

# Download
wget -O /tmp/sentinelgrid-agent.deb "$DOWNLOAD_URL"

# Install
sudo dpkg -i /tmp/sentinelgrid-agent.deb || sudo apt-get install -f -y

# Configure (requires tenant token)
# sudo /var/ossec/bin/agent-auth -m manager.sentinelgrid.ai -A YOUR_TENANT_TOKEN

# Start service
sudo systemctl enable sentinelgrid-agent
sudo systemctl start sentinelgrid-agent

echo "✅ SentinelGrid Endpoint Protection Agent installed successfully!"
"""
        elif platform == "windows":
            script = f"""@echo off
REM SentinelGrid Endpoint Protection Agent Installer (Windows)

set VERSION={version}
set DOWNLOAD_URL={base_url}/v%VERSION%/windows/sentinelgrid-agent-%VERSION%-1.msi

echo Installing SentinelGrid Endpoint Protection Agent...

REM Download
powershell -Command "Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%TEMP%\\sentinelgrid-agent.msi'"

REM Install
msiexec /i "%TEMP%\\sentinelgrid-agent.msi" /quiet /norestart

echo SentinelGrid Endpoint Protection Agent installed successfully!
"""
        else:  # macos
            script = f"""#!/bin/bash
# SentinelGrid Endpoint Protection Agent Installer (macOS)

set -e

VERSION="{version}"
DOWNLOAD_URL="{base_url}/v${{VERSION}}/macos/sentinelgrid-agent-${{VERSION}}-1.pkg"

echo "Installing SentinelGrid Endpoint Protection Agent..."

# Download
curl -L -o /tmp/sentinelgrid-agent.pkg "$DOWNLOAD_URL"

# Install
sudo installer -pkg /tmp/sentinelgrid-agent.pkg -target /

echo "✅ SentinelGrid Endpoint Protection Agent installed successfully!"
"""
        
        return {
            "platform": platform,
            "agent_type": agent_type,
            "version": version,
            "script": script,
            "content_type": "text/plain" if platform != "windows" else "text/x-msdos-batch"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating install script: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate install script: {str(e)}")

