"""Tests for IAM tools."""

import pytest
from unittest.mock import Mock, AsyncMock

from app.tools import iam_tools


@pytest.mark.asyncio
async def test_get_user(
    mock_service_clients,
    mock_security_manager,
    mock_tenant_id,
    mock_user_id,
    sample_user
):
    """Test get_user tool."""
    # Setup
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json = Mock(return_value=sample_user)
    mock_service_clients.iam_agent.get = AsyncMock(return_value=mock_response)
    
    # Execute
    result = await iam_tools.get_user(
        user_id="user-789",
        tenant_id=mock_tenant_id,
        requesting_user_id=mock_user_id
    )
    
    # Assert
    assert result == sample_user
    assert result["email"] == "john.doe@example.com"
    assert result["mfa_enabled"] is True
    
    # Verify correct endpoint was called
    call_args = mock_service_clients.iam_agent.get.call_args
    assert "/api/v1/users/user-789" in call_args[0][0]


@pytest.mark.asyncio
async def test_lock_account(
    mock_service_clients,
    mock_security_manager,
    mock_tenant_id,
    mock_user_id
):
    """Test lock_account tool (high-risk)."""
    # Setup
    lock_result = {
        "user_id": "user-789",
        "status": "locked",
        "reason": "Suspicious activity detected",
        "locked_at": "2024-12-02T10:00:00Z"
    }
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json = Mock(return_value=lock_result)
    mock_service_clients.iam_agent.post = AsyncMock(return_value=mock_response)
    
    # Execute
    result = await iam_tools.lock_account(
        user_id="user-789",
        reason="Suspicious activity detected",
        tenant_id=mock_tenant_id,
        requesting_user_id=mock_user_id
    )
    
    # Assert
    assert result == lock_result
    assert result["status"] == "locked"
    
    # Verify authorization was checked (high-risk action)
    mock_security_manager.authorize_tool_call.assert_called_once()
    auth_call_args = mock_security_manager.authorize_tool_call.call_args
    assert auth_call_args[0][0] == "lock_account"
    
    # Verify audit was logged
    mock_security_manager.audit_tool_call.assert_called_once()
    
    # Verify correct data was sent
    call_args = mock_service_clients.iam_agent.post.call_args
    assert call_args[1]['json']['reason'] == "Suspicious activity detected"


@pytest.mark.asyncio
async def test_lock_account_unauthorized(
    mock_service_clients,
    mock_security_manager,
    mock_tenant_id,
    mock_user_id
):
    """Test lock_account fails authorization."""
    # Setup - simulate authorization failure
    mock_security_manager.authorize_tool_call = AsyncMock(
        side_effect=PermissionError("Not authorized")
    )
    
    # Execute and assert exception
    with pytest.raises(PermissionError, match="Not authorized"):
        await iam_tools.lock_account(
            user_id="user-789",
            reason="Test",
            tenant_id=mock_tenant_id,
            requesting_user_id=mock_user_id
        )
    
    # Verify API was NOT called
    mock_service_clients.iam_agent.post.assert_not_called()

