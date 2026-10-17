"""No caller/body/config string is proof of tool or audit authority."""

import copy
from uuid import UUID
import pytest
from app.core.security import MCPSecurityManager
from app.core.tool_admission import MCPToolUnavailable, WIRE_TOOL_MAP

TENANT = str(UUID(int=1))
ACTOR = str(UUID(int=2))


@pytest.mark.parametrize(
    "tool", [*WIRE_TOOL_MAP, "unknown", "identity.lock_account", "LOCK_ACCOUNT"]
)
@pytest.mark.parametrize("flags", [False, True])
async def test_strings_uuid_body_approval_and_flags_never_authorize(
    tool, flags, monkeypatch
):
    monkeypatch.setenv("MCP_TENANT_ID", TENANT)
    monkeypatch.setenv("MCP_USER_ID", ACTOR)
    monkeypatch.setenv("MCP_REQUIRE_APPROVAL_FOR_HIGH_RISK", str(flags).lower())
    manager = MCPSecurityManager()
    manager.audit_enabled = flags
    manager.require_approval_for_high_risk = flags
    params = {
        "tenant_id": TENANT,
        "requesting_user_id": ACTOR,
        "user_id": str(UUID(int=3)),
        "approved": True,
        "roles": ["admin"],
        "capabilities": ["*"],
        "token": "synthetic-secret",
    }
    before = copy.deepcopy(params)
    with pytest.raises(MCPToolUnavailable) as error:
        await manager.authorize_tool_call(tool, TENANT, ACTOR, params)
    assert "synthetic-secret" not in str(error.value)
    assert params == before


@pytest.mark.parametrize(
    "tenant,actor", [("", ""), (None, None), ("tenant-slug", "admin"), (TENANT, ACTOR)]
)
async def test_audit_cannot_emit_unverified_identity_or_success(tenant, actor):
    manager = MCPSecurityManager()
    with pytest.raises(MCPToolUnavailable):
        await manager.audit_tool_call(
            "lock_account", tenant, actor, {}, {"verified": True}, True
        )


def test_classifications_are_metadata_and_include_every_write():
    manager = MCPSecurityManager()
    assert {name for name in WIRE_TOOL_MAP if manager.is_high_risk_tool(name)} == {
        "create_incident",
        "run_playbook",
        "lock_account",
    }
    assert manager.is_read_only_tool("get_playbook_execution")
    assert not manager.is_read_only_tool("unknown")
