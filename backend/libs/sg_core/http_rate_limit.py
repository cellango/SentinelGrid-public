"""Atomic shared fixed-window budgets. No headers or token text grant identity."""

from dataclasses import dataclass
import hashlib
import ipaddress
from urllib.parse import urlsplit

import anyio
from fastapi import HTTPException
from starlette.responses import JSONResponse

# One Redis hash slot deliberately groups the gateway's bounded counters. Redis
# server time selects the window; one Lua operation checks and increments all
# supplied buckets. Fixed windows permit a burst around the minute boundary.
_SCRIPT = """
local now = tonumber(redis.call('TIME')[1])
local window = math.floor(now / 60)
local reset = (window + 1) * 60
local keys = {}
for i, key in ipairs(KEYS) do
  keys[i] = key .. ':' .. window
  local count = tonumber(redis.call('GET', keys[i]) or '0')
  if count >= tonumber(ARGV[i]) then return {0, reset-now} end
end
for i, key in ipairs(keys) do
  redis.call('INCR', key)
  redis.call('EXPIRE', key, reset-now+1)
end
return {1, reset-now}
"""
_EXEMPT = frozenset({("GET", "/"), ("GET", "/health"), ("GET", "/ready")})


@dataclass(frozen=True)
class RateLimitPolicy:
    enabled: bool = False
    fail_closed: bool = True
    redis_url: str = "redis://redis:6379/0"
    namespace: str = "sentinelgrid-gateway"
    peer_rpm: int = 600
    tenant_rpm: int = 1200
    subject_rpm: int = 120
    trusted_proxy_cidrs: tuple[str, ...] = ()

    def __post_init__(self):
        if (
            type(self.enabled) is not bool
            or type(self.fail_closed) is not bool
            or type(self.trusted_proxy_cidrs) is not tuple
            or len(self.trusted_proxy_cidrs) > 256
        ):
            raise ValueError("Expected immutable owned limiter policy")
        if (
            not self.namespace
            or len(self.namespace) > 64
            or any(
                c
                not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
                for c in self.namespace
            )
        ):
            raise ValueError("Invalid limiter namespace")
        if any(
            type(n) is not int or not 1 <= n <= 1000000
            for n in (self.peer_rpm, self.tenant_rpm, self.subject_rpm)
        ):
            raise ValueError("Invalid rate limit")
        p = urlsplit(self.redis_url)
        if (
            p.scheme not in {"redis", "rediss"}
            or not p.hostname
            or p.query
            or p.fragment
            or p.port == 0
        ):
            raise ValueError("Expected owned Redis URL without query overrides")
        for cidr in self.trusted_proxy_cidrs:
            network = ipaddress.ip_network(cidr, strict=True)
            if network.prefixlen == 0:
                raise ValueError("Wildcard trusted proxies are unsupported")


def peer_address(scope, policy: RateLimitPolicy) -> str:
    """Use kernel peer unless an explicitly trusted proxy supplies a valid chain.

    Uvicorn must run with --no-proxy-headers so this boundary sees the direct
    peer. Reject ambiguous forwarding from trusted peers; never use tenant/role
    headers, a query, token hash or unverified claims to choose a bucket.
    """
    try:
        peer = ipaddress.ip_address(scope["client"][0])
    except (KeyError, TypeError, ValueError):
        return "unknown"
    networks = tuple(
        ipaddress.ip_network(n, strict=True) for n in policy.trusted_proxy_cidrs
    )
    trusted = lambda addr: any(addr in net for net in networks)
    if not trusted(peer):
        return str(peer)
    values = [v for k, v in scope.get("headers", []) if k.lower() == b"x-forwarded-for"]
    if not values:
        return str(peer)
    if len(values) != 1 or len(values[0]) > 2048:
        raise HTTPException(400, "Ambiguous forwarding chain")
    try:
        raw = values[0].decode("ascii").split(",")
        if not 1 <= len(raw) <= 16:
            raise ValueError()
        chain = [ipaddress.ip_address(v.strip()) for v in raw]
    except (ValueError, UnicodeError):
        raise HTTPException(400, "Invalid forwarding chain") from None
    for addr in reversed(chain):
        if not trusted(addr):
            return str(addr)
    return str(chain[0])


class RedisBudgetStore:
    def __init__(self, policy: RateLimitPolicy, client):
        self.policy = policy
        self.client = client

    def check(self, buckets: tuple[tuple[str, str, int], ...]):
        keys = [
            self.policy.namespace
            + ":{gateway}:"
            + kind
            + ":"
            + hashlib.sha256(value.encode()).hexdigest()
            for kind, value, _ in buckets
        ]
        try:
            result = self.client.eval(
                _SCRIPT, len(keys), *keys, *(n for _, _, n in buckets)
            )
            if (
                not isinstance(result, list)
                or len(result) != 2
                or type(result[0]) is not int
                or result[0] not in {0, 1}
                or type(result[1]) is not int
                or not 1 <= result[1] <= 60
            ):
                raise ValueError("Invalid limiter response")
        except Exception:
            # No permanent failure cache. Redis reconnects on the next request.
            # Failure text, credentials, identity and raw bucket IDs are not logged.
            if self.policy.fail_closed:
                raise HTTPException(503, "Request budget unavailable") from None
            return
        if result[0] == 0:
            raise HTTPException(
                429, "Request budget exceeded", headers={"Retry-After": str(result[1])}
            )

    def check_identity(self, identity):
        self.check(
            (
                ("tenant", identity.tenant_id, self.policy.tenant_rpm),
                (
                    "subject",
                    identity.tenant_id + ":" + identity.user_id,
                    self.policy.subject_rpm,
                ),
            )
        )


def create_budget_store(policy: RateLimitPolicy):
    if not policy.enabled:
        return None
    import redis
    from redis.backoff import NoBackoff
    from redis.retry import Retry

    client = redis.Redis.from_url(
        policy.redis_url,
        socket_connect_timeout=1,
        socket_timeout=1,
        decode_responses=False,
        retry=Retry(NoBackoff(), 0),
        max_connections=128,
    )
    return RedisBudgetStore(policy, client)


class PeerBudgetMiddleware:
    def __init__(self, app, store):
        self.app, self.store = app, store

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or self.store is None
            or (scope["method"], scope["path"]) in _EXEMPT
        ):
            return await self.app(scope, receive, send)
        try:
            address = peer_address(scope, self.store.policy)
            await anyio.to_thread.run_sync(
                self.store.check, (("peer", address, self.store.policy.peer_rpm),)
            )
        except HTTPException as exc:
            return await JSONResponse(
                {"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers
            )(scope, receive, send)
        return await self.app(scope, receive, send)
