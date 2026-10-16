"""Base rule interface."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseRule(ABC):
    """Base class for all detection rules."""
    
    def __init__(self, rule_config: Dict[str, Any], tenant_id: str):
        """
        Initialize rule.
        
        Args:
            rule_config: Rule configuration from database
            tenant_id: Tenant ID
        """
        self.rule_config = rule_config
        self.tenant_id = tenant_id
        self.rule_id = rule_config.get("id")
        self.rule_name = rule_config.get("name")
        self.severity = rule_config.get("severity", "medium")
        self.pattern = rule_config.get("pattern", {})
        self.siem_agent_url = settings.SIEM_AGENT_URL
        self.internal_token = settings.INTERNAL_SERVICE_TOKEN
    
    @abstractmethod
    def evaluate(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evaluate events against the rule.
        
        Args:
            events: List of events from SIEM Agent
        
        Returns:
            List of alerts generated (empty if no matches)
        """
        pass
    
    async def fetch_recent_events(
        self,
        lookback_minutes: int = 15,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent events from SIEM Agent for evaluation.
        
        Args:
            lookback_minutes: Minutes to look back
            filters: Additional filters for event search
        
        Returns:
            List of events
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=lookback_minutes)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Use SIEM Agent's search endpoint
                # Convert filters to query format if needed
                query_dict = {}
                if filters:
                    # Build query from filters
                    query_parts = []
                    if "event_type" in filters:
                        query_parts.append(f"event_type:{filters['event_type']}")
                    if "user.email" in filters:
                        query_parts.append(f"user.email:{filters['user.email']}")
                    if query_parts:
                        query_dict["query"] = " AND ".join(query_parts)
                
                response = await client.get(
                    f"{self.siem_agent_url}/api/v1/siem/logs/search",
                    params={
                        "query": query_dict.get("query", "*"),
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "limit": 10000,
                    },
                    headers={
                        "Authorization": f"Bearer {self.internal_token}",
                        "X-Tenant-ID": self.tenant_id,
                    },
                )
                response.raise_for_status()
                result = response.json()
                return result.get("events", [])
        
        except Exception as e:
            logger.error(f"Failed to fetch events from SIEM Agent: {e}")
            return []
    
    def create_alert(
        self,
        title: str,
        description: str,
        events: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an alert dictionary.
        
        Args:
            title: Alert title
            description: Alert description
            events: List of related events
            metadata: Additional metadata
        
        Returns:
            Alert dictionary
        """
        event_ids = [e.get("id") for e in events if e.get("id")]
        
        alert = {
            "tenant_id": self.tenant_id,
            "severity": self.severity,
            "status": "open",
            "title": title,
            "description": description,
            "detection_rule_id": str(self.rule_id),
            "events": event_ids,
            "metadata": {
                "rule_name": self.rule_name,
                "rule_type": self.get_rule_type(),
                **(metadata or {}),
            },
        }
        
        # Extract common fields from events
        if events:
            first_event = events[0]
            if "user" in first_event and "email" in first_event["user"]:
                alert["user_id"] = first_event["user"]["email"]
            if "source" in first_event and "ip" in first_event["source"]:
                alert["source_ip"] = first_event["source"]["ip"]
        
        return alert
    
    @abstractmethod
    def get_rule_type(self) -> str:
        """Get the rule type identifier."""
        pass

