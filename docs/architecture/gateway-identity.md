# Current delegated identity verification

Status: shared verification receipt checks plus mounted-gateway user identity
guards and strict browser credential resolution. Offline source checks only;
full route authorization, workload delegation and a supported login remain open.
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
| `IAM_USER_CLIENT_BINDINGS` | Exact owned issuer/client/tenant registrations for the user contract below; empty by default |

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

## Browser credentials and one request identity

[The common resolver](../../backend/libs/sg_core/request_credentials.py) reads raw
ASGI headers before middleware can collapse duplicates. It accepts one bearer,
one `access_token` cookie, the existing `Bearer session-cookie` marker with that
cookie, or matching bearer and cookie values. It rejects duplicate Authorization
fields, repeated access cookies, malformed schemes/tokens, quoted or empty access
cookies and conflicting bearer/cookie values. An invalid header cannot fall back
to a cookie. A marker or cookie is not itself authenticated.

Both tenant and payload dependencies use the same verified request snapshot. A
missing payload credential now returns 401. A credential change during a request
cannot reuse the previous identity, and a returned payload copy cannot change
another dependency's tenant or roles. A typed object, request-state dictionary,
UUID or forwarded identity hint cannot create the server-private verified cache.
CORS wraps credential rejection as well as successful responses.

## User versus workload contract

[User principal admission](../../backend/libs/sg_core/user_principals.py) requires
both the verified provider claims and an exact owned binding. Each binding names
`issuer`, `client_id`, canonical `tenant_id`, `contract: keycloak-user-v1`,
`service_accounts_enabled: false` and `token_exchange_enabled: false`. Bindings
are JSON configuration, not request fields. Several explicit tenant registrations
may share an issuer/client; duplicate exact registrations and wildcards are not
accepted. Non-development issuers require HTTPS.

The verified access token must have `typ: Bearer`, matching `iss`/`azp`/`tenant_id`,
`sg_principal_type: user` and `sg_identity_contract: keycloak-user-v1`. Actor or
exchange claims (`act`, `may_act`, `client_id`) are not accepted by this user
contract. A UUID subject, username, `sid`, role, or shared internal token does not
identify a human. This gate grants no action capability or provider permission.

The [Keycloak example fragment](../../infra/keycloak/user-principal-contract.example.json)
shows administrator-owned access-token hardcoded claims with machine grants and
standard token exchange disabled. It is a client fragment for review, not an import
or an executed migration. Existing clients/realms are **not** updated automatically.
Before real use, qualify the effective provider/client/grant policy, disable both
standard and legacy exchange paths for this contract, protect tenant claims from
user edits, and verify audience/mappers against the deployed Keycloak version.
Do not populate a user attribute or request body and treat it as a trusted mapper.
See the upstream [mapper reference](https://www.keycloak.org/admin-api/protocol-mappers)
and [token exchange guide](https://www.keycloak.org/securing-apps/token-exchange).
Bindings attest an owned registration policy; this code does not detect live
provider drift. Missing or unavailable registration returns 503; valid tokens
outside that user contract return 403. The default empty policy admits no users.

## Mounted gateway boundary

[The actual gateway](../../backend/services/api_gateway/app/main.py) binds verifier
and user policy snapshots to its own settings and applies the
[identity gate](../../backend/services/api_gateway/app/core/request_identity.py)
to every mounted FastAPI application route. Exact GET health/readiness/metrics
and POST login/refresh pairs retain their existing unauthenticated contracts.
No prefix, body flag or administrator role bypass is provided. Framework schema/docs
and unmatched paths do not execute business handlers.

Tenant/realm hints on user routes must match the verified identity exactly;
duplicates or conflicting actor/role/internal-token hints are rejected before
route dependencies. User identity is required for the existing legacy agent
routes too. The earlier included versions route receives the verified UUID; a
shadowed legacy handler no longer supplies a fabricated dashboard tenant.
Duplicate/shadowed route and OpenAPI operation-ID reconciliation remains open.

AI Shield's shared-token ingestion and the three global ingest diagnostics return
503 before their handler dependencies run. Their required functionality remains
migration work pending exact workload/admin delegation. They cannot promote a
shared credential and caller-selected tenant into user authority. Other downstream
proxy/action contracts still require their own authorization and qualification;
passing this identity gate does not qualify their effects or error semantics.

## Qualification and remaining work

`make preview-gateway-identity` retains the real generated RSA/current IAM validator
and response-model round trip with HTTPX MockTransport replacing network I/O.
`make preview-gateway` additionally mounts the actual gateway with real RSA tokens
and a verifying IAM HTTP test double. It checks all OpenAPI business method/path
pairs for unauthenticated denial, positive browser forms on the actual alert
route, signed workload/foreign/forged/expired context, raw credential conflicts,
immutable dependency sharing, exact registration, outages and blocked operations.
The two positive data operations use spies; no real SQL/provider/model is accessed.
Named older auth/config/metrics regressions run separately. The older route-unit
fixtures explicitly override identity and are not authentication acceptance evidence.

A wider legacy gateway run has existing failures and missing `pytest-mock` fixtures;
a comparison with the previous commit found no newly failing case after fixture
isolation was updated. That suite is not advertised as passing. The loopback HTTP
integration test and its runtime behavior remain outside these offline gates.

Required work remains: direct-service/internal-token caller reconciliation,
workload credentials/delegation, provider registration/drift and tenant-claim
qualification, complete proxy header/target/action/version/error contracts, and
existing route/test migration. Core MCP tools remain unavailable. No provider
effect or engine migration is enabled by these source controls.

The verifier limits decoded responses to 128 KiB and JWTs to 32 KiB. Phase timeouts
are not total deadlines. Live TLS, container/ingress/distributed behavior, SQL
isolation, cookie-mutation CSRF/origin policy, rate limits and full dependency graphs
remain unqualified. Root release scope continues to govern execution.
