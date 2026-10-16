# SentinelGrid P0 Tranche 1 Checklist

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Date: `2026-03-27`

This is the execution checklist for Tranche 1 from `docs/P0_TEST_IMPLEMENTATION_BACKLOG.md`.

Tranche 1 scope:

- authentication and session establishment
- tenant isolation and tenant resolution

Goal:

- define the exact tests, fixtures, helpers, and CI changes needed before implementation starts
- keep all new coverage owner-local
- avoid reintroducing root-level `app` import collisions

## Definition Of Done

Tranche 1 is complete when all of the following are true:

- `AUTH-001` through `AUTH-009` are implemented or explicitly covered by a stronger owner-local test.
- `TEN-001` through `TEN-007` are implemented or explicitly covered by a stronger owner-local test.
- PR CI runs the Tranche 1 suites in separate service-local pytest invocations plus a dedicated frontend Jest command.
- PR confidence no longer depends on `backend/tests/test_auth_endpoints.py`.
- PR confidence no longer depends on `backend/tests/test_multi_tenant_isolation.py`.

## Order Of Work

1. Create shared test helpers and fixtures.
2. Build frontend auth route and page tests.
3. Build gateway auth proxy and tenant isolation contract tests.
4. Split the root IAM unit tests into service-local IAM-agent unit files.
5. Wire the commands into CI as separate service-scoped test steps.

## Frontend Helpers To Create Or Extend

Extend:

- `frontend/src/test-utils/auth.js`

Create:

- `frontend/src/test-utils/renderWithProviders.tsx`
- `frontend/src/test-utils/navigation.ts`
- `frontend/src/test-utils/queryClient.ts`
- `frontend/src/test-utils/storage.ts`

Exact helper functions:

- `buildAuthProviderValue(overrides = {})`
- `buildPartnerTenantContextValue(overrides = {})`
- `createTestQueryClient()`
- `mockNextRouter(overrides = {})`
- `mockSearchParams(params = {})`
- `resetTestStorage()`
- `renderWithProviders(ui, options = {})`

Required behavior:

- override `isAuthenticated`, `hydrated`, `tenantId`, `planTier`, and `user`
- allow route tests to control `redirect` and other query params
- provide a stable React Query client
- reset local/session storage and router spies between tests

## Backend Helpers And Fixtures To Create Or Extend

Extend:

- `backend/services/api_gateway/tests/conftest.py`
- `backend/services/ingestion_service/tests/conftest.py`

Create:

- `backend/agents/iam_agent/tests/conftest.py`

Exact fixture names:

- `proxy_response_factory`
- `proxy_async_client_factory`
- `tenant_header_matrix`
- `token_payload_factory`
- `valid_token_validation_result`
- `invalid_token_validation_result`
- `missing_tenant_token_validation_result`
- `tenant_pair`
- `foreign_tenant_pair`
- `raw_event_factory`
- `iam_test_client`
- `mock_keycloak_admin`
- `customer_record_factory`

Required behavior:

- `proxy_async_client_factory` should stub `httpx.AsyncClient` cleanly for proxy-route tests
- `tenant_pair` should always return two stable tenant IDs for cross-tenant assertions
- IAM-agent fixtures should avoid per-file `sys.path` surgery by centralizing the app path in one place

## Exact Test Checklist

### Frontend Login Page

Target file:

- `frontend/src/app/(marketing)/login/__tests__/page.test.tsx`

Scenario IDs:

- `AUTH-001`
- `AUTH-002`

Exact tests to add:

- `redirects_authenticated_user_to_dashboard_when_no_redirect_query_is_present`
- `redirects_authenticated_user_to_redirect_query_target_when_present`
- `shows_mfa_form_when_login_raises_mfa_required`
- `blocks_mfa_submit_when_otp_is_blank`
- `submits_login_mfa_and_redirects_after_success`

Helpers required:

- `renderWithProviders`
- `mockNextRouter`
- `mockSearchParams`
- `resetTestStorage`

Mock points:

- `@/lib/providers/AuthProvider`
- `@/lib/api/auth`

Notes:

- keep this file focused on login-page behavior, not cookie semantics
- use the page route query param behavior as the source of truth

### Frontend Login Route Handler

Target file:

- `frontend/src/app/api/auth/login/__tests__/route.test.ts`

