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
