"""Direct legacy helpers cannot bypass the unavailable MCP surface."""

import pytest
from app.tools import soar_tools
from app.core.tool_admission import MCPToolUnavailable


@pytest.mark.parametrize(
    "name,arguments",
    [
        ("list_playbooks", {"tenant_id": "tenant", "user_id": "actor"}),
        (
            "get_playbook",
            {"playbook_id": "synthetic", "tenant_id": "tenant", "user_id": "actor"},
        ),
        (
            "run_playbook",
            {
                "playbook_id": "synthetic",
                "params": {"approved": True},
                "tenant_id": "tenant",
                "user_id": "actor",
            },
        ),
        (
            "get_playbook_execution",
            {"execution_id": "synthetic", "tenant_id": "tenant", "user_id": "actor"},
        ),
    ],
)
async def test_direct_helper_rejects_before_downstream_dependencies(name, arguments):
    with pytest.raises(MCPToolUnavailable):
        await getattr(soar_tools, name)(**arguments)