Scenario IDs:

- `AUTH-003`

Exact tests to add:

- `forwards_credentials_to_iam_login_endpoint`
- `sets_session_cookie_without_max_age_when_remember_me_is_false`
- `sets_persistent_cookie_with_max_age_when_remember_me_is_true`
- `returns_backend_error_status_and_detail_when_upstream_login_fails`

Helpers required:

- `makeNextRequest` helper inside file or local test helper
- `resetTestStorage` only if request helpers need it

Mock points:

- global `fetch`

Notes:

- verify cookie presence and key flags
- do not assert on log output

### API Gateway Auth Middleware

Target file:

- `backend/services/api_gateway/tests/test_auth_middleware.py`

Scenario IDs:

- `AUTH-005`
- `AUTH-006`
- `TEN-004`

Keep as-is:

- `test_health_check_no_auth_required`
- `test_root_endpoint_no_auth_required`
- `test_protected_endpoint_requires_tenant`

Replace weak placeholder-style tests with exact tests:

- `test_protected_route_returns_401_when_token_is_invalid`
- `test_protected_route_returns_401_when_token_has_no_tenant_id`
- `test_alert_route_passes_authenticated_tenant_id_to_service_layer`
- `test_tenant_context_isolation_is_applied_to_alert_queries`

Fixtures required:

- `mock_get_db`
- `mock_get_current_tenant`
- `token_payload_factory`
- `invalid_token_validation_result`
- `missing_tenant_token_validation_result`

Notes:

- current callable-only assertions are not enough; convert them into request/response assertions

### API Gateway Auth Proxy Routes

Target file:

- `backend/services/api_gateway/tests/test_auth_proxy_routes.py`

Scenario IDs:

- `AUTH-004`
- `AUTH-008`

Exact tests to add:

- `test_login_proxy_forwards_tenant_and_realm_headers`
- `test_refresh_proxy_forwards_tenant_and_realm_headers`
- `test_login_proxy_returns_upstream_error_payload_and_status`
- `test_refresh_proxy_returns_upstream_error_payload_and_status`
- `test_login_proxy_returns_503_when_iam_is_unreachable`
- `test_refresh_proxy_returns_503_when_iam_is_unreachable`

Fixtures required:

- `proxy_response_factory`
- `proxy_async_client_factory`
- `tenant_header_matrix`

Notes:

- run this suite in the gateway pytest process only
- assert on forwarded headers and returned status/body, not implementation internals

### API Gateway Tenant Resolution

Target file:

- `backend/services/api_gateway/tests/test_tenant_resolution.py`

Scenario IDs:

- `TEN-001`
- `TEN-002`
- `TEN-003`

Keep as-is:

- `test_pass_through_when_no_slug`
- `test_match_slug_same_tenant`
- `test_forbidden_on_mismatch`
- `test_not_found`

Optional small addition if needed:

- `test_match_slug_same_tenant_is_realm_scoped`

Fixtures required:

- existing dummy session/query fixtures are sufficient

### API Gateway Tenant Isolation Contracts

Target file:

- `backend/services/api_gateway/tests/test_tenant_isolation_contracts.py`

Scenario IDs:

- `TEN-006`
- `TEN-007`

Exact tests to add:

- `test_authenticated_tenant_cannot_override_scope_with_header_tenant_id`
- `test_authenticated_tenant_cannot_override_scope_with_query_tenant_id`
- `test_cross_tenant_resource_lookup_returns_bounded_error`
- `test_cross_tenant_list_request_does_not_return_foreign_rows`

Fixtures required:

- `tenant_pair`
- `foreign_tenant_pair`
- `mock_get_db`
- `mock_get_current_tenant`

Notes:

- keep these focused on gateway-owned enforcement
- do not recreate the monolithic legacy root suite

### IAM Agent Auth API

Target file:

- `backend/agents/iam_agent/tests/test_auth_api.py`

Scenario IDs:

- `AUTH-007`

Keep as-is:

- `test_validate_token_endpoint_no_token`
- `test_validate_token_endpoint_invalid_token`
- `test_validate_token_endpoint_valid_token`
- `test_introspect_endpoint`

Add if missing:

- `test_introspect_endpoint_returns_inactive_payload_for_invalid_token`

Fixtures required:

- `iam_test_client`
- `valid_token_validation_result`
- `invalid_token_validation_result`

### IAM Agent SecurityService Unit Tests

Target file:

- `backend/agents/iam_agent/tests/test_security_service.py`

Scenario IDs:

- `AUTH-009`

Exact tests to migrate or add:

- `test_validate_password_strength_accepts_strong_password`
- `test_validate_password_strength_rejects_short_password`
- `test_validate_password_strength_rejects_missing_uppercase`
- `test_validate_password_strength_rejects_missing_lowercase`
- `test_validate_password_strength_rejects_missing_digit`
- `test_sanitize_input_preserves_safe_input`
- `test_is_safe_email_accepts_valid_email`
- `test_is_safe_email_rejects_invalid_email`
- `test_is_safe_email_rejects_script_injection_shape`

Fixtures required:

- none beyond local unit fixtures

Notes:

- keep this pure unit coverage only

### IAM Agent PricingService Unit Tests

Target file:

- `backend/agents/iam_agent/tests/test_pricing_service.py`

Scenario IDs:

- `AUTH-009`

Exact tests to migrate or add:

- `test_get_realm_strategy_starter_returns_shared`
- `test_get_realm_strategy_enterprise_returns_dedicated`
- `test_get_realm_strategy_professional_500_users_returns_shared`
- `test_get_realm_strategy_professional_501_users_returns_dedicated`
- `test_get_realm_strategy_professional_1_org_returns_shared`
- `test_get_realm_strategy_professional_2_orgs_returns_dedicated`
- `test_can_create_org_respects_tier_limits`
- `test_can_add_user_respects_tier_limits`
- `test_requires_dedicated_realm_when_compliance_is_enabled`
- `test_get_pricing_info_defaults_invalid_tier_to_starter`

Fixtures required:

- none beyond local unit fixtures

### IAM Agent RealmManager Unit Tests

Target file:

- `backend/agents/iam_agent/tests/test_realm_manager.py`

Scenario IDs:

- `AUTH-009`

Exact tests to migrate or add:

- `test_get_realm_for_customer_shared`
- `test_get_realm_for_customer_dedicated`
- `test_get_realm_for_org_uses_org_realm_name`
- `test_get_realm_for_org_falls_back_to_sentinelgrid`
- `test_get_realm_for_customer_professional_shared`
- `test_get_realm_for_customer_professional_dedicated_users`
- `test_get_realm_for_customer_professional_dedicated_orgs`
- `test_get_realm_for_customer_existing_dedicated`
- `test_generate_realm_name_sanitizes_company_name`
- `test_generate_realm_name_handles_edge_cases`

Fixtures required:

- `mock_keycloak_admin`
- `customer_record_factory`

### IAM Agent Tenant Isolation Contracts

Target file:

- `backend/agents/iam_agent/tests/test_tenant_isolation_contracts.py`

Scenario IDs:

- `TEN-006`
- `TEN-007`

Exact tests to add:

- `test_validate_tenant_match_accepts_matching_tenant_ids`
- `test_validate_tenant_match_rejects_mismatched_tenant_ids`
- `test_get_tenant_id_for_query_uses_authenticated_tenant_scope`
- `test_foreign_tenant_identifier_is_not_echoed_in_error_paths`

Fixtures required:

- `tenant_pair`
- `foreign_tenant_pair`

Notes:

- keep this file centered on IAM-agent and shared helper behavior

### Ingestion Service Multi-Tenant Isolation

Target file:

- `backend/services/ingestion_service/tests/test_multi_tenant_isolation.py`

Scenario IDs:

- `TEN-005`

Keep as-is:

- `test_rejects_cross_tenant_event`
- `test_batch_processor_scoped_per_tenant`

Optional small addition if needed:

- `test_ingest_batch_reports_each_cross_tenant_failure_without_partial_success`

Fixtures required:

- `raw_event_factory`

## CI Command Additions

Principle:

- run each service family in a separate process
- do not combine gateway and IAM-agent pytest targets in one pytest invocation
- this avoids `app` package collisions

### Local Commands

Frontend:

```bash
cd frontend
npx jest --runInBand --watch=false "src/app/(marketing)/login/__tests__/page.test.tsx" "src/app/api/auth/login/__tests__/route.test.ts"
```

API Gateway:

