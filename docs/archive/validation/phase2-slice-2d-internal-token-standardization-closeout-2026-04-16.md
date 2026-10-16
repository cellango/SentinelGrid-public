# Phase 2 Slice 2D Internal Token Standardization Closeout

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 16, 2026  
**Status:** Complete for the current narrowed launch scope  
**Owner:** Clement Ellango

## Purpose

Close the remaining internal-token drift across the narrowed launch surface so internal-only routes use one explicit authentication model, launch-critical services fail closed on default tokens in production, and service-to-service callers stop inventing their own header conventions.

## Scope Closed In This Slice

- canonical internal auth helper expansion for token parsing, verification, and outbound header construction
- standardization of the primary internal auth transport on `Authorization: Bearer <INTERNAL_SERVICE_TOKEN>`
- canonical tenant propagation on `X-Tenant-ID` for tenant-scoped internal calls
- production rejection of default internal service tokens in launch-critical services and AI Shield services
- compatibility support for legacy `X-Internal-Service-Token` and `X-Internal-Token` readers where older callers may still exist
- launch-critical internal route coverage across IAM, orchestrator, SOAR detection ingest, observables, SIEM internal APIs, cert-service enrollment auth, API gateway AI Shield admin access, MCP clients, and AI Shield gateway-to-services traffic
- separation of production-safe token defaults from historical docs and local example material

## Internal Endpoint Inventory Closed By This Slice

The narrowed launch inventory now resolves to three explicit internal auth patterns:

1. Tenant-scoped internal service calls:
   `Authorization: Bearer <INTERNAL_SERVICE_TOKEN>` plus `X-Tenant-ID`
   Used by orchestrator, SOAR, observables, SIEM internal APIs, API gateway tenant-scoped proxy paths, and IAM internal request-context resolution.
2. Internal control-plane service calls without tenant header:
   `Authorization: Bearer <INTERNAL_SERVICE_TOKEN>`
   Used by AI Shield gateway-to-services admin traffic and internal service auth validation paths.
3. Cert-service internal enrollment:
   `Authorization: Bearer <INTERNAL_SERVICE_TOKEN>` plus tenant scope resolved from validated request content.
   Agent enrollment remains bootstrap-token based and is not part of the internal-service-token model.

Legacy header names remain accepted in selected validators only as compatibility transport. They are no longer the canonical emitted auth model.

## Code Areas Closed

- `backend/libs/sg_core/service_security.py`
- `backend/services/api_gateway/app/core/config.py`
- `backend/services/api_gateway/app/api/routes_ai_shield.py`
- `backend/agents/iam_agent/app/core/config.py`
- `backend/agents/iam_agent/app/api/marketing.py`
- `backend/agents/iam_agent/app/api/stats.py`
- `backend/agents/iam_agent/app/api/request_context.py`
- `backend/agents/soar_agent/app/core/config.py`
- `backend/agents/soar_agent/app/api/detection_events.py`
- `backend/services/orchestrator/app/api/dashboard.py`
- `backend/services/orchestrator/app/api/snapshot.py`
- `backend/services/observables_service/app/core/security.py`
- `backend/services/siem_agent/app/api/internal.py`
- `backend/services/siem_agent/app/api/events.py`
- `backend/services/cert_service/app/api/certificates.py`
- `backend/agents/mcp_server/app/core/service_clients.py`
- `SentinelGridAIShield/services/app/core/config.py`
- `SentinelGridAIShield/services/app/core/security.py`
- `SentinelGridAIShield/services/app/api/internal_keys.py`
- `SentinelGridAIShield/gateway/internal/auth/auth.go`
- `SentinelGridAIShield/gateway/internal/httpapi/router.go`
- `SentinelGridAIShield/gateway/internal/guardrails/client.go`
- `SentinelGridAIShield/gateway/internal/providers/key_fetcher.go`
- `SentinelGridAIShield/gateway/internal/telemetry/sink.go`

## What Changed

1. `backend/libs/sg_core/service_security.py` now owns the shared internal auth contract:
   - canonical bearer extraction
   - compatibility parsing for `X-Internal-Service-Token` and `X-Internal-Token`
   - conflicting-header rejection
   - exact token verification
   - canonical outbound header construction with `Authorization` and `X-Tenant-ID`
2. Launch-critical backend configs now share the same production guard against default internal tokens through `ServiceSecuritySettings` and the shared `DEFAULT_INTERNAL_SERVICE_TOKEN`.
3. IAM internal auth boundaries now use the shared helper and the IAM request-context layer accepts the explicit service model of:
   - exact internal bearer token
   - required `X-Tenant-ID`
   That closes the gap between API gateway or orchestrator internal callers and tenant-scoped IAM routes.
4. Orchestrator internal service calls now emit canonical internal auth headers instead of forwarding only tenant identity.
5. Observables, SIEM internal APIs, cert-service internal enrollment auth, and SOAR detection ingest now resolve internal auth through the same helper-backed contract instead of ad hoc token parsing.
6. `backend/agents/mcp_server/app/core/service_clients.py` now emits canonical service headers, including the normalized tenant header name `X-Tenant-ID`.
7. AI Shield gateway internal clients now send bearer `Authorization` to the services plane, AI Shield services reject the default internal token in production, and example configs moved to the safer `internal-service-token-change-in-production` placeholder.
8. Historical docs and Vault secret-path references still mention `internal-service-token` as a secret name or narrative label, but the runtime default-token ambiguity on the narrowed launch path is removed.

