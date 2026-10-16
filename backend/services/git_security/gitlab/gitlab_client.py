"""
GitLab API Client

Handles GitLab API interactions for repository access and scanning.
"""

import logging
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class GitLabClient:
    """Client for interacting with GitLab API."""
    
    def __init__(self, access_token: str, gitlab_url: str = "https://gitlab.com"):
        """
        Initialize GitLab client.
        
        Args:
            access_token: GitLab personal access token or OAuth token
            gitlab_url: GitLab instance URL (default: gitlab.com)
        """
        self.access_token = access_token
        self.base_url = f"{gitlab_url}/api/v4"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
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
    
    async def list_projects(
        self,
        group_id: Optional[int] = None,
        visibility: str = "private"
    ) -> List[Dict[str, Any]]:
        """
        List projects (repositories) for user or group.
        
        Args:
            group_id: Group ID (None for user projects)
            visibility: private, internal, or public
        
        Returns:
            List of project dictionaries
        """
        if group_id:
            url = f"{self.base_url}/groups/{group_id}/projects"
        else:
            url = f"{self.base_url}/projects"
        
        params = {
            "visibility": visibility,
            "per_page": 100,
            "order_by": "updated_at",
            "sort": "desc"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def get_project(
        self,
        project_id: int
    ) -> Dict[str, Any]:
        """Get project details."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/projects/{project_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def list_branches(
        self,
        project_id: int
    ) -> List[Dict[str, Any]]:
        """List branches for a project."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/projects/{project_id}/repository/branches",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_commits(
        self,
        project_id: int,
        branch: str = "main",
        since: Optional[datetime] = None,
        per_page: int = 100
    ) -> List[Dict[str, Any]]:
        """Get commits for a project."""
        params = {
            "ref_name": branch,
            "per_page": per_page
        }
        
        if since:
            params["since"] = since.isoformat()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/projects/{project_id}/repository/commits",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def get_file_contents(
        self,
        project_id: int,
        file_path: str,
        ref: str = "main"
    ) -> Dict[str, Any]:
        """Get file contents from repository."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/projects/{project_id}/repository/files/{file_path.replace('/', '%2F')}",
                headers=self.headers,
                params={"ref": ref}
            )
            response.raise_for_status()
            return response.json()
    
    async def list_project_members(
        self,
        project_id: int
    ) -> List[Dict[str, Any]]:
        """List project members."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/projects/{project_id}/members",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def list_group_members(
        self,
        group_id: int
    ) -> List[Dict[str, Any]]:
        """List group members."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/groups/{group_id}/members",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def create_webhook(
        self,
        project_id: int,
        webhook_url: str,
        events: List[str]
    ) -> Dict[str, Any]:
        """Create a webhook for project events."""
        payload = {
            "url": webhook_url,
            "push_events": "push" in events,
            "merge_requests_events": "merge_request" in events,
            "tag_push_events": "tag_push" in events,
            "enable_ssl_verification": True
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/projects/{project_id}/hooks",
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
                "user": user.get("username"),
                "email": user.get("email"),
                "permissions": {
                    "read_repository": True,
                    "read_user": True
                }
            }
        except Exception as e:
            logger.error(f"GitLab connection test failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

