# Phase 2 Slice 2B Orchestrator Response Auth Closeout

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 16, 2026  
**Status:** Complete for the current narrowed launch scope  
**Owner:** Clement Ellango

## Purpose

Close the placeholder-tenant trust flaw in orchestrator response and remediation endpoints so no alert orchestration, remediation orchestration, execution status, or execution reporting path can run under a synthetic default tenant.

## Scope Closed In This Slice

- removal of `Depends(lambda: "default")` from orchestrator response endpoints
- validated tenant resolution for orchestrator response/remediation routes
- strict support for only:
  - validated end-user bearer tokens, or
  - the configured internal service token plus `X-Tenant-ID`
- focused negative-path tests proving placeholder tenant values are rejected
- focused route coverage across all four launch-relevant orchestrator response endpoints

## Code Areas Closed

- `backend/services/orchestrator/app/api/response.py`
- `backend/services/orchestrator/app/core/security.py`
- `backend/services/orchestrator/tests/test_response_auth_boundary.py`

## What Changed

1. `backend/services/orchestrator/app/api/response.py` no longer uses `Depends(lambda: "default")` on any orchestration endpoint.
2. All four response endpoints now depend on a real tenant-resolution dependency that returns a validated tenant UUID instead of a placeholder string.
3. `backend/services/orchestrator/app/core/security.py` now enforces the same core trust model used in other hardened services:
   - validated user bearer token via IAM-backed token verification, or
   - exact internal service token plus a valid `X-Tenant-ID` header.
4. The orchestrator response endpoints no longer allow header-only tenant assertion and no longer have any placeholder or default tenant fallback.
5. For validated user tokens, tenant overrides in `X-Tenant-ID` are rejected if they do not match the authenticated tenant from the verified token.
6. For internal service requests, `X-Tenant-ID` is required and must be a valid UUID before any orchestration method runs.
7. The touched response routes now use timezone-aware UTC timestamps instead of `datetime.utcnow()` in their default response payloads.

## Verification Evidence

### Focused Orchestrator Auth-Boundary Suite

- `PYTHONPATH=backend/services/orchestrator:backend/libs pytest backend/services/orchestrator/tests/test_response_auth_boundary.py -q`
  - result: `11` tests passed

### Combined Orchestrator Regression Evidence

- `PYTHONPATH=backend/services/orchestrator:backend/libs pytest backend/services/orchestrator/tests/test_response_auth_boundary.py backend/services/orchestrator/tests/test_readiness.py backend/services/orchestrator/tests/test_request_tracing.py -q`
  - result: `16` tests passed

### Source Sweep Evidence

- `rg -n "Depends\\(lambda: \\\"default\\\"\\)|tenant_id: str = Depends\\(lambda: \\\"default\\\"\\)|UUID\\(tenant_id\\)" backend/services/orchestrator/app/api/response.py backend/services/orchestrator/app/core/security.py -g '!**/__pycache__/**'`
  - result: no matches

## Residual Risk After Closeout

- This slice closes the placeholder-tenant flaw in `response.py`, but it does not yet unify all orchestrator auth helpers. `snapshot.py` and `dashboard.py` still carry separate internal-token validation helpers that should be consolidated later for consistency.
- These response endpoints are now fail-closed when called directly, but the broader launch program still has open AI Shield, runtime hardening, dependency, and ops gates. This closeout does not change the overall `No-Go` state for broad launch.
- Some repo-local orchestrator tests still assume `backend/libs` is on `PYTHONPATH`. That is a test harness issue, not a production auth issue, but it remains part of local verification ergonomics.

## Exit Decision

`Slice 2B` is closed for the current narrowed launch scope.

No orchestrator response or remediation endpoint covered by this slice can execute under a placeholder tenant. Phase 2 should continue with `Slice 2C`.
