"""Tests for SIEM tools."""

import pytest
from unittest.mock import Mock, AsyncMock

from app.tools import siem_tools


@pytest.mark.asyncio
async def test_search_logs(
    mock_service_clients,
    mock_security_manager,
    mock_tenant_id,
    mock_user_id,
    sample_log_search_result
):
    """Test search_logs tool."""
    # Setup
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json = Mock(return_value=sample_log_search_result)
    mock_service_clients.siem_agent.post = AsyncMock(return_value=mock_response)
    
    # Execute
    result = await siem_tools.search_logs(
        query="failed_login AND user:admin",
        time_range="1h",
        limit=100,
        tenant_id=mock_tenant_id,
        user_id=mock_user_id
    )
    
    # Assert
    assert result == sample_log_search_result
    assert result["total"] == 2
    assert len(result["hits"]) == 2
    
    # Verify authorization was checked
    mock_security_manager.authorize_tool_call.assert_called_once()
    
    # Verify API was called
    mock_service_clients.siem_agent.post.assert_called_once()
    
    # Verify audit log was created
    mock_security_manager.audit_tool_call.assert_called_once()


@pytest.mark.asyncio
async def test_search_logs_with_error(
    mock_service_clients,
    mock_security_manager,
    mock_tenant_id,
    mock_user_id
):
    """Test search_logs with error."""
    # Setup - simulate API error
    mock_service_clients.siem_agent.post = AsyncMock(
        side_effect=Exception("API Error")
    )
    
    # Execute and assert exception
    with pytest.raises(Exception, match="API Error"):
        await siem_tools.search_logs(
            query="test",
            tenant_id=mock_tenant_id,
            user_id=mock_user_id
        )
    
    # Verify audit log was created with error
    assert mock_security_manager.audit_tool_call.call_count == 1
    call_args = mock_security_manager.audit_tool_call.call_args
    assert call_args[1]['success'] is False
    assert "API Error" in call_args[1]['error']


@pytest.mark.asyncio
async def test_get_detections(
    mock_service_clients,
    mock_security_manager,
    mock_tenant_id,
    mock_user_id
):
    """Test get_detections tool."""
    # Setup
    detections = [
        {"id": "DET-001", "severity": "critical", "status": "new"},
        {"id": "DET-002", "severity": "high", "status": "new"}
    ]
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json = Mock(return_value=detections)
    mock_service_clients.detection_service.get = AsyncMock(return_value=mock_response)
    
    # Execute
    result = await siem_tools.get_detections(
        severity="critical",
        status="new",
        tenant_id=mock_tenant_id,
        user_id=mock_user_id
    )
    
    # Assert
    assert result == detections
    assert len(result) == 2
    
    # Verify call was made with correct params
    call_args = mock_service_clients.detection_service.get.call_args
    assert call_args[1]['params']['severity'] == 'critical'
    assert call_args[1]['params']['status'] == 'new'


@pytest.mark.asyncio
async def test_get_incidents(
    mock_service_clients,
    mock_security_manager,
    mock_tenant_id,
    mock_user_id,
    sample_incident
):
    """Test get_incidents tool."""
    # Setup
    incidents = [sample_incident]
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json = Mock(return_value=incidents)
    mock_service_clients.ticketing_agent.get = AsyncMock(return_value=mock_response)
    
    # Execute
    result = await siem_tools.get_incidents(
        status="new",
        severity="high",
        tenant_id=mock_tenant_id,
        user_id=mock_user_id
    )
    
    # Assert
    assert result == incidents
    assert result[0]["id"] == "INC-123"
    assert result[0]["severity"] == "high"


@pytest.mark.asyncio
async def test_create_incident(
    mock_service_clients,
    mock_security_manager,
    mock_tenant_id,
    mock_user_id,
    sample_incident
):
    """Test create_incident tool."""
    # Setup
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json = Mock(return_value=sample_incident)
    mock_service_clients.ticketing_agent.post = AsyncMock(return_value=mock_response)
    
    # Execute
    result = await siem_tools.create_incident(
        title="Brute Force Attack",
        description="Multiple failed login attempts detected",
        severity="high",
        observables=["obs-001"],
        tenant_id=mock_tenant_id,
        user_id=mock_user_id
    )
    
    # Assert
    assert result == sample_incident
    assert result["title"] == "Brute Force Attack"
    
    # Verify incident data was passed correctly
    call_args = mock_service_clients.ticketing_agent.post.call_args
    incident_data = call_args[1]['json']
    assert incident_data['title'] == "Brute Force Attack"
    assert incident_data['severity'] == "high"
    assert "obs-001" in incident_data['observables']

