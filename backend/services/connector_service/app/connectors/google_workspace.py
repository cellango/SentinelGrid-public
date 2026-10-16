"""Google Workspace connector."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.connectors.base import BaseConnector
from app.models.event import RawEvent

logger = logging.getLogger(__name__)


class GoogleWorkspaceConnector(BaseConnector):
    """Connector for Google Workspace (Google Admin SDK)."""
    
    def __init__(self, config: Dict[str, Any], tenant_id: str):
        super().__init__(config, tenant_id)
        self.credentials = None
        self.admin_service = None
        self.reports_service = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Google API clients."""
        try:
            # Extract OAuth2 credentials from config
            token = self.config.get("access_token")
            refresh_token = self.config.get("refresh_token")
            client_id = self.config.get("client_id")
            client_secret = self.config.get("client_secret")
            
            if not token or not refresh_token:
                raise ValueError("Missing OAuth2 credentials in config")
            
            # Create credentials
            self.credentials = Credentials(
                token=token,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
            )
            
            # Build services
            self.admin_service = build("admin", "directory_v1", credentials=self.credentials)
            self.reports_service = build("admin", "reports_v1", credentials=self.credentials)
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Workspace client: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test connection to Google Workspace."""
        try:
            # Try to get domain info
            self.admin_service.users().list(domain=self.config.get("domain"), maxResults=1).execute()
            return True
        except Exception as e:
            logger.error(f"Google Workspace connection test failed: {e}")
            return False
    
    def fetch_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[RawEvent]:
        """
        Fetch login events from Google Workspace.
        
        Fetches:
        - User sign-in logs (login.success, login.failure)
        - Admin activity logs
        """
        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=1)
        if not end_time:
            end_time = datetime.utcnow()
        
        events = []
        
        try:
            # Fetch login events
            login_events = self._fetch_login_events(start_time, end_time, limit)
            events.extend(login_events)
            
            # Fetch admin activity events
            admin_events = self._fetch_admin_activity(start_time, end_time, limit)
            events.extend(admin_events)
            
        except HttpError as e:
            logger.error(f"Failed to fetch Google Workspace events: {e}")
            raise
        
        return events[:limit] if limit else events
    
    def _fetch_login_events(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: Optional[int]
    ) -> List[RawEvent]:
        """Fetch user login events."""
        events = []
        
        try:
            # Format timestamps for Google API
            start_timestamp = int(start_time.timestamp() * 1000)
            end_timestamp = int(end_time.timestamp() * 1000)
            
            # Fetch login events
            request = self.reports_service.activities().list(
                userKey="all",
                applicationName="login",
                startTime=start_timestamp,
                endTime=end_timestamp,
                maxResults=limit or 1000,
            )
            
            response = request.execute()
            
            for item in response.get("items", []):
                for event_item in item.get("events", []):
                    # Determine event type
                    event_type = "login.success"
                    if event_item.get("name") == "login_failure":
                        event_type = "login.failure"
                    
                    raw_event = {
                        "event_type": event_type,
                        "user": {
                            "email": item.get("actor", {}).get("email"),
                        },
                        "ip_address": event_item.get("parameters", {}).get("ip_address", [{}])[0].get("value"),
                        "user_agent": event_item.get("parameters", {}).get("user_agent", [{}])[0].get("value"),
                        "timestamp": datetime.fromtimestamp(int(event_item.get("id", {}).get("timeUsec", 0)) / 1000000),
                    }
                    
                    events.append(self.normalize_event(raw_event))
            
        except HttpError as e:
            logger.error(f"Failed to fetch login events: {e}")
            # Don't raise, return what we have
        
        return events
    
    def _fetch_admin_activity(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: Optional[int]
    ) -> List[RawEvent]:
        """Fetch admin activity events."""
        events = []
        
        try:
            start_timestamp = int(start_time.timestamp() * 1000)
            end_timestamp = int(end_time.timestamp() * 1000)
            
            request = self.reports_service.activities().list(
                userKey="all",
                applicationName="admin",
                startTime=start_timestamp,
                endTime=end_timestamp,
                maxResults=limit or 1000,
            )
            
            response = request.execute()
            
            for item in response.get("items", []):
                for event_item in item.get("events", []):
                    raw_event = {
                        "event_type": "admin.activity",
                        "user": {
                            "email": item.get("actor", {}).get("email"),
                        },
                        "action": event_item.get("name"),
                        "parameters": event_item.get("parameters", {}),
                        "timestamp": datetime.fromtimestamp(int(event_item.get("id", {}).get("timeUsec", 0)) / 1000000),
                    }
                    
                    events.append(self.normalize_event(raw_event))
            
        except HttpError as e:
            logger.error(f"Failed to fetch admin activity: {e}")
            # Don't raise, return what we have
        
        return events
    
    def fetch_users(self) -> List[Dict[str, Any]]:
        """Fetch user directory information."""
        users = []
        
        try:
            domain = self.config.get("domain")
            if not domain:
                logger.warning("No domain configured for Google Workspace connector")
                return users
            
            request = self.admin_service.users().list(domain=domain, maxResults=500)
            
            while request:
                response = request.execute()
                for user in response.get("users", []):
                    users.append({
                        "id": user.get("id"),
                        "email": user.get("primaryEmail"),
                        "name": user.get("name", {}).get("fullName"),
                        "status": user.get("suspended") and "suspended" or "active",
                        "is_admin": user.get("isAdmin", False),
                        "last_login": user.get("lastLoginTime"),
                    })
                
                request = self.admin_service.users().list_next(request, response)
        
        except HttpError as e:
            logger.error(f"Failed to fetch Google Workspace users: {e}")
            raise
        
        return users
    
    def normalize_event(self, raw_event: Dict[str, Any]) -> RawEvent:
        """Normalize Google Workspace event to ECS format."""
        timestamp = raw_event.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        elif not timestamp:
            timestamp = datetime.utcnow()
        
        return RawEvent(
            event_type=raw_event.get("event_type", "unknown"),
            source="google_workspace",
            timestamp=timestamp,
            raw_data=raw_event,
            tenant_id=self.tenant_id,
            metadata={
                "connector_type": "google_workspace",
                "fetched_at": datetime.utcnow().isoformat(),
            }
        )
    
    def get_source_name(self) -> str:
        return "google_workspace"
    
    def get_connector_type(self) -> str:
        return "google_workspace"

