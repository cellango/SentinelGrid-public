"""
Bitbucket API Client

Handles Bitbucket Cloud API interactions for repository access and scanning.
"""

import logging
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime
import base64

logger = logging.getLogger(__name__)


class BitbucketClient:
    """Client for interacting with Bitbucket Cloud API."""
    
    def __init__(self, username: str, app_password: str):
        """
        Initialize Bitbucket client.
        
        Args:
            username: Bitbucket username
            app_password: Bitbucket app password (not regular password)
        """
        self.username = username
        self.app_password = app_password
        self.base_url = "https://api.bitbucket.org/2.0"
        
        # Basic auth for Bitbucket
        credentials = f"{username}:{app_password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {encoded}",
            "Accept": "application/json"
        }
    
    async def get_user(self) -> Dict[str, Any]:
        """Get authenticated user information."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/user",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def list_workspaces(self) -> List[Dict[str, Any]]:
        """List workspaces for the authenticated user."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/user/permissions/workspaces",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            return data.get("values", [])
    
    async def list_repositories(
        self,
        workspace: str
    ) -> List[Dict[str, Any]]:
        """
        List repositories in a workspace.
        
        Args:
            workspace: Workspace name
        
        Returns:
            List of repository dictionaries
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repositories/{workspace}",
                headers=self.headers,
                params={"pagelen": 100}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("values", [])
    
    async def get_repository(
        self,
        workspace: str,
        repo_slug: str
    ) -> Dict[str, Any]:
        """Get repository details."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repositories/{workspace}/{repo_slug}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def list_branches(
        self,
        workspace: str,
        repo_slug: str
    ) -> List[Dict[str, Any]]:
        """List branches for a repository."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repositories/{workspace}/{repo_slug}/refs/branches",
                headers=self.headers,
                params={"pagelen": 100}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("values", [])
    
    async def get_commits(
        self,
        workspace: str,
        repo_slug: str,
        branch: str = "main",
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get commits for a repository."""
        params = {
            "pagelen": 100
        }
        
        if since:
            params["since"] = since.isoformat()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repositories/{workspace}/{repo_slug}/commits/{branch}",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()
            return data.get("values", [])
    
    async def get_file_contents(
        self,
        workspace: str,
        repo_slug: str,
        file_path: str,
        ref: str = "main"
    ) -> Dict[str, Any]:
        """Get file contents from repository."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repositories/{workspace}/{repo_slug}/src/{ref}/{file_path}",
                headers=self.headers
            )
            response.raise_for_status()
            return {"content": response.text}
    
    async def list_repository_permissions(
        self,
        workspace: str,
        repo_slug: str
    ) -> List[Dict[str, Any]]:
        """List repository permissions/users."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repositories/{workspace}/{repo_slug}/permissions",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            return data.get("values", [])
    
    async def create_webhook(
        self,
        workspace: str,
        repo_slug: str,
        webhook_url: str,
        events: List[str]
    ) -> Dict[str, Any]:
        """Create a webhook for repository events."""
        payload = {
            "description": "SentinelGrid Security Scanner",
            "url": webhook_url,
            "active": True,
            "events": events
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/repositories/{workspace}/{repo_slug}/hooks",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test API connection and permissions."""
        try:
            user = await self.get_user()
            workspaces = await self.list_workspaces()
            return {
                "success": True,
                "user": user.get("username"),
                "display_name": user.get("display_name"),
                "workspaces": [w.get("workspace", {}).get("slug") for w in workspaces],
                "permissions": {
                    "read": True,
                    "write": False  # Would check actual permissions
                }
            }
        except Exception as e:
            logger.error(f"Bitbucket connection test failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

