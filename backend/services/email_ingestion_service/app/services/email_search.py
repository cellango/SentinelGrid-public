"""Email search service for finding similar emails."""

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


class EmailSearchService:
    """Service for searching emails across organization."""
    
    def __init__(self):
        """Initialize email search service."""
        self.ms_graph_base_url = "https://graph.microsoft.com/v1.0"
        self.gmail_base_url = "https://gmail.googleapis.com/gmail/v1"
    
    async def search_similar_emails(
        self,
        tenant_id: str,
        search_criteria: Dict[str, Any],
        provider: str = "microsoft_graph"  # microsoft_graph, gmail
    ) -> List[Dict[str, Any]]:
        """
        Search for similar emails based on criteria.
        
        Args:
            tenant_id: Tenant ID
            search_criteria: Search criteria (subject, sender, domain, url, etc.)
            provider: Email provider (microsoft_graph, gmail)
            
        Returns:
            List of matching email metadata
        """
        if provider == "microsoft_graph":
            return await self._search_microsoft_graph(tenant_id, search_criteria)
        elif provider == "gmail":
            return await self._search_gmail(tenant_id, search_criteria)
        else:
            logger.error(f"Unsupported email provider: {provider}")
            return []
    
    async def _search_microsoft_graph(
        self,
        tenant_id: str,
        search_criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Search emails using Microsoft Graph API."""
        try:
            # Get access token (would need OAuth token from tenant config)
            access_token = await self._get_ms_graph_token(tenant_id)
            if not access_token:
                logger.error("Failed to get Microsoft Graph access token")
                return []
            
            # Build search query
            search_query = self._build_ms_graph_query(search_criteria)
            
            # Search across all users (requires admin permissions)
            # For now, search in a specific mailbox or use message search
            results = []
            
            # Option 1: Search in specific mailbox
            if search_criteria.get("mailbox"):
                mailbox = search_criteria["mailbox"]
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.ms_graph_base_url}/users/{mailbox}/messages",
                        params={
                            "$filter": search_query,
                            "$top": 100,  # Limit results
                        },
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": "application/json",
                        },
                        timeout=30.0,
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        results = data.get("value", [])
                    else:
                        logger.error(f"Microsoft Graph search failed: {response.status_code} - {response.text}")
            
            # Option 2: Use message search endpoint (if available)
            # This would require Microsoft Graph Search API
            
            return self._format_ms_graph_results(results)
            
        except Exception as e:
            logger.error(f"Error searching Microsoft Graph: {e}")
            return []
    
    async def _search_gmail(
        self,
        tenant_id: str,
        search_criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Search emails using Google Gmail API."""
        try:
            # Get access token (would need OAuth token from tenant config)
            access_token = await self._get_gmail_token(tenant_id)
            if not access_token:
                logger.error("Failed to get Gmail access token")
                return []
            
            # Build Gmail search query
            search_query = self._build_gmail_query(search_criteria)
            
            results = []
            
            # Search for message IDs
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.gmail_base_url}/users/me/messages",
                    params={
                        "q": search_query,
                        "maxResults": 100,
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    message_ids = [msg["id"] for msg in data.get("messages", [])]
                    
                    # Fetch full message details for each ID
                    for msg_id in message_ids[:50]:  # Limit to 50 for performance
                        msg_response = await client.get(
                            f"{self.gmail_base_url}/users/me/messages/{msg_id}",
                            headers={
                                "Authorization": f"Bearer {access_token}",
                            },
                            timeout=10.0,
                        )
                        
                        if msg_response.status_code == 200:
                            results.append(msg_response.json())
                else:
                    logger.error(f"Gmail search failed: {response.status_code} - {response.text}")
            
            return self._format_gmail_results(results)
            
        except Exception as e:
            logger.error(f"Error searching Gmail: {e}")
            return []
    
    def _build_ms_graph_query(self, criteria: Dict[str, Any]) -> str:
        """Build Microsoft Graph filter query."""
        filters = []
        
        if criteria.get("subject"):
            filters.append(f"contains(subject, '{criteria['subject']}')")
        
        if criteria.get("from"):
            filters.append(f"from/emailAddress/address eq '{criteria['from']}'")
        
        if criteria.get("domain"):
            filters.append(f"contains(from/emailAddress/address, '{criteria['domain']}')")
        
        # Combine filters with AND
        return " and ".join(filters) if filters else ""
    
    def _build_gmail_query(self, criteria: Dict[str, Any]) -> str:
        """Build Gmail search query."""
        query_parts = []
        
        if criteria.get("subject"):
            query_parts.append(f'subject:"{criteria["subject"]}"')
        
        if criteria.get("from"):
            query_parts.append(f'from:{criteria["from"]}')
        
        if criteria.get("domain"):
            query_parts.append(f'from:{criteria["domain"]}')
        
        return " ".join(query_parts)
    
    def _format_ms_graph_results(self, results: List[Dict]) -> List[Dict[str, Any]]:
        """Format Microsoft Graph results."""
        formatted = []
        for msg in results:
            formatted.append({
                "id": msg.get("id"),
                "message_id": msg.get("internetMessageId"),
                "subject": msg.get("subject"),
                "from": msg.get("from", {}).get("emailAddress", {}).get("address"),
                "received_date": msg.get("receivedDateTime"),
                "has_attachments": msg.get("hasAttachments", False),
            })
        return formatted
    
    def _format_gmail_results(self, results: List[Dict]) -> List[Dict[str, Any]]:
        """Format Gmail results."""
        formatted = []
        for msg in results:
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            formatted.append({
                "id": msg.get("id"),
                "message_id": headers.get("Message-ID"),
                "subject": headers.get("Subject"),
                "from": headers.get("From"),
                "received_date": headers.get("Date"),
                "has_attachments": bool(msg.get("payload", {}).get("parts", [])),
            })
        return formatted
    
    async def _get_ms_graph_token(self, tenant_id: str) -> Optional[str]:
        """Get Microsoft Graph access token for tenant."""
        # TODO: Implement OAuth token retrieval from tenant config
        # This would fetch the stored OAuth token for the tenant's M365 integration
        # For now, return None (would need to be implemented with connector service)
        return None
    
    async def _get_gmail_token(self, tenant_id: str) -> Optional[str]:
        """Get Gmail access token for tenant."""
        # TODO: Implement OAuth token retrieval from tenant config
        # This would fetch the stored OAuth token for the tenant's Google Workspace integration
        # For now, return None (would need to be implemented with connector service)
        return None

