"""OAuth flow management service."""

import logging
import secrets
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import text
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app.core.config import settings
from app.models.connector import ConnectorConfig

logger = logging.getLogger(__name__)


class OAuthService:
    """Service for managing OAuth flows for identity providers."""
    
    # Store OAuth state tokens temporarily (in production, use Redis)
    _oauth_states: Dict[str, Dict[str, Any]] = {}
    
    def __init__(self, db: Session):
        self.db = db

    def get_tenant_id_for_state(self, state_token: str) -> UUID:
        """Resolve the tenant bound to an OAuth state token."""
        state_data = self._oauth_states.get(state_token)
        if not state_data:
            raise ValueError("Invalid or expired state token")

        tenant_id = state_data.get("tenant_id")
        if not tenant_id:
            raise ValueError("OAuth state missing tenant_id")

        return UUID(tenant_id)
    
    def init_google_workspace_oauth(
        self,
        tenant_id: UUID,
        redirect_uri: str
    ) -> Dict[str, str]:
        """
        Initialize Google Workspace OAuth flow.
        
        Args:
            tenant_id: Tenant UUID
            redirect_uri: OAuth callback redirect URI
            
        Returns:
            Dictionary with oauth_url and state_token
        """
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise ValueError("Google OAuth credentials not configured")
        
        # Create OAuth flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=[
                "https://www.googleapis.com/auth/admin.directory.user.readonly",
                "https://www.googleapis.com/auth/admin.reports.audit.readonly",
                "https://www.googleapis.com/auth/admin.reports.usage.readonly"
            ]
        )
        flow.redirect_uri = redirect_uri
        
        # Generate state token
        state_token = secrets.token_urlsafe(32)
        
        # Get authorization URL
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # Store state (store flow config, not flow object)
        self._oauth_states[state_token] = {
            "tenant_id": str(tenant_id),
            "provider": "google_workspace",
            "flow_config": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "scopes": flow.scopes
            },
            "created_at": datetime.utcnow(),
            "redirect_uri": redirect_uri
        }
        
        logger.info(f"Initialized Google Workspace OAuth for tenant {tenant_id}")
        
        return {
            "oauth_url": auth_url,
            "state_token": state_token
        }
    
    def handle_google_workspace_callback(
        self,
        code: str,
        state_token: str
    ) -> Dict[str, Any]:
        """
        Handle Google Workspace OAuth callback.
        
        Args:
            code: Authorization code from OAuth provider
            state_token: State token from OAuth init
            
        Returns:
            Dictionary with connector_id and sync status
        """
        # Retrieve state
        state_data = self._oauth_states.get(state_token)
        if not state_data:
            raise ValueError("Invalid or expired state token")

        tenant_id = self.get_tenant_id_for_state(state_token)
        flow_config = state_data["flow_config"]
        
        # Recreate flow from config
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": flow_config["client_id"],
                    "client_secret": flow_config["client_secret"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [flow_config["redirect_uri"]]
                }
            },
            scopes=flow_config["scopes"]
        )
        flow.redirect_uri = flow_config["redirect_uri"]
        
        # Exchange code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Test connection and get domain info
        try:
            admin_service = build("admin", "directory_v1", credentials=credentials)
            domain_list = admin_service.domains().list(customer="my_customer").execute()
            domain = domain_list.get("domains", [{}])[0].get("domainName", "")
            
            # Get user count
            users = admin_service.users().list(domain=domain, maxResults=1).execute()
            users_count = users.get("users", [])
            
        except Exception as e:
            logger.error(f"Failed to test Google Workspace connection: {e}")
            raise
        
        # Store credentials (encrypted in production)
        connector = ConnectorConfig(
            tenant_id=tenant_id,
            type="google_workspace",
            name=f"Google Workspace - {domain}",
            credentials={
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes,
                "domain": domain
            },
            status="active",
            last_sync_at=datetime.utcnow()
        )
        
        self.db.add(connector)
        self.db.commit()
        self.db.refresh(connector)
        
        # Clean up state
        del self._oauth_states[state_token]
        
        logger.info(f"Created Google Workspace connector {connector.id} for tenant {tenant_id}")
        
        return {
            "connector_id": str(connector.id),
            "status": "connected",
            "users_synced": len(users_count),
            "domain": domain,
            "last_sync": connector.last_sync_at.isoformat() if connector.last_sync_at else None
        }
    
    def init_microsoft_oauth(
        self,
        tenant_id: UUID,
        redirect_uri: str
    ) -> Dict[str, str]:
        """
        Initialize Microsoft 365 OAuth flow.
        
        Args:
            tenant_id: Tenant UUID
            redirect_uri: OAuth callback redirect URI
            
        Returns:
            Dictionary with oauth_url and state_token
        """
        # TODO: Implement Microsoft OAuth
        raise NotImplementedError("Microsoft OAuth not yet implemented")
    
    def init_okta_oauth(
        self,
        tenant_id: UUID,
        redirect_uri: str
    ) -> Dict[str, str]:
        """
        Initialize Okta OAuth flow.
        
        Args:
            tenant_id: Tenant UUID
            redirect_uri: OAuth callback redirect URI
            
        Returns:
            Dictionary with oauth_url and state_token
        """
        # TODO: Implement Okta OAuth
        raise NotImplementedError("Okta OAuth not yet implemented")
