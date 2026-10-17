# Current delegated identity verification

Status: shared verification receipt checks plus mounted-gateway user identity
guards, strict browser credential resolution and a bounded workload-read contract.
Offline source checks only; complete route authorization, delegated actions and a
supported login remain open.
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

## IAM in-process user identity

IAM's [shared request context](../../backend/agents/iam_agent/app/api/request_context.py)
now uses the same owned `IAM_USER_CLIENT_BINDINGS` and signed user contract as the
gateway. Its current `TokenValidator(None)` remains the RSA/issuer/key authority;
IAM does not call its own validation endpoint. The shared
[receipt checks](../../backend/libs/sg_core/iam_verification.py) also check the
in-process result against the exact submitted claims, tenant/subject/roles,
audience and expiry. Parsing that token or constructing a result/context is not
signature verification. Contradictory or unavailable results fail closed without
returning raw validator diagnostics. Unavailable trusted keys currently return 401.

Direct IAM requires an explicit bearer. Cookie-only and browser session-marker
forms stay at the gateway; this change does not expand direct cookie-authenticated
mutation entrypoints. A matching bearer and access cookie is unambiguous, while
duplicate/malformed/conflicting credentials are rejected. The opaque internal
service credential plus a tenant header no longer establishes an IAM request
context. Workload JWTs, actor/exchange claims and unknown clients/tenants cannot
enter this user contract. Registration policy defaults to empty.

The immutable context contains the verified UUID tenant/subject, roles and owned
realm; optional email/username come only from signed claims. A server-private
request cache binds it to the exact token, not public request state. Conflicting
or duplicate tenant/realm hints and forwarded user/role/internal-token hints are
rejected, including when the context is reused. Canonical and legacy IAM Portal
policy user-info import names project this same context used by tenant sessions;
they no longer run separate token validators or log full validation payloads.

`make preview-iam-identity` mounts the actual policy and access-request routers
with generated RSA tokens and the current IAM validator. It checks positive
same-tenant data paths, one consistent identity for session/service/user info,
user-specific access-request filters, unavailable policy, forged/expired/foreign
credentials, hint conflicts, workload/static-token mutation attempts and retained
source-admission denial. Keys, session creation and domain data are test doubles;
the existing IAM unit harness supplies a Redis double. This is not real SQL/RLS,
full IAM startup, live provider registration/grant qualification or action authority.
Existing source selection and domain authorization/action restrictions remain.
SCIM retains its separate owned read-client contract. Other legacy IAM validators
and direct-library/worker callers still require reconciliation; this section does
not clear every IAM entrypoint or restore scheduled/workload operations.

## Direct-service workload reads

[The read contract](../../backend/libs/sg_core/workload_reads.py) reuses the same
IAM signature and receipt authority. It authenticates a registered workload reading
its own tenant; it does not delegate an end user or grant write/action authority.
Owned `SERVICE_READ_WORKLOAD_BINDINGS` JSON lists exact `issuer`, `client_id`,
canonical UUID `subject_id` and `tenant_id`, `service_id`, `permission` and
`contract: keycloak-workload-read-v1`. The immutable settings default to no bindings;
unconfigured reads fail closed. Issuers require HTTPS outside development/test.

A verified token must include `typ: Bearer`, `sg_principal_type: workload`,
`sg_identity_contract: keycloak-workload-read-v1`, exact `azp`/subject/tenant, and
`sg_permissions: ["ticketing.read"]`. Its audience set must be exactly the owned
`KEYCLOAK_CLIENT_ID` and `urn:sentinelgrid:service:ticketing_service`. Actor/exchange
claims are rejected; a signed role or user token supplies no workload permission.
The lifetime and current age cannot exceed 60 seconds, and `jti` must be a non-nil
canonical UUID. The signed `sg_request` object has exactly these fields:

| Field | Required binding |
| --- | --- |
| `service_id` | Server-selected `ticketing_service` |
| `method` | `GET` |
| `path` | Exact concrete request path, including resource/tab identifiers |
| `query_sha256` | SHA-256 hex digest of the exact raw query bytes, including order |

The three current read declarations are GET `/api/v1/tickets`,
`/api/v1/tickets/{ticket_id}` and `/api/v1/tickets/{ticket_id}/tabs/{tab_name}`.
The service adapter checks both the owned route declaration and concrete target;
unreviewed aliases cannot inherit admission. Encoded/ambiguous paths, read bodies,
conflicting/duplicate tenant or realm hints and forwarded user/role/internal-token
headers are rejected. Successful admission supplies the verified tenant to the
existing ticket session and domain lookup; a caller header cannot select it.