```bash
PYTHONPATH=backend/services/api_gateway:backend/libs \
pytest \
  backend/services/api_gateway/tests/test_auth_middleware.py \
  backend/services/api_gateway/tests/test_auth_proxy_routes.py \
  backend/services/api_gateway/tests/test_tenant_resolution.py \
  backend/services/api_gateway/tests/test_tenant_isolation_contracts.py \
  -q
```

IAM Agent:

```bash
PYTHONPATH=backend/agents/iam_agent:backend/libs \
pytest \
  backend/agents/iam_agent/tests/test_auth_api.py \
  backend/agents/iam_agent/tests/test_security_service.py \
  backend/agents/iam_agent/tests/test_pricing_service.py \
  backend/agents/iam_agent/tests/test_realm_manager.py \
  backend/agents/iam_agent/tests/test_tenant_isolation_contracts.py \
  -q
```

Ingestion Service:

```bash
PYTHONPATH=backend/services/ingestion_service:backend/libs \
pytest backend/services/ingestion_service/tests/test_multi_tenant_isolation.py -q
```

### GitHub Actions Changes

Target file to update later:

- `.github/workflows/test.yml`

Recommended changes:

1. Replace the current single-file gateway smoke in `unit-tests` with a service-local Tranche 1 matrix.
2. Add a `frontend-p0-tests` job using Node 18 or the repo-standard Node version.
3. Keep frontend and backend jobs separate.
4. Keep gateway, IAM-agent, and ingestion pytest commands in separate steps or separate jobs.

Recommended job or step names:

- `frontend-p0-auth-tests`
- `gateway-p0-auth-tenant-tests`
- `iam-agent-p0-auth-tests`
- `ingestion-p0-tenant-tests`

Recommended step commands:

Frontend job:

```bash
cd frontend
npm ci
npx jest --runInBand --watch=false "src/app/(marketing)/login/__tests__/page.test.tsx" "src/app/api/auth/login/__tests__/route.test.ts"
```

Gateway step:

```bash
pip install -r backend/libs/requirements.txt
pip install -r backend/tests/requirements.txt
PYTHONPATH=backend/services/api_gateway:backend/libs \
pytest \
  backend/services/api_gateway/tests/test_auth_middleware.py \
  backend/services/api_gateway/tests/test_auth_proxy_routes.py \
  backend/services/api_gateway/tests/test_tenant_resolution.py \
  backend/services/api_gateway/tests/test_tenant_isolation_contracts.py \
  -q
```

IAM-agent step:

```bash
pip install -r backend/libs/requirements.txt
pip install -r backend/tests/requirements.txt
PYTHONPATH=backend/agents/iam_agent:backend/libs \
pytest \
  backend/agents/iam_agent/tests/test_auth_api.py \
  backend/agents/iam_agent/tests/test_security_service.py \
  backend/agents/iam_agent/tests/test_pricing_service.py \
  backend/agents/iam_agent/tests/test_realm_manager.py \
  backend/agents/iam_agent/tests/test_tenant_isolation_contracts.py \
  -q
```

Ingestion step:

```bash
pip install -r backend/libs/requirements.txt
pip install -r backend/tests/requirements.txt
PYTHONPATH=backend/services/ingestion_service:backend/libs \
pytest backend/services/ingestion_service/tests/test_multi_tenant_isolation.py -q
```

## Legacy Files To Stop Depending On

Do not use these as Tranche 1 CI gates:

- `backend/tests/test_auth_endpoints.py`
- `backend/tests/test_multi_tenant_isolation.py`

Do not add new Tranche 1 tests to:

- `backend/tests/`

## Immediate Handoff

If implementation starts next, begin with this exact sequence:

1. `frontend/src/test-utils/renderWithProviders.tsx`
2. `backend/agents/iam_agent/tests/conftest.py`
3. `backend/services/api_gateway/tests/test_auth_proxy_routes.py`
4. `frontend/src/app/api/auth/login/__tests__/route.test.ts`
5. `frontend/src/app/(marketing)/login/__tests__/page.test.tsx`
6. `backend/services/api_gateway/tests/test_tenant_isolation_contracts.py`
7. IAM-agent unit file split from `backend/tests/test_auth_api_client.py`

That sequence removes the biggest harness uncertainty first and keeps the early wins in the most deterministic layers.
