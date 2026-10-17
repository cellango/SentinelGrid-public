"""Agent registration and management service."""

import logging
from app.core.security import require_owned_wazuh_operation
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.wazuh_api_client import WazuhAPIClient

logger = logging.getLogger(__name__)


class AgentService:
    """
    Service for managing SentinelGrid Endpoint Protection agents.

    Handles agent registration, lifecycle management, and tenant isolation.
    """

    def __init__(self, db: Session, wazuh_client: WazuhAPIClient):
        """
        Initialize agent service.

        Args:
            db: Database session
            wazuh_client: Wazuh API client
        """
        self.db = db
        self.wazuh = wazuh_client

    async def register_agent(
        self,
        tenant_id: UUID,
        hostname: str,
        ip_address: Optional[str] = None,
        os_platform: Optional[str] = None,
        os_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Register a new endpoint agent with multi-tenant isolation.

        Flow:
        1. Create agent in Wazuh Manager
        2. Set tenant_id label on agent (server-side, CRITICAL for isolation)
        3. Get agent authentication key
        4. Store agent record in database
        5. Return registration info for agent installation

        Args:
            tenant_id: Globally unique tenant ID (extracted from JWT)
            hostname: Agent hostname
            ip_address: Agent IP (optional)
            os_platform: OS type (linux, windows, macos)
            os_version: OS version string

        Returns:
            Agent registration details including auth key and instructions
        """
        require_owned_wazuh_operation()
        try:
            # Step 1: Create agent in Wazuh Manager
            logger.info(
                f"Creating agent in Wazuh Manager: {hostname} for tenant {tenant_id}"
            )
            wazuh_response = await self.wazuh.create_agent(name=hostname, ip=ip_address)

            wazuh_agent_id = wazuh_response["data"]["id"]  # e.g., "001"
            logger.info(f"Agent created in Wazuh Manager with ID: {wazuh_agent_id}")

            # Step 2: CRITICAL - Set tenant_id as agent label (server-side)
            # This label will be injected into every event from this agent
            logger.info(f"Setting tenant_id label on agent {wazuh_agent_id}")
            await self.wazuh.update_agent_labels(
                agent_id=wazuh_agent_id,
                labels={
                    "tenant_id": str(tenant_id),
                    "registered_at": datetime.utcnow().isoformat(),
                    "registered_via": "sentinelgrid_api",
                    "platform": os_platform or "unknown",
                },
            )
            logger.info(f"Labels set successfully: tenant_id={tenant_id}")

            # Step 3: Get agent authentication key
            logger.info(f"Retrieving agent authentication key")
            agent_key_response = await self.wazuh.get_agent_key(wazuh_agent_id)
            agent_key = agent_key_response["data"]["key"]

            # Step 4: Store in database
            logger.info(f"Storing agent record in database")
            self.db.execute(
                text("""
                    INSERT INTO endpoint_agents (
                        id, tenant_id, wazuh_agent_id, agent_name,
                        ip_address, os_platform, os_version,
                        status, registration_date, created_at, updated_at
                    )
                    VALUES (
                        gen_random_uuid(), :tenant_id, :wazuh_agent_id, :agent_name,
                        :ip_address, :os_platform, :os_version,
                        'pending', :registration_date, :created_at, :updated_at
                    )
                """),
                {
                    "tenant_id": str(tenant_id),
                    "wazuh_agent_id": wazuh_agent_id,
                    "agent_name": hostname,
                    "ip_address": ip_address,
                    "os_platform": os_platform,
                    "os_version": os_version,
                    "registration_date": datetime.utcnow(),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                },
            )
            self.db.commit()
            logger.info(
                f"Agent {wazuh_agent_id} registered successfully for tenant {tenant_id}"
            )

            # Step 5: Return registration info with platform-specific instructions
            return {
                "success": True,
                "agent_id": wazuh_agent_id,
                "agent_key": agent_key,
                "manager_address": "manager.sentinelgrid.ai",  # Production DNS (or localhost for dev)
                "manager_port": 1514,
                "tenant_id": str(tenant_id),
                "instructions": {
                    "linux": (
                        f"# Import agent key\n"
                        f"echo '{agent_key}' | sudo /var/ossec/bin/manage_agents -i\n\n"
                        f"# Configure manager address\n"
                        f"sudo sed -i 's/<address>MANAGER_IP<\\/address>/<address>manager.sentinelgrid.ai<\\/address>/' /var/ossec/etc/ossec.conf\n\n"
                        f"# Start agent\n"
                        f"sudo systemctl enable sentinelgrid-agent\n"
                        f"sudo systemctl start sentinelgrid-agent\n\n"
                        f"# Check status\n"
                        f"sudo systemctl status sentinelgrid-agent"
                    ),
                    "windows": (
                        f"# PowerShell commands:\n"
                        f"# 1. Import key to C:\\Program Files\\ossec-agent\\client.keys\n"
                        f"# 2. Edit C:\\Program Files\\ossec-agent\\ossec.conf - set manager address\n"
                        f"# 3. Restart-Service -Name SentinelGridAgent"
                    ),
                    "macos": (
                        f"# Import agent key\n"
                        f"echo '{agent_key}' | sudo /Library/Ossec/bin/manage_agents -i\n\n"
                        f"# Configure manager\n"
                        f"sudo sed -i '' 's/<address>MANAGER_IP<\\/address>/<address>manager.sentinelgrid.ai<\\/address>/' /Library/Ossec/etc/ossec.conf\n\n"
                        f"# Start agent\n"
                        f"sudo launchctl load /Library/LaunchDaemons/com.sentinelgrid.agent.plist"
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Failed to register agent: {e}", exc_info=True)
            self.db.rollback()
            raise Exception(f"Agent registration failed: {str(e)}")

    async def list_agents(self, tenant_id: UUID) -> List[Dict[str, Any]]:
        """
        List all agents for a specific tenant (tenant-isolated).

        Args:
            tenant_id: Tenant ID for filtering

        Returns:
            List of agent details
        """
        require_owned_wazuh_operation()
        # Query database for tenant's agents
        result = self.db.execute(
            text("""
                SELECT
                    id, wazuh_agent_id, agent_name, ip_address,
                    os_platform, os_version, status, last_keepalive,
                    registration_date, agent_version
                FROM endpoint_agents
                WHERE tenant_id = :tenant_id
                ORDER BY registration_date DESC
            """),
            {"tenant_id": str(tenant_id)},
        )

        agents = []
        for row in result:
            # Enrich with live data from Wazuh Manager
            try:
                wazuh_data = await self.wazuh.get_agent(row.wazuh_agent_id)
                agent_status = wazuh_data["data"]["status"]
                last_keepalive = wazuh_data["data"].get("lastKeepAlive")
                wazuh_version = wazuh_data["data"].get("version")
            except Exception as e:
                logger.warning(
                    f"Could not fetch live data for agent {row.wazuh_agent_id}: {e}"
                )
                agent_status = "unknown"
                last_keepalive = None
                wazuh_version = None

            agents.append(
                {
                    "id": str(row.id),
                    "wazuh_agent_id": row.wazuh_agent_id,
                    "name": row.agent_name,
                    "ip": row.ip_address,
                    "os": f"{row.os_platform} {row.os_version}"
                    if row.os_platform
                    else None,
                    "status": agent_status,
                    "last_seen": last_keepalive
                    or (row.last_keepalive.isoformat() if row.last_keepalive else None),
                    "registered": row.registration_date.isoformat(),
                    "version": wazuh_version or row.agent_version,
                }
            )

        return agents

    async def get_agent_details(
        self, tenant_id: UUID, wazuh_agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific agent (tenant-isolated).

        Args:
            tenant_id: Tenant ID for authorization
            wazuh_agent_id: Wazuh agent ID

        Returns:
            Agent details or None if not found/unauthorized
        """
        require_owned_wazuh_operation()
        # Verify agent belongs to tenant
        result = self.db.execute(
            text("""
                SELECT id, agent_name, ip_address, os_platform, os_version,
                       status, registration_date, agent_version
                FROM endpoint_agents
                WHERE tenant_id = :tenant_id AND wazuh_agent_id = :wazuh_agent_id
            """),
            {"tenant_id": str(tenant_id), "wazuh_agent_id": wazuh_agent_id},
        ).first()

        if not result:
            return None

        # Get live data from Wazuh Manager
        try:
            wazuh_data = await self.wazuh.get_agent(wazuh_agent_id)
            agent_info = wazuh_data["data"]

            return {
                "id": str(result.id),
                "wazuh_agent_id": wazuh_agent_id,
                "name": result.agent_name,
                "ip": result.ip_address,
                "os": agent_info.get("os"),
                "version": agent_info.get("version"),
                "status": agent_info.get("status"),
                "last_keepalive": agent_info.get("lastKeepAlive"),
                "registration_date": result.registration_date.isoformat(),
                "labels": agent_info.get("labels", {}),
                "groups": agent_info.get("group", []),
            }
        except Exception as e:
            logger.error(f"Failed to get agent details from Wazuh: {e}")
            return None

    async def delete_agent(self, tenant_id: UUID, wazuh_agent_id: str) -> bool:
        """
        Delete an agent (tenant-isolated).

        Args:
            tenant_id: Tenant ID for authorization
            wazuh_agent_id: Wazuh agent ID

        Returns:
            True if deleted successfully
        """
        require_owned_wazuh_operation()
        # Verify agent belongs to tenant
        result = self.db.execute(
            text("""
                SELECT id FROM endpoint_agents
                WHERE tenant_id = :tenant_id AND wazuh_agent_id = :wazuh_agent_id
            """),
            {"tenant_id": str(tenant_id), "wazuh_agent_id": wazuh_agent_id},
        ).first()

        if not result:
            raise Exception("Agent not found or access denied")

        # Delete from Wazuh Manager
        try:
            await self.wazuh.delete_agent(wazuh_agent_id)
        except Exception as e:
            logger.error(f"Failed to delete agent from Wazuh Manager: {e}")
            # Continue with database deletion even if Wazuh deletion fails

        # Delete from database
        self.db.execute(
            text("""
                DELETE FROM endpoint_agents
                WHERE tenant_id = :tenant_id AND wazuh_agent_id = :wazuh_agent_id
            """),
            {"tenant_id": str(tenant_id), "wazuh_agent_id": wazuh_agent_id},
        )
        self.db.commit()

        logger.info(f"Agent {wazuh_agent_id} deleted for tenant {tenant_id}")
        return True

    async def restart_agent(
        self, tenant_id: UUID, wazuh_agent_id: str
    ) -> Dict[str, Any]:
        """
        Restart an agent (tenant-isolated).

        Args:
            tenant_id: Tenant ID for authorization
            wazuh_agent_id: Wazuh agent ID

        Returns:
            Restart response
        """
        require_owned_wazuh_operation()
        # Verify agent belongs to tenant
        result = self.db.execute(
            text("""
                SELECT id FROM endpoint_agents
                WHERE tenant_id = :tenant_id AND wazuh_agent_id = :wazuh_agent_id
            """),
            {"tenant_id": str(tenant_id), "wazuh_agent_id": wazuh_agent_id},
        ).first()

        if not result:
            raise Exception("Agent not found or access denied")

        # Restart agent via Wazuh API
        response = await self.wazuh.restart_agent(wazuh_agent_id)

        return {
            "success": True,
            "agent_id": wazuh_agent_id,
            "message": "Restart command sent to agent",
        }
