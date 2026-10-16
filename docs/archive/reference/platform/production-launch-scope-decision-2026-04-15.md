# SentinelGrid Production Launch Scope Decision

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 15, 2026  
**Status:** Approved Phase 0 launch-boundary baseline  
**Purpose:** Freeze the initial production launch scope so engineering, product, security, and GTM all work against the same boundary

## Decision

The initial SentinelGrid production launch will be positioned and engineered as:

**A unified security operations platform for SMB and mid-market teams centered on one operator workflow across detections, incidents, identity, posture, a qualified endpoint coverage path, and a narrowed baseline compliance and reporting subset.**

This is a narrower scope than the full monorepo surface.

## Canonical Product Surface

### Canonical frontend

- `frontend/` is the only canonical production operator and marketing surface.
- `frontend/src/app/(marketing)/*` is the canonical marketing route tree.
- `frontend/src/app/(dashboard)/*` is the canonical authenticated product route tree.

### Canonical route model

- authenticated product paths should resolve under `/dashboard/*`
- legacy aliases may remain temporarily only for compatibility

## Launch-In Scope

### Core operator workflow

- dashboard landing and persona routing
- Now queue / operator overview
- war room / prioritized action queue
- incident detail and case workflow
- security graph where backed by real data

### SIEM and detections

- detection rule catalog, builder, preview, and deployment
- alert list, alert detail, and alert update
- basic log search and detection pipeline health

### IAM and access hygiene

- people and access views needed for launch package
- access profiles and birthright rules
- access review and privileged-access flows only if backed by real enforcement and auditability
- core auth and tenant-aware access patterns

### Cloud posture and scans

- posture score, coverage, findings, and recommendations
- scanner orchestration and scan detail flows
- hardened image recommendations tied to the main console

### Endpoint coverage

- SentinelGuard-based endpoint collection path
- endpoint coverage and install workflow
- endpoint signals feeding detections and incidents
- endpoint positioning only as a guided coverage path tied to the main console, not as a claim of full EDR/XDR parity

### Compliance and reporting

- baseline compliance dashboard limited to the evidence-backed reporting subset supported by the deployed path
- core report generation and evidence views
- trust/reporting features that are backed by real evidence, not placeholder status
- no claim that the launch package is a full enterprise compliance-suite replacement

### AI Shield

- may be included only as a controlled add-on
- only provider paths that are real, supported, and tested may be exposed as production-ready

### Partner / MSP motion

- may be sold only as a qualified sales-assisted motion
- must stay tied to the explicit partner operating model and delivery review
- is not part of the default self-serve launch promise

## Launch-Out Of Scope Or Explicitly Gated

### Legacy and non-canonical surfaces

- `website/` as an active product or marketing surface
- any new user-facing feature work in `website/`

### Separate subsystem frontends

- `SentinelGridPostureAgent/frontend/` as a primary customer-facing production console

### Over-broad product claims

- enterprise-grade CNAPP parity
- enterprise-grade EDR/XDR parity
- enterprise compliance-suite replacement parity
- broad generalized AI-agent automation claims
- replacing Wiz, CrowdStrike, Okta, or SailPoint across their full category depth

### PenTest platform

- `SentinelGridPenTestAgent/` is **not** part of the initial core self-serve SaaS promise
- it may be sold later as:
  - a separate package
  - a services-led engagement
  - a gated product line with independent readiness review

### AI Shield unsupported provider paths

- any provider path still returning mock responses
- any feature that depends on stubbed policy or telemetry behavior
- dedicated `ai-security/*` standalone routes as a default launch console

### Partner default self-serve motion

- partner-led or MSP-led delivery as the default launch website or signup path
- any partner promise that assumes broad unmanaged cross-tenant operations without explicit operating-model qualification

### Stub-backed automation

- playbook or response flows that report completed execution without actual execution evidence

## Product Boundary Rules

1. If a user-facing workflow is not in `frontend/`, it is not part of the canonical launch surface unless explicitly approved.
2. If a workflow depends on mock, stub, or demo fallback logic, it must be:
   - removed from launch scope,
   - hidden,
   - clearly labeled beta, or
   - completed before launch.
3. If a feature is marketed on the website, it must have:
   - a real backend path,
   - a defined owner,
   - a support model,
   - production-safe auth and audit behavior.

## Repo-Level Implications

### `frontend/`

- receives all net-new launch-critical user-facing work

### `website/`

- archived reference only
- may receive archival labeling or removal-prep changes only

### `SentinelGridPostureAgent/`

- remains a subsystem during remediation
- must not create user-facing ambiguity about the canonical console

### `SentinelGridAIShield/`

- remains a meaningful product differentiator
- remains controlled add-on scope for the default launch
- only production-real provider paths may be launched

### `SentinelGridPenTestAgent/`

- treated as adjacent product/services scope
- excluded from the initial core SaaS production promise

## Phase 0 Decision Freeze

The following Phase 0 launch-boundary decisions are now frozen:

1. compliance and reporting stay limited to the baseline evidence and reporting subset backed by the current deployed path
2. endpoint coverage is an in-scope guided coverage path, not a claim of full EDR/XDR depth
3. AI Shield remains a controlled add-on only for the default launch package
4. partner / MSP motion remains qualified sales-assisted scope only

## Remaining Follow-On Decisions

These still require later remediation work, but they do not reopen the frozen Phase 0 boundary above:

1. which exact AI Shield provider paths graduate from controlled add-on to hardened production support
2. whether any IAM advanced workflows should be beta-gated
3. whether `SentinelGridPostureAgent/frontend/` is folded in, hidden, or retained only as an internal subsystem surface

## Exit Criteria For Phase 0

Phase 0 launch-scope work is complete when:

- this launch scope is treated as canonical in planning and delivery
- no team is building launch-critical user-facing work outside `frontend/`
- GTM language aligns to the narrowed scope
- all out-of-scope areas are either documented, gated, or explicitly excluded from the production promise
