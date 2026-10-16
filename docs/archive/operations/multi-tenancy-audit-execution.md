# Multi-Tenancy Audit Execution Runbook

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Purpose

This runbook explains how to execute the repeatable multi-tenancy audit pack and where to find the resulting evidence bundle.

Current status:

- foundation scaffold implemented
- scripts create a dated artifact tree and manifest
- control inventory and owner review queue are evidence-producing
- curated two-tenant negative-suite execution is now evidence-producing
- RLS static and live-proof stages are now evidence-producing
- blocked-violation collection is now evidence-producing
- remediation reporting is now evidence-producing
- owner remediation queues are now evidence-producing
- remediation program generation is now evidence-producing

## Entry Point

```bash
scripts/audit/multi-tenancy/run-full-audit.sh --profile standard --env local
```

## Profiles

- `smoke`: minimal local or CI sanity run
- `standard`: routine audit-readiness run
- `full`: formal evidence run

## Prerequisites

- repository checked out locally
- `git`, `bash`, and `python3` installed
- `psql` installed for live database proof
- optional local override file at:
  - `scripts/audit/multi-tenancy/config/audit-pack.env`
- a non-superuser, non-`BYPASSRLS` verifier role for valid live row-visibility proof

## Example Commands

### Smoke

```bash
scripts/audit/multi-tenancy/run-full-audit.sh --profile smoke --env local
```

### Standard

```bash
scripts/audit/multi-tenancy/run-full-audit.sh --profile standard --env staging
```

### Full

```bash
scripts/audit/multi-tenancy/run-full-audit.sh --profile full --env audit
```

### Provision verifier role

```bash
POSTGRES_ADMIN_URL=postgresql://sg:sg@localhost:5432/sg \
AUDIT_RLS_VERIFIER_ROLE=sg_audit_verifier \
AUDIT_RLS_VERIFIER_PASSWORD=sg_audit_verifier \
bash scripts/audit/multi-tenancy/provision-rls-verifier-role.sh
```

### Prepare live RLS inputs automatically

When `POSTGRES_URL` is set, the audit pack can now auto-discover a tenant pair and optionally provision the verifier role before the RLS stage:

```bash
AUDIT_ARTIFACT_DIR=$(mktemp -d) \
POSTGRES_URL=postgresql://sg:sg@localhost:5432/sg \
POSTGRES_ADMIN_URL=postgresql://sg:sg@localhost:5432/sg \
AUDIT_PROVISION_RLS_VERIFIER=true \
bash scripts/audit/multi-tenancy/prepare-live-rls-inputs.sh
```

The step writes:

- `rls-report/live-inputs.json`
- `rls-report/live-inputs.env`

`run-full-audit.sh` now invokes that preparation step automatically before `verify_rls_coverage`.

## Artifact Output

Artifacts are written to:

```text
artifacts/audit/multi-tenancy/<YYYY-MM-DD>/<run-id>/
```

The root contains:

- `manifest.json`
- `summary.md`
- `environment.txt`
- `git-revision.txt`
- `commands.log`

Subdirectories include:

- `control-matrix/`
- `rls-report/`
- `test-results/`
- `logs/`
- `exceptions/`
- `binder/`

## What The Current Scaffold Produces

At this stage, the pack produces:

- a manifest initialized with run metadata
- profile-aware step execution
- fully classified control inventory outputs and review queue
- static RLS table and policy inventory from migrations
- runtime session-usage analysis for route/database scoping
- optional live Postgres RLS proof when `POSTGRES_URL` and tenant pair values are configured
- curated negative-suite evidence from selected service-local tenant-isolation tests
- claim-level blocked-violation evidence linked to test results, logs, and source excerpts
- grouped remediation findings for live catalog drift, sampled cross-tenant exposure, and route-adoption gaps
- owner-specific remediation queues for database and service owners
- a phased remediation program with entry and exit criteria
- final summary and binder metadata

It does not yet produce a complete auditor binder because live RLS proof still requires a reachable Postgres target plus a populated tenant pair.
The tenant pair can now be auto-discovered, but a reachable Postgres target is still required.

## Current Negative-Suite Scope

The negative-suite stage currently runs a curated target manifest from:

```text
scripts/audit/multi-tenancy/config/negative-suite-targets.json
```

The initial scope includes:

