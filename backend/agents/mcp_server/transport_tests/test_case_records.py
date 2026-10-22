"""Real SDK HTTP and signed users; bounded receiver HTTP is mocked here.

Native PostgreSQL + actual receiving API checks are a separate non-skipping gate.
"""

from types import SimpleNamespace
import gzip, json, time
from uuid import uuid4
import anyio, httpx, pytest
from fastapi.testclient import TestClient
from app import verified_http
from app.core import case_records
from app.core.case_records import CaseRecordPolicy, WIRE_OPERATIONS
from app.core.tool_admission import WIRE_TOOL_MAP
from sg_core.action_contracts import ProposalInput, proposal_payload, digest
from sg_core.http_rate_limit import RateLimitPolicy
from sg_core.iam_verification import IAMVerificationSettings
from test_verified_http import (
    setup as setup,
    no_downstream_effects as no_downstream_effects,
    rpc,
    TENANT,
    USER,
)

REAL_ASYNC = httpx.AsyncClient
CASE = "33333333-3333-4333-8333-333333333333"
PROPOSAL = "44444444-4444-4444-8444-444444444444"
ACTION = "55555555-5555-4555-8555-555555555555"
TARGET = "66666666-6666-4666-8666-666666666666"


def body():
    return dict(
        tool_id="identity.lock_account",
        tool_version="source-preview-v1",
        targets=[dict(kind="identity.user", resource_id=TARGET)],
        parameters={"reason": "Synthetic investigation"},
        risk="high",
        expected_effect="Account locked",
        verification={"check": "authoritative directory state"},
        expires_at=int(time.time()) + 300,
    )


def metadata():
    return dict(
        tenant_id=TENANT,
        case_id=CASE,
        action_id=ACTION,
        proposal_id=PROPOSAL,
        proposal_hash="a" * 64,
        proposal_revision=1,
        status="pending_approval",
        execution_available=False,
    )


def document():
    return proposal_payload(
        ProposalInput.model_validate(body()),
        tenant_id=TENANT,
        case_id=CASE,
        case_revision=1,
        plan_revision=1,
        policy_version="action-policy-v1",
        action_id=ACTION,
        proposal_id=PROPOSAL,
        actor_id=USER,
    )


@pytest.fixture
def bridge(setup, monkeypatch):
    original, sign, iam_calls = setup
    state = SimpleNamespace(calls=[], options=[], response=None, delay=0, fail=False)

    async def transport(request):
        state.calls.append(request)
        if state.delay:
            await anyio.sleep(state.delay)
        if state.fail:
            raise httpx.ReadTimeout("synthetic-secret-not-for-output")
        if state.response is not None:
            return state.response
        value = metadata()
        if request.method == "GET":
            value["proposal"] = document()
            value["proposal_hash"] = digest(value["proposal"])
        return httpx.Response(201 if request.method == "POST" else 200, json=value)

    def factory(**kwargs):
        state.options.append(kwargs)
        return REAL_ASYNC(transport=httpx.MockTransport(transport), **kwargs)

    monkeypatch.setattr(case_records.httpx, "AsyncClient", factory)
    policy = CaseRecordPolicy(origin="http://case_runtime:8000")
    app = verified_http.create_verified_http_app(
        verification=original.state.iam_verification_settings,
        users=original.state.user_principal_settings,
        allowed_hosts=("testserver",),
        case_records=policy,
    )
    with TestClient(app) as client:
        state.client = client
        state.app = app
        state.sign = sign
        state.iam_calls = iam_calls
        yield state


def invoke(bridge, name="case_propose_action", arguments=None, headers=None):
    arguments = (
        arguments
        if arguments is not None
        else {"case_id": CASE, "request_key": str(uuid4()), "proposal": body()}
    )
    return rpc(
        bridge.client,
        "tools/call",
        headers or {"Authorization": "Bearer " + bridge.sign()},
        dict(name=name, arguments=arguments),
    )


