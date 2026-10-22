# Current HTTP transport boundaries

Status: local source qualification on October 22, 2026. The gateway and optional
MCP discovery transport share ingress and request-budget code. This does not
qualify a deployment, a live issuer, tool execution or all domain routes.

## Browser ingress

The gateway checks raw framing, headers and actual body bytes before credential
normalization and route effects. Defaults are 2 MiB body, 64 KiB/128 headers,
10 seconds to receive the body and 128 concurrent requests per worker. Encoded
request bodies are rejected. Exceeding size, time or capacity returns 413, 408
or 503. Duplicate framing and mismatched Content-Length return 400.

A mutation carrying any cookie requires an exact owned `Origin` in `CORS_ORIGINS`.
This includes refresh and `Bearer session-cookie` requests. A supplied origin on
any mutation must match even with bearer authentication. Native bearer clients
without cookies may omit Origin. GET/HEAD/OPTIONS still need their normal route
identity and authorization. CORS permits credentials only for the owned allowlist.

## Shared request budgets and trusted ingress

`RATE_LIMIT_ENABLED` defaults false for the local source preview. Non-development
gateway settings require it true, `RATE_LIMIT_FAIL_CLOSED=true`, and a `rediss://`
`RATE_LIMIT_REDIS_URL`. Query parameters cannot override Redis connection settings.
The client uses verified TLS defaults, one-second connection/read bounds and no
automatic command retries. Redis credentials belong in private configuration.

Defaults are 600 requests per peer, 1200 per verified tenant and 120 per verified
subject per minute. The relevant settings are `RATE_LIMIT_RPM_PEER`,
`RATE_LIMIT_RPM_TENANT`, `RATE_LIMIT_RPM_SUBJECT` and `RATE_LIMIT_NAMESPACE`.
Tenant and subject budgets run after verified user admission and before scoped
route dependencies. Token rotation, unverified claims and tenant/role headers do
not select those buckets. Redis server time and one atomic Lua operation check
and increment the relevant counters together. These are fixed windows; a burst
can cross a minute boundary. They are request counts, not model/provider cost limits.

An exceeded budget returns 429 with Retry-After. Redis failure returns 503 with
fail-closed policy; explicit local fail-open is separately tested. The next request
can reconnect after recovery. HA failover, eviction, persistence and deployment-wide
capacity guarantees are not qualified by these local tests.

Run Uvicorn with `--no-proxy-headers`, as in the gateway Dockerfile. The application
needs the direct socket peer. `TRUSTED_PROXY_CIDRS` is an empty tuple by default;
only explicitly trusted peers may supply one fully valid X-Forwarded-For chain.
The rightmost untrusted address selects the peer budget. Other forwarding headers
cannot select a bucket. Configure every worker with the same namespace and owned
Redis service; a distributed production topology remains an integration gate.

`make preview-gateway` runs source/ASGI tests without infrastructure. The actual
Redis check requires an owned disposable Unix-socket server with TCP/persistence
disabled: set `SG_TEST_REDIS_SOCKET` and run `make preview-gateway-redis`. It uses a
random namespace and cleans up only its own keys. Local qualification also checked
a real server outage (503) and restart recovery. No Redis implementation is bundled.

## Bounded gateway forwarding

Login/refresh, IAM portal and dashboard, devices, governance, reports and the
SOAR catch-all use one shared proxy. It preserves raw queries including duplicates,
raw bodies including DELETE, statuses, error bodies and multiple Set-Cookie fields.
It selects only the caller bearer and verified tenant for authenticated routes.
Login hints remain unverified routing hints. Cookies, role/internal-token headers,
forwarding headers and arbitrary headers are not relayed as authority.

Upstreams are owned origins; path traversal, encoded separators and malformed
query encoding are rejected. Non-development origins require HTTPS. Ambient proxy
configuration and redirects are disabled. Responses have a configurable 2 MiB
actual byte bound and a 30-second total proxy deadline. Non-identity upstream Content-Encoding is rejected before decompression. Timeout returns
504; transport failure returns 503 without raw diagnostics. Missing policies stay
404 rather than becoming a fabricated empty 200 response. Other route-specific
proxy/data paths still require individual contract review; this helper does not
replace domain authorization or unblock unavailable actions.

## Optional MCP HTTP discovery

`app.verified_http.create_verified_http_app` requires owned IAM verifier/user-client
settings and exact host/origin allowlists. It uses the installed MCP 1.30.0
Streamable HTTP SDK in stateless JSON mode at POST `/mcp`. The default stdio
entrypoint and all twelve discovery schemas remain unchanged. No deployment or
public HTTP endpoint is added by this factory.

Every request needs a direct bearer, current verified user binding and UUID
identity. Cookies/markers, forwarded identity hints, mismatched tenants/clients,
expired or invalid signatures and unowned origins are denied. The SDK receives
that request's immutable actor/tenant snapshot; capabilities are empty. A constructed
context, body target or approval flag grants nothing. There is no resumable session
or cross-request authentication cache. Shared ingress bounds apply, and owned
`rate_policy` enables the same peer/tenant/subject budgets. Non-development
configuration requires TLS Redis and fail-closed policy.

Discovery is authenticated; **all tool execution remains unavailable**. Exact
operation/target grants, replay controls for effects, downstream data ownership,
deterministic action authority and durable outcomes remain required before any
operation can be enabled. Authentication alone does not satisfy those gates.
