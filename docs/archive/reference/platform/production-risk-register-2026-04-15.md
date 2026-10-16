# SentinelGrid Production Risk Register

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 15, 2026  
**Status:** Baseline register for Phase 0  
**Purpose:** Track the major risks that must be managed before a fresh production audit and release candidate review

## Severity Definitions

- `P0`: blocks production launch until closed
- `P1`: should close before launch if the affected capability is marketed or customer-visible
- `P2`: important, but can follow after launch if clearly scoped and not misleading

## Current Risks

| ID | Priority | Risk | Current Evidence | Required Closure |
| --- | --- | --- | --- | --- |
| R-001 | P0 | Browser bearer-token handling is not production-safe | frontend auth depends on `localStorage` / `sessionStorage` and client-readable access token cookies | move to hardened session model with server-trustable auth enforcement |
| R-002 | P0 | TLS verification is disabled on live service paths | widespread `verify=False` and `InsecureSkipVerify` in backend and adjacent modules | remove insecure verification bypasses from live production code paths |
| R-003 | P0 | Wildcard CORS remains on multiple services | many `allow_origins=["*"]` occurrences across services | enforce environment-specific allowlists and verify preflight behavior |
| R-004 | P0 | Unsafe default secrets and admin defaults still exist | default internal token, Keycloak admin defaults, TLS-off defaults | fail closed on unsafe prod config and move secrets to external management |
| R-005 | P0 | Service-to-Keycloak auth model is not production-grade | password-based admin and bootstrap dependencies still exist | migrate to least-privilege service accounts with rotated secrets |
| R-006 | P0 | Product scope is broader than the current production posture | monorepo includes multiple adjacent product surfaces and subsystems | freeze initial launch scope and gate non-launch surfaces |
| R-007 | P0 | Stub-backed automation can mislead operators and buyers | playbook execution and some provider paths still use stub/mock behavior | replace with real execution or explicitly gate/hide |
| R-008 | P0 | Production truth is fragmented across multiple docs and surfaces | current docs reflect both historical and current-state realities | freeze canonical doc set and use it as the only launch reference |
| R-009 | P1 | Canonical entity/evidence model is not yet broad enough for the full operator-plane story | queue, graph, incident, posture, and IAM flows are not yet fully unified | define and adopt one current-state operator model |
| R-010 | P1 | `SentinelGridPostureAgent` creates product-boundary ambiguity | subsystem still has its own frontend and product identity | decide merge, hide, or explicitly boundary the surface |
| R-011 | P1 | AI Shield provider support may be overstated | Anthropic and local providers still contain mock behavior | restrict launch support to real, tested provider paths |
| R-012 | P1 | IAM breadth exceeds hardening depth | multiple advanced IAM flows still contain TODOs or assumptions | reduce launch claim set or finish the critical IAM paths |
| R-013 | P1 | Queue / incident / graph coherence is not fully proven | some surfaces still rely on fallback or partially unified models | prove one coherent operator workflow across core surfaces |
| R-014 | P1 | Compliance claims may outrun evidence integrity | reporting exists, but evidence rigor and audit readiness need stronger proof | scope compliance claims to what is actually backed by evidence |
| R-015 | P1 | Launch support model is not yet production-ready | support runbooks, on-call, and incident procedures are incomplete | create support model, escalation matrix, and runbooks |
| R-016 | P1 | Deployment, rollback, and migration evidence is incomplete | production ops docs exist, but not all runbooks and proofs are complete | validate deploy, rollback, migration, and restore procedures |
| R-017 | P1 | Observability is not yet sufficient for production operations | metrics, tracing, alerting, and runbooks remain incomplete | add production dashboards, alerts, and correlation IDs |
| R-018 | P1 | Customer trust package is not yet strong enough for diligence | trust/security docs exist, but evidence pack is not fully assembled | prepare trust artifacts and security review FAQ |
| R-019 | P2 | Pentest product surface increases GTM and operational confusion | standalone pentest platform remains in the monorepo | keep outside core SaaS scope until separately hardened and packaged |
| R-020 | P2 | Enterprise comparison pressure can distort roadmap priorities | platform breadth invites unfair category comparison | keep GTM focused on SMB operator workflow and guided remediation |

## Risk Clusters

### Cluster A: Security trust boundary risks

- `R-001`
- `R-002`
- `R-003`
- `R-004`
- `R-005`
- `R-007`

These must be treated as the top program priority.

### Cluster B: Scope and product-boundary risks

- `R-006`
- `R-008`
- `R-010`
- `R-019`
- `R-020`

These determine whether the product can be honestly and cleanly launched.

### Cluster C: Productization and workflow integrity risks

- `R-009`
- `R-011`
- `R-012`
- `R-013`
- `R-014`

These determine whether the product experience matches the product story.

### Cluster D: Production operations risks

- `R-015`
- `R-016`
- `R-017`
- `R-018`

These determine whether the team can actually operate the platform after launch.

## Required Evidence Before Fresh Audit

Each P0 and launch-relevant P1 item should have evidence attached before the next audit:

- code and config references
- tests added or expanded
- screenshots or artifacts where relevant
- runbooks or decision docs
- residual-risk statement if partial

## Phase Mapping

| Risk ID | Planned Closure Phase |
| --- | --- |
| R-001 | Phase 1 |
| R-002 | Phase 1 |
| R-003 | Phase 1 |
| R-004 | Phase 1 |
| R-005 | Phase 1 |
| R-006 | Phase 0 / Phase 2 |
| R-007 | Phase 3 |
| R-008 | Phase 0 |
| R-009 | Phase 2 |
| R-010 | Phase 2 |
| R-011 | Phase 3 |
| R-012 | Phase 3 |
| R-013 | Phase 3 |
| R-014 | Phase 3 / Phase 5 |
| R-015 | Phase 4 |
| R-016 | Phase 4 |
| R-017 | Phase 4 |
| R-018 | Phase 5 |
| R-019 | Phase 0 |
| R-020 | Phase 5 |

## Phase 0 Exit Criteria For The Register

Phase 0 risk work is complete when:

- every P0 risk has an owner
- every P0 risk has a planned closure phase
- all out-of-scope risks are explicitly marked rather than left ambiguous
- this register is being used as the baseline for status reviews
