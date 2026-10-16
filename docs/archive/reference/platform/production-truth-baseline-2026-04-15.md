# SentinelGrid Production Truth Baseline

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 15, 2026  
**Status:** Updated on April 18, 2026 after the Phase 7 Slice 7D final signoff  
**Purpose:** Define the canonical document set and precedence rules for production remediation work

## Why This Exists

The repository contains a mix of current-state docs, implementation plans, completed phase notes, and historical design documents. That creates avoidable ambiguity during remediation.

This document freezes the production truth set that should be used until the next audit and release-candidate review.

## Canonical Production Truth Documents

Use these documents first when making launch, scope, security, and sequencing decisions:

1. `docs/archive/validation/release-candidate-go-signoff-2026-04-18.md`
2. `docs/archive/validation/production-go-recommendation-2026-04-18.md`
3. `docs/archive/validation/production-re-audit-2026-04-18.md`
4. `docs/PRODUCTION_READINESS_AND_COMPETITIVE_AUDIT_2026-04-16.md`
5. `docs/PRODUCTION_GO_READINESS_IMPLEMENTATION_PLAN_2026-04-16.md`
6. `docs/archive/reference/platform/production-go-acceptance-contract-2026-04-16.md`
7. `docs/archive/reference/infrastructure/production-launch-scope-deployment-matrix-2026-04-16.md`
8. `docs/archive/reference/platform/phase0-truth-reset-checklist-2026-04-16.md`
9. `docs/archive/reference/platform/phase0-to-phase1-owner-review-2026-04-16.md`
10. `docs/archive/validation/phase1-slice-1b-bff-session-boundary-closeout-2026-04-16.md`
11. `docs/archive/validation/phase1-slice-1c-keycloak-admin-pattern-closeout-2026-04-16.md`
12. `docs/archive/validation/phase1-slice-1d-frontend-security-header-proxy-closeout-2026-04-16.md`
13. `docs/archive/validation/phase2-slice-2a-soar-tenant-trust-closeout-2026-04-16.md`
14. `docs/archive/validation/phase2-slice-2b-orchestrator-response-auth-closeout-2026-04-16.md`
15. `docs/archive/validation/phase2-slice-2c-ai-shield-auth-closeout-2026-04-16.md`
16. `docs/archive/validation/phase2-slice-2d-internal-token-standardization-closeout-2026-04-16.md`
17. `docs/archive/validation/phase3-slice-3a-https-only-public-edge-closeout-2026-04-17.md`
18. `docs/archive/validation/phase3-slice-3b-kubernetes-network-containment-closeout-2026-04-17.md`
19. `docs/archive/validation/phase3-slice-3c-runtime-hardening-closeout-2026-04-17.md`
20. `docs/archive/validation/phase3-slice-3d-secret-and-default-credential-elimination-closeout-2026-04-17.md`
21. `docs/archive/validation/phase4-slice-4a-frontend-dependency-remediation-closeout-2026-04-17.md`
22. `docs/archive/validation/phase4-slice-4b-model-gateway-dependency-remediation-closeout-2026-04-17.md`
23. `docs/archive/validation/phase4-slice-4c-reproducible-dependency-policy-closeout-2026-04-17.md`
24. `docs/archive/validation/phase4-slice-4d-base-image-and-image-scan-discipline-closeout-2026-04-18.md`
25. `docs/archive/validation/phase5-slice-5a-non-launch-surface-gate-closeout-2026-04-18.md`
26. `docs/archive/validation/phase5-slice-5b-workflow-truthfulness-closeout-2026-04-18.md`
27. `docs/PHASE5_SLICE_5C_LAUNCH_PACKAGING_AND_GTM_ALIGNMENT_CLOSEOUT_2026-04-18.md`
28. `docs/PHASE5_SLICE_5D_DIFFERENTIATE_ON_SIMPLICITY_NOT_BREADTH_CLOSEOUT_2026-04-18.md`
29. `docs/archive/validation/phase6-slice-6a-readiness-metrics-alerting-closeout-2026-04-18.md`
30. `docs/archive/validation/phase6-slice-6b-backup-restore-rollback-drills-closeout-2026-04-18.md`
31. `docs/archive/validation/phase6-slice-6c-production-support-and-incident-rehearsal-closeout-2026-04-18.md`
32. `docs/archive/validation/phase6-slice-6d-final-pre-audit-dry-run-closeout-2026-04-18.md`
33. `docs/archive/validation/phase7-slice-7b-independent-security-review-closeout-2026-04-18.md`
34. `docs/archive/reference/platform/production-risk-exception-policy-2026-04-16.md`
35. `docs/archive/reference/platform/production-approved-exception-register-2026-04-16.md`
36. `docs/archive/reference/platform/production-launch-scope-decision-2026-04-15.md`
37. `docs/archive/reference/platform/phase5-gated-feature-inventory-2026-04-16.md`
38. `docs/PRODUCTION_OWNER_MATRIX_2026-04-15.md`
39. `docs/archive/reference/platform/production-risk-register-2026-04-15.md`
40. `docs/PRODUCTION_REMEDIATION_IMPLEMENTATION_PLAN.md`
41. `docs/PRODUCTION_READINESS_TODO.md`
42. `docs/archive/reference/platform/production-security-checklist.md`
43. `docs/design/SENTINELGRID_OVERALL_DESIGN.md`
44. `docs/reference/entity-model.md`
45. `docs/reference/product-catalog.md`
46. `docs/archive/reference/platform/website-archival-decision.md`
47. `docs/archive/reference/platform/production-operations-topology-2026-04-15.md`
48. `docs/archive/reference/platform/production-capacity-baseline-2026-04-15.md`

