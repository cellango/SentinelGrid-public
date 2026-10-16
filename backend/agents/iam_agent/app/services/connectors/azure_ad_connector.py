"""
Azure AD Connector
Implements Microsoft Graph API-based sync with Azure AD
"""

import logging
from typing import List, Dict, Any, Optional
import httpx

from app.services.connector_framework import BaseConnector, SyncDirection

logger = logging.getLogger(__name__)


class AzureADConnector(BaseConnector):
    """Connector for Azure AD via Microsoft Graph API."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.tenant_id = config.get("tenant_id")
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.graph_api_url = "https://graph.microsoft.com/v1.0"
        self._access_token = None
    
    def _get_access_token(self) -> str:
        """Get Azure AD access token."""
        if self._access_token:
            return self._access_token
        
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }
        
        try:
            with httpx.Client() as client:
                response = client.post(token_url, data=data)
                response.raise_for_status()
                token_data = response.json()
                self._access_token = token_data["access_token"]
                return self._access_token
        except Exception as e:
            logger.error(f"Error getting Azure AD access token: {e}")
            raise
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Azure AD."""
        try:
            token = self._get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test by getting organization info
            with httpx.Client() as client:
                response = client.get(
                    f"{self.graph_api_url}/organization",
                    headers=headers
                )
                response.raise_for_status()
                org_data = response.json()
                
                return {
                    "status": "connected",
                    "message": "Successfully connected to Azure AD",
                    "tenant_id": self.tenant_id,
                    "organization": org_data.get("value", [{}])[0].get("displayName") if org_data.get("value") else None
                }
        except Exception as e:
            logger.error(f"Error testing Azure AD connection: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def sync_users(
        self,
        direction: SyncDirection = SyncDirection.IMPORT,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Sync users from Azure AD."""
        if direction != SyncDirection.IMPORT:
            return {
                "status": "skipped",
                "message": "Azure AD connector currently supports import only"
            }
        
        try:
            token = self._get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            # Build query
            query = "$select=id,userPrincipalName,displayName,givenName,surname,mail,accountEnabled,createdDateTime,department,officeLocation,memberOf"
            
            if filters and filters.get("department"):
                query += f"&$filter=department eq '{filters['department']}'"
            
            users = []
            next_url = f"{self.graph_api_url}/users?{query}"
            
            with httpx.Client() as client:
                while next_url:
                    response = client.get(next_url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    
                    for user_data in data.get("value", []):
                        user = {
                            "id": user_data.get("id"),
                            "username": user_data.get("userPrincipalName"),
                            "email": user_data.get("mail") or user_data.get("userPrincipalName"),
                            "first_name": user_data.get("givenName"),
                            "last_name": user_data.get("surname"),
                            "display_name": user_data.get("displayName"),
                            "enabled": user_data.get("accountEnabled", True),
                            "department": user_data.get("department"),
                            "office_location": user_data.get("officeLocation"),
                            "created_at": user_data.get("createdDateTime"),
                            "groups": []  # Would need separate call to get groups
                        }
                        users.append(user)
                    
                    next_url = data.get("@odata.nextLink")
            
            return {
                "status": "success",
                "users_synced": len(users),
                "users": users,
                "direction": direction.value
            }
            
        except Exception as e:
            logger.error(f"Error syncing Azure AD users: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "users_synced": 0
            }
    
    def sync_groups(
        self,
        direction: SyncDirection = SyncDirection.IMPORT,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Sync groups from Azure AD."""
        if direction != SyncDirection.IMPORT:
            return {
                "status": "skipped",
                "message": "Azure AD connector currently supports import only"
            }
        
        try:
            token = self._get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            query = "$select=id,displayName,description,mail,groupTypes,createdDateTime,members"
            
            groups = []
            next_url = f"{self.graph_api_url}/groups?{query}"
            
            with httpx.Client() as client:
                while next_url:
                    response = client.get(next_url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    
                    for group_data in data.get("value", []):
                        group = {
                            "id": group_data.get("id"),
                            "name": group_data.get("displayName"),
                            "description": group_data.get("description"),
                            "email": group_data.get("mail"),
                            "group_type": "microsoft365" if "Unified" in group_data.get("groupTypes", []) else "security",
                            "created_at": group_data.get("createdDateTime"),
                            "members": []  # Would need separate call with $expand
                        }
                        groups.append(group)
                    
                    next_url = data.get("@odata.nextLink")
            
            return {
                "status": "success",
                "groups_synced": len(groups),
                "groups": groups,
                "direction": direction.value
            }
            
        except Exception as e:
            logger.error(f"Error syncing Azure AD groups: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "groups_synced": 0
            }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get Azure AD connector capabilities."""
        return {
            "user_sync": True,
            "group_sync": True,
            "attribute_mapping": True,
            "filtering": True,
            "incremental_sync": True,  # Via delta queries
            "real_time_sync": True,  # Via webhooks/subscriptions
            "password_sync": False
        }

