"""Direct legacy helpers cannot bypass the unavailable MCP surface."""

import pytest
from app.tools import iam_tools
from app.core.tool_admission import MCPToolUnavailable


@pytest.mark.parametrize(
    "name,arguments",
    [
        (
            "get_user",
            {
                "user_id": "target-user",
                "tenant_id": "tenant",
                "requesting_user_id": "actor",
            },
        ),
        (
            "lock_account",
            {
                "user_id": "target-user",
                "reason": "synthetic",
                "tenant_id": "tenant",
                "requesting_user_id": "actor",
            },
        ),
    ],
)
async def test_direct_helper_rejects_before_downstream_dependencies(name, arguments):
    with pytest.raises(MCPToolUnavailable):
        await getattr(iam_tools, name)(**arguments)


@pytest.mark.parametrize(
    "name,arguments",
    [
        (
            "get_user",
            {
                "user_id": "target-user",
                "tenant_id": "tenant",
                "requesting_user_id": "actor",
            },
        ),
        (
            "lock_account",
            {
                "user_id": "target-user",
                "reason": "synthetic",
                "tenant_id": "tenant",
                "requesting_user_id": "actor",
            },
        ),
    ],
)
async def test_raw_client_guard_remains_when_legacy_authorizer_is_bypassed(
    name, arguments, monkeypatch
):
    from unittest.mock import AsyncMock

    monkeypatch.setattr(
        iam_tools.security_manager, "authorize_tool_call", AsyncMock(return_value=True)
    )
    with pytest.raises(MCPToolUnavailable):
        await getattr(iam_tools, name)(**arguments)
