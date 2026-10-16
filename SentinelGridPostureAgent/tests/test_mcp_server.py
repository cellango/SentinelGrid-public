"""Tests for MCP server functionality."""

import pytest
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def test_tenant_id():
    """Test tenant ID."""
    return "test-tenant-123"


@pytest.fixture
def mock_posture_summary():
    """Mock posture summary data."""
    return {
        "tenant_id": "test-tenant-123",
        "posture_score": 78.5,
        "grade": "C",
        "total_findings": 15,
        "critical_findings": 2,
        "high_findings": 5,
        "medium_findings": 6,
        "low_findings": 2,
        "info_findings": 0,
        "findings_by_source": {"cspm": 10, "dast": 5},
        "total_assets": 50
    }


@pytest.fixture
def mock_findings_list():
    """Mock findings list data."""
    return {
        "findings": [
            {
                "id": "finding-1",
                "title": "Public S3 bucket",
                "severity": "critical",
                "status": "open",
                "source": "cspm",
                "tool": "prowler"
            },
            {
                "id": "finding-2",
                "title": "XSS vulnerability",
                "severity": "high",
                "status": "open",
                "source": "dast",
                "tool": "zap"
            }
        ],
        "total_count": 2
    }


class TestMCPTools:
    """Test MCP tool definitions."""
    
    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing available MCP tools."""
        # Import after path setup
        from services.mcp_server.app.main import list_tools
        
        tools = await list_tools()
        
        assert len(tools) >= 8  # We defined 8 tools
        
        tool_names = [t.name for t in tools]
        assert "get_posture_summary" in tool_names
        assert "list_findings" in tool_names
        assert "get_finding_details" in tool_names
        assert "analyze_observable" in tool_names
        assert "get_top_risks" in tool_names
        assert "list_analyzers" in tool_names
        assert "update_finding_status" in tool_names
        assert "list_assets" in tool_names
    
    @pytest.mark.asyncio
    async def test_get_posture_summary_tool_schema(self):
        """Test get_posture_summary tool has correct schema."""
        from services.mcp_server.app.main import list_tools
        
        tools = await list_tools()
        summary_tool = next(t for t in tools if t.name == "get_posture_summary")
        
        assert summary_tool.description
        assert "inputSchema" in summary_tool.__dict__
        schema = summary_tool.inputSchema
        assert "tenant_id" in schema["properties"]
        assert "tenant_id" in schema["required"]
    
    @pytest.mark.asyncio
    async def test_analyze_observable_tool_schema(self):
        """Test analyze_observable tool has correct schema."""
        from services.mcp_server.app.main import list_tools
        
        tools = await list_tools()
        analyze_tool = next(t for t in tools if t.name == "analyze_observable")
        
        schema = analyze_tool.inputSchema
        assert "tenant_id" in schema["properties"]
        assert "observable_type" in schema["properties"]
        assert "observable_value" in schema["properties"]
        assert all(k in schema["required"] for k in ["tenant_id", "observable_type", "observable_value"])


class TestMCPToolCalls:
    """Test MCP tool execution."""
    
    @pytest.mark.asyncio
    async def test_call_get_posture_summary(self, test_tenant_id, mock_posture_summary):
        """Test calling get_posture_summary tool."""
        from services.mcp_server.app.main import call_tool
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_posture_summary
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await call_tool(
                "get_posture_summary",
                {"tenant_id": test_tenant_id}
            )
            
            assert len(result) > 0
            assert result[0].type == "text"
            text = result[0].text
            assert test_tenant_id in text
            assert "78.5" in text  # Score
            assert "Grade: C" in text
    
    @pytest.mark.asyncio
    async def test_call_list_findings(self, test_tenant_id, mock_findings_list):
        """Test calling list_findings tool."""
        from services.mcp_server.app.main import call_tool
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_findings_list
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await call_tool(
                "list_findings",
                {"tenant_id": test_tenant_id, "severity": "critical"}
            )
            
            assert len(result) > 0
            text = result[0].text
            assert "Public S3 bucket" in text
            assert "CRITICAL" in text
    
    @pytest.mark.asyncio
    async def test_call_analyze_observable(self, test_tenant_id):
        """Test calling analyze_observable tool."""
        from services.mcp_server.app.main import call_tool
        
        mock_analysis_result = {
            "job_id": "abc-123",
            "analyzers_scheduled": ["zap-dast"],
            "status": "running"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_analysis_result
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await call_tool(
                "analyze_observable",
                {
                    "tenant_id": test_tenant_id,
                    "observable_type": "web_application",
                    "observable_value": "https://example.com"
                }
            )
            
            assert len(result) > 0
            text = result[0].text
            assert "abc-123" in text  # Job ID
            assert "zap-dast" in text
    
    @pytest.mark.asyncio
    async def test_call_update_finding_status(self, test_tenant_id):
        """Test calling update_finding_status tool."""
        from services.mcp_server.app.main import call_tool
        
        finding_id = "finding-123"
        mock_update_result = {
            "id": finding_id,
            "status": "fixed"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_update_result
            mock_client.return_value.__aenter__.return_value.patch.return_value = mock_response
            
            result = await call_tool(
                "update_finding_status",
                {
                    "finding_id": finding_id,
                    "status": "fixed",
                    "resolved_by": test_tenant_id
                }
            )
            
            assert len(result) > 0
            text = result[0].text
            assert finding_id in text
            assert "fixed" in text


class TestMCPResources:
    """Test MCP resources."""
    
    @pytest.mark.asyncio
    async def test_list_resources(self):
        """Test listing MCP resources."""
        from services.mcp_server.app.main import list_resources
        
        resources = await list_resources()
        
        assert len(resources) >= 3
        
        resource_uris = [r.uri for r in resources]
        assert any("posture://summary" in uri for uri in resource_uris)
        assert any("posture://findings" in uri for uri in resource_uris)
        assert any("posture://assets" in uri for uri in resource_uris)
    
    @pytest.mark.asyncio
    async def test_read_resource_summary(self, mock_posture_summary):
        """Test reading posture summary resource."""
        from services.mcp_server.app.main import read_resource
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.text = json.dumps(mock_posture_summary)
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await read_resource("posture://summary/test-tenant-123")
            
            assert result
            data = json.loads(result)
            assert data["tenant_id"] == "test-tenant-123"


class TestMCPPrompts:
    """Test MCP prompts."""
    
    @pytest.mark.asyncio
    async def test_list_prompts(self):
        """Test listing MCP prompts."""
        from services.mcp_server.app.main import list_prompts
        
        prompts = await list_prompts()
        
        assert len(prompts) >= 3
        
        prompt_names = [p.name for p in prompts]
        assert "analyze-posture" in prompt_names
        assert "prioritize-risks" in prompt_names
        assert "remediation-plan" in prompt_names
    
    @pytest.mark.asyncio
    async def test_get_analyze_posture_prompt(self):
        """Test getting analyze-posture prompt."""
        from services.mcp_server.app.main import get_prompt
        
        prompt_text = await get_prompt(
            "analyze-posture",
            {"tenant_id": "test-tenant"}
        )
        
        assert "test-tenant" in prompt_text
        assert "get_posture_summary" in prompt_text
        assert "get_top_risks" in prompt_text
    
    @pytest.mark.asyncio
    async def test_get_prioritize_risks_prompt(self):
        """Test getting prioritize-risks prompt."""
        from services.mcp_server.app.main import get_prompt
        
        prompt_text = await get_prompt(
            "prioritize-risks",
            {
                "tenant_id": "test-tenant",
                "business_context": "E-commerce platform"
            }
        )
        
        assert "test-tenant" in prompt_text
        assert "E-commerce platform" in prompt_text
        assert "prioritize" in prompt_text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

