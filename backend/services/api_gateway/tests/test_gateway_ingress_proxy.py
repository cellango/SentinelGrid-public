"""Real ASGI/HTTPX boundary tests; no database, provider or network effects."""

import asyncio

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.ingress import GatewayIngressMiddleware, IngressPolicy
from app.core import proxy
from sg_core.request_credentials import AuthCookieMiddleware

ORIGIN = "https://console.example.test"
TENANT = "e53ae16f-4381-4da5-9992-8d8d85b1d0eb"


def ingress_app(**policy):
    effects = []
    app = FastAPI()

    @app.api_route("/effect", methods=["GET", "POST", "DELETE"])
    async def effect(request: Request):
        body = await request.body()
        effects.append(body)
        return {
            "body": body.decode(),
            "authorization": request.headers.get("authorization"),
        }

    app.add_middleware(AuthCookieMiddleware)
    app.add_middleware(
        GatewayIngressMiddleware,
        policy=IngressPolicy(allowed_origins=(ORIGIN,), **policy),
    )
    return app, effects


@pytest.mark.parametrize(
    "headers,status",
    [
        ({"cookie": "access_token=synthetic"}, 403),
        ({"cookie": "access_token=synthetic", "origin": "https://attacker.test"}, 403),
        ({"cookie": "access_token=synthetic", "origin": "null"}, 403),
        ({"cookie": "access_token=synthetic", "origin": ORIGIN}, 200),
        (
            {
                "cookie": "access_token=synthetic",
                "authorization": "Bearer session-cookie",
                "origin": ORIGIN,
            },
            200,
        ),
        ({"authorization": "Bearer synthetic"}, 200),
        ({"authorization": "Bearer synthetic", "origin": "https://attacker.test"}, 403),
        (
            {"authorization": "Bearer synthetic", "cookie": "access_token=synthetic"},
            403,
        ),
    ],
)
def test_cookie_origin_boundary_before_normalization(headers, status):
    app, effects = ingress_app()
    response = TestClient(app).post("/effect", headers=headers, content="unchanged")
    assert response.status_code == status
    assert effects == ([b"unchanged"] if status == 200 else [])


def test_safe_cookie_read_does_not_require_origin():
    app, effects = ingress_app()
    response = TestClient(app).get(
        "/effect", headers={"cookie": "access_token=synthetic"}
    )
    assert (
        response.status_code == 200
        and response.json()["authorization"] == "Bearer synthetic"
    )
    assert effects == [b""]


async def raw_call(
    app, headers=(), chunks=(b"",), method="POST", receive_override=None
):
    messages = []
    items = iter(chunks)
    count = 0

    async def receive():
        nonlocal count
        if receive_override:
            return await receive_override()
        body = next(items)
        count += 1
        return {"type": "http.request", "body": body, "more_body": count < len(chunks)}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "path": "/effect",
        "raw_path": b"/effect",
        "query_string": b"",
        "headers": list(headers),
        "client": ("127.0.0.1", 123),
        "server": ("testserver", 80),
        "scheme": "http",
        "root_path": "",
    }
    await app(scope, receive, send)
    return messages


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers,chunks,status",
    [
        ([(b"content-length", b"1"), (b"content-length", b"1")], (b"x",), 400),
        ([(b"content-length", b"1"), (b"transfer-encoding", b"chunked")], (b"x",), 400),
        ([(b"content-length", b"+1")], (b"x",), 400),
        ([(b"content-length", b"2")], (b"x",), 400),
        ([(b"content-length", b"9")], (b"x",), 413),
        ([], (b"1234", b"56789"), 413),
        ([(b"content-encoding", b"gzip")], (b"x",), 415),
        ([(b"origin", ORIGIN.encode()), (b"origin", ORIGIN.encode())], (b"x",), 403),
        ([(b"content-length", b"8")], (b"1234", b"5678"), 200),
    ],
)
async def test_raw_framing_and_actual_byte_limits(headers, chunks, status):
    app, effects = ingress_app(max_body_bytes=8)
    messages = await raw_call(app, headers, chunks)
    assert messages[0]["status"] == status
    assert effects == ([b"12345678"] if status == 200 else [])