## Verification Evidence

### Shared Helper And Launch-Service Guard Evidence

- `pytest tests/test_internal_service_security_helpers.py tests/test_phase1_service_config_guards.py -q`
  - working directory: `backend`
  - result: `11` tests passed

### IAM Internal Auth Evidence

- `pytest tests/test_stats_internal_boundary.py tests/test_request_context_internal_token.py -q`
  - working directory: `backend/agents/iam_agent`
  - result: `4` tests passed

### API Gateway And Observables Evidence

- `pytest tests/test_config_security.py -q`
  - working directory: `backend/services/api_gateway`
  - result: `4` tests passed

- `PYTHONPATH=.:../../libs pytest tests/test_tenant_scoped_routes.py -q`
  - working directory: `backend/services/observables_service`
  - result: `7` tests passed

### Cert-Service Evidence

- `PYTHONPATH=.:../../libs pytest tests/test_service_token_auth.py tests/test_enrollment_tenant_isolation.py tests/test_certificate_routes_tenant_session.py -q`
  - working directory: `backend/services/cert_service`
  - result: `6` tests passed

### SIEM Internal Auth Evidence

- `PYTHONPATH=.:../../libs pytest tests/test_internal_auth_contract.py -q`
  - working directory: `backend/services/siem_agent`
  - result: `3` tests passed

### SOAR Regression Evidence

- `PYTHONPATH=backend/agents/soar_agent:backend/libs pytest backend/agents/soar_agent/tests/test_security_tenant_trust.py backend/agents/soar_agent/tests/test_critical_route_tenant_isolation.py -q`
  - working directory: repository root
  - result: `12` tests passed

### AI Shield Evidence

- `pytest tests/test_config_security.py tests/test_ai_assistant.py tests/test_guardrails.py tests/test_internal_keys.py tests/test_auth_boundary.py::test_gateway_config_requires_internal_token tests/test_auth_boundary.py::test_gateway_config_rejects_cross_tenant_access -q`
  - working directory: `SentinelGridAIShield/services`
  - result: `16` tests passed

- `go test ./...`
  - working directory: `SentinelGridAIShield/gateway`
  - result: passed

### Syntax Validation Evidence

- `python -m py_compile backend/agents/soar_agent/app/api/detection_events.py backend/services/siem_agent/app/api/internal.py backend/services/siem_agent/app/api/events.py backend/services/cert_service/app/api/certificates.py backend/libs/sg_core/service_security.py backend/agents/iam_agent/app/api/marketing.py backend/agents/iam_agent/app/api/stats.py backend/agents/iam_agent/app/api/request_context.py backend/services/orchestrator/app/api/dashboard.py backend/services/orchestrator/app/api/snapshot.py backend/services/api_gateway/app/api/routes_ai_shield.py backend/services/observables_service/app/core/security.py backend/agents/mcp_server/app/core/service_clients.py`
  - working directory: repository root
  - result: passed

### Source Sweep Evidence

- `rg -n "if token != .*INTERNAL_SERVICE_TOKEN" backend/services backend/agents SentinelGridAIShield/services -g '!**/__pycache__/**'`
  - result: the remaining runtime manual compare is limited to `SentinelGridAIShield/services/app/core/security.py`

- `rg -n --pcre2 "internal-service-token(?!-change-in-production)" SentinelGridAIShield backend charts .github docs -g '!**/__pycache__/**'`
  - result: remaining matches are doc prose, integration-guide placeholders, and Vault secret-path references, not runtime default-token configuration on the narrowed launch path

## Residual Risk After Closeout

- AI Shield services still accept `X-Internal-Service-Token` for compatibility and still carry one local token comparison in `SentinelGridAIShield/services/app/core/security.py`. The canonical emitted transport is now bearer `Authorization`, but that compatibility path remains until a later cleanup pass.
- `SentinelGridAIShield/services/app/main.py` still includes `X-Internal-Service-Token` in one CORS allow-header list. That does not reopen the auth ambiguity closed here, but it should be tightened when AI Shield edge hardening is revisited.
- The broader `backend/services/siem_agent` package still has local verification ergonomics problems unrelated to this auth slice, including a missing local `opensearchpy` dependency and route modules that depend on package structure not fully represented in the service test harness. The focused auth-contract test added here isolates the changed logic, but full route regression for that service still needs packaging cleanup.
- This slice closes internal-token ambiguity for the narrowed launch path. It does not close the remaining edge, network, runtime, dependency, or operational gates. Broad launch remains `No-Go` until those later phases pass.

## Exit Decision

`Slice 2D` is closed for the current narrowed launch scope.

The narrowed launch surface now has one explicit internal authentication model, canonical service-to-service header transport, and production guards against default internal-token use. Phase 3 should continue with `Slice 3A`.
