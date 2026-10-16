# Phase 2 Slice 2A SOAR Tenant Trust Closeout

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 16, 2026  
**Status:** Complete for the current narrowed launch scope  
**Owner:** Clement Ellango

## Purpose

Close the SOAR tenant-trust flaws called out in the April 16 audit so the service no longer accepts unsigned tenant claims, placeholder tenant defaults, or weakly authenticated detection-ingest traffic.

## Scope Closed In This Slice

- validated tenant resolution for SOAR user-facing auth paths
- internal-only detection event ingest authentication and tenant binding
- removal of default or debug tenant fallback from production code paths
- explicit tenant-scoped TheHive webhook handling after tenant-resolution hardening
- focused negative-path tests for forged, missing, malformed, and mismatched tenant context

## Code Areas Closed

- `backend/agents/soar_agent/app/core/security.py`
- `backend/agents/soar_agent/app/api/detection_events.py`
- `backend/agents/soar_agent/app/api/webhooks.py`
- `backend/agents/soar_agent/tests/test_security_tenant_trust.py`
- `backend/agents/soar_agent/tests/test_critical_route_tenant_isolation.py`

## What Changed

1. `backend/agents/soar_agent/app/core/security.py` no longer parses tenant context from unsigned JWT payload data. It now accepts only:
   - a validated end-user bearer token resolved through `sg_core.security.verify_token`, or
   - the configured internal service token plus a valid `X-Tenant-ID` header.
2. The old debug/default tenant fallback is removed from the production path. Header-only tenant assertion remains available only in `development` and `test` to preserve direct-service local workflows and existing unit tests.
3. SOAR now rejects tenant-header overrides that do not match the validated tenant carried by the authenticated bearer token.
4. `backend/agents/soar_agent/app/api/detection_events.py` now treats detection ingest as internal-only traffic, requiring the exact internal service token and a UUID `X-Tenant-ID` header before any incident creation path runs.
5. Detection ingest now validates the event body tenant UUID against the authenticated header tenant UUID and rejects missing, malformed, or mismatched values before the incident creator is invoked.
6. `backend/agents/soar_agent/app/api/webhooks.py` now uses explicit TheHive API-key plus `X-Tenant-ID` validation and its own tenant-scoped database dependency, so the SOAR tenant hardening did not re-open or weaken TheHive webhook behavior.
7. Focused regression coverage now exists for:
   - header-only tenant resolution in production
   - forged JWT rejection
   - token/header tenant mismatch
   - internal service token acceptance
   - missing internal token on detection ingest
   - invalid tenant header on detection ingest
   - mismatched event tenant on detection ingest

## Verification Evidence

### Focused SOAR Regression Suite

- `pytest backend/agents/soar_agent/tests/test_config_security.py backend/agents/soar_agent/tests/test_security_tenant_trust.py backend/agents/soar_agent/tests/test_critical_route_tenant_isolation.py backend/agents/soar_agent/tests/test_playbook_routes_tenant_session.py -q`
  - result: `27` tests passed

### Source Sweep Evidence

- `rg -n "verify_signature=False|jwt\\.decode\\(|TODO.*token|TODO.*auth|00000000-0000-0000-0000-000000000000" backend/agents/soar_agent/app backend/agents/soar_agent/tests -g '!**/__pycache__/**'`
  - result: no matches in live SOAR app or test code

## Residual Risk After Closeout

- Header-only tenant assertion still exists in `development` and `test` for direct-service local workflows. That is intentional and no longer available in production mode, but it remains a code path that should stay tightly bounded to non-production environments.
- This slice closes the SOAR tenant-trust flaws identified in the April 16 audit, but it does not close the separate placeholder-tenant problems in orchestrator or the remaining AI Shield auth boundary work. Those remain open Phase 2 gates.
- TheHive webhook auth still relies on a shared API key plus explicit tenant header rather than a stronger signed service identity. That is acceptable for the narrowed launch only if the key is rotated and stored as a real secret, but it remains weaker than mutual service authentication.

## Exit Decision

`Slice 2A` is closed for the current narrowed launch scope.

SOAR no longer accepts unsigned, missing, mismatched, or placeholder tenant context on the launch-critical paths covered by this slice. Phase 2 should continue with `Slice 2B`.
