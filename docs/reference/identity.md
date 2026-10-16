# Identity and tenant review boundaries

Status: focused source and disposable-database review; deployment qualification remains pending. The [tenant UUID rule](../AGENTS.md) is a required
invariant, not evidence that all existing endpoints enforce it. Slugs are a
customer-facing convenience at the gateway edge; downstream programmatic traffic
must use the authenticated tenant UUID and reject mismatches.

| Boundary | Source to inspect |
| --- | --- |
| Browser/API proxy routes | [frontend API routes](../../frontend/src/app/api/), [gateway routes](../../backend/services/api_gateway/app/api/) |
| IAM token validation and public auth | [auth.py](../../backend/agents/iam_agent/app/api/auth.py), [IAM services](../../backend/agents/iam_agent/app/services/) |
| Shared service security helpers | [security.py](../../backend/libs/sg_core/security.py) |
| Tenant-aware persistence | [shared models](../../backend/libs/sg_core/models.py) and individual service queries |
| Regression evidence | [IAM auth tests](../../backend/agents/iam_agent/tests/test_auth_api.py) and [release review](../release/review.md) |

## IAM token validation source checks

The [IAM validator](../../backend/agents/iam_agent/app/services/token_validator.py)
now uses PyJWT's RS256 signature, exact issuer, audience and time validation, with
required subject and tenant UUID claims. It rejects unsigned/wrong-algorithm tokens,
untrusted issuer origins/realm paths, missing or incompatible signing keys and
invalid claim types. Identity comes from verified claims; email domains and realm
names cannot remap a tenant. Failed validation has no authenticated payload.

Signing keys come only from configured `KEYCLOAK_URL`, using
`KEYCLOAK_VERIFY_TLS`, bounded cache lifetime and no redirects. An external browser
issuer must be explicitly configured using `KEYCLOAK_ISSUER_BASE_URLS`, a JSON list
of trusted bases such as `["https://identity.example.test"]`. The base excludes
`/realms/...`; each token must match an exact base plus a valid realm segment.
Production also requires secure issuer-base URLs. Tokens must include
`KEYCLOAK_CLIENT_ID` in `aud`; configure the identity provider's audience mapper
rather than accepting `azp` or disabling audience validation. No automatic
localhost/public-host aliases are added.

Introspection validates the JWT boundary before using signed identity. Explicit
inactive results deny; unavailable introspection retains the existing local signed-
JWT fallback and therefore cannot prove immediate revocation. Keys newly rotated
into a cached realm become available after `JWKS_CACHE_TTL` expires; unknown keys
fail closed. Revocation and rotation behavior still require live provider qualification.

The [token tests](../../backend/agents/iam_agent/tests/test_token_validator.py) use
real ephemeral RSA keys/signatures with mocked key transport; configuration tests
also retain TLS/production guards. They run in `make preview-check` alongside the
existing mocked auth-route checks. This verifies the named source boundary, not
live Keycloak configuration, all callers, RLS or an operational IAM deployment.
Focused audit/session controls are described below. ITDR/NHI/SCIM/editor and full
IAM acceptance remain separate migration slices; live provider/runtime qualification
is pending.

The old direct-reset endpoint returns HTTP 410 in IAM and the frontend proxy;
that removes the bypass and does not implement account recovery. The mocked tests
prove the named route does not construct an identity-provider admin client.
They do not certify live Keycloak, SSO, MFA, realm provisioning, enrollment,
all internal callers, or a two-tenant end-to-end isolation boundary.

The agent runtime and AI Shield Go gateway retain the known missing-configuration
internal-token fallback described in [the credential review](../release/credentials.md).
Those runtimes are excluded from supported execution. Do not translate old
"resolved" tenant-attribute notes or production signoffs into a current security
claim. Use [SECURITY.md](../../SECURITY.md) for private findings; no product
credentials are needed to run the supported preview checks.

## IAM authorization and policy source checks

