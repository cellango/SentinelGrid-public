# Multi-Tenancy Audit Implementation Backlog

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Status:** Draft  
**Date:** 2026-03-28  
**Audience:** Engineering, Security, Compliance, Platform  
**Related:**
- [MULTI_TENANCY_AUDIT_READINESS_PLAN.md](../README.md#retired-references)
- [MULTI_TENANCY_AUDIT_EXECUTION_SPEC.md](multi-tenancy-audit-execution-spec.md)
- [MULTI_TENANCY_REMEDIATION_STATUS.md](multi-tenancy-remediation-status.md)

## Purpose

This backlog turns the audit execution spec into deliverable work.

It is intentionally implementation-oriented:

- work item IDs
- tranche sequencing
- owners
- dependencies
- acceptance criteria
- recommended first sprint scope

## Delivery Goal

Deliver a repeatable, script-driven multi-tenancy audit pack that can be executed on demand and produce an auditor-ready evidence bundle tied to a specific git revision and environment.

## Workstream Summary

| Workstream | Goal | Primary Owner |
|---|---|---|
| Foundation | Create script/runbook/artifact scaffolding and manifest contract | Platform Engineering |
| Control Inventory | Export route, service, exception, and shared-data control inventories | Security Engineering + Service Owners |
| RLS Verification | Prove DB coverage and runtime tenant session usage | Platform Engineering + Database |
| Negative Test Pack | Run repeatable two-tenant denial tests | QA / Test Engineering + Service Owners |
| Evidence Collection | Preserve logs and structured artifacts | Security Engineering + Platform |
| Binder Packaging | Assemble final package for audit use | Platform Engineering + Compliance |
| CI / Operations | Run nightly and on-demand with artifact retention | Platform Engineering |

## Tranche Sequence

### Tranche 1: Foundation Scaffold

Build the skeleton first.

Output:

- script directory
- runbook skeleton
- artifact structure
- manifest schema
- main orchestrator shell

### Tranche 2: Inventory and Registers

Build the static evidence producers.

Output:

- control matrix export
- exception register export
- shared/global data register

### Tranche 3: RLS Verification

Build the DB and runtime verification layer.

Output:

- RLS coverage report
- runtime session-usage report

### Tranche 4: Two-Tenant Negative Suite

Build the evidence-grade negative suite and fixture strategy.

Output:

- tenant pair fixture
- scenario matrix
- runner script

### Tranche 5: Evidence Collection and Binder

Build log collection and final packaging.

Output:

- blocked-violation evidence collector
- binder packager
- checksums and manifest finalization

### Tranche 6: CI and Operationalization

Wire scheduled and on-demand execution.

Output:

- CI workflow entry
- artifact upload
- retention policy
- operator handoff documentation

## Immediate Recommended Sprint Scope

The first sprint should stop at the foundation boundary. Do not start with broad negative tests before the pack has a stable structure.

### Sprint 1 target items

- `MT-AUD-001`
- `MT-AUD-002`
- `MT-AUD-003`
- `MT-AUD-004`
- `MT-AUD-005`
- `MT-AUD-006`

### Sprint 1 completion criteria

- one entry-point command exists
- artifact directory creation works
- manifest file is produced
- runbook skeleton exists
- execution profiles are defined
- command logging is standardized

## Backlog

## Tranche 1: Foundation Scaffold

### `MT-AUD-001` Create audit pack directory scaffold

**Owner:** Platform Engineering  
**Priority:** P0  
**Dependencies:** None

**Scope**

- create `scripts/audit/multi-tenancy/`
- create `scripts/audit/multi-tenancy/lib/`
- create `scripts/audit/multi-tenancy/config/`
- create `scripts/audit/multi-tenancy/config/profiles/`
- create `scripts/audit/multi-tenancy/fixtures/`

**Deliverables**

- empty script files or placeholders per spec
- `README.md` in the script directory

**Acceptance Criteria**

- directory structure matches the execution spec
- all referenced script paths exist
- directory naming is final and documented

### `MT-AUD-002` Define manifest schema and status contract

**Owner:** Platform Engineering  
**Priority:** P0  
**Dependencies:** `MT-AUD-001`

**Scope**

- define `manifest.json` schema
- define step status vocabulary
- define run-level status vocabulary
- define required fields vs optional fields

**Deliverables**

- manifest schema document or schema file
- example `manifest.json`

**Acceptance Criteria**

- every script can write a step result compatible with the schema
- schema includes git SHA, environment, run ID, tenant pair, profile, step results
- schema versioning strategy is documented

### `MT-AUD-003` Implement artifact directory and logging conventions

**Owner:** Platform Engineering  
**Priority:** P0  
**Dependencies:** `MT-AUD-001`, `MT-AUD-002`

**Scope**

- standard artifact root path
- run ID format
- `commands.log` behavior
- summary file naming
- per-step output directories

**Deliverables**

- artifact path convention
- helper shell functions for creating artifact directories
- logging conventions in `common.sh` / `logging.sh`

**Acceptance Criteria**

- every run creates a self-contained artifact tree
- repeated runs do not overwrite each other by default
- command execution is recorded consistently

### `MT-AUD-004` Build `run-full-audit.sh` orchestrator skeleton

**Owner:** Platform Engineering  
**Priority:** P0  
**Dependencies:** `MT-AUD-001`, `MT-AUD-002`, `MT-AUD-003`

**Scope**

- parse profile and environment flags
- create artifact directory
- initialize manifest
- call placeholder step scripts in the correct order
- stop on failure by default

**Deliverables**

- `run-full-audit.sh`

**Acceptance Criteria**

- script supports `--profile` and `--env`
- script writes an initial manifest and final status
- script prints final artifact path

### `MT-AUD-005` Create profile configuration model

**Owner:** Platform Engineering  
**Priority:** P0  
**Dependencies:** `MT-AUD-001`

**Scope**

- define `smoke`, `standard`, `full` profiles
- define environment variable loading order
- define environment override model

**Deliverables**

- `config/audit-pack.env.example`
- `config/profiles/smoke.env`
- `config/profiles/standard.env`
- `config/profiles/full.env`

**Acceptance Criteria**

- profile files are sufficient to drive the orchestrator
- no live secrets are committed
- the runbook can explain profile behavior without ambiguity

### `MT-AUD-006` Create runbook skeleton

**Owner:** Compliance + Platform Engineering  
**Priority:** P0  
**Dependencies:** `MT-AUD-002`, `MT-AUD-004`, `MT-AUD-005`

**Scope**

- create the operator-facing runbook
- define prerequisites, commands, expected outputs, troubleshooting headings

**Deliverables**

- `docs/archive/operations/multi-tenancy-audit-execution.md`

**Acceptance Criteria**

- a new engineer can understand how the pack is meant to run
- the runbook matches the script names and paths in the spec
- the runbook has sections for prerequisites, execution, interpretation, and troubleshooting

## Tranche 2: Inventory and Registers

### `MT-AUD-007` Implement control inventory exporter

**Owner:** Security Engineering  
**Priority:** P0  
**Dependencies:** `MT-AUD-004`

**Scope**

- export public routes
- export internal routes
- annotate tenant source and override inputs

**Deliverables**

- `verify-tenant-control-inventory.py`
- `control-matrix.json`
- `control-matrix.csv`

**Acceptance Criteria**

- exporter runs deterministically
- route inventory can be regenerated without manual editing
- outputs map cleanly to the control matrix template

### `MT-AUD-008` Create shared/global data register

**Owner:** Security Engineering + Service Owners  
**Priority:** P0  
**Dependencies:** `MT-AUD-007`

**Scope**

- enumerate `tenant_id IS NULL` and similar patterns
- classify each as allowed shared, system-only, admin-only, or prohibited

**Deliverables**

- `shared-data-register.json`
- `shared-data-register.md`

**Acceptance Criteria**

- every known shared/global dataset is classified
- each entry has an owner and justification

### `MT-AUD-009` Create approved exception register

**Owner:** Security Engineering + Compliance  
**Priority:** P0  
**Dependencies:** `MT-AUD-007`, `MT-AUD-008`

**Scope**

- document temporary or structural exceptions
- include expiry/review dates

**Deliverables**

- `approved-exceptions.json`
- `approved-exceptions.md`

**Acceptance Criteria**

- every exception has an owner
- every exception has a review cadence
- unresolved exceptions are visible in the summary output

## Tranche 3: RLS Verification

### `MT-AUD-010` Implement RLS coverage exporter

**Owner:** Platform Engineering + Database  
**Priority:** P0  
**Dependencies:** `MT-AUD-004`

**Scope**

- enumerate tenant-bearing tables
- enumerate RLS-enabled tables
- enumerate policies and force-RLS status

**Deliverables**

- `verify-rls-coverage.py`
- `rls-tables.json`
- `rls-policies.json`
- `rls-summary.md`

**Acceptance Criteria**

- script can distinguish protected vs unprotected tables
- output is machine-readable and human-readable

### `MT-AUD-011` Implement runtime tenant-session usage review

**Owner:** Platform Engineering  
**Priority:** P0  
**Dependencies:** `MT-AUD-010`

**Scope**

- identify routes using tenant-scoped DB sessions
- identify routes still using plain DB sessions for tenant-scoped access

**Deliverables**

- `runtime-session-usage.json`
- section in `rls-summary.md`

**Acceptance Criteria**

- report highlights mismatch between schema RLS and runtime DB usage
- output can be used as an audit risk register input

## Tranche 4: Two-Tenant Negative Suite

### `MT-AUD-012` Define audit tenant pair fixture strategy

**Owner:** QA / Test Engineering + Platform  
**Priority:** P0  
**Dependencies:** `MT-AUD-005`

**Scope**

- define canonical audit tenants
- define fixture file shape
- define seeded resources required for negative tests

**Deliverables**

- `tenant-pair.example.json`
- tenant fixture documentation

**Acceptance Criteria**

- fixture strategy is deterministic
- pack fails if fixtures are missing or ambiguous

### `MT-AUD-013` Build P0 scenario matrix

**Owner:** QA / Test Engineering + Security Engineering  
**Priority:** P0  
**Dependencies:** `MT-AUD-012`

**Scope**

- define negative scenarios for auth, onboarding, alerts, incidents, ticketing, ingestion, IAM, AI/RAG

**Deliverables**

- `scenario-matrix.csv`
- `scenario-matrix.md`

**Acceptance Criteria**

- every P0 domain has at least one list-path and one direct-resource negative test
- each scenario maps to expected bounded behavior

### `MT-AUD-014` Implement two-tenant negative suite runner

**Owner:** QA / Test Engineering  
**Priority:** P0  
**Dependencies:** `MT-AUD-012`, `MT-AUD-013`, `MT-AUD-004`

**Scope**

- run the scenario matrix
- emit JUnit and summary JSON

**Deliverables**

- `run-two-tenant-negative-suite.sh`
- `junit.xml`
- `summary.json`

**Acceptance Criteria**

- runner supports profile-aware subsets
- outputs are stable and machine-readable

## Tranche 5: Evidence Collection and Binder

### `MT-AUD-015` Implement blocked-violation log collector

**Owner:** Security Engineering  
**Priority:** P1  
**Dependencies:** `MT-AUD-014`

**Scope**

- collect relevant blocked-attempt logs
- redact secrets

**Deliverables**

- `collect-blocked-violation-evidence.sh`
- `blocked-violations.log`
- `blocked-violations.json`

**Acceptance Criteria**

- logs cover only the relevant time window
- artifacts are safe to share internally with auditors

### `MT-AUD-016` Implement binder packager

**Owner:** Platform Engineering + Compliance  
**Priority:** P1  
**Dependencies:** `MT-AUD-007`, `MT-AUD-010`, `MT-AUD-014`, `MT-AUD-015`

**Scope**

- assemble final evidence package
- write final summary
- compute checksums

**Deliverables**

- `package-audit-binder.py`
- `summary.md`
- packaged binder output

**Acceptance Criteria**

- package contains all required sections
- package is usable without manual reconstruction

## Tranche 6: CI and Operationalization

### `MT-AUD-017` Add scheduled CI execution

**Owner:** Platform Engineering  
**Priority:** P1  
**Dependencies:** `MT-AUD-016`

**Scope**

- create nightly or weekly audit run workflow
- upload artifacts

**Deliverables**

- CI workflow config
- artifact retention settings

**Acceptance Criteria**

- scheduled run completes in target environment
- artifacts are retained and downloadable

### `MT-AUD-018` Add manual audit workflow dispatch

**Owner:** Platform Engineering  
**Priority:** P1  
**Dependencies:** `MT-AUD-016`

**Scope**

- enable operator-triggered audit pack run

**Deliverables**

- manual dispatch workflow entry

**Acceptance Criteria**

- operator can choose environment and profile
- resulting artifact bundle is preserved

### `MT-AUD-019` Finalize runbook and handoff procedure

**Owner:** Compliance + Platform + Security  
**Priority:** P1  
**Dependencies:** `MT-AUD-017`, `MT-AUD-018`

**Scope**

- finish runbook
- define who runs the pack
- define how evidence is handed to auditors

**Deliverables**

- final runbook
- evidence handoff checklist

**Acceptance Criteria**

- non-author engineer can run from the runbook
- compliance accepts the handoff flow

## Suggested Ownership Map

| Area | Recommended Owner |
|---|---|
| Script orchestration | Platform Engineering |
| Manifest schema | Platform Engineering |
| Control matrix export | Security Engineering |
| Shared/global register | Security Engineering + Service Owners |
| RLS verification | Platform Engineering + Database |
| Scenario matrix | QA / Test Engineering + Security |
| Log collection | Security Engineering |
| Binder packaging | Platform Engineering + Compliance |
| Runbook | Compliance + Platform |

## Risk Notes

- Do not start with full CI integration before the local pack contract is stable.
- Do not rely on ad hoc customer tenants for evidence generation.
- Do not let the binder depend on one engineer's shell history or local notes.
- Do not mark the pack complete until the manifest and artifact contract are stable.

## Definition Of Done

This backlog is complete only when:

- the execution pack exists at the paths defined in the spec
- the runbook is sufficient for a new engineer
- the artifact bundle is reproducible
- scheduled and manual runs are available
- compliance can use the bundle without manual reconstruction
