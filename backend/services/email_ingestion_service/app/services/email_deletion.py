"""Email deletion/quarantine service."""

import sys
import os
from typing import List, Dict, Any, Optional
import logging
import httpx

# Add libs to path
libs_path = os.path.join(os.path.dirname(__file__), "../../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailDeletionService:
    """Service for deleting or quarantining emails."""
    
    def __init__(self):
        """Initialize email deletion service."""
        self.ms_graph_base_url = "https://graph.microsoft.com/v1.0"
        self.gmail_base_url = "https://gmail.googleapis.com/gmail/v1"
    
    async def delete_emails(
        self,
        tenant_id: str,
        email_ids: List[str],
        provider: str = "microsoft_graph",
        action: str = "delete"  # delete, quarantine, move
    ) -> Dict[str, Any]:
        """
        Delete or quarantine emails.
        
        Args:
            tenant_id: Tenant ID
            email_ids: List of email IDs to delete
            provider: Email provider (microsoft_graph, gmail)
            action: Action to take (delete, quarantine, move)
            
        Returns:
            Result dictionary with success/failure counts
        """
        if len(email_ids) > 100:
            raise ValueError("Cannot delete more than 100 emails at once")
        
        if provider == "microsoft_graph":
            return await self._delete_microsoft_graph(tenant_id, email_ids, action)
        elif provider == "gmail":
            return await self._delete_gmail(tenant_id, email_ids, action)
        else:
            raise ValueError(f"Unsupported email provider: {provider}")
    
    async def _delete_microsoft_graph(
        self,
        tenant_id: str,
        email_ids: List[str],
        action: str
    ) -> Dict[str, Any]:
        """Delete emails using Microsoft Graph API."""
        try:
            access_token = await self._get_ms_graph_token(tenant_id)
            if not access_token:
                raise ValueError("Failed to get Microsoft Graph access token")
            
            success_count = 0
            failure_count = 0
            errors = []
            
            async with httpx.AsyncClient() as client:
                for email_id in email_ids:
                    try:
                        if action == "delete":
                            # Delete email
                            response = await client.delete(
                                f"{self.ms_graph_base_url}/users/me/messages/{email_id}",
                                headers={
                                    "Authorization": f"Bearer {access_token}",
                                },
                                timeout=10.0,
                            )
                        elif action == "quarantine":
                            # Move to Junk Email folder
                            response = await client.post(
                                f"{self.ms_graph_base_url}/users/me/messages/{email_id}/move",
                                json={
                                    "destinationId": "JunkEmail",  # Junk Email folder ID
                                },
                                headers={
                                    "Authorization": f"Bearer {access_token}",
                                    "Content-Type": "application/json",
                                },
                                timeout=10.0,
                            )
                        else:
                            # Move to specific folder
                            response = await client.post(
                                f"{self.ms_graph_base_url}/users/me/messages/{email_id}/move",
                                json={
                                    "destinationId": action,  # Folder ID
                                },
                                headers={
                                    "Authorization": f"Bearer {access_token}",
                                    "Content-Type": "application/json",
                                },
                                timeout=10.0,
                            )
                        
                        if response.status_code in [200, 204]:
                            success_count += 1
                        else:
                            failure_count += 1
                            errors.append({
                                "email_id": email_id,
                                "error": f"HTTP {response.status_code}: {response.text}",
                            })
                    except Exception as e:
                        failure_count += 1
                        errors.append({
                            "email_id": email_id,
                            "error": str(e),
                        })
                        logger.error(f"Error deleting email {email_id}: {e}")
            
            return {
                "success_count": success_count,
                "failure_count": failure_count,
                "total": len(email_ids),
                "errors": errors,
            }
            
        except Exception as e:
            logger.error(f"Error deleting emails via Microsoft Graph: {e}")
            raise
    
    async def _delete_gmail(
        self,
        tenant_id: str,
        email_ids: List[str],
        action: str
    ) -> Dict[str, Any]:
        """Delete emails using Gmail API."""
        try:
            access_token = await self._get_gmail_token(tenant_id)
            if not access_token:
                raise ValueError("Failed to get Gmail access token")
            
            success_count = 0
            failure_count = 0
            errors = []
            
            async with httpx.AsyncClient() as client:
                if action == "delete":
                    # Batch delete (more efficient)
                    response = await client.post(
                        f"{self.gmail_base_url}/users/me/messages/batchDelete",
                        json={
                            "ids": email_ids,
                        },
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": "application/json",
                        },
                        timeout=30.0,
                    )
                    
                    if response.status_code == 204:
                        success_count = len(email_ids)
                    else:
                        failure_count = len(email_ids)
                        errors.append({
                            "error": f"HTTP {response.status_code}: {response.text}",
                        })
                else:
                    # Move to folder (trash, spam, etc.)
                    for email_id in email_ids:
                        try:
                            if action == "quarantine":
                                # Move to spam
                                response = await client.post(
                                    f"{self.gmail_base_url}/users/me/messages/{email_id}/modify",
                                    json={
                                        "addLabelIds": ["SPAM"],
                                        "removeLabelIds": ["INBOX"],
                                    },
                                    headers={
                                        "Authorization": f"Bearer {access_token}",
                                        "Content-Type": "application/json",
                                    },
                                    timeout=10.0,
                                )
                            else:
                                # Move to specific label
                                response = await client.post(
                                    f"{self.gmail_base_url}/users/me/messages/{email_id}/modify",
                                    json={
                                        "addLabelIds": [action],
                                    },
                                    headers={
                                        "Authorization": f"Bearer {access_token}",
                                        "Content-Type": "application/json",
                                    },
                                    timeout=10.0,
                                )
                            
                            if response.status_code == 200:
                                success_count += 1
                            else:
                                failure_count += 1
                                errors.append({
                                    "email_id": email_id,
                                    "error": f"HTTP {response.status_code}: {response.text}",
                                })
                        except Exception as e:
                            failure_count += 1
                            errors.append({
                                "email_id": email_id,
                                "error": str(e),
                            })
            
            return {
                "success_count": success_count,
                "failure_count": failure_count,
                "total": len(email_ids),
                "errors": errors,
            }
            
        except Exception as e:
            logger.error(f"Error deleting emails via Gmail: {e}")
            raise
    
    async def _get_ms_graph_token(self, tenant_id: str) -> Optional[str]:
        """Get Microsoft Graph access token for tenant."""
        # TODO: Implement OAuth token retrieval from tenant config
        return None
    
    async def _get_gmail_token(self, tenant_id: str) -> Optional[str]:
        """Get Gmail access token for tenant."""
        # TODO: Implement OAuth token retrieval from tenant config
        return None

