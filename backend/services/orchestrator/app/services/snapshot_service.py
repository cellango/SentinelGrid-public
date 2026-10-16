"""Snapshot service for orchestrator."""

import logging
from typing import Dict, Any
from datetime import datetime
from app.services.siem_client import SIEMClient
from app.services.iam_client import IAMClient
from app.services.model_gateway_client import ModelGatewayClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class SnapshotService:
    """Service for generating security snapshots."""
    
    def __init__(self):
        self.siem_client = SIEMClient()
        self.iam_client = IAMClient()
        self.model_gateway_client = ModelGatewayClient()
    
    async def generate_security_snapshot(self, tenant_id: str) -> Dict[str, Any]:
        """
        Generate comprehensive security snapshot for a tenant.
        
        This aggregates data from SIEM Agent, IAM Agent, and generates
        AI analysis via Model Gateway.
        
        Args:
            tenant_id: Tenant ID
        
        Returns:
            Complete security snapshot dictionary
        """
        logger.info(f"Generating security snapshot for tenant: {tenant_id}")
        
        # 1. Get SIEM statistics
        logger.debug("Fetching SIEM statistics...")
        siem_stats = await self.siem_client.get_stats(tenant_id)
        
        # 2. Get top alerts
        logger.debug("Fetching top alerts...")
        alerts = await self.siem_client.list_alerts(
            tenant_id,
            limit=settings.SNAPSHOT_ALERT_LIMIT
        )
        
        # 3. Get IAM statistics
        logger.debug("Fetching IAM statistics...")
        iam_stats = await self.iam_client.get_identity_stats(tenant_id)
        
        # 4. Build snapshot data structure
        snapshot_data = {
            "tenant_id": tenant_id,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "events_count": siem_stats.get("events_count", 0),
                "alerts_count": siem_stats.get("alerts_count", 0),
                "users_active": iam_stats.get("active_users_count", iam_stats.get("users_count", 0)),
                "users_total": iam_stats.get("users_count", 0),
            },
            "alerts_by_severity": siem_stats.get("alerts_by_severity", {}),
            "alerts_by_status": siem_stats.get("alerts_by_status", {}),
            "top_findings": [
                {
                    "id": alert.get("id"),
                    "title": alert.get("title"),
                    "severity": alert.get("severity"),
                    "status": alert.get("status"),
                    "description": alert.get("description", "")[:200],  # Truncate
                    "created_at": alert.get("created_at") or alert.get("timestamp"),
                }
                for alert in alerts[:settings.SNAPSHOT_ALERT_LIMIT]
            ],
            "iam_summary": {
                "users_count": iam_stats.get("users_count", 0),
                "active_users_count": iam_stats.get("active_users_count", 0),
                "roles_count": iam_stats.get("roles_count", 0),
                "groups_count": iam_stats.get("groups_count", 0),
            },
        }
        
        # 5. Generate AI analysis
        logger.debug("Generating AI analysis...")
        try:
            ai_analysis = await self.model_gateway_client.generate_snapshot_analysis(
                tenant_id,
                snapshot_data
            )
            snapshot_data["ai_analysis"] = ai_analysis
        except Exception as e:
            logger.error(f"Failed to generate AI analysis: {e}")
            snapshot_data["ai_analysis"] = {
                "posture": "Unknown",
                "risk_level": "Medium",
                "key_findings": [],
                "recommendations": [],
                "summary": "AI analysis unavailable",
                "error": str(e),
            }
        
        logger.info(f"Security snapshot generated successfully for tenant: {tenant_id}")
        
        return snapshot_data