## Precedence Rules

If documents conflict, resolve them in this order:

1. `PRODUCTION_LAUNCH_SCOPE_DECISION_2026-04-15.md`
2. `PRODUCTION_GO_RECOMMENDATION_2026-04-18.md`
3. `RELEASE_CANDIDATE_GO_SIGNOFF_2026-04-18.md`
4. `PRODUCTION_RE_AUDIT_2026-04-18.md`
5. `PRODUCTION_READINESS_AND_COMPETITIVE_AUDIT_2026-04-16.md`
6. `PRODUCTION_GO_READINESS_IMPLEMENTATION_PLAN_2026-04-16.md`
7. `PRODUCTION_GO_ACCEPTANCE_CONTRACT_2026-04-16.md`
8. `PRODUCTION_LAUNCH_SCOPE_DEPLOYMENT_MATRIX_2026-04-16.md`
9. `PHASE0_TRUTH_RESET_CHECKLIST_2026-04-16.md`
10. `PHASE0_TO_PHASE1_OWNER_REVIEW_2026-04-16.md`
11. `PHASE1_SLICE_1B_BFF_SESSION_BOUNDARY_CLOSEOUT_2026-04-16.md`
12. `PHASE1_SLICE_1C_KEYCLOAK_ADMIN_PATTERN_CLOSEOUT_2026-04-16.md`
13. `PHASE1_SLICE_1D_FRONTEND_SECURITY_HEADER_PROXY_CLOSEOUT_2026-04-16.md`
14. `PHASE2_SLICE_2A_SOAR_TENANT_TRUST_CLOSEOUT_2026-04-16.md`
15. `PHASE2_SLICE_2B_ORCHESTRATOR_RESPONSE_AUTH_CLOSEOUT_2026-04-16.md`
16. `PHASE2_SLICE_2C_AI_SHIELD_AUTH_CLOSEOUT_2026-04-16.md`
17. `PHASE2_SLICE_2D_INTERNAL_TOKEN_STANDARDIZATION_CLOSEOUT_2026-04-16.md`
18. `PHASE3_SLICE_3A_HTTPS_ONLY_PUBLIC_EDGE_CLOSEOUT_2026-04-17.md`
19. `PHASE3_SLICE_3B_KUBERNETES_NETWORK_CONTAINMENT_CLOSEOUT_2026-04-17.md`
20. `PHASE3_SLICE_3C_RUNTIME_HARDENING_CLOSEOUT_2026-04-17.md`
21. `PHASE3_SLICE_3D_SECRET_AND_DEFAULT_CREDENTIAL_ELIMINATION_CLOSEOUT_2026-04-17.md`
22. `PHASE4_SLICE_4A_FRONTEND_DEPENDENCY_REMEDIATION_CLOSEOUT_2026-04-17.md`
23. `PHASE4_SLICE_4B_MODEL_GATEWAY_DEPENDENCY_REMEDIATION_CLOSEOUT_2026-04-17.md`
24. `PHASE4_SLICE_4C_REPRODUCIBLE_DEPENDENCY_POLICY_CLOSEOUT_2026-04-17.md`
25. `PHASE4_SLICE_4D_BASE_IMAGE_AND_IMAGE_SCAN_DISCIPLINE_CLOSEOUT_2026-04-18.md`
26. `PHASE5_SLICE_5A_NON_LAUNCH_SURFACE_GATE_CLOSEOUT_2026-04-18.md`
27. `PHASE5_SLICE_5B_WORKFLOW_TRUTHFULNESS_CLOSEOUT_2026-04-18.md`
28. `PHASE5_SLICE_5C_LAUNCH_PACKAGING_AND_GTM_ALIGNMENT_CLOSEOUT_2026-04-18.md`
29. `PHASE5_SLICE_5D_DIFFERENTIATE_ON_SIMPLICITY_NOT_BREADTH_CLOSEOUT_2026-04-18.md`
30. `PHASE6_SLICE_6A_READINESS_METRICS_ALERTING_CLOSEOUT_2026-04-18.md`
31. `PHASE6_SLICE_6B_BACKUP_RESTORE_ROLLBACK_DRILLS_CLOSEOUT_2026-04-18.md`
32. `PHASE6_SLICE_6C_PRODUCTION_SUPPORT_AND_INCIDENT_REHEARSAL_CLOSEOUT_2026-04-18.md`
33. `PHASE6_SLICE_6D_FINAL_PRE_AUDIT_DRY_RUN_CLOSEOUT_2026-04-18.md`
34. `PHASE7_SLICE_7B_INDEPENDENT_SECURITY_REVIEW_CLOSEOUT_2026-04-18.md`
35. `PRODUCTION_RISK_EXCEPTION_POLICY_2026-04-16.md`
36. `PRODUCTION_APPROVED_EXCEPTION_REGISTER_2026-04-16.md`
37. `PRODUCTION_RISK_REGISTER_2026-04-15.md`
38. current code in the canonical launch surface
39. operational checklists such as `PRODUCTION_READINESS_TODO.md` and `PRODUCTION_SECURITY_CHECKLIST.md`
40. historical phase docs, migration notes, and design drafts

