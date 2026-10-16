"""
Azure DevOps API Client

Handles Azure DevOps REST API interactions for repository access and scanning.
"""

import logging
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime
import base64

logger = logging.getLogger(__name__)


class AzureDevOpsClient:
    """Client for interacting with Azure DevOps API."""
    
    def __init__(self, organization: str, personal_access_token: str):
        """
        Initialize Azure DevOps client.
        
        Args:
            organization: Azure DevOps organization name
            personal_access_token: Personal Access Token (PAT)
        """
        self.organization = organization
        self.pat = personal_access_token
        self.base_url = f"https://dev.azure.com/{organization}"
        
        # Basic auth with PAT
        credentials = f":{personal_access_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json"
        }
    
    async def get_user(self) -> Dict[str, Any]:
        """Get authenticated user information."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/_apis/connectionData",
                headers=self.headers,
                params={"api-version": "7.1"}
            )
            response.raise_for_status()
            return response.json()
    
    async def list_projects(self) -> List[Dict[str, Any]]:
        """List projects in the organization."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/_apis/projects",
                headers=self.headers,
                params={"api-version": "7.1"}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("value", [])
    
    async def list_repositories(
        self,
        project: str
    ) -> List[Dict[str, Any]]:
        """
        List Git repositories in a project.
        
        Args:
            project: Project name or ID
        
        Returns:
            List of repository dictionaries
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/{project}/_apis/git/repositories",
                headers=self.headers,
                params={"api-version": "7.1"}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("value", [])
    
    async def get_repository(
        self,
        project: str,
        repo_id: str
    ) -> Dict[str, Any]:
        """Get repository details."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/{project}/_apis/git/repositories/{repo_id}",
                headers=self.headers,
                params={"api-version": "7.1"}
            )
            response.raise_for_status()
            return response.json()
    
    async def list_branches(
        self,
        project: str,
        repo_id: str
    ) -> List[Dict[str, Any]]:
        """List branches for a repository."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/{project}/_apis/git/repositories/{repo_id}/refs",
                headers=self.headers,
                params={"api-version": "7.1", "filter": "heads/"}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("value", [])
    
    async def get_commits(
        self,
        project: str,
        repo_id: str,
        branch: str = "main",
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get commits for a repository."""
        params = {
            "api-version": "7.1",
            "searchCriteria.itemVersion.version": branch,
            "$top": 100
        }
        
        if since:
            params["searchCriteria.fromDate"] = since.isoformat()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/{project}/_apis/git/repositories/{repo_id}/commits",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()
            return data.get("value", [])
    
    async def get_file_contents(
        self,
        project: str,
        repo_id: str,
        file_path: str,
        ref: str = "main"
    ) -> Dict[str, Any]:
        """Get file contents from repository."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/{project}/_apis/git/repositories/{repo_id}/items",
                headers=self.headers,
                params={
                    "api-version": "7.1",
                    "path": file_path,
                    "versionDescriptor.version": ref,
                    "includeContent": True
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def list_repository_permissions(
        self,
        project: str,
        repo_id: str
    ) -> List[Dict[str, Any]]:
        """List repository permissions."""
        # Azure DevOps uses security namespaces for permissions
        # This is a simplified version
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/{project}/_apis/git/repositories/{repo_id}/permissions",
                headers=self.headers,
                params={"api-version": "7.1"}
            )
            response.raise_for_status()
            return response.json()
    
    async def create_webhook(
        self,
        project: str,
        repo_id: str,
        webhook_url: str,
        events: List[str]
    ) -> Dict[str, Any]:
        """Create a webhook for repository events."""
        payload = {
            "publisherId": "tfs",
            "eventType": "git.push",
            "resourceVersion": "1.0",
            "consumerId": "webHooks",
            "consumerActionId": "httpRequest",
            "consumerInputs": {
                "url": webhook_url,
                "httpHeaders": "{}"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/_apis/hooks/subscriptions",
                headers=self.headers,
                params={"api-version": "7.1"},
                json=payload
            )
            response.raise_for_status()
            return response.json()
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test API connection and permissions."""
        try:
            user_data = await self.get_user()
            projects = await self.list_projects()
            return {
                "success": True,
                "organization": self.organization,
                "projects": [p.get("name") for p in projects[:5]],  # First 5 projects
                "permissions": {
                    "read": True,
                    "code_read": True
                }
            }
        except Exception as e:
            logger.error(f"Azure DevOps connection test failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

