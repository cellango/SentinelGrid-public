"""Bound browser requests before credential normalization or route effects."""

from dataclasses import dataclass

import anyio
from starlette.responses import JSONResponse

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


@dataclass(frozen=True)
class IngressPolicy:
    allowed_origins: tuple[str, ...]
    max_body_bytes: int = 2 * 1024 * 1024
    max_header_bytes: int = 65536
    max_headers: int = 128
    body_timeout_seconds: float = 10.0
    max_concurrent_requests: int = 128

    def __post_init__(self):
        if not 1 <= self.max_body_bytes <= 64 * 1024 * 1024:
            raise ValueError("Invalid request body bound")
        if (
            not 1024 <= self.max_header_bytes <= 262144
            or not 1 <= self.max_headers <= 512
        ):
            raise ValueError("Invalid request header bound")
        if (
            not 0 < self.body_timeout_seconds <= 60
            or not 1 <= self.max_concurrent_requests <= 4096
        ):
            raise ValueError("Invalid request time/concurrency bound")


class GatewayIngressMiddleware:
    """Origin/CSRF, framing and actual-byte bounds, independent of claimed identity.

    Forwarded/tenant/role headers never grant authority or select a budget. This
    middleware does not claim a distributed rate limit; that is a separate gate.
    """

    def __init__(self, app, policy: IngressPolicy):
        self.app = app
        self.policy = policy
        self.capacity = anyio.CapacityLimiter(policy.max_concurrent_requests)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def reject(status, detail):
            origins = [v for k, v in scope.get("headers", []) if k.lower() == b"origin"]
            cors = {}
            if len(origins) == 1:
                try:
                    origin = origins[0].decode("ascii")
                    if origin in self.policy.allowed_origins:
                        cors = {
                            "Access-Control-Allow-Origin": origin,
                            "Access-Control-Allow-Credentials": "true",
                            "Vary": "Origin",
                        }
                except UnicodeError:
                    pass
            await JSONResponse({"detail": detail}, status_code=status, headers=cors)(
                scope, receive, send
            )

        headers = scope.get("headers", [])
        if (
            len(headers) > self.policy.max_headers
            or sum(len(k) + len(v) for k, v in headers) > self.policy.max_header_bytes
        ):
            return await reject(431, "Request headers too large")
        values = {}
        for name, value in headers:
            values.setdefault(name.lower(), []).append(value)
        lengths = values.get(b"content-length", [])
        if len(lengths) > 1 or lengths and b"transfer-encoding" in values:
            return await reject(400, "Ambiguous request framing")
        length = None
        if lengths:
            raw = lengths[0]
            if not raw or any(c < 48 or c > 57 for c in raw) or len(raw) > 12:
                return await reject(400, "Invalid Content-Length")
            length = int(raw)
            if length > self.policy.max_body_bytes:
                return await reject(413, "Request body too large")
        encodings = values.get(b"content-encoding", [])
        if len(encodings) > 1 or encodings and encodings[0].lower() != b"identity":
            return await reject(415, "Encoded request bodies are unsupported")
        origins = values.get(b"origin", [])
        if len(origins) > 1:
            return await reject(403, "Invalid request origin")
        if scope["method"] not in _SAFE_METHODS:
            # Cookie and frontend marker authentication is ambient authority.
            # Matching bearer+cookie still requires the browser-origin check.
            if origins:
                try:
                    origin = origins[0].decode("ascii")
                except UnicodeError:
                    return await reject(403, "Invalid request origin")
                if origin not in self.policy.allowed_origins:
                    return await reject(403, "Request origin not allowed")
            elif values.get(b"cookie"):
                return await reject(
                    403, "Cookie-authenticated mutations require Origin"
                )
        try:
            self.capacity.acquire_nowait()
        except anyio.WouldBlock:
            return await reject(503, "Gateway request capacity unavailable")
        try:
            chunks = []
            size = 0
            try:
                with anyio.fail_after(self.policy.body_timeout_seconds):
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            return
                        if message["type"] != "http.request":
                            return await reject(400, "Invalid request message")
                        body = message.get("body", b"")
                        size += len(body)
                        if size > self.policy.max_body_bytes:
                            return await reject(413, "Request body too large")
                        chunks.append(body)
                        if not message.get("more_body", False):
                            break
            except TimeoutError:
                return await reject(408, "Request body timed out")
            if length is not None and length != size:
                return await reject(400, "Content-Length does not match request body")
            delivered = False

            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {
                        "type": "http.request",
                        "body": b"".join(chunks),
                        "more_body": False,
                    }
                return await receive()

            await self.app(scope, replay, send)
        finally:
            self.capacity.release()
