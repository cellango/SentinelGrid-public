# SentinelGrid P0 Test Capability Specs

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Date: `2026-03-27`

This document applies the coverage-spec template from `docs/TEST_SUITE_SPEC_REBUILD_PLAN.md` to the first P0 areas that should anchor the rebuild.

Use these sections as the implementation contract for new or refit tests. Current product behavior is the source of truth. Legacy tests are only supporting evidence.

Status note:

- `KEEP`, `REFIT`, and `REPLACE` match the rebuild-plan vocabulary
- `NEW` means there is no current test worth carrying forward for that scenario

## Capability: Authentication And Session Establishment

Owner: `frontend/src/app/(marketing)/login/page.tsx`, `frontend/src/app/api/auth/login/route.ts`, `backend/services/api_gateway/app/api/routes_auth.py`, `backend/services/api_gateway/tests/test_auth_middleware.py`, `backend/agents/iam_agent/app/api/auth.py`

Criticality: `P0`

Primary surfaces:

- `/login`
- `POST /api/auth/login`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /internal/iam/auth/validate-token`
- `GET /internal/iam/auth/introspect`

Source of truth:

- `frontend/src/app/(marketing)/login/page.tsx`
- `frontend/src/app/api/auth/login/route.ts`
- `backend/services/api_gateway/app/api/routes_auth.py`
- `backend/services/api_gateway/tests/test_auth_middleware.py`
- `backend/agents/iam_agent/app/api/auth.py`
- `backend/agents/iam_agent/tests/test_auth_api.py`
- `docs/UI_UX_ARCHITECTURE_IMPLEMENTATION_TODO.md`

Invariants:

- Successful login ends in an authenticated dashboard redirect to the `redirect` query param or `/dashboard`.
- MFA-required login must not authenticate or redirect until OTP validation succeeds.
- The Next.js login route sets the `access_token` cookie server-side before the dashboard shell relies on auth state.
- The API gateway preserves `x-tenant-id` and `x-realm` headers when proxying login and refresh flows.
- Protected gateway surfaces reject tokens that are invalid or missing tenant identity.
- Token validation and introspection remain tenant-scoped.

Scenarios:

| ID | Scenario | Level | Fixtures | Expected result | Current test | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AUTH-001 | Login page redirects authenticated users to the requested destination or `/dashboard` | component | mocked `useAuth`, mocked router, query params | authenticated render triggers `router.push` to canonical target | none | NEW |
| AUTH-002 | MFA-required login holds on the verification step until OTP is provided and accepted | component | mocked `login`, mocked `loginMFA`, router | MFA view renders, missing OTP is rejected locally, successful OTP redirects | none | NEW |
| AUTH-003 | Next.js login route forwards credentials to IAM and sets `access_token` cookie with the expected session or remember-me lifetime | contract | mocked `fetch`, `NextRequest` fixture | `200` response plus server-side cookie with correct flags and `maxAge` behavior | none | NEW |
| AUTH-004 | Gateway `/login` and `/refresh` preserve tenant and realm headers while proxying to IAM | contract | mocked `httpx.AsyncClient`, request header fixtures | upstream request receives `x-tenant-id` and `x-realm` unchanged | `backend/tests/test_auth_endpoints.py` | REPLACE |
| AUTH-005 | Gateway middleware rejects protected requests with invalid tokens or missing `tenant_id` claims | contract | token payload fixture, test client | request fails with auth error instead of hitting protected handler | `backend/services/api_gateway/tests/test_auth_middleware.py` | KEEP |
| AUTH-006 | Gateway passes the authenticated tenant context into downstream service calls | contract | mocked DB/session plus tenant-scoped client request | tenant ID used for downstream query or filter path | `backend/services/api_gateway/tests/test_auth_middleware.py` | KEEP |
| AUTH-007 | IAM validate-token and introspection endpoints distinguish invalid and valid tokens correctly | contract | mocked token validator and payload fixtures | invalid token rejected, valid token returns tenant-aware identity payload | `backend/agents/iam_agent/tests/test_auth_api.py` | KEEP |
| AUTH-008 | Login and refresh failures propagate useful status/details without leaking internal proxy exceptions | contract | mocked IAM `401`, `403`, `5xx` responses | downstream status/details returned intentionally; proxy error paths stay bounded | none | NEW |
| AUTH-009 | Low-level security and realm-strategy logic remains unit-tested inside the IAM agent instead of through root-path import hacks | unit | local service objects only | deterministic password, realm, and sanitization logic coverage | `backend/tests/test_auth_api_client.py` | REFIT |

CI stage:

- `required-pr`

Notes:

- Keep `backend/services/api_gateway/tests/test_auth_middleware.py` and `backend/agents/iam_agent/tests/test_auth_api.py` as the mainline auth base.
- Replace `backend/tests/test_auth_endpoints.py` with service-local proxy contract tests.
- Split `backend/tests/test_auth_api_client.py` into agent-local unit tests so it no longer depends on root-level `sys.path` surgery.

## Capability: Onboarding Progress And First-Value Activation

Owner: `frontend/src/components/onboarding/OnboardingWizard.tsx`, `frontend/src/components/dashboard/OnboardingBanner.tsx`, `backend/services/api_gateway/app/api/routes_onboarding.py`, `backend/agents/iam_agent/app/api/onboarding.py`

Criticality: `P0`

Primary surfaces:

- `GET /api/v1/onboarding/status`
- `POST /api/v1/onboarding/complete`
- `POST /api/v1/onboarding/connect-idp`
- `POST /api/v1/onboarding/connect-aws`
- `POST /api/v1/onboarding/connect-appsec`
- `POST /api/v1/onboarding/connect-ai`
- `POST /api/v1/onboarding/connect-ticketing`
- `POST /api/v1/onboarding/recheck-health`
- `frontend/src/components/onboarding/OnboardingWizard.tsx`
- `frontend/src/components/dashboard/OnboardingBanner.tsx`

Source of truth:

- `frontend/src/components/onboarding/OnboardingWizard.tsx`
- `frontend/src/components/dashboard/OnboardingBanner.tsx`
- `frontend/src/lib/api/onboarding.ts`
- `backend/services/api_gateway/app/api/routes_onboarding.py`
- `backend/agents/iam_agent/app/api/onboarding.py`
- `docs/UI_UX_ARCHITECTURE_IMPLEMENTATION_TODO.md`

Invariants:

- The onboarding status payload is authoritative for `steps`, readiness flags, `last_incomplete_step_id`, `status_version`, and service-selection state.
- The wizard derives its step list from `services_selected`; `ticketing` appears only when `socManaged === false`, and `tenant` is always the last step.
- Completed steps are seeded from the backend status response plus readiness backfills.
- The dashboard banner renders only when onboarding is still incomplete or people-readiness work remains.
- Banner dismissal is keyed by `status_version`, so a changed onboarding state re-shows the banner.
- The gateway forwards auth and tenant headers to IAM and does not fail onboarding completion if the best-effort initial scan enqueue fails.

Scenarios:

| ID | Scenario | Level | Fixtures | Expected result | Current test | Status |
| --- | --- | --- | --- | --- | --- | --- |
| ONB-001 | Onboarding status returns the canonical progress shape used by the UI | contract | IAM response fixture or service-local test DB | payload includes readiness flags, `steps[]`, `overall_complete`, and `status_version` | `backend/tests/test_onboarding_status_api.py` | REPLACE |
| ONB-002 | Wizard seeds completed steps and renders the canonical flow from backend status | component | mocked `getOnboardingStatus`, auth harness, router | existing completed steps are shown and tenant-readiness remains the final step | `frontend/src/components/onboarding/__tests__/OnboardingWizard.test.tsx` | REFIT |
| ONB-003 | Wizard includes the ticketing step only for customer-managed SOC onboarding | component | mocked onboarding status with `socManaged: false` | `Ticketing` step appears in the flow | `frontend/src/components/onboarding/__tests__/OnboardingWizard.test.tsx` | REFIT |
| ONB-004 | Wizard includes the AI Shield step only when `aiShield` is selected | component | mocked onboarding status with hosted or self-managed AI selected | `AI Shield` step appears in the flow | `frontend/src/components/onboarding/__tests__/OnboardingWizard.test.tsx` | REFIT |
| ONB-005 | Banner shows the current next step and coverage summary while onboarding is incomplete | component | mocked onboarding status, auth provider, local storage | banner renders with next-step summary and progress state | `frontend/src/components/dashboard/__tests__/OnboardingBanner.test.tsx` | REFIT |
| ONB-006 | Banner hides only when both onboarding and people-readiness are complete | component | mocked onboarding status with `overall_complete`, access-profile, and birthright readiness | banner returns `null` | `frontend/src/components/dashboard/__tests__/OnboardingBanner.test.tsx` | REFIT |
| ONB-007 | Banner dismissal is versioned by `status_version` instead of hiding future onboarding deltas forever | component | local storage plus two status versions | dismissing one version does not hide a later version | none | NEW |
| ONB-008 | Gateway `/complete` proxies to IAM and still returns success when the follow-on scan enqueue fails | contract | mocked IAM `200`, mocked orchestrator failure | onboarding completion succeeds and scan enqueue failure is only logged | none | NEW |
| ONB-009 | Gateway onboarding proxy methods forward auth and tenant headers correctly for connector setup and health rechecks | contract | mocked `httpx.AsyncClient`, request header fixtures | upstream request receives tenant/auth context and returns proxied payload/status | `backend/tests/test_onboarding_status_api.py` | REPLACE |
| ONB-010 | Ticketing, AI, AppSec, and cloud health rechecks preserve structured health payloads for the UI | contract | mocked IAM health payloads | recheck response contains `health` dict with the selected target | `backend/tests/test_onboarding_status_api.py` | REPLACE |

CI stage:

- `required-pr`
- real-provider connectivity belongs in `nightly` or `manual`, not in the deterministic gate

Notes:

- Refit the two frontend onboarding suites with a stable auth-provider and `fetch`/analytics harness.
- Replace the tolerant root HTTP tests with deterministic gateway and IAM-agent contract tests.
- Treat provider-specific connectivity as separate nightly coverage once deterministic payload contracts are in place.

## Capability: Dashboard Shell Navigation And Operator Entry Points

Owner: `frontend/src/app/(dashboard)/layout.tsx`, `frontend/src/components/layout/DashboardSidebar.tsx`, `frontend/src/components/layout/DashboardHeader.tsx`, `frontend/src/components/ui/Breadcrumbs.tsx`, `frontend/src/components/ai-chat/CommandPalette.tsx`, `frontend/src/components/layout/NowQueueDock.tsx`, `backend/services/orchestrator/app/services/now_queue_service.py`

Criticality: `P0`

Primary surfaces:

- `frontend/src/app/(dashboard)/layout.tsx`
- `frontend/src/components/layout/DashboardSidebar.tsx`
- `frontend/src/components/layout/DashboardHeader.tsx`
- `frontend/src/components/ui/Breadcrumbs.tsx`
- `frontend/src/components/ai-chat/CommandPalette.tsx`
- `frontend/src/components/layout/NowQueueDock.tsx`
- `GET /api/v1/orchestrator/dashboard/now-queue`
- `GET /api/v1/orchestrator/dashboard/stream`

Source of truth:

- `frontend/src/app/(dashboard)/layout.tsx`
- `frontend/src/components/layout/DashboardSidebar.tsx`
- `frontend/src/components/layout/DashboardHeader.tsx`
- `frontend/src/components/ui/Breadcrumbs.tsx`
- `frontend/src/components/ai-chat/CommandPalette.tsx`
- `frontend/src/components/layout/NowQueueDock.tsx`
- `backend/services/orchestrator/app/services/now_queue_service.py`
- `backend/services/orchestrator/tests/test_welcome_prioritization.py`
- `docs/UI_UX_ARCHITECTURE_IMPLEMENTATION_TODO.md`

Invariants:

- The dashboard shell redirects unauthenticated users to `/login` after auth hydration settles.
- Shell-level widgets that require tenant context render only when an effective tenant is available.
- Primary navigation remains grouped into `Detect`, `Respond`, and `Govern`, with plan and role gating preserved.
- Header route metadata must match canonical dashboard routes and power consistent titles and subtitles.
- Breadcrumbs replace dynamic IDs with human-readable entity labels when resolver data is available.
- The command palette is a universal dashboard entry point for route jumps, entity search, recent items, saved actions, and AI fallback.
- The Now Queue dock persists its expand/collapse state and falls back to polling when SSE is unavailable.

Scenarios:

| ID | Scenario | Level | Fixtures | Expected result | Current test | Status |
| --- | --- | --- | --- | --- | --- | --- |
| DSH-001 | Dashboard layout renders a loading state until auth is hydrated and then redirects unauthenticated users to `/login` | component | mocked auth provider, router, storage state | loading status first, then redirect or `null` shell for unauthenticated state | none | NEW |
| DSH-002 | Shell-level tenant widgets render only when partner tenant context resolves an effective tenant | component | mocked auth provider and partner tenant context | `NowQueueDock`, `CommandPalette`, and chatbot are absent without tenant context and present with it | none | NEW |
| DSH-003 | Sidebar preserves the `Detect` / `Respond` / `Govern` grouping and plan gating | component | mocked auth provider, pathname, plan tier overrides | lower tiers do not see gated items; canonical groups remain visible | none | NEW |
| DSH-004 | Header maps canonical routes to the correct workflow, title, and subtitle and exposes command-palette entry points | component | mocked pathname, `openCommandPalette` spy | route metadata matches canonical path and search entry opens the palette | none | NEW |
| DSH-005 | Breadcrumbs resolve alert, incident, ticket, scan, app, and certificate IDs to human-readable labels | component | React Query harness plus mocked entity APIs | resolved breadcrumb trail shows readable labels instead of raw IDs | none | NEW |
| DSH-006 | Command palette returns grouped route, entity, recent, saved, and AI fallback results with plan-aware filtering | component | mocked route context, API search results, auth provider | results are grouped and filtered correctly, keyboard navigation works | none | NEW |
| DSH-007 | Now Queue dock restores persisted collapse state, renders queue priority summaries, and falls back to polling when stream support fails | component | query client, local storage, mocked SSE hook, mocked dashboard API | persisted state is restored and polling activates on stream error or unsupported mode | none | NEW |
| DSH-008 | Backend prioritization keeps incidents ahead of alerts and recommendations in the shell queue model | unit | local payload fixtures only | item ordering and summary counts remain stable | `backend/services/orchestrator/tests/test_welcome_prioritization.py` | KEEP |
| DSH-009 | Recommendation generation surfaces activation work, including degraded ticketing handoff, before lower-signal tasks | unit | local posture, onboarding, people-access fixtures | top recommendations prioritize activation and operator-value work first | `backend/services/orchestrator/tests/test_welcome_prioritization.py` | KEEP |

CI stage:

- `required-pr`
- one thin browser smoke for shell load, nav, and command palette can be added later after the component suite exists

Notes:

- There is effectively no trusted frontend shell coverage today; this capability is mostly `NEW`.
- Keep the backend prioritization tests as the data-contract anchor for queue ordering while the shell tests are rebuilt on top.

## Capability: Tenant Isolation And Tenant Resolution

Owner: `backend/services/api_gateway/app/utils/tenant_resolution.py`, `backend/services/api_gateway/tests/test_tenant_resolution.py`, `backend/services/api_gateway/tests/test_auth_middleware.py`, `backend/libs/sg_core/security.py`, `backend/agents/iam_agent/app/core/tenant_isolation.py`, `backend/services/ingestion_service/tests/test_multi_tenant_isolation.py`

Criticality: `P0`

Primary surfaces:

- gateway tenant resolution utilities
- gateway auth middleware and `get_current_tenant`
- shared tenant-isolation helpers in `sg_core`
- IAM-agent tenant-isolation helpers
- ingestion-service tenant filtering and batch isolation

Source of truth:

- `backend/services/api_gateway/app/utils/tenant_resolution.py`
- `backend/services/api_gateway/tests/test_tenant_resolution.py`
- `backend/services/api_gateway/tests/test_auth_middleware.py`
- `backend/libs/sg_core/security.py`
- `backend/agents/iam_agent/app/core/tenant_isolation.py`
- `backend/services/ingestion_service/tests/test_multi_tenant_isolation.py`

Invariants:

- The authenticated tenant UUID from the token is authoritative.
- Slug-based routing may only resolve to the same tenant as the authenticated token.
- Missing slug mappings return `404`; mismatched tenant mappings return `403`.
- Tokens missing tenant identity are rejected at protected boundaries.
- Header, body, or query tampering must not override authenticated tenant scope.
- Cross-tenant access must not leak another tenant's data through success paths or detailed error responses.

Scenarios:

| ID | Scenario | Level | Fixtures | Expected result | Current test | Status |
| --- | --- | --- | --- | --- | --- | --- |
| TEN-001 | Tenant resolution passes through the authenticated tenant UUID when no slug is provided | unit | dummy DB session | current tenant UUID is returned untouched | `backend/services/api_gateway/tests/test_tenant_resolution.py` | KEEP |
| TEN-002 | Matching tenant slug resolves only when it belongs to the authenticated tenant and optional realm | unit | dummy DB rows with realm fixtures | matching slug resolves to the token tenant UUID | `backend/services/api_gateway/tests/test_tenant_resolution.py` | KEEP |
| TEN-003 | Missing slugs return `404` and cross-tenant slug matches return `403` | unit | dummy DB rows | gateway edge rejects bad slug resolution with the correct status class | `backend/services/api_gateway/tests/test_tenant_resolution.py` | KEEP |
| TEN-004 | Gateway auth middleware rejects invalid tokens and tokens missing `tenant_id` | contract | mocked JWT payloads and test client | protected routes fail before hitting tenant-owned logic | `backend/services/api_gateway/tests/test_auth_middleware.py` | KEEP |
| TEN-005 | Service-owned ingestion paths reject or isolate cross-tenant events and batches | integration | ingestion-service fixtures with two tenants | events cannot be processed under the wrong tenant scope | `backend/services/ingestion_service/tests/test_multi_tenant_isolation.py` | KEEP |
| TEN-006 | Token, path, and payload manipulation cannot read or mutate another tenant's resources | integration | two-tenant fixtures and scoped clients | all cross-tenant access attempts fail consistently | `backend/tests/test_multi_tenant_isolation.py` | REPLACE |
| TEN-007 | Cross-tenant failures do not reveal sensitive existence details about foreign tenant resources | contract | two-tenant fixtures and error assertions | error bodies stay generic and bounded | `backend/tests/test_multi_tenant_isolation.py` | REPLACE |

CI stage:

- `required-pr`

Notes:

- Keep the focused gateway and ingestion tests.
- Replace the monolithic root isolation suite with smaller service-local packs owned by the services that actually enforce the boundary.

## Capability: Customer-Managed Ticketing Handoff

Owner: `backend/services/ticketing_service/app/services/ticket_service.py`, `backend/services/ticketing_service/app/tests/test_customer_managed_handoff.py`, `backend/agents/iam_agent/app/api/onboarding.py`, `frontend/src/components/onboarding/StepTicketing.tsx`

Criticality: `P0`

Primary surfaces:

- `POST /api/v1/onboarding/connect-ticketing`
- `POST /api/v1/onboarding/ticketing-assignees/search`
- `frontend/src/components/onboarding/StepTicketing.tsx`
- ticket creation, update, and comment sync paths in `TicketService`

Source of truth:

- `backend/services/ticketing_service/app/services/ticket_service.py`
- `backend/services/ticketing_service/app/tests/test_customer_managed_handoff.py`
- `backend/agents/iam_agent/app/api/onboarding.py`
- `frontend/src/components/onboarding/StepTicketing.tsx`
- `frontend/src/lib/api/onboarding.ts`
- `backend/services/orchestrator/tests/test_welcome_prioritization.py`

Invariants:

- Customer-managed handoff configuration can override tenant defaults when onboarding collected richer ticketing settings.
- Provider-specific validation rules are enforced before ticketing config is accepted.
- Assignment mode, assignee identifier type, health state, and Slack notification requirements remain consistent across onboarding and ticket sync.
- Customer-managed external ticket payloads preserve SentinelGrid routing context such as SG ticket IDs, incident references, assignee hints, and severity/status mappings.
- Ticket update and comment flows dispatch customer-managed sync only when the resolved handoff mode requires it.
- Degraded ticketing health feeds activation and recommendation surfaces.

Scenarios:

| ID | Scenario | Level | Fixtures | Expected result | Current test | Status |
| --- | --- | --- | --- | --- | --- | --- |
| TKT-001 | Ticketing handoff resolution prefers onboarding customer-managed settings over tenant defaults | unit | fake DB rows | resolved config reflects onboarding ticketing config and health | `backend/services/ticketing_service/app/tests/test_customer_managed_handoff.py` | KEEP |
| TKT-002 | Ticketing handoff falls back to tenant preferences when onboarding config is absent | unit | fake DB rows | tenant-level provider, project, and mode defaults are used | `backend/services/ticketing_service/app/tests/test_customer_managed_handoff.py` | KEEP |
| TKT-003 | External ticket descriptions include SentinelGrid routing context for downstream operators | unit | simple ticket and config fixtures | description includes SG ticket ID, incident linkage, and assignment hint | `backend/services/ticketing_service/app/tests/test_customer_managed_handoff.py` | KEEP |
| TKT-004 | Jira and ServiceNow payload builders map assignee identifiers, status, severity, and urgency correctly | unit | simple ticket/config fixtures | provider payloads contain the correct assignee and severity/status mappings | `backend/services/ticketing_service/app/tests/test_customer_managed_handoff.py` | KEEP |
| TKT-005 | Ticket update and comment operations dispatch customer-managed synchronization only on the correct paths | integration | async mocks plus ticket fixtures | sync helpers fire for customer-managed mode and preserve mutation metadata | `backend/services/ticketing_service/app/tests/test_customer_managed_handoff.py` | KEEP |
| TKT-006 | Onboarding `/connect-ticketing` enforces provider, URL, project, API token, default assignee, and Slack-validation rules | contract | request payload matrix per provider and routing mode | invalid configurations fail fast with intentional validation errors | none | NEW |
| TKT-007 | Assignee lookup uses draft or stored config and returns provider-aware identifier metadata | contract | mocked lookup backend plus stored-config fixtures | response includes `provider`, `assigneeIdentifierType`, `source`, and result list | none | NEW |
| TKT-008 | Welcome prioritization surfaces `ticketing-handoff` activation work when customer-managed handoff is degraded | unit | onboarding status with `socManaged: false` and degraded ticketing health | recommendations include `ticketing-handoff` in the activation set | `backend/services/orchestrator/tests/test_welcome_prioritization.py` | KEEP |

CI stage:

- `required-pr`
- real Jira and ServiceNow connectivity belongs in `nightly` or `manual`

Notes:

- The strongest current ticketing coverage already lives in the owning service and should stay there.
- The largest missing piece is deterministic contract coverage for onboarding validation and assignee lookup.

## Recommended First Implementation Order

1. `Authentication And Session Establishment`
2. `Tenant Isolation And Tenant Resolution`
3. `Onboarding Progress And First-Value Activation`
4. `Customer-Managed Ticketing Handoff`
5. `Dashboard Shell Navigation And Operator Entry Points`

Why this order:

- auth and tenant isolation are the base contracts other capabilities depend on
- onboarding and ticketing are the current user-facing activation path
- the dashboard shell has the broadest frontend gap, so it should be rebuilt after the lower-level contracts are stable
