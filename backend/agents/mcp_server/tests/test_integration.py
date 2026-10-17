"""Real MCP1.x session checks; no conditionally skipped handler assertions."""

import copy
import hashlib
import json
from datetime import timedelta
import pytest
import mcp.types as types
from mcp.shared.exceptions import McpError
from mcp.shared.memory import create_connected_server_and_client_session
from app.servers.core_server import create_core_server
from app.core.tool_admission import WIRE_TOOL_MAP, UNAVAILABLE_MESSAGE

SCHEMA_DIGESTS = {
    "search_logs": "de71b2835eb4194c7e4a35a4137f21465c78aac9348070017dce0640bbe14e62",
    "get_detections": "4f62e71ede98fb9eb4f039e4247aba63fb9c9d413c1bb263b18f5306eac69e44",
    "get_incidents": "c1512b8e5db6abe24481265dab3f069f84eac4376c6773ca9e3e12dd1863ecf5",
    "create_incident": "e3abfb593693999a48e65dfa92114a1f5b07bada4e08ca88626062154c6757de",
    "list_playbooks": "be62292184dad15670ef4ac0877d4501168bfc27f902b964fd4c3fba1c497d25",
    "get_playbook": "354d582e1ec82edfd8bbfa2be95d332024c16735e2d972735487daabd2411076",
    "run_playbook": "a39f1606dfdc31f7ac8e00132eb70a46c1572cd12d1028784537fd2f7a7de980",
    "get_playbook_execution": "e18637eb67f5565835340f05d1edfd0bba99e511c7ed34bc23caac93a0d3737f",
    "get_user": "c8b29ef59dc3b608b3d2100a3b543a24c06348070be1dd145385bb2534aa74e8",
    "lock_account": "074729ea4e28f46fdb625fae9efc01b236bdf93451400d02b464869a275b1583",
    "get_observable": "6d622aad8e1d635e8e84e4f12ec5e09b4af6f17cf56929722b6d2e3f88347e74",
    "search_observables": "60f3165e60d341b13b00a7889cb0c107b8f4e464f092c8f06c86d9efba69c62d",
}


async def test_real_session_initialization_discovery_ping_and_schema_compatibility():
    server = create_core_server(tenant_id="unverified", user_id="unverified")
    async with create_connected_server_and_client_session(
        server, read_timeout_seconds=timedelta(seconds=5)
    ) as session:
        await session.send_ping()
        tools = (await session.list_tools()).tools
        assert {t.name for t in tools} == set(WIRE_TOOL_MAP) == set(SCHEMA_DIGESTS)
        for tool in tools:
            assert tool.description.startswith("Unavailable source-preview tool.")
            assert (
                hashlib.sha256(
                    json.dumps(tool.inputSchema, sort_keys=True).encode()
                ).hexdigest()
                == SCHEMA_DIGESTS[tool.name]
            )


@pytest.mark.parametrize(
    "name", [*SCHEMA_DIGESTS, "unknown", "identity.lock_account", "LOCK_ACCOUNT"]
)
async def test_real_session_reports_tool_error_and_preserves_target(name):
    server = create_core_server(
        tenant_id="00000000-0000-0000-0000-000000000001",
        user_id="00000000-0000-0000-0000-000000000002",
    )
    arguments = {
        "user_id": "target-user",
        "tenant_id": "other-tenant",
        "approved": True,
        "token": "synthetic-secret",
        "query": {"model_authority": "admin"},
    }
    before = copy.deepcopy(arguments)
    async with create_connected_server_and_client_session(
        server, read_timeout_seconds=timedelta(seconds=5)
    ) as session:
        if name not in WIRE_TOOL_MAP:
            with pytest.raises(McpError) as error:
                await session.call_tool(name, arguments)
            assert error.value.error.code == types.INVALID_PARAMS
            assert error.value.error.message == "Unknown MCP tool"
            assert arguments == before
            return
        result = await session.call_tool(name, arguments)
        assert result.isError is True
        assert not result.structuredContent
        assert result.content and all(
            "synthetic-secret" not in item.text for item in result.content
        )
    assert arguments == before


async def test_handler_rejects_without_traversing_or_mutating_arguments():
    class HostileDict(dict):
        def __iter__(self):
            raise AssertionError("arguments traversed")

        def __setitem__(self, *args):
            raise AssertionError("arguments changed")

    server = create_core_server(user_id="caller-not-target")
    handler = server.request_handlers[types.CallToolRequest]
    request = types.CallToolRequest(
        params=types.CallToolRequestParams(
            name="get_user", arguments={"user_id": "target"}
        )
    )
    request.params.arguments = HostileDict(user_id="target")
    result = (await handler(request)).root
    assert result.isError is True
    assert result.content[0].text == UNAVAILABLE_MESSAGE
    assert request.params.arguments["user_id"] == "target"


async def test_real_stdio_ignores_environment_identity_and_never_constructs_clients():
    import os
    import sys
    from pathlib import Path
    import mcp
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    root = Path(__file__).resolve().parents[1]
    code = """
from unittest.mock import patch
import asyncio, socket, httpx, psycopg2
from sqlalchemy.engine import Engine
def blocked(*args, **kwargs): raise AssertionError('Forbidden downstream effect')
with patch.object(httpx.Client, '__init__', blocked), patch.object(httpx.AsyncClient, '__init__', blocked), patch.object(socket.socket, 'connect', blocked), patch.object(socket.socket, 'connect_ex', blocked), patch.object(socket, 'getaddrinfo', blocked), patch.object(psycopg2, 'connect', blocked), patch.object(Engine, 'connect', blocked):
    from app.main import main
    asyncio.run(main())
"""
    environment = {
        "PYTHONPATH": os.pathsep.join(
            [
                str(root),
                str(root.parents[1] / "libs"),
                str(Path(mcp.__file__).resolve().parents[1]),
            ]
        ),
        "PYTHONDONTWRITEBYTECODE": "1",
        "MCP_TENANT_ID": "00000000-0000-0000-0000-000000000001",
        "MCP_USER_ID": "00000000-0000-0000-0000-000000000002",
        "MCP_REQUIRE_APPROVAL_FOR_HIGH_RISK": "false",
        "INTERNAL_SERVICE_TOKEN": "synthetic-unused-token",
    }
    params = StdioServerParameters(
        command=sys.executable, args=["-c", code], env=environment
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(
            read, write, read_timeout_seconds=timedelta(seconds=10)
        ) as session:
            await session.initialize()
            assert len((await session.list_tools()).tools) == 12
            result = await session.call_tool(
                "lock_account", {"user_id": "target-user", "approved": True}
            )
            assert result.isError is True
            assert result.content[0].text == UNAVAILABLE_MESSAGE
