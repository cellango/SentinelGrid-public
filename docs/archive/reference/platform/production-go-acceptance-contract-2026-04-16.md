# SentinelGrid Production Go Acceptance Contract

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 16, 2026  
**Status:** Updated on April 18, 2026 after the Phase 7 Slice 7D final signoff  
**Purpose:** Define the exact gates that must be satisfied before SentinelGrid can move from the current `No-Go` baseline to a fresh `Go` recommendation

## Why This Exists

The current repo contains enough documentation to explain the problems, but not enough precision to prevent teams from declaring success early.

This contract fixes that. It defines:

- what must be true before the final re-audit begins
- what evidence is required for closure
- who must sign off
- what conditions automatically block `Go`

## Current Baseline

The current canonical decision baseline is:

- `docs/PRODUCTION_READINESS_AND_COMPETITIVE_AUDIT_2026-04-16.md`

That baseline remains in force until every gate in this contract is passed and a fresh re-audit supersedes it.

## Gate Rules

- A gate is either `Pass` or `Open`. There is no “mostly done” state at final signoff.
- A gate can be marked `Pass` only with explicit evidence.
- A gate cannot be waived by optimism, roadmap intent, or “we’ll fix it right after launch.”
- If any `Critical Gate` is still `Open`, the program remains `No-Go`.
- Any approved exception must follow `docs/archive/reference/platform/production-risk-exception-policy-2026-04-16.md` and be recorded in `docs/archive/reference/platform/production-approved-exception-register-2026-04-16.md`.

## Critical Gates

| Gate ID | Gate | Required Evidence | Direct Owner | Draft Target Week | Blocks `Go` If Open |
| --- | --- | --- | --- | --- | --- |
| G-01 | Current production truth is unambiguous | updated truth baseline, docs index, and historical markers on conflicting older `Go` docs | Product Lead | Week of April 20, 2026 | Yes |
| G-02 | Launch boundary equals shipped and supported surface | approved deployment matrix and gated feature inventory aligned to website/demo/product | Product Lead | Week of April 20, 2026 | Yes |
| G-03 | IAM public auth paths no longer trust unsigned token claims | code changes, tests, and audit notes covering `logout`, `refresh`, `me`, OIDC callback handling | IAM / Identity Lead | Week of April 27, 2026 | Yes |
| G-04 | SOAR no longer accepts unsigned, fallback, or placeholder tenant context | code changes and regression tests for `backend/agents/soar_agent/app/core/security.py` and detection webhooks | SOAR / Backend Lead | Week of May 4, 2026 | Yes |
| G-05 | Orchestrator response/remediation endpoints no longer use placeholder tenants | code changes and tenant-isolation tests for `backend/services/orchestrator/app/api/response.py` | Platform / Backend Lead | Week of May 4, 2026 | Yes |
| G-06 | AI Shield is either hardened or remains fully gated from default launch | authz closure evidence, deployment/runbook evidence, or explicit gated status proof | AI Shield Lead | Week of May 11, 2026 | Yes |
| G-07 | Public ingress is HTTPS-only and runtime/network hardening baseline is enforced | ingress config, network policy evidence, pod security baseline, rollout proof | DevOps / Platform Lead | Week of April 27, 2026 | Yes |
| G-08 | Launch-scope dependencies have no unresolved high / critical known vulnerabilities without approved exceptions | `npm audit`, `pip-audit`, image scan, SBOM artifacts, and `docs/archive/reference/platform/production-approved-exception-register-2026-04-16.md` if needed | Security Lead + Engineering Lead | Week of May 11, 2026 | Yes |
| G-09 | No marketed launch workflow silently falls back to stub/mock/placeholder behavior | feature review, gated feature inventory, workflow verification notes | Product Lead | Week of May 11, 2026 | Yes |
| G-10 | Restore, rollback, readiness, and support rehearsals are proven on the current narrowed launch scope | fresh drill artifacts, runbook validation, support rehearsal notes | DevOps / Platform Lead + Support Lead | Week of May 18, 2026 | Yes |
| G-11 | Final re-audit concludes the narrowed launch package is defensible | new re-audit report with explicit `Go` recommendation | Security Lead | Re-audit week | Yes |
| G-12 | Named approvers record final signoff | final signoff memo with named approvers and decision date | Product Lead + Security Lead + Engineering Lead | Re-audit week | Yes |

## Secondary Gates

These are still important, but they do not block Phase 7 entry if they are explicitly classified as post-launch and do not undermine launch claims.

