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
Policy/SoD, persistent audit/session controls and ITDR/NHI/SCIM/editor reconciliation
remain separate IAM migration slices.

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
