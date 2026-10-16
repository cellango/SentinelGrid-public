"""Tests for containment functionality."""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from app.services.email_search import EmailSearchService
from app.services.email_deletion import EmailDeletionService


class TestEmailSearchService:
    """Test email search service."""
    
    @pytest.mark.asyncio
    async def test_search_microsoft_graph(self):
        """Test Microsoft Graph email search."""
        service = EmailSearchService()
        
        search_criteria = {
            "subject": "Urgent: Verify Your Account",
            "from": "noreply@example.com",
        }
        
        with patch.object(service, '_get_ms_graph_token', return_value="mock_token"):
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "value": [
                        {
                            "id": "msg1",
                            "subject": "Urgent: Verify Your Account",
                            "from": {"emailAddress": {"address": "noreply@example.com"}},
                            "receivedDateTime": "2024-01-01T12:00:00Z",
                        }
                    ]
                }
                mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
                
                results = await service.search_similar_emails(
                    str(uuid4()),
                    search_criteria,
                    "microsoft_graph"
                )
                
                assert len(results) > 0
                assert results[0]["id"] == "msg1"
    
    @pytest.mark.asyncio
    async def test_search_gmail(self):
        """Test Gmail email search."""
        service = EmailSearchService()
        
        search_criteria = {
            "subject": "Test Subject",
            "from": "sender@example.com",
        }
        
        with patch.object(service, '_get_gmail_token', return_value="mock_token"):
            with patch('httpx.AsyncClient') as mock_client:
                # Mock message list response
                mock_list_response = AsyncMock()
                mock_list_response.status_code = 200
                mock_list_response.json.return_value = {
                    "messages": [{"id": "msg1"}]
                }
                
                # Mock message detail response
                mock_detail_response = AsyncMock()
                mock_detail_response.status_code = 200
                mock_detail_response.json.return_value = {
                    "id": "msg1",
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "Test Subject"},
                            {"name": "From", "value": "sender@example.com"},
                            {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"},
                        ]
                    }
                }
                
                mock_client_instance = mock_client.return_value.__aenter__.return_value
                mock_client_instance.get.side_effect = [mock_list_response, mock_detail_response]
                
                results = await service.search_similar_emails(
                    str(uuid4()),
                    search_criteria,
                    "gmail"
                )
                
                assert len(results) > 0


class TestEmailDeletionService:
    """Test email deletion service."""
    
    @pytest.mark.asyncio
    async def test_delete_emails_microsoft_graph(self):
        """Test deleting emails via Microsoft Graph."""
        service = EmailDeletionService()
        tenant_id = str(uuid4())
        email_ids = ["msg1", "msg2"]
        
        with patch.object(service, '_get_ms_graph_token', return_value="mock_token"):
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = AsyncMock()
                mock_response.status_code = 204  # Success
                mock_client.return_value.__aenter__.return_value.delete.return_value = mock_response
                
                result = await service.delete_emails(
                    tenant_id,
                    email_ids,
                    "microsoft_graph",
                    "delete"
                )
                
                assert result["success_count"] == len(email_ids)
                assert result["failure_count"] == 0
    
    @pytest.mark.asyncio
    async def test_quarantine_emails_gmail(self):
        """Test quarantining emails via Gmail."""
        service = EmailDeletionService()
        tenant_id = str(uuid4())
        email_ids = ["msg1", "msg2"]
        
        with patch.object(service, '_get_gmail_token', return_value="mock_token"):
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = AsyncMock()
                mock_response.status_code = 204  # Success
                mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
                
                result = await service.delete_emails(
                    tenant_id,
                    email_ids,
                    "gmail",
                    "quarantine"
                )
                
                assert result["success_count"] == len(email_ids)
    
    @pytest.mark.asyncio
    async def test_delete_limit_enforcement(self):
        """Test that deletion limit is enforced."""
        service = EmailDeletionService()
        tenant_id = str(uuid4())
        email_ids = [f"msg{i}" for i in range(101)]  # 101 emails (over limit)
        
        with pytest.raises(ValueError, match="Cannot delete more than 100 emails"):
            await service.delete_emails(
                tenant_id,
                email_ids,
                "microsoft_graph",
                "delete"
            )