@pytest.mark.asyncio
async def test_slow_body_and_capacity_recovery():
    app, effects = ingress_app(body_timeout_seconds=0.01, max_concurrent_requests=1)

    async def slow():
        await asyncio.sleep(1)

    messages = await raw_call(app, receive_override=slow)
    assert messages[0]["status"] == 408 and effects == []
    assert (await raw_call(app))[0]["status"] == 200


@pytest.mark.asyncio
async def test_overload_rejects_before_effect_then_recovers():
    started, release = asyncio.Event(), asyncio.Event()
    calls = []

    async def downstream(scope, receive, send):
        calls.append(1)
        started.set()
        await release.wait()
        await JSONResponse({"ok": True})(scope, receive, send)

    app = GatewayIngressMiddleware(
        downstream, IngressPolicy(allowed_origins=(), max_concurrent_requests=1)
    )
    first = asyncio.create_task(raw_call(app))
    await started.wait()
    assert (await raw_call(app))[0]["status"] == 503 and calls == [1]
    release.set()
    assert (await first)[0]["status"] == 200
    assert (await raw_call(app))[0]["status"] == 200 and calls == [1, 1]


def proxy_app(monkeypatch, handler, **kwargs):
    calls, options = [], []
    real_client = httpx.AsyncClient

    def factory(**client_options):
        options.append(client_options)
        return real_client(**client_options, transport=httpx.MockTransport(record))

    async def record(request):
        calls.append(request)
        return handler(request)

    monkeypatch.setattr(proxy.httpx, "AsyncClient", factory)
    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST", "DELETE", "HEAD"])
    async def route(request: Request, path: str):
        return await proxy.proxy_request(
            request,
            origin=kwargs.get("origin", "http://iam_agent:8000"),
            prefix="/owned/",
            path=path,
            tenant_id=TENANT,
            pre_auth=kwargs.get("pre_auth", False),
        )

    return TestClient(app), calls, options


def test_exact_delete_query_body_and_filtered_identity_headers(monkeypatch):
    client, calls, options = proxy_app(
        monkeypatch, lambda _: httpx.Response(202, content=b"accepted")
    )
    response = client.request(
        "DELETE",
        "/users?tag=a&tag=b&literal=%2F",
        content=b' {"a": 1} ',
        headers={
            "authorization": "Bearer synthetic",
            "x-tenant-id": "foreign",
            "x-roles": "admin",
            "x-internal-service-token": "forged",
            "x-forwarded-for": "1.2.3.4",
            "cookie": "access_token=synthetic",
            "content-type": "application/json",
            "if-match": '"revision-1"',
        },
    )
    assert response.status_code == 202 and response.content == b"accepted"
    assert (
        len(calls) == 1
        and str(calls[0].url)
        == "http://iam_agent:8000/owned/users?tag=a&tag=b&literal=%2F"
    )
    assert calls[0].content == b' {"a": 1} ' and calls[0].method == "DELETE"
    assert calls[0].headers["authorization"] == "Bearer synthetic"
    assert (
        calls[0].headers["x-tenant-id"] == TENANT
        and calls[0].headers["if-match"] == '"revision-1"'
    )
    assert not {
        "cookie",
        "x-roles",
        "x-internal-service-token",
        "x-forwarded-for",
    } & set(calls[0].headers)
    assert options[0]["trust_env"] is False and options[0]["follow_redirects"] is False


def test_login_keeps_invalid_json_and_only_unverified_routing_hints(monkeypatch):
    client, calls, _ = proxy_app(
        monkeypatch, lambda _: httpx.Response(400, content=b"invalid"), pre_auth=True
    )
    response = client.post(
        "/login",
        content=b"invalid json",
        headers={
            "x-realm": "synthetic",
            "x-tenant-id": TENANT,
            "authorization": "Bearer forged",
            "x-roles": "admin",
        },
    )
    assert response.status_code == 400 and calls[0].content == b"invalid json"
    assert (
        calls[0].headers["x-realm"] == "synthetic"
        and "authorization" not in calls[0].headers
    )
    assert "x-roles" not in calls[0].headers