def test_discovery_adds_only_record_tools_and_legacy_stays_closed(bridge):
    response = rpc(
        bridge.client, "tools/list", {"Authorization": "Bearer " + bridge.sign()}
    )
    tools = response.json()["result"]["tools"]
    assert {x["name"] for x in tools} == set(WIRE_TOOL_MAP) | set(WIRE_OPERATIONS)
    for tool in WIRE_OPERATIONS:
        annotations = next(x["annotations"] for x in tools if x["name"] == tool)
        assert (
            annotations["destructiveHint"] is False
            and annotations["idempotentHint"] is True
        )
    for tool in [
        *WIRE_TOOL_MAP,
        "case_approve_action",
        "case_execute_action",
        "identity.lock_account",
    ]:
        result = invoke(bridge, tool).json()
        assert (
            result.get("result", {}).get("isError") is True
            or result["error"]["code"] == -32602
        )
    assert bridge.calls == []


def test_submission_forwards_only_verified_identity_and_stable_key(bridge):
    arguments = {"case_id": CASE, "request_key": str(uuid4()), "proposal": body()}
    token = bridge.sign()
    result = invoke(
        bridge, arguments=arguments, headers={"Authorization": "Bearer " + token}
    ).json()["result"]
    assert not result["isError"] and result["structuredContent"] == metadata()
    call = bridge.calls[0]
    assert (
        str(call.url)
        == "http://case_runtime:8000/api/v1/cases/" + CASE + "/action-proposals"
    )
    assert (
        call.method == "POST"
        and call.headers["authorization"] == "Bearer " + token
        and call.headers["x-tenant-id"] == TENANT
    )
    assert call.headers["idempotency-key"] == arguments["request_key"]
    assert (
        json.loads(call.content)
        == ProposalInput.model_validate(arguments["proposal"]).model_dump()
    )
    assert not {"cookie", "x-user-id", "x-roles", "x-internal-token"} & set(
        call.headers
    )
    assert (
        bridge.options[0]["verify"] is True
        and bridge.options[0]["trust_env"] is False
        and bridge.options[0]["follow_redirects"] is False
    )


def test_read_verifies_exact_document_hash_and_bound_case(bridge):
    result = invoke(
        bridge, "case_get_action_proposal", {"case_id": CASE, "proposal_id": PROPOSAL}
    ).json()["result"]
    assert (
        not result["isError"]
        and result["structuredContent"]["proposal"]["tenant_id"] == TENANT
    )
    assert bridge.calls[0].method == "GET" and str(bridge.calls[0].url).endswith(
        "/" + PROPOSAL
    )
    assert "idempotency-key" not in bridge.calls[0].headers


@pytest.mark.parametrize(
    "extra",
    [
        {"tenant_id": str(uuid4())},
        {"user_id": USER},
        {"approved": True},
        {"requires_approval": False},
        {"origin": "https://attacker.test"},
        {"authorization": "forged"},
    ],
)
def test_tool_arguments_cannot_supply_authority_or_destination(bridge, extra):
    args = {"case_id": CASE, "request_key": str(uuid4()), "proposal": body(), **extra}
    response = invoke(bridge, arguments=args)
    assert (
        response.json()["error"]["code"] == -32602
        and bridge.calls == []
        and bridge.options == []
    )


@pytest.mark.parametrize(
    "patch",
    [
        {"case_id": "other"},
        {"request_key": "../../escape"},
        {"case_id": None},
        {"proposal": {"requires_approval": False}},
    ],
)
def test_invalid_ids_or_proposal_are_protocol_errors_before_client(bridge, patch):
    args = {"case_id": CASE, "request_key": str(uuid4()), "proposal": body(), **patch}
    assert (
        invoke(bridge, arguments=args).json()["error"]["code"] == -32602
        and bridge.calls == []
    )


