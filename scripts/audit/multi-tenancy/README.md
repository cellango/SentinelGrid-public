# Multi-Tenancy Audit Pack

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../RELEASE_SCOPE.md) first.


This directory contains the repeatable multi-tenancy audit execution pack.

Current status:

- foundation scaffold implemented
- manifest, profile, artifact, and runbook structure in place
- control inventory now produces a fully classified route matrix
- negative-suite stage now executes curated service-local tenant-isolation evidence targets
- RLS stage now produces static migration coverage, runtime session analysis, and optional live database proof
- blocked-violation collection now packages claim-level denial evidence from the curated negative suite
- remediation reporting now converts failed live audits into grouped owner-ready findings
- owner remediation queues now export service and platform worklists from the same audit run
- remediation program generation now sequences those worklists into execution phases

## Entry Point

```bash
scripts/audit/multi-tenancy/run-full-audit.sh --profile standard --env local
```

## Layout

- `run-full-audit.sh`: orchestrates the full pack
- `prepare-audit-env.sh`: validates prerequisites and records environment metadata
- `verify-tenant-control-inventory.py`: exports the classified route control inventory and review queue
- `verify-rls-coverage.py`: exports schema-level RLS inventory and runtime session-usage analysis
- `verify-rls-coverage.py`: also runs live Postgres RLS proof when tenant IDs and `POSTGRES_URL` are configured
- `run-two-tenant-negative-suite.sh`: launches the curated two-tenant negative-suite runner
- `run-two-tenant-negative-suite.py`: executes evidence targets and writes JUnit, logs, and scenario matrix outputs
- `collect-blocked-violation-evidence.sh`: packages claim-level blocked-violation evidence
- `collect-blocked-violation-evidence.py`: resolves configured audit claims to test results, logs, and test-source excerpts
- `generate-remediation-report.py`: consolidates live catalog drift, sampled cross-tenant exposure, and runtime adoption gaps
- `generate-owner-remediation-queues.py`: exports owner-specific remediation queues for database and service owners
- `generate-remediation-program.py`: turns the findings and owner queues into a phased remediation program
- `provision-rls-verifier-role.sh`: provisions a non-superuser verifier role for valid live RLS proof
- `package-audit-binder.py`: finalizes manifest and summary output
- `lib/`: shared shell helpers
- `config/`: profile and manifest configuration
- `fixtures/`: tenant-pair and expected-service examples

## Profiles

- `smoke`: fast local or CI sanity check
- `standard`: routine audit-readiness pack
- `full`: formal evidence run

## Artifacts

By default, artifacts are written to:

```text
artifacts/audit/multi-tenancy/<YYYY-MM-DD>/<run-id>/
```

The negative-suite stage currently writes:

- `test-results/junit.xml`: aggregate JUnit report across curated evidence targets
- `test-results/scenario-matrix.csv`: per-testcase evidence matrix with owner, service, command, and artifact refs
- `test-results/summary.json`: target-level pass/fail summary
- `test-results/target-manifest.json`: executed target definitions and result metadata
- `test-results/raw/*.log`: per-target command logs
- `test-results/raw/*.junit.xml`: per-target pytest JUnit outputs

The RLS stage currently writes:

- `rls-report/rls-tables.json`: tenant-scoped table inventory from migration sources
- `rls-report/rls-policies.json`: policy inventory from migration sources
- `rls-report/runtime-session-usage.json`: route-level DB session usage and risk classification
- `rls-report/live-runtime-verification.json`: live Postgres RLS proof or structured skip result
- `rls-report/summary.json`: aggregate counts for schema and runtime coverage
- `rls-report/rls-summary.md`: reviewer-ready markdown summary

Important:

- live row-visibility proof must not run as a superuser or `BYPASSRLS` role
- set `AUDIT_RLS_VERIFIER_ROLE` to a non-bypass role for the live proof stage
- use `provision-rls-verifier-role.sh` to create that role when needed

The blocked-violation stage currently writes:

- `logs/blocked-violations.json`: claim-level denial evidence records
- `logs/blocked-violations.csv`: flat export of claim-level evidence
- `logs/log-collection-summary.md`: reviewer-ready blocked-violation summary
- `logs/blocked-violations.log`: simple machine-readable log summary
- `logs/evidence-excerpts/*.py`: extracted test-source assertions used as proof

The remediation stage currently writes:

- `remediation/summary.json`: top-level remediation counts for drift, exposure, and runtime adoption gaps
- `remediation/catalog-drift.json`: grouped live catalog drift by failure class
- `remediation/cross-tenant-exposure.json`: sampled tables that still expose foreign-tenant rows
- `remediation/runtime-adoption-gaps.json`: grouped route-level DB scoping adoption gaps
- `remediation/remediation-report.md`: reviewer-ready remediation narrative and priority order

The owner queue stage currently writes:

- `remediation/owner-queues/index.json`: owner queue manifest
- `remediation/owner-queues/index.md`: owner queue summary for the run
- `remediation/owner-queues/<owner>.json`: machine-readable queue for a service or platform owner
- `remediation/owner-queues/<owner>.md`: reviewer-friendly owner queue summary

The remediation program stage currently writes:

- `remediation/program-summary.json`: machine-readable phased remediation program
- `remediation/remediation-program.md`: reviewer-ready phased remediation plan
