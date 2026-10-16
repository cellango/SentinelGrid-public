"""Sync service for connectors."""

import logging
import asyncio
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.connector import ConnectorConfig
from app.connectors import GoogleWorkspaceConnector, AWSConnector
from app.services.ingestion_service import send_to_ingestion
from app.core.config import settings

logger = logging.getLogger(__name__)


class SyncService:
    """Service for syncing connector data."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def sync_connector(self, connector_id: str, tenant_id: str) -> dict:
        """
        Sync a single connector.
        
        Args:
            connector_id: Connector ID
            tenant_id: Tenant ID
        
        Returns:
            Sync result
        """
        # Get connector config
        connector_config = self.db.query(ConnectorConfig).filter(
            ConnectorConfig.id == connector_id,
            ConnectorConfig.tenant_id == tenant_id
        ).first()
        
        if not connector_config:
            raise ValueError(f"Connector {connector_id} not found for tenant {tenant_id}")
        
        if connector_config.status != "active":
            logger.warning(f"Connector {connector_id} is not active, skipping sync")
            return {"status": "skipped", "reason": "connector_not_active"}
        
        try:
            # Create connector instance
            connector = self._create_connector(connector_config)
            
            # Test connection
            if not connector.test_connection():
                raise ConnectionError("Connection test failed")
            
            # Determine time range
            last_sync = connector_config.last_sync_at
            if not last_sync:
                # First sync: last 24 hours
                start_time = datetime.utcnow() - timedelta(hours=24)
            else:
                # Incremental sync: since last sync
                start_time = last_sync
            
            end_time = datetime.utcnow()
            
            # Fetch events
            logger.info(f"Fetching events from {start_time} to {end_time}")
            events = connector.fetch_events(start_time=start_time, end_time=end_time)
            
            # Send to ingestion service
            if events:
                events_data = [event.model_dump() for event in events]
                send_to_ingestion(tenant_id, events_data)
                logger.info(f"Sent {len(events)} events to ingestion service")
            
            # Update connector status
            connector_config.last_sync_at = datetime.utcnow()
            connector_config.status = "active"
            connector_config.error_message = None
            self.db.commit()
            
            return {
                "status": "success",
                "events_count": len(events),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            }
        
        except Exception as e:
            logger.error(f"Sync failed for connector {connector_id}: {e}")
            
            # Update connector status
            connector_config.status = "error"
            connector_config.error_message = str(e)
            self.db.commit()
            
            return {
                "status": "error",
                "error": str(e),
            }
    
    def sync_all_active_connectors(self, tenant_id: Optional[str] = None) -> dict:
        """
        Sync all active connectors for a tenant (or all tenants).
        
        Args:
            tenant_id: Optional tenant ID to filter
        
        Returns:
            Sync results
        """
        query = self.db.query(ConnectorConfig).filter(ConnectorConfig.status == "active")
        
        if tenant_id:
            query = query.filter(ConnectorConfig.tenant_id == tenant_id)
        
        connectors = query.all()
        results = []
        
        for connector in connectors:
            try:
                result = self.sync_connector(str(connector.id), str(connector.tenant_id))
                results.append({
                    "connector_id": str(connector.id),
                    "connector_name": connector.name,
                    **result,
                })
            except Exception as e:
                logger.error(f"Failed to sync connector {connector.id}: {e}")
                results.append({
                    "connector_id": str(connector.id),
                    "connector_name": connector.name,
                    "status": "error",
                    "error": str(e),
                })
        
        return {
            "total": len(connectors),
            "results": results,
        }
    
    def _create_connector(self, config: ConnectorConfig):
        """Create connector instance from config."""
        connector_type = config.type
        connector_config = {
            **config.credentials,
            **(config.sync_settings or {}),
        }
        
        if connector_type == "google_workspace":
            return GoogleWorkspaceConnector(connector_config, str(config.tenant_id))
        elif connector_type == "aws":
            return AWSConnector(connector_config, str(config.tenant_id))
        else:
            raise ValueError(f"Unknown connector type: {connector_type}")

