"""
Connector Framework
Base classes and interfaces for building integration connectors
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class SyncDirection(str, Enum):
    """Sync direction options."""
    IMPORT = "import"  # From external system to Keycloak
    EXPORT = "export"  # From Keycloak to external system
    BIDIRECTIONAL = "bidirectional"  # Both directions


class SyncStatus(str, Enum):
    """Sync job status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BaseConnector(ABC):
    """Base class for all integration connectors."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", "unknown")
        self.integration_type = config.get("type", "custom")
        self.enabled = config.get("enabled", True)
    
    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to the external system.
        
        Returns:
            Dictionary with connection status and details
        """
        pass
    
    @abstractmethod
    def sync_users(
        self,
        direction: SyncDirection = SyncDirection.IMPORT,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sync users between systems.
        
        Args:
            direction: Sync direction
            filters: Optional filters for selective sync
            
        Returns:
            Dictionary with sync results
        """
        pass
    
    @abstractmethod
    def sync_groups(
        self,
        direction: SyncDirection = SyncDirection.IMPORT,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sync groups between systems.
        
        Args:
            direction: Sync direction
            filters: Optional filters for selective sync
            
        Returns:
            Dictionary with sync results
        """
        pass
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get connector capabilities.
        
        Returns:
            Dictionary describing what the connector supports
        """
        return {
            "user_sync": True,
            "group_sync": True,
            "attribute_mapping": True,
            "filtering": False,
            "incremental_sync": False,
            "real_time_sync": False
        }
    
    def validate_config(self) -> Dict[str, Any]:
        """
        Validate connector configuration.
        
        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []
        
        required_fields = ["name", "type"]
        for field in required_fields:
            if field not in self.config:
                errors.append(f"Missing required field: {field}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }


class ConnectorFactory:
    """Factory for creating connector instances."""
    
    _connectors: Dict[str, type] = {}
    
    @classmethod
    def register(cls, connector_type: str, connector_class: type):
        """Register a connector class."""
        cls._connectors[connector_type] = connector_class
    
    @classmethod
    def create(cls, connector_type: str, config: Dict[str, Any]) -> BaseConnector:
        """Create a connector instance."""
        if connector_type not in cls._connectors:
            raise ValueError(f"Unknown connector type: {connector_type}")
        
        connector_class = cls._connectors[connector_type]
        return connector_class(config)
    
    @classmethod
    def list_connector_types(cls) -> List[str]:
        """List all registered connector types."""
        return list(cls._connectors.keys())


class SyncJob:
    """Represents a sync job execution."""
    
    def __init__(
        self,
        job_id: str,
        connector: BaseConnector,
        sync_type: str,
        direction: SyncDirection,
        filters: Optional[Dict[str, Any]] = None
    ):
        self.job_id = job_id
        self.connector = connector
        self.sync_type = sync_type  # 'users', 'groups', 'full'
        self.direction = direction
        self.filters = filters or {}
        self.status = SyncStatus.PENDING
        self.created_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.error = None
    
    def execute(self) -> Dict[str, Any]:
        """Execute the sync job."""
        self.status = SyncStatus.RUNNING
        self.started_at = datetime.utcnow()
        
        try:
            if self.sync_type == "users":
                self.result = self.connector.sync_users(self.direction, self.filters)
            elif self.sync_type == "groups":
                self.result = self.connector.sync_groups(self.direction, self.filters)
            elif self.sync_type == "full":
                users_result = self.connector.sync_users(self.direction, self.filters)
                groups_result = self.connector.sync_groups(self.direction, self.filters)
                self.result = {
                    "users": users_result,
                    "groups": groups_result
                }
            else:
                raise ValueError(f"Unknown sync type: {self.sync_type}")
            
            self.status = SyncStatus.SUCCESS
            self.completed_at = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Sync job {self.job_id} failed: {e}")
            self.status = SyncStatus.FAILED
            self.error = str(e)
            self.completed_at = datetime.utcnow()
        
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "duration_seconds": (
                (self.completed_at - self.started_at).total_seconds()
                if self.completed_at and self.started_at else None
            )
        }

