"""Integration tests for MCP server."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import json

from app.servers.core_server import create_core_server


@pytest.mark.asyncio
async def test_mcp_server_creation():
    """Test MCP server can be created."""
    server = create_core_server(tenant_id="tenant-123", user_id="user-456")
    
    assert server is not None
    assert server.name == "sentinelgrid-core"


@pytest.mark.asyncio
async def test_list_tools():
    """Test listing available tools."""
    server = create_core_server(tenant_id="tenant-123", user_id="user-456")
    
    # Get list_tools handler
    list_tools_handler = None
    for handler in server._request_handlers.values():
        if hasattr(handler, '__name__') and 'list_tools' in handler.__name__:
            list_tools_handler = handler
            break
    
    if list_tools_handler:
        tools = await list_tools_handler()
        
        assert len(tools) > 0
        
        # Verify key tools are present
        tool_names = [t.name for t in tools]
        assert "search_logs" in tool_names
        assert "get_incidents" in tool_names
        assert "run_playbook" in tool_names
        assert "lock_account" in tool_names
        assert "get_observable" in tool_names
        
        # Verify tool has proper schema
        search_logs_tool = next(t for t in tools if t.name == "search_logs")
        assert search_logs_tool.description is not None
        assert search_logs_tool.inputSchema is not None
        assert "query" in search_logs_tool.inputSchema["properties"]


@pytest.mark.asyncio
async def test_tool_execution_workflow(
    mock_service_clients,
    mock_security_manager
):
    """Test end-to-end tool execution workflow."""
    # Setup
    server = create_core_server(tenant_id="tenant-123", user_id="user-456")
    
    # Mock API response
    search_result = {
        "total": 1,
        "hits": [{"timestamp": "2024-12-02T10:00:00Z", "message": "Failed login"}]
    }
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json = Mock(return_value=search_result)
    mock_service_clients.siem_agent.post = AsyncMock(return_value=mock_response)
    
    # Get call_tool handler
    call_tool_handler = None
    for handler in server._request_handlers.values():
        if hasattr(handler, '__name__') and 'call_tool' in handler.__name__:
            call_tool_handler = handler
            break
    
    if call_tool_handler:
        # Execute tool
        with patch('app.tools.siem_tools.clients', mock_service_clients):
            with patch('app.tools.siem_tools.security_manager', mock_security_manager):
                result = await call_tool_handler(
                    name="search_logs",
                    arguments={
                        "query": "failed_login",
                        "time_range": "1h"
                    }
                )
        
        # Verify result
        assert len(result) == 1
        assert result[0].type == "text"
        
        # Parse JSON response
        response_data = json.loads(result[0].text)
        assert response_data["total"] == 1
        assert len(response_data["hits"]) == 1
        
        # Verify authorization was checked
        mock_security_manager.authorize_tool_call.assert_called()
        
        # Verify audit was logged
        mock_security_manager.audit_tool_call.assert_called()


@pytest.mark.asyncio
async def test_tool_execution_error_handling(
    mock_service_clients,
    mock_security_manager
):
    """Test error handling in tool execution."""
    server = create_core_server(tenant_id="tenant-123", user_id="user-456")
    
    # Setup - simulate API error
    mock_service_clients.siem_agent.post = AsyncMock(
        side_effect=Exception("API Connection Error")
    )
    
    # Get call_tool handler
    call_tool_handler = None
    for handler in server._request_handlers.values():
        if hasattr(handler, '__name__') and 'call_tool' in handler.__name__:
            call_tool_handler = handler
            break
    
    if call_tool_handler:
        # Execute tool
        with patch('app.tools.siem_tools.clients', mock_service_clients):
            with patch('app.tools.siem_tools.security_manager', mock_security_manager):
                result = await call_tool_handler(
                    name="search_logs",
                    arguments={"query": "test"}
                )
        
        # Verify error is returned
        assert len(result) == 1
        assert "Error executing search_logs" in result[0].text
        assert "API Connection Error" in result[0].text


@pytest.mark.asyncio
async def test_unknown_tool_handling():
    """Test handling of unknown tool calls."""
    server = create_core_server(tenant_id="tenant-123", user_id="user-456")
    
    # Get call_tool handler
    call_tool_handler = None
    for handler in server._request_handlers.values():
        if hasattr(handler, '__name__') and 'call_tool' in handler.__name__:
            call_tool_handler = handler
            break
    
    if call_tool_handler:
        result = await call_tool_handler(
            name="unknown_tool",
            arguments={}
        )
        
        assert len(result) == 1
        assert "Unknown tool: unknown_tool" in result[0].text