@pytest.mark.parametrize(
    "patch",
    [
        {"tenant_id": str(uuid4())},
        {"case_id": str(uuid4())},
        {"execution_available": True},
        {"execution_available": 0},
        {"status": "verified"},
        {"proposal_hash": "not-a-hash"},
        {"unexpected": "synthetic-secret-not-for-output"},
    ],
)
def test_untrusted_receipt_cannot_change_binding_or_claim_execution(bridge, patch):
    bridge.response = httpx.Response(201, json={**metadata(), **patch})
    result = invoke(bridge).json()["result"]
    assert (
        result["isError"]
        and result["structuredContent"]["execution_available"] is False
    )
    assert "synthetic-secret-not-for-output" not in json.dumps(result)


@pytest.mark.parametrize(
    "status", [202, 301, 401, 403, 404, 409, 410, 422, 429, 500, 503]
)
def test_receiver_failure_status_never_becomes_success_or_leaks_body(bridge, status):
    bridge.response = httpx.Response(
        status,
        json={"message": "synthetic-secret-not-for-output"},
        headers={"Location": "https://attacker.test"},
    )
    result = invoke(bridge).json()["result"]
    assert result["isError"] and len(bridge.calls) == 1
    assert "synthetic-secret-not-for-output" not in json.dumps(result)


@pytest.mark.parametrize(
    "bad", ["hash", "tenant", "case", "proposal", "action", "revision", "missing"]
)
def test_read_document_integrity_failures_are_unavailable(bridge, bad):
    value = metadata()
    doc = document()
    value.update(proposal=doc, proposal_hash=digest(doc))
    if bad == "hash":
        value["proposal_hash"] = "0" * 64
    elif bad == "missing":
        del value["proposal"]
    else:
        key = {
            "tenant": "tenant_id",
            "case": "case_id",
            "proposal": "proposal_id",
            "action": "action_id",
            "revision": "proposal_revision",
        }[bad]
        doc[key] = 2 if bad == "revision" else str(uuid4())
        value["proposal_hash"] = digest(doc)
    bridge.response = httpx.Response(200, json=value)
    result = invoke(
        bridge, "case_get_action_proposal", {"case_id": CASE, "proposal_id": PROPOSAL}
    ).json()["result"]
    assert result["isError"]


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(
            201, content=b"x" * 65537, headers={"Content-Type": "application/json"}
        ),
        httpx.Response(
            201,
            content=b'{"tenant_id":"one","tenant_id":"two"}',
            headers={"Content-Type": "application/json"},
        ),
        httpx.Response(
            201,
            content=gzip.compress(json.dumps(metadata()).encode()),
            headers={"Content-Encoding": "gzip", "Content-Type": "application/json"},
        ),
        httpx.Response(201, content=b"not-json", headers={"Content-Type": "text/html"}),
    ],
)
def test_bounded_strict_json_reply_and_encoding(bridge, response):
    bridge.response = response
    assert invoke(bridge).json()["result"]["isError"]


def test_transport_failure_is_sanitized(bridge):
    bridge.fail = True
    result = invoke(bridge).json()["result"]
    assert result["isError"] and "synthetic-secret-not-for-output" not in json.dumps(
        result
    )


