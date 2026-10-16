# Phase 2 Slice 2C AI Shield Gateway And Service Auth Closeout

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 16, 2026  
**Status:** Complete for the current narrowed launch scope  
**Owner:** Clement Ellango

## Purpose

Close the AI Shield trust-boundary flaws that allowed the gateway to accept synthetic org/app context and allowed service APIs to expose org-scoped behavior without an explicit internal authentication model.

## Scope Closed In This Slice

- removal of default org/app fallback behavior from the AI Shield gateway
- server-derived org/app/realm resolution from a validated API key
- rejection of caller-supplied tenant, app, or realm spoofing headers
- internal-token enforcement on AI Shield service APIs and internal gateway admin paths
- org-scope enforcement on internal AI Shield service routes
- unsupported-provider negative-path coverage on the launch-supported gateway surface
- test-harness support for running non-database AI Shield service auth tests without forcing startup schema creation

## Code Areas Closed

- `SentinelGridAIShield/gateway/internal/auth/auth.go`
- `SentinelGridAIShield/gateway/internal/httpapi/request_context.go`
- `SentinelGridAIShield/gateway/internal/httpapi/handlers_chat.go`
- `SentinelGridAIShield/gateway/internal/httpapi/handlers_completions.go`
- `SentinelGridAIShield/gateway/internal/httpapi/router.go`
- `SentinelGridAIShield/gateway/internal/guardrails/client.go`
- `SentinelGridAIShield/gateway/internal/providers/key_fetcher.go`
- `SentinelGridAIShield/gateway/internal/telemetry/sink.go`
- `SentinelGridAIShield/gateway/internal/httpapi/router_test.go`
- `SentinelGridAIShield/services/app/core/security.py`
- `SentinelGridAIShield/services/app/api/internal_auth.py`
- `SentinelGridAIShield/services/app/api/ai_apps.py`
- `SentinelGridAIShield/services/app/api/ai_policies.py`
- `SentinelGridAIShield/services/app/api/ai_events.py`
- `SentinelGridAIShield/services/app/api/telemetry.py`
- `SentinelGridAIShield/services/app/api/gateway_config.py`
- `SentinelGridAIShield/services/app/api/ai_assistant.py`
- `SentinelGridAIShield/services/app/guardrails/pii.py`
- `SentinelGridAIShield/services/app/guardrails/injection.py`
- `SentinelGridAIShield/services/app/guardrails/secrets.py`
- `SentinelGridAIShield/services/app/guardrails/validation.py`
- `SentinelGridAIShield/services/app/core/config.py`
- `SentinelGridAIShield/services/app/main.py`
- `SentinelGridAIShield/services/tests/conftest.py`
- `SentinelGridAIShield/services/tests/test_ai_apps.py`
- `SentinelGridAIShield/services/tests/test_policies.py`
- `SentinelGridAIShield/services/tests/test_telemetry.py`
- `SentinelGridAIShield/services/tests/test_auth_boundary.py`

## What Changed

1. `SentinelGridAIShield/gateway/internal/auth/auth.go` no longer returns `default-org` or `default-app`. The gateway now validates external API keys by calling an internal AI Shield service endpoint and only proceeds with server-derived org, app, and realm values.
2. `SentinelGridAIShield/gateway/internal/httpapi/request_context.go` now resolves the caller context from `Authorization: Bearer <api-key>` and rejects cross-tenant spoof attempts when the caller tries to override `X-Tenant-ID`, `X-App-ID`, or `X-Realm`.
3. The public AI Shield gateway handlers in `handlers_chat.go` and `handlers_completions.go` now derive org/app/realm from validated server context instead of trusting caller-supplied headers.
4. `SentinelGridAIShield/gateway/internal/httpapi/router.go` now requires the configured internal service token on `/admin/config/refresh`.
5. The gateway-to-services internal clients now propagate the internal service token explicitly:
   - guardrail scans
   - provider-key fetch
   - telemetry event and tool-call ingestion
6. `SentinelGridAIShield/services/app/core/security.py` now defines the canonical internal auth contract for the services plane:
   - exact `X-Internal-Service-Token` or bearer internal token validation
   - strict `X-Tenant-ID` parsing as a UUID
   - explicit org-scope enforcement helpers
7. The service control plane now has a dedicated internal auth route in `SentinelGridAIShield/services/app/api/internal_auth.py` so the gateway can validate API keys and derive org/app/realm server-side.
8. Org-scoped service APIs now fail closed behind the internal auth model:
   - `ai_apps.py`
   - `ai_policies.py`
   - `ai_events.py`
   - `telemetry.py`
   - `gateway_config.py`
   - `ai_assistant.py`
   - guardrail scan/validation routes
9. The AI Shield services app no longer enables wildcard CORS by default. `SentinelGridAIShield/services/app/main.py` now mounts CORS only when explicit origins are configured.
10. The services test harness now supports a test-only startup bypass for schema initialization so non-database auth routes can be exercised locally without changing runtime production behavior.

## Verification Evidence

### AI Shield Gateway Test Evidence

- `go test ./...`
  - working directory: `SentinelGridAIShield/gateway`
  - result: gateway packages passed, including `internal/httpapi`, `internal/policy`, and `internal/telemetry`

### AI Shield Service Non-DB Auth Evidence

- `pytest tests/test_ai_assistant.py tests/test_guardrails.py tests/test_internal_keys.py tests/test_auth_boundary.py::test_gateway_config_requires_internal_token tests/test_auth_boundary.py::test_gateway_config_rejects_cross_tenant_access -q`
  - working directory: `SentinelGridAIShield/services`
  - result: `15` tests passed

### Syntax Validation Evidence

- `python -m py_compile app/core/security.py app/api/internal_auth.py app/api/ai_apps.py app/api/ai_policies.py app/api/ai_events.py app/api/gateway_config.py app/api/ai_assistant.py app/api/telemetry.py app/guardrails/pii.py app/guardrails/injection.py app/guardrails/secrets.py app/guardrails/validation.py`
  - working directory: `SentinelGridAIShield/services`
  - result: passed

- `python -m py_compile app/core/config.py app/main.py tests/conftest.py`
  - working directory: `SentinelGridAIShield/services`
  - result: passed

### Source Sweep Evidence

- `rg -n "default-org|default-app|X-Tenant-ID.*Header\\(|allow_origins=\\[\\\"\\*\\\"\\]|allow_methods=\\[\\\"\\*\\\"\\]|allow_headers=\\[\\\"\\*\\\"\\]" SentinelGridAIShield/gateway SentinelGridAIShield/services`
  - result: no matches

## Residual Risk After Closeout

- The database-backed AI Shield service tests for `ai_apps`, `ai_policies`, `telemetry`, and the positive-path API-key validation route are not fully executed on this machine because there is no runnable local Postgres server available. The test code is updated for the new internal-auth contract, but those suites still need execution in CI or on a Postgres-equipped runner.
- `SentinelGridAIShield/gateway/internal/middleware/middleware.go` still contains permissive wildcard CORS behavior at the Gin edge. That is outside the exact auth-closure scope of this slice, but it should be tightened before AI Shield is widened beyond the current controlled add-on launch posture.
- This slice closes the main cross-tenant spoofing flaw in AI Shield, but it does not by itself close the broader runtime, dependency, or launch-scope gates. Broad launch remains `No-Go` until the remaining contract gates pass.

## Exit Decision

`Slice 2C` is closed for the current narrowed launch scope.

The AI Shield gateway no longer trusts synthetic org/app context, AI Shield service routes now use an explicit internal authentication model, and the launch-supported negative paths are verified. Phase 2 should continue with `Slice 2D`.
