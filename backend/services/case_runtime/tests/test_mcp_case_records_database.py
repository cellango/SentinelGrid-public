"""Real MCP SDK -> receiving ASGI API -> native Flyway/PostgreSQL.

Only the IAM HTTP transport is a synthetic RSA-verifying fixture. No identity,
case permission, database store or action handler is substituted. The ASGI HTTP
link is in-process; this does not qualify TCP/TLS deployment or provider effects.
"""

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import UUID, uuid4
import httpx, pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from backend.agents.mcp_server.app import verified_http
from backend.agents.mcp_server.app.core import case_records
from backend.agents.mcp_server.app.core.case_records import CaseRecordPolicy
from test_action_database import lab as lab, flow as flow  # noqa:F401
from test_action_boundary import proposal

REAL_ASYNC = httpx.AsyncClient
TENANT = "11111111-1111-4111-8111-111111111111"


@pytest.fixture
def connected(flow, monkeypatch):
    api = flow["api"]
    state = SimpleNamespace(calls=[], lose_once=False)
    upstream = httpx.ASGITransport(app=api.app)

    class Link(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            state.calls.append((request.method, str(request.url)))
            response = await upstream.handle_async_request(request)
            if (
                state.lose_once
                and request.method == "POST"
                and response.status_code == 201
            ):
                state.lose_once = False
                await response.aclose()
                raise httpx.ReadTimeout("Synthetic response lost after durable commit")
            return response

    monkeypatch.setattr(
        case_records.httpx,
        "AsyncClient",
        lambda **kwargs: REAL_ASYNC(transport=Link(), **kwargs),
    )
    app = verified_http.create_verified_http_app(
        verification=api.app.state.iam_verification_settings,
        users=api.app.state.user_principal_settings,
        allowed_hosts=("testserver",),
        case_records=CaseRecordPolicy(origin="http://case-runtime.internal.test"),
    )
    with TestClient(app) as client:
        state.client = client
        state.flow = flow

        def call(name, args, user=0, claims=None, headers=None):
            return client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": args},
                },
                headers={
                    "Accept": "application/json, text/event-stream",
                    **api.headers(flow["users"][user], **(claims or {})),
                    **(headers or {}),
                },
            )

        state.call = call
        yield state
    assert not api.app.dependency_overrides


def create(connected, *, body=None, key=None, user=0):
    args = dict(
        case_id=connected.flow["case_id"],
        request_key=key or str(uuid4()),
        proposal=body or proposal(),
    )
    return connected.call("case_propose_action", args, user=user)


def read(connected, p, *, case=None, user=0):
    return connected.call(
        "case_get_action_proposal",
        {"case_id": case or connected.flow["case_id"], "proposal_id": p["proposal_id"]},
        user=user,
    )


def counts(connected):
    with connected.flow["lab"]["owner"].connect() as c:
        proposals = (
            c.execute(
                text("SELECT id FROM case_runtime.action_proposals WHERE case_id=:id"),
                {"id": connected.flow["case_id"]},
            )
            .scalars()
            .all()
        )
        outbox = c.execute(
            text(
                "SELECT count(*) FROM case_runtime.outbox_events WHERE aggregate_id IN (SELECT id FROM case_runtime.action_proposals WHERE case_id=:id)"
            ),
            {"id": connected.flow["case_id"]},
        ).scalar()
        return proposals, outbox


def test_sdk_proposal_and_inspection_use_real_receiver_authority(connected):
    result = create(connected).json()["result"]
    assert not result["isError"]
    p = result["structuredContent"]
    assert (
        p["tenant_id"] == TENANT
        and p["case_id"] == connected.flow["case_id"]
        and p["execution_available"] is False
    )
    got = read(connected, p).json()["result"]
    assert not got["isError"]
    assert (
        got["structuredContent"]["proposal"]["proposed_by"]
        == connected.flow["users"][0]
    )
    assert counts(connected) == ([UUID(p["proposal_id"])], 1)
    # Each HTTP boundary verifies the same bearer independently; no trusted user headers.
    assert len(connected.flow["api"].calls) == 4


@pytest.mark.parametrize("operation", ["submit", "read"])
def test_current_case_grant_required_by_actual_receiving_api(connected, operation):
    if operation == "submit":
        result = create(connected, user=3).json()["result"]
    else:
        p = create(connected).json()["result"]["structuredContent"]
        result = read(connected, p, user=3).json()["result"]
    assert result["isError"] and "permission denied" in result["content"][0]["text"]
    if operation == "submit":
        assert counts(connected) == ([], 0)


def test_model_authority_fields_never_reach_receiving_api(connected):
    before = len(connected.calls)
    response = connected.call(
        "case_propose_action",
        {
            "case_id": connected.flow["case_id"],
            "request_key": str(uuid4()),
            "proposal": proposal(),
            "approved": True,
            "tenant_id": str(uuid4()),
        },
    )
    assert (
        response.json()["error"]["code"] == -32602
        and len(connected.calls) == before
        and counts(connected) == ([], 0)
    )


def test_foreign_verified_tenant_and_headers_denied_before_receiver(connected):
    args = {
        "case_id": connected.flow["case_id"],
        "request_key": str(uuid4()),
        "proposal": proposal(),
    }
    assert (
        connected.call(
            "case_propose_action", args, claims={"tenant_id": str(uuid4())}
        ).status_code
        == 403
    )
    assert (
        connected.call(
            "case_propose_action", args, headers={"X-Tenant-ID": TENANT}
        ).status_code
        == 403
    )
    assert connected.calls == [] and counts(connected) == ([], 0)


