"""Tests for SOAR tools."""

import pytest
from unittest.mock import Mock, AsyncMock

from app.tools import soar_tools


@pytest.mark.asyncio
async def test_list_playbooks(
    mock_service_clients,
    mock_security_manager,
    mock_tenant_id,
    mock_user_id,
    sample_playbook
):
    """Test list_playbooks tool."""
    # Setup
    playbooks = [sample_playbook]
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json = Mock(return_value=playbooks)
    mock_service_clients.soar_agent.get = AsyncMock(return_value=mock_response)
    
    # Execute
    result = await soar_tools.list_playbooks(
        category="phishing",
        tenant_id=mock_tenant_id,
        user_id=mock_user_id
    )
    
    # Assert
    assert result == playbooks
    assert len(result) == 1
    assert result[0]["name"] == "Phishing Containment"
    
    # Verify category filter was passed
    call_args = mock_service_clients.soar_agent.get.call_args
    assert call_args[1]['params']['category'] == 'phishing'


@pytest.mark.asyncio
async def test_get_playbook(
    mock_service_clients,
    mock_security_manager,
    mock_tenant_id,
    mock_user_id,
    sample_playbook
):
    """Test get_playbook tool."""
    # Setup
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json = Mock(return_value=sample_playbook)
    mock_service_clients.soar_agent.get = AsyncMock(return_value=mock_response)
    
    # Execute
    result = await soar_tools.get_playbook(
        playbook_id="PB-001",
        tenant_id=mock_tenant_id,
        user_id=mock_user_id
    )
    
    # Assert
    assert result == sample_playbook
    assert result["id"] == "PB-001"
    assert len(result["steps"]) == 3
    
    # Verify correct endpoint was called
    call_args = mock_service_clients.soar_agent.get.call_args
    assert "/api/v1/playbooks/PB-001" in call_args[0][0]


@pytest.mark.asyncio
async def test_run_playbook(
    mock_service_clients,
    mock_security_manager,
    mock_tenant_id,
    mock_user_id
):
    """Test run_playbook tool."""
    # Setup
    execution_result = {
        "execution_id": "EXEC-001",
        "playbook_id": "PB-001",
        "status": "running",
        "started_at": "2024-12-02T10:00:00Z"
    }
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json = Mock(return_value=execution_result)
    mock_service_clients.soar_agent.post = AsyncMock(return_value=mock_response)
    
    # Execute
    result = await soar_tools.run_playbook(
        playbook_id="PB-001",
        params={"user_id": "user-789"},
        incident_id="INC-123",
        tenant_id=mock_tenant_id,
        user_id=mock_user_id
    )
    
    # Assert
    assert result == execution_result
    assert result["execution_id"] == "EXEC-001"
    assert result["status"] == "running"
    
    # Verify execution data was passed correctly
    call_args = mock_service_clients.soar_agent.post.call_args
    execution_data = call_args[1]['json']
    assert execution_data['playbook_id'] == "PB-001"
    assert execution_data['params']['user_id'] == "user-789"
    assert execution_data['incident_id'] == "INC-123"


@pytest.mark.asyncio
async def test_get_playbook_execution(
    mock_service_clients,
    mock_security_manager,
    mock_tenant_id,
    mock_user_id
):
    """Test get_playbook_execution tool."""
    # Setup
    execution_status = {
        "execution_id": "EXEC-001",
        "playbook_id": "PB-001",
        "status": "completed",
        "started_at": "2024-12-02T10:00:00Z",
        "completed_at": "2024-12-02T10:05:00Z",
        "results": {"actions_completed": 3, "success": True}
    }
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json = Mock(return_value=execution_status)
    mock_service_clients.soar_agent.get = AsyncMock(return_value=mock_response)
    
    # Execute
    result = await soar_tools.get_playbook_execution(
        execution_id="EXEC-001",
        tenant_id=mock_tenant_id,
        user_id=mock_user_id
    )
    
    # Assert
    assert result == execution_status
    assert result["status"] == "completed"
    assert result["results"]["success"] is True