## Historical Document Rule

The following documents remain useful as historical execution evidence, but they are **not** the current production decision baseline while the current `No-Go` audit is in force:

- `docs/archive/reference/platform/phase6-execution-checklist.md`
- `docs/archive/reference/platform/phase6-audit-evidence-pack-2026-04-16.md`
- `docs/archive/reference/platform/phase6-release-candidate-signoff-2026-04-16.md`

They can be used for:

- prior verification context
- rehearsal artifacts
- evidence structure

They cannot be used to override the current April 18 final signoff baseline for the narrowed launch package, the April 16 broad-launch `No-Go` baseline, or to claim the repo is already broadly `Go`.

## Canonical Repo Truths For The Initial Launch

- `frontend/` is the only canonical customer-facing application surface for the initial SaaS launch.
- `frontend/src/app/(marketing)/` is the canonical marketing route tree.
- `frontend/src/app/(dashboard)/` is the canonical authenticated product route tree.
- `website/` is archived legacy code and not part of the initial production launch.
- `SentinelGridPostureAgent/` remains an implementation subsystem and is not the primary production console.
- `SentinelGridAIShield/` is a valid differentiator, but only real and tested provider paths may be exposed as launch-ready.
- `SentinelGridPenTestAgent/` is outside the initial core self-serve SaaS promise.

## How To Use Historical Docs

Historical docs still have value, but only for one of these reasons:

- implementation context
- migration rationale
- architectural background
- evidence of why a decision was made

They should not be used to expand launch scope, override current security priorities, or re-open already frozen product-boundary decisions.

## Required Maintenance During Remediation

When any launch-critical decision changes, update:

1. the launch scope decision if the customer-facing boundary changes
2. the current audit if the release decision changes
3. the go-readiness implementation plan if the phase sequence changes
4. the go acceptance contract if the pass/fail gates change
5. the deployment matrix if shipped scope changes
6. the Phase 0 truth reset checklist if current tranche status changes
7. the Phase 0 owner review memo if baseline acceptance or signoff status changes
8. the production exception policy or register if exception posture changes
9. this baseline doc if the canonical set changes

## Phase 0 Exit Condition Covered By This Doc

Phase 0 document-freeze work is complete when:

- teams can identify the current production truth set without guessing
- conflicting historical docs are subordinated to the baseline
- launch-scope decisions are easy to trace back to one canonical place
