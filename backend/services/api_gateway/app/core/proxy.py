"""Owned upstream paths, selected credentials and bounded transparent replies.

This transports a credential and verified tenant; it does not authorize a domain
operation. Receivers must retain their own identity/action/source admission.
"""

from urllib.parse import quote, urlsplit
import ssl
import anyio
import re

from fastapi import HTTPException, Request, Response
import httpx

from app.core.config import settings
from sg_core.request_credentials import request_token
from sg_core.request_tracing import build_trace_headers

_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "content-length",
        "content-encoding",
    }
)
_REQUEST_HEADERS = frozenset(
    {"accept", "content-type", "if-match", "if-none-match", "if-modified-since", "idempotency-key"}
)


def _origin(value: str) -> str:
    try:
        p = urlsplit(value)
        port = p.port
    except (TypeError, ValueError):
        raise HTTPException(503, "Upstream configuration unavailable") from None
    if (
        p.scheme not in {"http", "https"}
        or not p.hostname
        or p.username is not None
        or p.password is not None
        or p.path not in {"", "/"}
        or p.query
        or p.fragment
        or "?" in value
        or "#" in value
        or "%" in value
        or "\\" in value
        or any(ord(c) < 33 or ord(c) == 127 for c in value)
        or port == 0
    ):
        raise HTTPException(503, "Upstream configuration unavailable")
    if settings.ENVIRONMENT not in {"development", "test"} and p.scheme != "https":
        raise HTTPException(503, "Upstream configuration unavailable")
    return value.rstrip("/")


def _headers(request: Request, tenant_id: str | None, pre_auth: bool) -> dict[str, str]:
    result = {}
    for name in _REQUEST_HEADERS:
        values = request.headers.getlist(name)
        if len(values) > 1:
            raise HTTPException(400, "Ambiguous request headers")
        if values:
            result[name] = values[0]
    if pre_auth:
        # These are unverified login-routing hints, never a principal or grant.
        for name in ("x-tenant-id", "x-realm"):
            values = request.headers.getlist(name)
            if (
                len(values) > 1
                or values
                and (
                    not values[0]
                    or len(values[0]) > 256
                    or any(ord(c) < 33 or ord(c) == 127 for c in values[0])
                )
            ):
                raise HTTPException(400, "Invalid login routing hint")
            if values:
                result[name] = values[0]
    else:
        if not tenant_id:
            raise HTTPException(503, "Verified tenant context unavailable")
        result["authorization"] = "Bearer " + request_token(request)
        result["x-tenant-id"] = tenant_id
    # Never forward cookie, host, arbitrary identity/internal/forwarding headers.
    result["accept-encoding"] = "identity"
    return build_trace_headers(result)


def _response_headers(headers) -> list[tuple[bytes, bytes]]:
    pairs = (
        list(headers.multi_items())
        if hasattr(headers, "multi_items")
        else list(headers.items())
    )
    nominated = {
        v.strip().lower()
        for k, value in pairs
        if k.lower() == "connection"
        for v in value.split(",")
    }
    blocked = _HOP | nominated
    return [
        (k.lower().encode("latin-1"), v.encode("latin-1"))
        for k, v in pairs
        if k.lower() not in blocked
        and not k.lower().startswith(("access-control-", "x-internal-"))
    ]


async def proxy_request(
    request: Request,
    *,
    origin: str,
    prefix: str,
    path: str = "",
    tenant_id: str | None = None,
    pre_auth: bool = False,
) -> Response:
    base = _origin(origin)
    if (
        not prefix.startswith("/")
        or "?" in prefix
        or "#" in prefix
        or path.startswith("/")
        or any(c in path for c in "\\%?#")
        or any(ord(c) < 32 or ord(c) == 127 for c in path)
        or any(segment in {".", ".."} for segment in path.split("/"))
    ):
        raise HTTPException(400, "Invalid upstream path")
    target = base + prefix + quote(path, safe="/-._~")
    query = request.scope.get("query_string", b"")
    raw_path = request.scope.get("raw_path", b"").lower()
    if b"%2f" in raw_path or b"%5c" in raw_path:
        raise HTTPException(400, "Ambiguous encoded upstream path")
    if (
        len(query) > 8192
        or any(c < 33 or c == 127 for c in query)
        or b"#" in query
        or re.search(rb"%(?![0-9A-Fa-f]{2})", query)
    ):
        raise HTTPException(400, "Invalid query encoding")
    if query:
        try:
            target += "?" + query.decode("ascii")
        except UnicodeError:
            raise HTTPException(400, "Invalid query encoding") from None
    headers = _headers(request, tenant_id, pre_auth)
    body = await request.body()
    verify = settings.UPSTREAM_TLS_VERIFY
    if verify and origin == settings.IAM_AGENT_URL and settings.IAM_VERIFIER_CA_BUNDLE:
        try:
            verify = ssl.create_default_context(cafile=settings.IAM_VERIFIER_CA_BUNDLE)
        except (OSError, ValueError):
            raise HTTPException(503, "Upstream TLS configuration unavailable") from None
    try:
        with anyio.fail_after(30.0):
            async with httpx.AsyncClient(
                timeout=30.0, verify=verify, trust_env=False, follow_redirects=False
            ) as client:
                async with client.stream(
                    request.method, target, content=body, headers=headers
                ) as upstream:
                    if not 200 <= upstream.status_code <= 599:
                        raise HTTPException(502, "Invalid upstream response")
                    encodings = upstream.headers.get_list("content-encoding")
                    if (
                        len(encodings) > 1
                        or encodings
                        and encodings[0].lower() != "identity"
                    ):
                        raise HTTPException(
                            502, "Encoded upstream response unsupported"
                        )
                    content = bytearray()
                    async for chunk in upstream.aiter_bytes():
                        if (
                            len(content) + len(chunk)
                            > settings.MAX_UPSTREAM_RESPONSE_BYTES
                        ):
                            raise HTTPException(502, "Upstream response too large")
                        content.extend(chunk)
                    response = Response(
                        content=bytes(content)
                        if request.method != "HEAD"
                        and upstream.status_code not in {204, 304}
                        else b"",
                        status_code=upstream.status_code,
                    )
                    response.raw_headers = [
                        h for h in response.raw_headers if h[0] != b"content-type"
                    ] + _response_headers(upstream.headers)
                    return response
    except (httpx.TimeoutException, TimeoutError):
        raise HTTPException(504, "Upstream request timed out") from None
    except httpx.RequestError:
        raise HTTPException(503, "Upstream service unavailable") from None