def test_cross_case_identifier_cannot_read_another_proposal(connected):
    p = create(connected).json()["result"]["structuredContent"]
    got = read(connected, p, case=str(uuid4())).json()["result"]
    assert got["isError"] and "not found" in got["content"][0]["text"]
    assert "proposal_hash" not in got["structuredContent"]


def test_human_api_approval_is_visible_but_no_mcp_approval_or_execution_exists(
    connected,
):
    p = create(connected).json()["result"]["structuredContent"]
    assert connected.flow["decide"](p, user=0).status_code == 403
    approved = connected.flow["decide"](p)
    assert approved.status_code == 201
    got = read(connected, p).json()["result"]["structuredContent"]
    assert got["status"] == "approved" and got["execution_available"] is False
    for tool in ["case_approve_action", "case_execute_action"]:
        assert (
            connected.call(
                tool, {"proposal_id": p["proposal_id"], "approved": True}
            ).json()["error"]["code"]
            == -32602
        )
    assert connected.call(
        "lock_account", {"user_id": str(uuid4()), "approved": True}
    ).json()["result"]["isError"]
    with connected.flow["lab"]["owner"].connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM case_runtime.action_claims WHERE proposal_id=:id"
                ),
                {"id": p["proposal_id"]},
            ).scalar()
            == 0
        )
        assert (
            c.execute(
                text("SELECT count(*) FROM case_runtime.action_receipts")
            ).scalar()
            == 0
        )


def test_response_lost_after_commit_retries_same_intent_without_duplicate(connected):
    body = proposal()
    key = str(uuid4())
    connected.lose_once = True
    first = create(connected, body=body, key=key).json()["result"]
    assert first["isError"]
    rows, outbox = counts(connected)
    assert len(rows) == 1 and outbox == 1
    repeated = create(connected, body=body, key=key).json()["result"]
    assert not repeated["isError"] and repeated["structuredContent"][
        "proposal_id"
    ] == str(rows[0])
    assert counts(connected) == (rows, 1)
    changed = {**body, "parameters": {"reason": "Changed intent"}}
    assert create(connected, body=changed, key=key).json()["result"]["isError"]
    assert create(connected, body=body, key=key, user=1).json()["result"]["isError"]
    assert counts(connected) == (rows, 1)


def test_receiver_storage_failure_is_atomic_and_not_an_in_memory_success(connected):
    owner = connected.flow["lab"]["owner"]
    with owner.begin() as c:
        c.execute(
            text("REVOKE INSERT ON case_runtime.outbox_events FROM sg_action_app")
        )
    try:
        assert create(connected).json()["result"]["isError"] and counts(connected) == (
            [],
            0,
        )
    finally:
        with owner.begin() as c:
            c.execute(
                text("GRANT INSERT ON case_runtime.outbox_events TO sg_action_app")
            )
    assert not create(connected).json()["result"]["isError"]


def test_stale_revision_is_not_executable_and_replay_status_is_truthful(connected):
    body = proposal()
    key = str(uuid4())
    p = create(connected, body=body, key=key).json()["result"]["structuredContent"]
    with connected.flow["lab"]["owner"].begin() as c:
        c.execute(
            text("UPDATE case_runtime.cases SET revision=revision+1 WHERE id=:id"),
            {"id": connected.flow["case_id"]},
        )
    assert read(connected, p).json()["result"]["isError"]
    replay = create(connected, body=body, key=key).json()["result"]["structuredContent"]
    assert replay["status"] == "stale" and replay["execution_available"] is False


def test_revoke_current_approver_authority_remains_visible_through_mcp(connected):
    p = create(connected).json()["result"]["structuredContent"]
    assert connected.flow["decide"](p).status_code == 201
    with connected.flow["lab"]["owner"].begin() as c:
        c.execute(
            text(
                "DELETE FROM case_runtime.case_access_grants WHERE case_id=:case AND subject_id=:user AND permission='approve'"
            ),
            {"case": connected.flow["case_id"], "user": connected.flow["users"][1]},
        )
    got = read(connected, p).json()["result"]["structuredContent"]
    assert (
        got["status"] == "approval_authority_revoked"
        and got["execution_available"] is False
    )


def test_concurrent_sdk_requests_do_not_mix_verified_proposers(connected):
    def invoke(user):
        return user, create(connected, user=user).json()["result"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(invoke, [0, 1]))
    assert all(not result["isError"] for _, result in results), results
    for user, result in results:
        p = result["structuredContent"]
        got = read(connected, p, user=user).json()["result"]["structuredContent"]
        assert got["proposal"]["proposed_by"] == connected.flow["users"][user]
    rows, outbox = counts(connected)
    assert len(rows) == 2 and outbox == 2


def test_same_key_recovers_after_actual_postgresql_crash_restart(connected):
    body = proposal()
    key = str(uuid4())
    p = create(connected, body=body, key=key).json()["result"]["structuredContent"]
    connected.flow["lab"]["restart"]()
    replay = create(connected, body=body, key=key).json()["result"]
    assert not replay["isError"] and replay["structuredContent"] == p
    assert (
        not read(connected, p).json()["result"]["isError"]
        and len(counts(connected)[0]) == 1
    )
