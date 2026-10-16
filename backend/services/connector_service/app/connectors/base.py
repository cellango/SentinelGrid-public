"""Base connector interface."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.models.event import RawEvent


class BaseConnector(ABC):
    """Base class for all connectors."""
    
    def __init__(self, config: Dict[str, Any], tenant_id: str):
        """
        Initialize connector.
        
        Args:
            config: Connector configuration (credentials, settings)
            tenant_id: Tenant ID
        """
        self.config = config
        self.tenant_id = tenant_id
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test connection to the external service.
        
        Returns:
            True if connection successful
        """
        pass
    
    @abstractmethod
    def fetch_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[RawEvent]:
        """
        Fetch events from the external service.
        
        Args:
            start_time: Start time for event range
            end_time: End time for event range
            limit: Maximum number of events to fetch
        
        Returns:
            List of raw events
        """
        pass
    
    @abstractmethod
    def fetch_users(self) -> List[Dict[str, Any]]:
        """
        Fetch user directory information.
        
        Returns:
            List of user information
        """
        pass
    
    def normalize_event(self, raw_event: Dict[str, Any]) -> RawEvent:
        """
        Normalize a raw event to ECS format.
        Override in subclasses for provider-specific normalization.
        
        Args:
            raw_event: Raw event from provider
        
        Returns:
            Normalized RawEvent
        """
        from datetime import datetime
        
        return RawEvent(
            event_type=raw_event.get("event_type", "unknown"),
            source=self.get_source_name(),
            timestamp=datetime.utcnow(),
            raw_data=raw_event,
            tenant_id=self.tenant_id,
            metadata={
                "connector_type": self.get_connector_type(),
                "fetched_at": datetime.utcnow().isoformat(),
            }
        )
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Get the source name for this connector."""
        pass
    
    @abstractmethod
    def get_connector_type(self) -> str:
        """Get the connector type identifier."""
        pass

