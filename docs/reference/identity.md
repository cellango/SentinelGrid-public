# Identity and tenant review boundaries

Status: source review only. The [tenant UUID rule](../AGENTS.md) is a required
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
Persistent audit/session controls and ITDR/NHI/SCIM/editor reconciliation remain
separate IAM migration slices. The policy checks below cover source decisions only.

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
context spoofing, stale grants, scoped targets, expiry and write failures. Live
identity provisioning, all downstream enforcement and durable audit/RLS/session
qualification remain open. Existing usage/log errors deny, but application logs
are not a persistent decision audit trail and the legacy policy audit helper is
not used to commit partway through authorization. No schema change is included.
