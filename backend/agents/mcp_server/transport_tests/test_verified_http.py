"""Actual MCP SDK HTTP with real RSA signatures and a mocked IAM transport."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import json
import time

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
import httpx
import jwt
import pytest

from app import verified_http
from app.core.tool_admission import WIRE_TOOL_MAP
from sg_core import iam_verification as verifier
from sg_core.user_principals import UserClientBinding, UserPrincipalSettings

TENANT = "e53ae16f-4381-4da5-9992-8d8d85b1d0eb"
USER = "238699f6-5d17-48a0-935f-539c6d3594cf"
ISSUER = "https://identity.internal.test/realms/synthetic"
_REAL_HTTP = httpx.Client


@pytest.fixture(autouse=True)
def no_downstream_effects(monkeypatch):
    import socket
    from sqlalchemy.engine import Engine

    def blocked(*args, **kwargs):
        pytest.fail("Unexpected downstream network/database effect")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    monkeypatch.setattr(Engine, "connect", blocked)


@pytest.fixture
def setup(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    claims = dict(
        sub=USER,
        tenant_id=TENANT,
        iss=ISSUER,
        aud="review-audience",
        azp="review-browser",
        typ="Bearer",
        sg_principal_type="user",
        sg_identity_contract="keycloak-user-v1",
        realm_access={"roles": ["SOC_ANALYST"]},
        exp=int(time.time()) + 60,
        iat=int(time.time()) - 1,
    )
    calls = []

    def transport(request):
        calls.append(request)
        assert (
            str(request.url)
            == "https://iam.internal.test/internal/iam/auth/validate-token"
        )
        token = json.loads(request.content)["token"]
        try:
            payload = jwt.decode(
                token,
                key.public_key(),
                algorithms=["RS256"],
                issuer=ISSUER,
                audience="review-audience",
            )
        except jwt.PyJWTError:
            return httpx.Response(200, json={"valid": False})
        return httpx.Response(
            200,
            json=dict(
                valid=True,
                payload=payload,
                tenant_id=payload["tenant_id"],
                user_id=payload["sub"],
                roles=payload["realm_access"]["roles"],
                expires_at=datetime.fromtimestamp(
                    payload["exp"], timezone.utc
                ).isoformat(),
            ),
        )

    monkeypatch.setattr(
        verifier.httpx,
        "Client",
        lambda **kwargs: _REAL_HTTP(transport=httpx.MockTransport(transport), **kwargs),
    )
    verification = verifier.IAMVerificationSettings(
        _env_file=None,
        IAM_AGENT_URL="https://iam.internal.test",
        KEYCLOAK_CLIENT_ID="review-audience",
    )
    users = UserPrincipalSettings(
        _env_file=None,
        IAM_USER_CLIENT_BINDINGS=(
            UserClientBinding(
                issuer=ISSUER,
                client_id="review-browser",
                tenant_id=TENANT,
                contract="keycloak-user-v1",
                service_accounts_enabled=False,
                token_exchange_enabled=False,
            ),
        ),
    )
    app = verified_http.create_verified_http_app(
        verification=verification, users=users, allowed_hosts=("testserver",)
    )

    def sign(**update):
        return jwt.encode(
            {**claims, **update}, key, algorithm="RS256", headers={"kid": "review-key"}
        )

    return app, sign, calls


def rpc(client, method, headers=None, params=None):
    return client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            **({"params": params} if params is not None else {}),
        },
        headers={"Accept": "application/json, text/event-stream", **(headers or {})},
    )


def test_sdk_discovery_is_authenticated_and_execution_remains_unavailable(
    setup, monkeypatch
):
    app, sign, calls = setup
    seen = []
    original = verified_http.get_transport_caller
    # Observe context at the real SDK boundary, not a substituted authentication function.
    from mcp.types import ListToolsRequest

    # Record from the factory's real core server via the existing request context.
    old_factory = verified_http.create_core_server

    def factory():
        server = old_factory()
        handler = server.request_handlers[ListToolsRequest]

        async def inspect(request):
            caller = original(server.request_context.request)
            seen.append(caller)
            with pytest.raises(FrozenInstanceError):
                caller.tenant_id = USER
            return await handler(request)

        server.request_handlers[ListToolsRequest] = inspect
        return server

    monkeypatch.setattr(verified_http, "create_core_server", factory)
    app = verified_http.create_verified_http_app(
        verification=app.state.iam_verification_settings,
        users=app.state.user_principal_settings,
        allowed_hosts=("testserver",),
    )
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer " + sign()}
        response = rpc(client, "tools/list", headers)
        assert response.status_code == 200
        assert {t["name"] for t in response.json()["result"]["tools"]} == set(
            WIRE_TOOL_MAP
        )
        assert (
            str(seen[0].tenant_id) == TENANT and str(seen[0].actor_subject_id) == USER
        )
        assert seen[0].capabilities == ()
        for tool in WIRE_TOOL_MAP:
            response = rpc(
                client,
                "tools/call",
                headers,
                {
                    "name": tool,
                    "arguments": {
                        "tenant_id": "forged",
                        "user_id": "target",
                        "approved": True,
                    },
                },
            )
            assert (
                response.status_code == 200
                and response.json()["result"]["isError"] is True
            )
        assert (
            rpc(
                client,
                "tools/call",
                headers,
                {"name": "identity.lock_account", "arguments": {}},
            ).json()["error"]["code"]
            == -32602
        )
    assert len(calls) == 14


@pytest.mark.parametrize(
    "update,status",
    [
        ({"tenant_id": "6308d149-5958-48ed-a052-075a1ec50fe5"}, 403),
        ({"exp": 1}, 401),
        ({"sg_principal_type": "workload"}, 403),
        ({"azp": "other-client"}, 403),
    ],
)
def test_wrong_expired_or_unbound_identity_denied_before_sdk(setup, update, status):
    app, sign, calls = setup
    with TestClient(app) as client:
        response = rpc(
            client, "tools/list", {"Authorization": "Bearer " + sign(**update)}
        )
        assert response.status_code == status and "result" not in response.json()
    assert len(calls) == 1


@pytest.mark.parametrize(
    "headers,status",
    [
        ({}, 401),
        ({"Cookie": "access_token=synthetic"}, 403),
        (
            {
                "Authorization": "Bearer session-cookie",
                "Cookie": "access_token=synthetic",
            },
            403,
        ),
        ({"Authorization": "Bearer forged", "Origin": "https://attacker.test"}, 403),
    ],
)
def test_unverified_wire_credentials_or_origins_never_reach_verifier(
    setup, headers, status
):
    app, sign, calls = setup
    with TestClient(app) as client:
        assert rpc(client, "tools/list", headers).status_code == status
    assert calls == []


@pytest.mark.parametrize(
    "name",
    ["x-tenant-id", "x-user-id", "x-roles", "x-realm", "x-internal-service-token"],
)
def test_headers_cannot_replace_verified_actor_or_tenant(setup, name):
    app, sign, calls = setup
    with TestClient(app) as client:
        assert (
            rpc(
                client,
                "tools/list",
                {"Authorization": "Bearer " + sign(), name: "forged"},
            ).status_code
            == 403
        )
    assert len(calls) == 1
