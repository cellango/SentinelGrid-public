# Current delegated identity verification

Status: implemented shared verification client with offline RSA/IAM round-trip
checks. This is a source boundary, not a qualified gateway or a supported login.
[Release scope](../../RELEASE_SCOPE.md) governs execution. The separate
[identity reference](../reference/identity.md) describes tenant requirements.

## Owned verification transport

[The shared verifier](../../backend/libs/sg_core/iam_verification.py) is called by
[sg_core.security.verify_token](../../backend/libs/sg_core/security.py). IAM's
[existing validator](../../backend/agents/iam_agent/app/services/token_validator.py)
remains the signature/issuer/key authority. There is no second JWT verification
engine and no local-decode fallback when IAM or its trusted keys are unavailable.

| Process setting | Contract |
| --- | --- |
| `IAM_AGENT_URL` | Origin only, no credentials/path/query/fragment; fixed validation path appended server-side |
| `ENVIRONMENT` | Plain HTTP only in development/test to `iam_agent`, `localhost`, `127.0.0.1` or `::1`; all other environments require HTTPS and a non-placeholder origin |
| `IAM_TOKEN_VALIDATION_TIMEOUT` | Finite positive phase timeout up to ten seconds; default five seconds, pool timeout one second |
| `IAM_VERIFIER_CA_BUNDLE` | Optional explicit CA file; otherwise HTTPX's verified default trust store |
| `KEYCLOAK_CLIENT_ID` | Expected audience, matching the authoritative IAM validator |

Settings load once per process from owned environment/`.env`. Restart after changes.
TLS verification is always on; the legacy proxy `UPSTREAM_TLS_VERIFY` flag cannot
turn it off for token verification. HTTPX environment proxies and implicit CA
variables are disabled, redirects are rejected, and only the submitted token is
sent. No forwarded tenant, realm, actor, role, internal credential or request URL
can choose the verifier or supply identity. The local HTTP exception is for owned
disposable development, not public or shared deployment.

## Input and receipt checks

The input must be a bounded compact RS256 JWT with a key ID and no external-key
hints. Parsing it only binds the receipt to the exact submitted JSON claims;
parsed input alone never authenticates. A successful receipt requires HTTP 200,
JSON content, literal `valid: true`, and no reported error. It must preserve the
submitted claims and agree on non-nil UUID tenant/subject, realm roles and expiry.
Conflicting summary identities, role aliases, unsigned plan enrichment, duplicate
JSON fields and malformed/oversized responses fail closed. Tenant/subject UUIDs
are normalized in a fresh returned dictionary. Current expiration, issued-at,
optional not-before, and the configured audience are checked again.

Invalid tokens receive generic 401 responses. Transport, TLS, configuration,
malformed or contradictory receipt failures receive generic 503 responses.
Tokens, raw upstream diagnostics and response bodies are not logged or disclosed
by this client. IAM currently reports unavailable signing keys as an invalid
validation result; this client therefore returns 401 for that particular case.

## Qualification and remaining work

`make preview-gateway-identity` runs separately from other `app` packages. It uses
real generated RSA signatures, the current IAM validator and response model, and
HTTPX MockTransport in place of network I/O. It covers a positive verified UUID
round trip, stale/forged/invalid tokens, foreign tenant/role headers and bodies,
wrong-token receipts, contradictory identities/roles/expiry, redirects, failures,
configuration bounds, ambient proxy/trust variables and response limits. A small
FastAPI test route proves the existing tenant dependency rejects before its
handler. It does not mount or qualify the full API gateway.

Browser bearer/cookie/session-marker conflict handling, missing payload credentials,
user versus workload classification, every mounted route/proxy/direct caller and
workload delegation remain required work. A valid signed subject is not proof of
a human principal, a UUID is not an authorization, and a shared internal token is
not end-user or action authority. No human classification or action capability is
issued by this module. Existing service-specific internal-token paths have not
been reconciled by these tests.

The body limit is 128 KiB of decoded response and the JWT limit is 32 KiB. Phase
timeouts are not a total request deadline. Live TLS/proxy/container/distributed
behavior, resource isolation in real SQL, rate limits and full dependency graphs
remain unqualified. Core MCP tools remain unavailable; no action, provider effect
or engine migration is enabled by this change.
