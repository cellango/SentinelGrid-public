"""
GitHub API Client

Handles GitHub OAuth and API interactions for repository access and scanning.
"""

import logging
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class GitHubClient:
    """Client for interacting with GitHub API."""
    
    def __init__(self, access_token: str):
        """
        Initialize GitHub client.
        
        Args:
            access_token: GitHub OAuth access token
        """
        self.access_token = access_token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SentinelGrid/1.0"
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
    
    async def list_repositories(
        self,
        organization: Optional[str] = None,
        visibility: str = "all"
    ) -> List[Dict[str, Any]]:
        """
        List repositories for user or organization.
        
        Args:
            organization: Organization name (None for user repos)
            visibility: all, public, or private
        
        Returns:
            List of repository dictionaries
        """
        if organization:
            url = f"{self.base_url}/orgs/{organization}/repos"
        else:
            url = f"{self.base_url}/user/repos"
        
        params = {
            "visibility": visibility,
            "per_page": 100,
            "sort": "updated",
            "direction": "desc"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def get_repository(
        self,
        owner: str,
        repo: str
    ) -> Dict[str, Any]:
        """Get repository details."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def list_branches(
        self,
        owner: str,
        repo: str
    ) -> List[Dict[str, Any]]:
        """List branches for a repository."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/branches",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_commits(
        self,
        owner: str,
        repo: str,
        branch: str = "main",
        since: Optional[datetime] = None,
        per_page: int = 100
    ) -> List[Dict[str, Any]]:
        """Get commits for a repository."""
        params = {
            "sha": branch,
            "per_page": per_page
        }
        
        if since:
            params["since"] = since.isoformat()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/commits",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def get_file_contents(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str = "main"
    ) -> Dict[str, Any]:
        """Get file contents from repository."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/contents/{path}",
                headers=self.headers,
                params={"ref": ref}
            )
            response.raise_for_status()
            return response.json()
    
    async def list_collaborators(
        self,
        owner: str,
        repo: str
    ) -> List[Dict[str, Any]]:
        """List collaborators for a repository."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/collaborators",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_organization_members(
        self,
        org: str
    ) -> List[Dict[str, Any]]:
        """Get organization members."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/orgs/{org}/members",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def create_webhook(
        self,
        owner: str,
        repo: str,
        webhook_url: str,
        events: List[str]
    ) -> Dict[str, Any]:
        """Create a webhook for repository events."""
        payload = {
            "name": "web",
            "active": True,
            "events": events,
            "config": {
                "url": webhook_url,
                "content_type": "json",
                "insecure_ssl": "0"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/hooks",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test API connection and permissions."""
        try:
            user = await self.get_user()
            return {
                "success": True,
                "user": user.get("login"),
                "type": user.get("type"),
                "permissions": {
                    "repos": True,  # Would check actual scopes
                    "admin": user.get("type") == "User"
                }
            }
        except Exception as e:
            logger.error(f"GitHub connection test failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