`/api/v1/authorize` and its batch route now require a current, active, unexpired
user entitlement matching the authenticated tenant, subject, resource and action,
plus an explicit applicable `access` or `authorization` policy `allow`. Missing
policies, no matching grant, lookup failures and unsupported definitions deny.
Only `*` is a resource wildcard; the complete remaining suffix must match.
Decision caching is disabled; the `use_cache` service argument and tenant-scoped
cache-clear endpoint remain compatible with existing callers and old entries.

Every active applicable policy is evaluated, including configured `sod` rules.
Priority, policy order and action order cannot make an allow or challenge override
a denial. Deny takes precedence, followed by approval, step-up and explicit allow.
`log` and `notify` are auxiliary declarations; this evaluator does not send
notifications or treat them as grants. Unsupported actions, including
`auto_approve`, deny until a separately reviewed implementation exists. The
binary authorization endpoint denies step-up/approval requirements: request-body
`mfa_verified`, `approved` or similar flags cannot fulfill them.

Tenant policies apply to every requested target. App-scoped policies match an
exact `resource_type="app"` and resource UUID; entitlement-scoped policies match
current matching entitlement UUIDs. Scoped policies require a UUID. The stored
policy type/scope must agree with its DSL. No implicit app membership, resource
hierarchy, group inheritance or automatic provider action is implemented.

Policy rules AND their conditions; an empty condition list matches. The supported
facts are `role`, `group`, `department`, `ip`, `country`, `device_known`,
`time_of_day`, `day_of_week`, `risk_level`, `risk_score`, `user_id`, `username`,
`email`, `resource`, `resource_type` and `action`. Operators are `equals`,
`not_equals`, `includes`/`contains`, `in`/`not_in`, `greater_than` and `less_than`.
Operands must have compatible types; ordered comparisons are numeric. Missing
facts and unsupported fields/operators fail closed, including in a condition
following a false condition. Model-generated/custom attributes are not authority.

For authorization, subject roles come from the verified caller's token for
self-requests. Only verified `TENANT_ADMIN`, `IAM_ADMIN`, `PLATFORM_ADMIN` or
`INTERNAL_SERVICE` callers can request another subject in the same tenant; their
own roles are never substituted for that subject's roles. Such delegated requests
have unavailable subject roles and therefore deny any role-dependent policy until
an authoritative subject lookup is implemented. The peer IP comes from the server
request, without trusting forwarded headers. Time is current server UTC, formatted
as `HH:MM` and a lowercase weekday. Groups, risk, device, location and directory
attributes remain unavailable to authorization until trusted providers are added;
policies requiring them deny. Caller metadata cannot supply trusted facts.

Policy create/update/delete/activate/reject, seed cloning, template instantiation
and `/policies/evaluate` require verified `TENANT_ADMIN`, `IAM_ADMIN` or
`PLATFORM_ADMIN` roles within the authenticated tenant. The evaluation endpoint
and the duplicate legacy IAM Portal policy routes use the same guard and evaluator.
Evaluation is an administrator simulation using supplied hypothetical facts; its response
cannot authorize an action. A SoD policy can deny conflicting verified role
combinations without hardcoded role pairs, and a SoD-only allow cannot grant access.

The [policy regressions](../../backend/agents/iam_agent/tests/test_policy_enforcement.py)
and tenant-route checks run in `make preview-check` with synthetic storage and
blocked database initialization. They test default deny, ordering, SoD conflicts,
context spoofing, stale grants, scoped targets, expiry and write failures. These are focused source checks. The durable audit and database tests below extend
that boundary; live identity provisioning and all downstream enforcement remain open.


## Persistent audit and tenant database checks

The shared `DB_URL` holds app-catalog entitlements, policies and directory/catalog
records. `IAM_DB_URL` explicitly selects a **separate PostgreSQL database** for
fine-grained access grants, governance and grant audit; it is never inferred from
`DB_URL`. Missing grant-store configuration returns HTTP 503. Selecting the same
configured host/port/database for both stores is rejected. Catalog `app_id`/`name`
rows and grant `resource_type`/`resource_id`/`action` rows are incompatible contracts.
The session split preserves them; it moves no existing data. Authorization reads
policy state in the shared tenant session and commits grant usage and its audit in
the IAM session. These reads across databases are not a distributed transaction or
an exact provider-action authorization/approval mechanism.

