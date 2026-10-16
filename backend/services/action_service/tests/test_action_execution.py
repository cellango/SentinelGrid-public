"""
Tests for Action Executor Service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.action_executor import ActionExecutor, ActionStatus


class TestActionExecution:
    """Tests for action execution."""
    
    @pytest.mark.asyncio
    async def test_iam_action_execution(self):
        """Test IAM action execution."""
        executor = ActionExecutor()
        
        with patch('app.services.action_executor.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"status": "disabled"}
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await executor.execute_action(
                action_type="iam_disable_user",
                action_params={"user_id": "user-123"},
                tenant_id="test-tenant",
                requires_approval=False
            )
            
            assert result["status"] == ActionStatus.COMPLETED
            assert result["action_type"] == "iam_disable_user"
    
    @pytest.mark.asyncio
    async def test_action_approval_required(self):
        """Test action approval requirement."""
        executor = ActionExecutor()
        executor.require_approval = True
        
        result = await executor.execute_action(
            action_type="iam_disable_user",
            action_params={"user_id": "user-123"},
            tenant_id="test-tenant"
        )
        
        assert result["status"] == ActionStatus.PENDING
        assert result["approval_required"] is True
    
    @pytest.mark.asyncio
    async def test_endpoint_action_execution(self):
        """Test endpoint action execution."""
        executor = ActionExecutor()
        
        result = await executor.execute_action(
            action_type="endpoint_quarantine",
            action_params={"asset_id": "asset-123"},
            tenant_id="test-tenant",
            requires_approval=False
        )
        
        assert result["status"] == ActionStatus.COMPLETED
        assert result["action_type"] == "endpoint_quarantine"
    
    @pytest.mark.asyncio
    async def test_network_action_execution(self):
        """Test network action execution."""
        executor = ActionExecutor()
        
        result = await executor.execute_action(
            action_type="network_block_ip",
            action_params={"ip_address": "192.168.1.100"},
            tenant_id="test-tenant",
            requires_approval=False
        )
        
        assert result["status"] == ActionStatus.COMPLETED
        assert result["action_type"] == "network_block_ip"

