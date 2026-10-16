# Multi-Tenancy Defensible Remediation Worklist

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Status:** Complete  
**Last Updated:** 2026-03-30  
**Audience:** Engineering, Security, Compliance

**Related**
- [MULTI_TENANCY_REMEDIATION_STATUS.md](multi-tenancy-remediation-status.md)
- [MULTI_TENANCY_AUDIT_READINESS_PLAN.md](../README.md#retired-references)
- [MULTI_TENANCY_AUDIT_EXECUTION_SPEC.md](multi-tenancy-audit-execution-spec.md)

## Purpose

This document isolates the work required to make SentinelGrid's multi-tenancy controls technically defensible before spending more time on audit packaging and evidence expansion.

It is intentionally narrower than the full audit program.

It answers:

- what still needs to be remediated in product and service code
- what shared-data policy decisions or approved exceptions still matter
- what work is explicitly deferred to the audit-evidence parking lot

## Current Baseline

Current baseline artifact:

- `artifacts/audit/multi-tenancy/2026-03-30/110555-local-smoke`

Current remediation state from `remediation/summary.json`:

| Metric | Current Value |
|---|---:|
| Plain DB routes | `3` |
| Plain DB routes without tenant signal | `0` |
| Critical routes | `0` |
| Review-required routes | `0` |

Interpretation:

- The emergency containment problem is solved.
- The remaining runtime remediation work is solved.
- The remaining review-closure work is solved.
- The next work is the parked audit-evidence phase.

## Goal Of This Worklist

This worklist is complete when the remaining remediation backlog is reduced to the point that the claim below is technically defensible:

`Tenant-scoped routes consistently derive tenant scope from authenticated identity or an explicitly approved shared-data model, and no remaining route family depends on ambiguous plain-session behavior.`

This engineering state is now reached. It is not yet the same thing as “audit closed,” but it is the state required before the final evidence phase is worth doing.

## In Scope

The following work was in scope for this document:

- explicit closure of remaining `review_required` route families

## Out Of Scope For Now

The following work is intentionally deferred:

- expanding the negative suite across every remaining reviewed surface
- running the `full` audit profile in the audit environment
- packaging the final audit binder for external review

Those items are still required later, but they are not part of the remediation focus of this list.

## Remediation Priorities

### Priority 1: Finish Small Mechanical High-Risk Queues

These are straightforward route-family conversions where the tenant model is already clear.

Current queue order from the latest owner index:

All small mechanical queues are now cleared.

Required outcome:

- keep them at `0`
- avoid reopening plain-session access while larger and policy-dependent queues are addressed

### Priority 2: Resolve Policy-Dependent Remediation

These queues should not be “mechanically fixed” without first making the access model explicit.

Resolved:

- `reporting-service` shared-template policy is now explicit and implemented
- `model-gateway` shared/global ingestion model is now explicit and implemented
- shared templates remain browseable global product content
- direct schedule mutation is restricted to tenant-owned templates
- shared framework loaders now use an explicit superadmin-scoped DB path
- git-ingestion now separates tenant-owned operations from explicit platform-operation global access

Required outcome:

- keep both owner queues at `0`
- treat any regression in these shared/global paths as priority remediation

### Priority 3: Burn Down Large High-Risk Owners

These are not blocked on audit packaging. They are direct remediation backlog.

Current large queues:

All runtime `high_risk` owner queues are now cleared.

Required outcome:

- keep runtime `high_risk` owner queues at `0`
- prevent regressions that would reopen plain-session route families
- use the smoke audit as the regression gate for runtime adoption

Current `iam-agent` progress:

- completed runtime-scoping and review-closure slices:
  - `backend/agents/iam_agent/app/api/entitlements.py`
  - `backend/agents/iam_agent/app/api/bulk_operations.py`
  - `backend/agents/iam_agent/app/api/authorize.py`
  - `backend/agents/iam_agent/app/api/access_requests.py`
  - `backend/agents/iam_agent/app/api/iam_portal.py`
  - `backend/agents/iam_agent/app/api/onboarding.py`
  - `backend/agents/iam_agent/app/api/policies.py`
  - `backend/agents/iam_agent/app/api/governance.py`
  - `backend/agents/iam_agent/app/api/role_mappings.py`
  - `backend/agents/iam_agent/app/api/app_catalog.py`
  - `backend/agents/iam_agent/app/api/apps.py`
  - `backend/agents/iam_agent/app/api/devices.py`
  - `backend/agents/iam_agent/app/api/git_providers.py`
  - `backend/agents/iam_agent/app/api/git_scanning.py`
  - `backend/agents/iam_agent/app/api/hardened_images.py`
  - `backend/agents/iam_agent/app/api/user_onboarding.py`
  - `backend/agents/iam_agent/app/api/compliance.py`
  - `backend/agents/iam_agent/app/api/audit.py`
  - `backend/agents/iam_agent/app/api/automation.py`
  - `backend/agents/iam_agent/app/api/ai_features.py`
  - `backend/agents/iam_agent/app/api/mfa.py`
  - `backend/agents/iam_agent/app/api/protocols.py`
  - `backend/agents/iam_agent/app/api/ai_chat.py`
  - `backend/agents/iam_agent/app/api/sync_jobs.py`
  - `backend/agents/iam_agent/app/api/payment.py`
- added request-context-backed tenant-scoped DB sessions in:
  - `backend/agents/iam_agent/app/api/request_context.py`
- latest reduction:
  - `iam-agent high_risk 138 -> 0`
  - `iam-agent review_required 94 -> 0`
  - payment conversion routes moved from pending public-record review to an approved pre-tenant commercial boundary backed by provisioning tokens and checkout-session matching
  - organization provisioning routes moved to an explicit superadmin DB path and approved as platform-admin boundaries
  - realm provisioning routes now require authenticated `PLATFORM_ADMIN` request context and are approved platform-admin boundaries
  - external IdP OIDC and SAML diagnostic routes now require authenticated tenant-admin or platform-admin request context
  - public OIDC state issuance plus OIDC/SAML callback routes now operate as explicit approved public-auth boundaries with server-side state binding and compatibility-query validation
  - identity stats now operate as an approved internal orchestrator analytics boundary with service-token verification and tenant-scoped Keycloak counts
  - dashboard snapshot now derives tenant scope only from authenticated request context and no longer falls back to raw `X-Tenant-ID`
  - marketing funnel summary now operates as an approved internal analytics boundary with internal service-token verification
  - public lead lookup now operates as an approved pre-tenant lookup boundary gated by an opaque lead ID, backend-issued provisioning token, lead-expiry validation, and minimized response payloads

### Priority 4: Close Review-Required Surfaces

These are no longer “unknowns.” They are explicit decisions that still need to be made.

Current review-required backlog:

None. The latest baseline reports `review_required_routes = 0`.

Outcome achieved:

- remaining `review_required` queue reduced to `0`
- no unresolved ambiguous public tenant-selection surfaces remain in the control-plane services covered by the smoke baseline

## Recommended Execution Order

Use this order to keep momentum while preserving correctness.

There is no remaining remediation-only execution order. Route-family remediation is complete.

Latest reduction:

- `api-gateway review_required 37 -> 0`
- orchestrator scan routes are now classified as authenticated tenant-derived gateway boundaries
- tenant-path orchestrator routes now require exact same-tenant path matching before querying or proxying downstream data
- SIEM search, detection-rule detail, and entity-timeline routes are now classified as authenticated tenant-derived gateway boundaries
- compliance dashboard, SOC 2 coverage, and evidence-collect routes are now classified as authenticated tenant-derived gateway boundaries, and evidence collection rejects foreign body tenant overrides
- audit AI-activity read and write routes are now classified as authenticated tenant-derived gateway boundaries, and query/body tenant overrides are rejected on mismatch
- onboarding status and completion routes are now classified as authenticated tenant-derived gateway boundaries, and caller-supplied X-Tenant-ID hints are ignored for both IAM proxying and initial scan enqueue
- vulnerability and dashboard chat routes are now classified as authenticated tenant-derived gateway boundaries, and any body tenant override is rejected on mismatch
- IAM dashboard snapshot is now classified as an authenticated tenant-derived gateway boundary, and caller-supplied X-Tenant-ID hints are ignored
- incident update is now classified as an authenticated tenant-derived gateway boundary, and caller-supplied X-Tenant-ID hints are ignored
- AI Shield ingest is now classified as an internal service-token boundary, and any body org_id must match the dispatch tenant header
- login and refresh are now classified as an approved pre-auth hint boundary that allowlists only X-Tenant-ID and X-Realm before identity is established or refreshed
- ingest pipeline simulation is now classified as an approved shared diagnostic boundary for platform ingest pipeline testing and no longer remains in the review queue

## Parking Lot: Deferred Audit Evidence Work

The following items are intentionally parked until the remediation state is stronger:

1. Expand the curated negative suite across all remaining reviewed surfaces.
2. Run the `full` audit profile in the audit environment.
3. Produce and archive the final evidence binder for auditors.

These are now the next required steps. They were deferred only to avoid packaging weak or transitional controls as if they were final.

## Definition Of Done For This Worklist

This remediation-only worklist is done when:

- the small remaining mechanical queues are cleared
- no active policy-dependent runtime owner queue remains
- large high-risk owners are closed
- remaining `review_required` control-plane surfaces are explicitly resolved
- the codebase is in a state where final audit evidence work is worth executing

Current status:

- done