New [V014](../../backend/migrations_consolidated/V014__public_iam_audit_and_tenant_guards.sql)
and [IAMAuditEvent](../../backend/agents/iam_agent/app/models/audit_event.py) add
`public.iam_audit_events` without altering or backfilling legacy `entitlement_audit_log`.
The new table records tenant, actual actor/type, subject, decision, resource/action,
reason and bounded redacted context/change snapshots. IDs have no cascading foreign
keys, so deleting a live grant cannot erase the new event. Legacy history retains
its existing shape and retention limitations; it is not silently relabelled or copied.
Credential-like payload keys are redacted; this is not a complete arbitrary-PII
classification or external tamper-evidence system.

Each allow/deny made by the evaluation engine, including lookup errors, attempts an
event. Authentication/admission rejections before evaluation are outside this stream. Allow requires
an audit commit in the same IAM transaction as usage. Audit failure rolls back usage,
returns a deny marked unaudited internally, and the HTTP authorization adapter returns
503. It does not claim that an unavailable database recorded the failed attempt.
The individual and bulk grant-create/update/revoke paths couple changes and events
in one transaction; bulk items use savepoints and report success only after the
outer commit. Grant mutations require a verified tenant administrator and user UUID;
a body `granted_by` value or a previous grantor cannot impersonate the current actor.
Other legacy governance/editor/provider writers still need their feature acceptance.

The [shared transaction helper](../../backend/libs/sg_core/tenant_session.py) validates
a UUID before opening a session and binds parameterized transaction-local `set_config`
on every SQLAlchemy transaction, including savepoints and transactions after commit/
rollback. A session cannot be rebound to another tenant. Pool checkout clears old
session-level tenant/admin settings outside a transaction. IAM ownership helpers
require an explicit authenticated tenant; a resource merely having a tenant or a
user UUID is insufficient. Importing IAM database configuration no longer runs DDL.

V014 forces RLS for the named existing IAM tenant tables and parent-bound child rows.
Restrictive guards intersect older permissive policies, preventing the
`app.is_superadmin` flag from widening those tables. New audit events permit scoped
read/append and prohibit application update/delete. The application must be a
nonowner, nonsuperuser, `NOBYPASSRLS` role without policy-alter, role-membership or
truncate privileges. The old shared superadmin helper fails closed; the IAM helper's
legacy name retains platform-role checks and tenant scope. Cross-tenant maintenance
requires a separately provisioned operational identity, not an application flag.
Custom tenant settings remain trusted middleware input, not protection from a
compromised service that can execute arbitrary SQL.

Run `make preview-check` for unit/source checks and `make preview-iam-db` for the
[real database suite](../../backend/agents/iam_agent/tests/test_iam_database.py).
The latter requires PostgreSQL server tools (`SG_TEST_PG_BINDIR` can select them)
and starts/removes its own private Unix-socket cluster, ignoring existing DB URLs.
Missing tools fail the gate. It tests two tenants using a nonowner application role,
commit/rollback/savepoint/pool reuse, stale session flags, invalid context, cross-tenant
writes/child links, model/DDL parity, immutable audit writes, retained legacy rows,
allow/deny events and atomic failure handling. Local qualification used PostgreSQL
17.5, SQLAlchemy 2.0.39 and psycopg2 2.9.10. The separate CI job targets PostgreSQL 16
on Ubuntu; its hosted result must be checked after publication of this change.

The [database profile notes](../architecture/database-compatibility.md#iam-audit-and-session-implementation)
explain history selection and adoption gates. These tests qualify the named boundary
and synthetic upgrade. They do not certify the complete V001–V013 application
baseline/Flyway runner, arbitrary populated legacy databases, all views/functions,
all downstream endpoints or live identity configuration. Shared/global grant patterns
and seed clones receive no cross-tenant exception in the new guards; their authorized
sharing path and the older governance model/schema differences remain feature
reconciliation work before runtime enablement.