@pytest.mark.parametrize(
    "raw",
    [
        b'{"jsonrpc":"2.0","id":1,"id":2,"method":"tools/list"}',
        b'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"case_propose_action","arguments":{"case_id":"one","case_id":"two"}}}',
    ],
)
def test_duplicate_rpc_fields_rejected_before_sdk_and_receiver(bridge, raw):
    response = bridge.client.post(
        "/mcp",
        content=raw,
        headers={
            "Authorization": "Bearer " + bridge.sign(),
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    assert response.status_code == 400 and bridge.calls == []


@pytest.mark.parametrize(
    "origin",
    [
        "http://user:secret@host",
        "http://host/path",
        "http://host?override=x",
        "http://host#fragment",
        "ftp://host",
        "http://host/%2f",
        "http://host:0",
        "http://host\\evil",
        23,
    ],
)
def test_owned_destination_validation(origin):
    with pytest.raises(ValueError):
        CaseRecordPolicy(origin=origin)


def test_owned_read_only_profile_has_no_submission_tool(setup):
    original, sign, calls = setup
    policy = CaseRecordPolicy(
        origin="http://case_runtime:8000", operations=("case.get_action_proposal",)
    )
    app = verified_http.create_verified_http_app(
        verification=original.state.iam_verification_settings,
        users=original.state.user_principal_settings,
        allowed_hosts=("testserver",),
        case_records=policy,
    )
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer " + sign()}
        names = {
            v["name"]
            for v in rpc(client, "tools/list", headers).json()["result"]["tools"]
        }
        assert (
            "case_get_action_proposal" in names and "case_propose_action" not in names
        )
        result = rpc(
            client,
            "tools/call",
            headers,
            {"name": "case_propose_action", "arguments": {}},
        ).json()
        assert result["error"]["code"] == -32602


def test_nondev_destination_requires_https(setup):
    original, _, _ = setup
    config = IAMVerificationSettings(
        _env_file=None,
        ENVIRONMENT="production",
        IAM_AGENT_URL="https://iam.internal.test",
        KEYCLOAK_CLIENT_ID="review-audience",
    )
    with pytest.raises(ValueError, match="TLS required"):
        verified_http.create_verified_http_app(
            verification=config,
            users=original.state.user_principal_settings,
            allowed_hosts=("testserver",),
            rate_policy=RateLimitPolicy(
                enabled=True, redis_url="rediss://budget.internal.test:6379/0"
            ),
            case_records=CaseRecordPolicy(origin="http://case_runtime:8000"),
        )


def test_owned_deadline_bounds_slow_receiver(bridge):
    bridge.delay = 1
    policy = CaseRecordPolicy(origin="http://case_runtime:8000", timeout_seconds=0.01)
    app = verified_http.create_verified_http_app(
        verification=bridge.app.state.iam_verification_settings,
        users=bridge.app.state.user_principal_settings,
        allowed_hosts=("testserver",),
        case_records=policy,
    )
    with TestClient(app) as client:
        result = rpc(
            client,
            "tools/call",
            {"Authorization": "Bearer " + bridge.sign()},
            {
                "name": "case_propose_action",
                "arguments": {
                    "case_id": CASE,
                    "request_key": str(uuid4()),
                    "proposal": body(),
                },
            },
        ).json()["result"]
        assert result["isError"] and len(bridge.calls) == 1


def test_identity_expiry_while_waiting_does_not_release_record(bridge):
    bridge.delay = 2.1
    token = bridge.sign(exp=int(time.time()) + 2)
    result = invoke(bridge, headers={"Authorization": "Bearer " + token}).json()[
        "result"
    ]
    assert result["isError"] and "proposal_hash" not in result["structuredContent"]


@pytest.mark.asyncio
async def test_constructed_caller_without_authenticated_sdk_scope_grants_nothing(
    bridge,
):
    from starlette.requests import Request
    from uuid import UUID

    request = Request(
        {
            "type": "http",
            "headers": [(b"authorization", ("Bearer " + bridge.sign()).encode())],
            "app": bridge.app,
        }
    )
    request.state.caller = verified_http.MCPTransportCaller(
        UUID(TENANT),
        UUID(USER),
        "review-browser",
        time.time() + 100,
        tuple(WIRE_OPERATIONS.values()),
    )
    adapter = case_records.CaseRecordTools(
        bridge.app.state.case_record_policy, verified_http.get_transport_caller
    )
    result = await adapter.call(
        request,
        "case_propose_action",
        {"case_id": CASE, "request_key": str(uuid4()), "proposal": body()},
    )
    assert result.isError and bridge.calls == []