- API Gateway alert-scope tenant override protections
- IAM tenant-isolation validator protections
- ingestion batch cross-tenant rejection protections

The resulting artifacts are written under `test-results/`:

- `junit.xml`
- `scenario-matrix.csv`
- `summary.json`
- `target-manifest.json`
- `raw/*.log`
- `raw/*.junit.xml`

## Current Blocked-Violation Evidence Scope

The blocked-violation stage uses the configured claim metadata in:

```text
scripts/audit/multi-tenancy/config/negative-suite-targets.json
```

For each configured claim, it records:

- the audit claim and control identifier
- the mapped testcase and its JUnit status
- the target command, JUnit file, and raw log file
- the exact test-source excerpt used as proof
- a reviewer-facing summary statement

The resulting artifacts are written under `logs/`:

- `blocked-violations.json`
- `blocked-violations.csv`
- `log-collection-summary.md`
- `blocked-violations.log`
- `evidence-excerpts/*.py`

## Current Remediation Scope

The remediation stage reads:

- `rls-report/summary.json`
- `rls-report/live-runtime-verification.json`
- `rls-report/runtime-session-usage.json`
- `control-matrix/review-queue.json`
- `test-results/summary.json`
- `logs/blocked-violations.json`

It then writes:

- `remediation/summary.json`
- `remediation/catalog-drift.json`
- `remediation/cross-tenant-exposure.json`
- `remediation/runtime-adoption-gaps.json`
- `remediation/remediation-report.md`

This stage is designed to answer the immediate auditor and engineering question after a failed `full` run: what failed, how widespread it is, and what should be fixed first.

## Current Owner Queue Scope

The owner queue stage reads:

- `remediation/catalog-drift.json`
- `remediation/cross-tenant-exposure.json`
- `rls-report/runtime-session-usage.json`
- `control-matrix/review-queue.json`

It then writes:

- `remediation/owner-queues/index.json`
- `remediation/owner-queues/index.md`
- `remediation/owner-queues/<owner>.json`
- `remediation/owner-queues/<owner>.md`

This stage is designed to answer the next engineering-management question after a failed run: which owner needs to act, on what queue, and in what order.

## Current Remediation Program Scope

The remediation program stage reads:

- `remediation/summary.json`
- `remediation/owner-queues/index.json`
- `remediation/owner-queues/*.json`

It then writes:

- `remediation/program-summary.json`
- `remediation/remediation-program.md`

This stage is designed to answer the next program-management question after the owner queues exist: what is the execution order, what must be true before each phase starts, and what evidence closes each phase.

## Current Live RLS Scope

When these values are set:

- `POSTGRES_URL`
- `AUDIT_TENANT_A_ID`
- `AUDIT_TENANT_B_ID`
- `AUDIT_RLS_VERIFIER_ROLE` for valid row-visibility proof

the RLS stage also writes:

- `rls-report/live-runtime-verification.json`

That artifact includes:

- live catalog confirmation that expected tables have RLS and `FORCE RLS`
- policy-name comparison against the migration-derived inventory
- candidate table discovery for tables populated by both configured tenants
- actual cross-tenant denial checks under tenant A and tenant B contexts
- no-context bounded visibility checks
- superadmin bypass verification

`full` profile requires this live stage. `smoke` and `standard` record a structured `skipped` result when the live prerequisites are not available.

If the configured connection role is `SUPERUSER` or has `BYPASSRLS`, the live proof is not valid. The verifier now detects that case and requires a non-bypass verifier role.

## How To Read The Manifest

Key fields:

- `run_id`
- `timestamp_utc`
- `git_sha`
- `environment`
- `profile`
- `step_results`
- `overall_status`

## Troubleshooting

### Unknown profile or env

Use only the supported values:

- profiles: `smoke`, `standard`, `full`
- envs: `local`, `staging`, `audit`

### Missing commands

Install:

- `git`
- `bash`
- `python3`
- `psql`

### Missing local overrides

Copy:

```text
scripts/audit/multi-tenancy/config/audit-pack.env.example
```

to:

```text
scripts/audit/multi-tenancy/config/audit-pack.env
```

and fill in local values as needed.

## Next Planned Enhancements

- real prerequisite and environment health checks
- expanded two-tenant negative suite coverage for review-required routes
- auditor-ready binder packaging
- automatic owner-specific remediation exports