@pytest.mark.parametrize("status", [201, 204, 302, 304, 401, 404, 409, 422, 503])
def test_status_error_content_and_multiple_cookies_are_preserved(monkeypatch, status):
    client, calls, _ = proxy_app(
        monkeypatch,
        lambda _: httpx.Response(
            status,
            content=b"upstream",
            headers=[
                ("content-type", "text/plain"),
                ("set-cookie", "first=a; HttpOnly"),
                ("set-cookie", "second=b; HttpOnly"),
                ("connection", "x-remove"),
                ("x-remove", "secret"),
                ("access-control-allow-origin", "*"),
                ("x-internal-detail", "secret"),
            ],
        ),
    )
    response = client.get(
        "/policies",
        headers={"authorization": "Bearer synthetic"},
        follow_redirects=False,
    )
    assert response.status_code == status and len(calls) == 1
    assert response.content == (b"" if status in {204, 304} else b"upstream")
    assert response.headers.get_list("set-cookie") == [
        "first=a; HttpOnly",
        "second=b; HttpOnly",
    ]
    assert (
        "x-remove" not in response.headers
        and "access-control-allow-origin" not in response.headers
    )
    assert "x-internal-detail" not in response.headers


@pytest.mark.parametrize(
    "error,status",
    [
        (httpx.ConnectError("sensitive endpoint"), 503),
        (httpx.ReadTimeout("sensitive endpoint"), 504),
    ],
)
def test_unavailable_and_timeout_are_sanitized(monkeypatch, error, status):
    def fail(_):
        raise error

    client, calls, _ = proxy_app(monkeypatch, fail)
    response = client.get("/users", headers={"authorization": "Bearer synthetic"})
    assert (
        response.status_code == status
        and "sensitive" not in response.text
        and len(calls) == 1
    )


@pytest.mark.parametrize(
    "origin",
    [
        "http://user:pass@iam_agent",
        "http://iam_agent/other",
        "http://iam_agent:invalid",
        "http://iam_agent/#x",
    ],
)
def test_invalid_owned_origin_never_connects(monkeypatch, origin):
    client, calls, _ = proxy_app(
        monkeypatch, lambda _: httpx.Response(200), origin=origin
    )
    assert (
        client.get("/users", headers={"authorization": "Bearer synthetic"}).status_code
        == 503
    )
    assert calls == []


def test_missing_credentials_and_response_bound(monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPSTREAM_RESPONSE_BYTES", 8)
    client, calls, _ = proxy_app(
        monkeypatch, lambda _: httpx.Response(200, content=b"0123456789")
    )
    assert client.get("/users").status_code == 401 and calls == []
    assert (
        client.get("/users", headers={"authorization": "Bearer synthetic"}).status_code
        == 502
    )
    assert len(calls) == 1


@pytest.mark.parametrize(
    "path", ["/users%2Fadmin", "/users%5Cadmin", "/users?x=%invalid", "/users?x=%1"]
)
def test_ambiguous_encoded_targets_never_connect(monkeypatch, path):
    client, calls, _ = proxy_app(monkeypatch, lambda _: httpx.Response(200))
    assert (
        client.get(path, headers={"Authorization": "Bearer synthetic"}).status_code
        == 400
    )
    assert calls == []


def test_encoded_upstream_is_rejected_before_decompression(monkeypatch):
    class MustNotRead(httpx.AsyncByteStream):
        async def __aiter__(self):
            pytest.fail(
                "Encoded upstream must be rejected before any decoded allocation"
            )
            yield b""

    client, calls, _ = proxy_app(
        monkeypatch,
        lambda _: httpx.Response(
            200, headers={"content-encoding": "gzip"}, stream=MustNotRead()
        ),
    )
    assert (
        client.get("/users", headers={"Authorization": "Bearer synthetic"}).status_code
        == 502
    )
    assert len(calls) == 1