The [shared dependency](../../backend/libs/sg_core/dependencies.py) no longer
accepts a tenant UUID from a header. Its legacy unscoped entrypoint returns 503.
All five production import sites now use explicit service adapters: ticketing API
and database, scanner API and entrypoint, and SOAR's built-in catalog API. Writes
remain unavailable. Scanner artifact reads and SOAR shared-catalog reads also
remain unavailable pending their object/credential and catalog-ownership reviews.
The logical `soar_service` auth ID maps the existing `soar_agent` source folder;
this change does not rename a deployment or installed identity.

Existing gateway ticket proxies forward tenant hints without this workload token,
so they cannot use these reads yet. Required gateway, scheduler and direct-call
compatibility, scanner/SOAR operations and all mutations remain restoration work.
No token issuer, workload credential provisioning, provider registration/mappers,
end-user delegation or live caller adoption is supplied. The example user-client
fragment above must not be repurposed as workload issuance. This is a local contract,
not a claim of RFC 9068 compliance, DPoP or mTLS. The exact read can repeat until
expiry; `jti` is a binding, not a consumed nonce. No one-time replay protection,
durable read audit or provider/effect qualification is claimed.

`make preview-workload-reads` checks positive registered RSA-signed reads and
forged/foreign/expired/ambiguous/missing authority. A separate process mounts the
actual ticket router and tenant dependency with the current IAM validator in an
isolated namespace. Only key/HTTP I/O, SQL-session creation and domain data reads
are test doubles. Rejections must precede scoped session creation; accepted reads
must carry the exact tenant and resource. This does not qualify SQL execution,
full service startup, provider issuance or a deployed caller.

## Orchestrator HTTP source boundary

The [actual orchestrator](../../backend/services/orchestrator/app/main.py) now applies
[a common gate](../../backend/services/orchestrator/app/core/security.py) to every
FastAPI application route. Each of its six source routers also carries that gate
so standalone router inclusion cannot restore an unqualified operation. Exact GET
`/` and `/health` expose local metadata without data, provider or readiness probes.
Schema/docs and unmatched method/path errors do not enter business handlers.

The only admitted business source operation is GET
`/api/v1/orchestrator/tenant/{tenant_id}/posture-score/history`. It requires a strict
direct bearer, the existing delegated IAM verification receipt and signed user
contract, matching `IAM_USER_CLIENT_BINDINGS`, plus an explicit
`ORCHESTRATOR_POSTURE_HISTORY_READERS` JSON grant. Each grant names exact `issuer`,
`client_id`, canonical UUID `tenant_id` and `subject_id`, and
`permission: posture.read_history`. Grants must reference an owned user-client
registration; duplicate grants and wildcards are rejected. Both policy lists
default to empty. User classification or an administrator role alone is insufficient.
The [policy model](../../backend/services/orchestrator/app/core/principal_policy.py)
is owned configuration, not a token issuer or evidence of live provider registration.

The application binds immutable verifier/policy snapshots from its own settings.
`IAM_AGENT_URL`, `KEYCLOAK_CLIENT_ID`, `IAM_TOKEN_VALIDATION_TIMEOUT` and
`IAM_VERIFIER_CA_BUNDLE` use the shared transport contract above. Forwarded
identity fields cannot select that verifier. The path tenant must match the verified
UUID exactly; encoded targets, conflicting/duplicate hints, forwarded actor/role/
internal-token fields, bodies and unknown/duplicate query keys are rejected.
Only one optional `limit` is accepted, from 1 through 90 (default 14).

The history handler performs one parameterized SELECT from the fixed
`public.posture_score_snapshot` source using the verified tenant and bounded limit.
It does not compute/persist a score or call another service. Storage failures return
503 rather than fabricated empty success; an actual empty result remains
`{"items": []}`. This is source admission only. That legacy table is not part of the
qualified Flyway profile: physical ownership, schema/model/Flyway adoption, SQL/RLS,
installation and data compatibility remain required before supporting the read.
This change creates no table, schema or migration and runs no legacy Alembic setup.

The other twenty current operations return 503 before their handler dependencies:
aggregate snapshots/dashboard/recommendations/queues, scoring/rescore, phishing
analysis, response/remediation, execution status/report, scanner registry/health,
readiness/global metrics and the synthetic internal alert stub. Some GETs write
scores or call models; their method names do not make them effect-free. Required
functionality remains restoration work with owned data/workload/operator/action
contracts. Global readiness/metrics cannot be exposed as tenant data, and a shared
credential plus arbitrary tenant cannot regain user authority. No workflow engine,
provider effect, direct-library action authority or scheduler/workload admission is
implemented by this gate. Direct component calls still require separate review.

`make preview-orchestrator-identity` tests the actual assembly with current IAM RSA
validation in an isolated process, replacing key/HTTP I/O and history storage. It
checks accepted exact readers, foreign/forged/expired/unavailable authority, all
unqualified operations, standalone aliases, query limits and store failure. No
identity/admission override is used in these boundary tests. Existing scanner-metric
and readiness component tests explicitly bypass HTTP admission or call the rendering
functions directly; they do not qualify those routes. Local metadata is not a
supported runtime/readiness claim. All other caller/provider/action, deployment
and runtime qualifications remain open under root release scope.