| Gate ID | Gate | Required Outcome | Default Priority |
| --- | --- | --- | --- |
| S-01 | partner / MSP motion is bounded and qualified | sales-assisted scope only unless fully operationalized | P1 |
| S-02 | compliance and reporting claims are evidence-backed and scoped | no enterprise compliance-suite overclaim | P1 |
| S-03 | endpoint coverage story is qualified, not overstated | no false EDR/XDR parity claim | P1 |
| S-04 | AI Shield unsupported providers stay visibly gated | no broad provider-coverage overclaim | P1 |

## Automatic `No-Go` Conditions

Any one of the following automatically blocks a final `Go` recommendation:

1. any live launch path still trusts unsigned JWT payload data for tenant, identity, or authorization
2. any launch-critical endpoint still depends on placeholder tenant defaults such as `Depends(lambda: "default")`
3. any public launch path still depends on wildcard CORS or a plain-HTTP primary ingress
4. any launch-scope dependency set still has unresolved critical findings and no approved exception
5. any marketed production workflow still performs fake completion, mock execution, or silent fallback while being presented as real
6. the final re-audit finds that the current docs, deployment workflow, and product surface still disagree

## Approved Exception Rule

An approved exception is valid only if:

1. it complies with `docs/archive/reference/platform/production-risk-exception-policy-2026-04-16.md`
2. it is recorded in `docs/archive/reference/platform/production-approved-exception-register-2026-04-16.md`
3. it does not override an automatic `No-Go` condition
4. it has a direct owner, review date, and expiration date

If any one of those is missing, the issue remains `Open`.

## Draft Schedule Baseline

Until named owners override the dates in Phase 0 Slice 0C, use this as the default execution baseline:

1. week of April 20, 2026: close Phase 0 ownership, acceptance, and gate paperwork
2. week of April 27, 2026: close `G-03` and start `G-07`
3. week of May 4, 2026: close `G-04` and `G-05`
4. week of May 11, 2026: close `G-06`, `G-08`, and `G-09`
5. week of May 18, 2026: close `G-10`

## Phase Entry / Exit Contract

### Entry To Phase 1

Required:

- Phase 0 truth reset artifacts are published
- current `No-Go` decision is explicitly treated as canonical baseline
- draft target weeks and the exception rule are frozen
- named owners are assigned before formal Phase 1 closure tracking begins

### Entry To Phase 7

Required:

- all critical gates `G-01` through `G-10` are `Pass`
- no automatic `No-Go` condition remains
- launch-scope deployment matrix is current

### Exit From Phase 7

Required:

- `G-11` passed with a fresh re-audit report
- `G-12` passed with named signoff
- a new report explicitly states `Go`

## Required Final Artifacts

The following documents must exist before the final signoff:

1. `docs/PRODUCTION_RE_AUDIT_<date>.md`
2. `docs/PRODUCTION_GO_RECOMMENDATION_<date>.md`
3. `docs/RELEASE_CANDIDATE_GO_SIGNOFF_<date>.md`

The second document must explicitly say **`Go`**. If it does not, the contract is not complete.

## Named Approver Roles

The following roles must sign the final decision:

- Security Lead
- Engineering Lead
- Product Lead
- DevOps / Platform Lead
- IAM / Identity Lead
- Frontend Lead

Additional approvers may be included, but those roles are the minimum set.

## Current Program Interpretation

As of April 18, 2026 after the Phase 7 Slice 7D final signoff:

- `G-01` is passed
- `G-02` is passed
- `G-03` is passed with evidence in `docs/archive/validation/phase1-slice-1a-unsigned-token-trust-closeout-2026-04-16.md`
- `G-04` is passed with evidence in `docs/archive/validation/phase2-slice-2a-soar-tenant-trust-closeout-2026-04-16.md`
- `G-05` is passed with evidence in `docs/archive/validation/phase2-slice-2b-orchestrator-response-auth-closeout-2026-04-16.md`
- `G-06` is passed with evidence in `docs/archive/validation/phase2-slice-2c-ai-shield-auth-closeout-2026-04-16.md`
- `Slice 1B` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase1-slice-1b-bff-session-boundary-closeout-2026-04-16.md`
- `Slice 1C` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase1-slice-1c-keycloak-admin-pattern-closeout-2026-04-16.md`
- `Slice 1D` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase1-slice-1d-frontend-security-header-proxy-closeout-2026-04-16.md`
- `Slice 2A` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase2-slice-2a-soar-tenant-trust-closeout-2026-04-16.md`
- `Slice 2B` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase2-slice-2b-orchestrator-response-auth-closeout-2026-04-16.md`
- `Slice 2C` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase2-slice-2c-ai-shield-auth-closeout-2026-04-16.md`
- `Slice 2D` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase2-slice-2d-internal-token-standardization-closeout-2026-04-16.md`
- `Slice 3A` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase3-slice-3a-https-only-public-edge-closeout-2026-04-17.md`
- `Slice 3B` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase3-slice-3b-kubernetes-network-containment-closeout-2026-04-17.md`
- `Slice 3C` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase3-slice-3c-runtime-hardening-closeout-2026-04-17.md`
- `Slice 3D` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase3-slice-3d-secret-and-default-credential-elimination-closeout-2026-04-17.md`
- `Slice 4A` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase4-slice-4a-frontend-dependency-remediation-closeout-2026-04-17.md`
- `Slice 4B` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase4-slice-4b-model-gateway-dependency-remediation-closeout-2026-04-17.md`
- `Slice 4C` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase4-slice-4c-reproducible-dependency-policy-closeout-2026-04-17.md`
- `Slice 4D` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase4-slice-4d-base-image-and-image-scan-discipline-closeout-2026-04-18.md`
- `Slice 5A` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase5-slice-5a-non-launch-surface-gate-closeout-2026-04-18.md`
- `Slice 5B` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase5-slice-5b-workflow-truthfulness-closeout-2026-04-18.md`
- `Slice 5C` is complete for the narrowed launch scope with evidence in `docs/PHASE5_SLICE_5C_LAUNCH_PACKAGING_AND_GTM_ALIGNMENT_CLOSEOUT_2026-04-18.md`
- `Slice 5D` is complete for the narrowed launch scope with evidence in `docs/PHASE5_SLICE_5D_DIFFERENTIATE_ON_SIMPLICITY_NOT_BREADTH_CLOSEOUT_2026-04-18.md`
- `Slice 6A` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase6-slice-6a-readiness-metrics-alerting-closeout-2026-04-18.md`
- `Slice 6B` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase6-slice-6b-backup-restore-rollback-drills-closeout-2026-04-18.md`
- `Slice 6C` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase6-slice-6c-production-support-and-incident-rehearsal-closeout-2026-04-18.md`
- `Slice 6D` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase6-slice-6d-final-pre-audit-dry-run-closeout-2026-04-18.md` and `artifacts/phase6/preaudit-dry-run/2026-04-18/phase6-slice6d-local/phase7-entry-review.md`
- `G-07` is passed with evidence in `docs/archive/validation/phase3-slice-3d-secret-and-default-credential-elimination-closeout-2026-04-17.md`
- `G-08` is passed with evidence in `docs/archive/validation/phase4-slice-4d-base-image-and-image-scan-discipline-closeout-2026-04-18.md` and approved exceptions in `docs/archive/reference/platform/production-approved-exception-register-2026-04-16.md`
- `G-09` is passed with evidence in `docs/archive/validation/phase5-slice-5b-workflow-truthfulness-closeout-2026-04-18.md`
- `G-10` is passed with evidence in `docs/archive/validation/phase6-slice-6d-final-pre-audit-dry-run-closeout-2026-04-18.md`
- `G-11` is passed with evidence in `docs/archive/validation/production-re-audit-2026-04-18.md`
- `Slice 7B` is complete for the narrowed launch scope with evidence in `docs/archive/validation/phase7-slice-7b-independent-security-review-closeout-2026-04-18.md`
- `Slice 7C` is complete for the narrowed launch scope with evidence in `docs/archive/validation/production-go-recommendation-2026-04-18.md`
- `Slice 7D` is complete for the narrowed launch scope with evidence in `docs/archive/validation/release-candidate-go-signoff-2026-04-18.md`
- `G-12` is passed with evidence in `docs/archive/validation/release-candidate-go-signoff-2026-04-18.md`
- the Phase 0 owner and exception baseline is complete
- Phase 7 is complete for the narrowed launch scope

That means the current state remains:

- broad launch: `No-Go`
- narrowed launch: final `Go` recommendation and named signoff are now recorded

## Phase 0 Exit Condition Covered By This Doc

Phase 0 acceptance-contract work is complete when:

- every stakeholder can see the exact gates required for `Go`
- no one can credibly declare launch-ready status without producing the required evidence
- Phase 1 work can be sequenced against explicit pass/fail conditions instead of interpretation
