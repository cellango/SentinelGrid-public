"""Direct legacy helpers cannot bypass the unavailable MCP surface."""

import pytest
from app.tools import siem_tools
from app.core.tool_admission import MCPToolUnavailable


@pytest.mark.parametrize(
    "name,arguments",
    [
        (
            "search_logs",
            {"query": "synthetic", "tenant_id": "tenant", "user_id": "actor"},
        ),
        ("get_detections", {"tenant_id": "tenant", "user_id": "actor"}),
        ("get_incidents", {"tenant_id": "tenant", "user_id": "actor"}),
        (
            "create_incident",
            {
                "title": "synthetic",
                "description": "synthetic",
                "severity": "low",
                "tenant_id": "tenant",
                "user_id": "actor",
            },
        ),
    ],
)
async def test_direct_helper_rejects_before_downstream_dependencies(name, arguments):
    with pytest.raises(MCPToolUnavailable):
        await getattr(siem_tools, name)(**arguments)
