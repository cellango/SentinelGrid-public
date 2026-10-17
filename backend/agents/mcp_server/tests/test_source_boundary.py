"""Raw clients, helper imports and environment values cannot confer authority."""

import ast
import importlib
from pathlib import Path
import pytest
from app.core.service_clients import ServiceClients, clients
from app.core.tool_admission import MCPToolUnavailable
from app.tools import observable_tools


@pytest.mark.parametrize("service", sorted(ServiceClients.SERVICE_NAMES))
def test_raw_service_clients_are_unavailable_without_credentials_or_http(service):
    with pytest.raises(MCPToolUnavailable):
        getattr(clients, service)


async def test_imports_and_shutdown_never_construct_http_clients(monkeypatch):
    import app.main
    import app.core.security
    import app.core.service_clients
    import app.servers.core_server

    for module in [
        app.main,
        app.core.security,
        app.core.service_clients,
        app.servers.core_server,
    ]:
        importlib.reload(module)
    await app.core.service_clients.clients.close_all()
    with pytest.raises(MCPToolUnavailable):
        clients.add_tenant_header("arbitrary-tenant")
    with pytest.raises(AttributeError):
        getattr(clients, "arbitrary_service")


@pytest.mark.parametrize(
    "name,arguments",
    [
        (
            "get_observable",
            {"observable_id": "synthetic", "tenant_id": "tenant", "user_id": "actor"},
        ),
        ("search_observables", {"tenant_id": "tenant", "user_id": "actor"}),
    ],
)
async def test_observable_helpers_are_also_unavailable(name, arguments):
    with pytest.raises(MCPToolUnavailable):
        await getattr(observable_tools, name)(**arguments)


def test_entrypoint_never_uses_environment_identity_or_loads_tool_clients():
    root = Path(__file__).resolve().parents[1] / "app"
    main = ast.parse((root / "main.py").read_text())
    assert not any(
        isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr in {"getenv", "getenvb"}
        for n in ast.walk(main)
    )
    core = ast.parse((root / "servers/core_server.py").read_text())
    assert not any(
        isinstance(n, ast.ImportFrom)
        and n.module
        and (n.module.startswith("app.tools") or n.module == "app.core.service_clients")
        for n in ast.walk(core)
    )