## SOAR owned definition reads and source admission

The [actual SOAR assembly](../../backend/agents/soar_agent/app/main.py) and all five
routers now apply an [exact source gate](../../backend/agents/soar_agent/app/core/security.py)
before handler dependencies. Only exact GET `/` and `/health` expose local metadata.
GET `/soar/playbooks` and `/soar/playbooks/{playbook_id}` are the two admitted business
source reads. A strict direct bearer, the current IAM receipt/user contract and
`IAM_USER_CLIENT_BINDINGS` are required, together with an explicit
`SOAR_PLAYBOOK_READERS` grant. Each grant names exact `issuer`, `client_id`, canonical
UUID `tenant_id` and `subject_id`, and `permission: playbook.read_owned`. Grants must
reference an owned user-client registration; both policy lists default to empty.
A user UUID, administrator role, workload token or constructed context grants no
read by itself. Verifier and policy snapshots come from SOAR's owned settings,
using the same IAM origin/audience/timeout/CA rules as the other services above.

[The owned reader](../../backend/agents/soar_agent/app/services/playbook_reader.py)
performs tenant-only ORM SELECTs; detail reads additionally bind the resource UUID.
It never constructs the legacy service that looks up `sg_admin` or merges global
built-ins. A built-in flag cannot expose another tenant's row; contradictory row
ownership fails closed. The existing logical definition/version projection is
retained, with the installed `n8n_webhook_url` withheld and no stored-row mutation.
This is not a general credential-redaction review of arbitrary saved workflow data.
The shared catalog and its intended functionality remain separate restoration work.

Conflicting/duplicate tenant/realm hints and forwarded actor/role/internal/API-key
headers are rejected. Reads accept no body or encoded target. The list permits only
one each of `category` (up to 50 characters), `is_template`, `skip` (0–10,000) and
`limit` (1–100, default 100); queries are bounded to 4 KiB and validated before session
creation. Detail accepts no query fields. Unknown/duplicate query keys cannot
supply tenant or authority. A genuine empty list is returned unchanged, a missing
owned detail is 404, and store/session failures return generic 503 without private
diagnostics. Function-scoped session cleanup finishes before a response can succeed.

The [session dependency](../../backend/agents/soar_agent/app/core/database.py) derives
its tenant from this verified read context and uses the existing shared transaction/
pool tenant-binding helper. The legacy raw-UUID session entrypoint is unavailable;
`init_db` refuses runtime table creation. ORM mappings and the existing SOAR Flyway
files are unchanged. Physical schema ownership/search path, ORM/Flyway adoption,
least-privilege roles, real SQL/RLS, upgrades/data and complete installation remain
required before supporting these reads. Source tests use storage/session doubles.

The other 26 unique current operations stay unavailable and required restoration
work: definition writes/approval/execution, shared/OOTB catalog and seeding, execution
status, TheHive/analyzers/observables, webhooks/detection ingress, containment,
enrichment and the internal execution stub. Independent webhook validators no
longer promote API/shared credentials plus a tenant header into authority; query
session helpers also deny. Enrichment clients are initialized lazily after admitted
dependencies, not on module import. No model/provider/worker/queue or workflow engine
is enabled. Direct component/library calls still require their own action authority.
Two existing duplicate write declarations (copy/validate) remain blocked; full
route/status/schema/client compatibility reconciliation is still required.

`make preview-soar-identity` mounts the actual assembly and owned reader, with the
current IAM RSA validator in a separate process, key/HTTP and session/query-result
doubles, and no identity/admission override. It checks exact tenant/resource queries,
foreign built-in rows, store/session failures, missing/forged/expired/foreign identity,
raw credentials/hints/queries, all unavailable operations and standalone helpers.
Legacy tests that treated header-only or shared-token calls as accepted now assert
source denial. A legacy execution-unit model double is scoped to its own test module;
those unit tests do not qualify real execution. Older database-integration fixtures
still require an owned managed profile and are not advertised as passing runtime
qualification. No workload issuer, live provider registration/client/grant policy,
shared catalog, action approval/audit/effect or full feature migration is qualified.

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

Required work remains: other direct-service/internal-token caller reconciliation,
workload credential issuance/caller adoption and end-user delegation, provider registration/drift and tenant-claim
qualification, complete proxy header/target/action/version/error contracts, and
existing route/test migration. Core MCP tools remain unavailable. No provider
effect or engine migration is enabled by these source controls.

The verifier limits decoded responses to 128 KiB and JWTs to 32 KiB. Phase timeouts
are not total deadlines. Live TLS, container/ingress/distributed behavior, SQL
isolation, cookie-mutation CSRF/origin policy, rate limits and full dependency graphs
remain unqualified. Root release scope continues to govern execution.
