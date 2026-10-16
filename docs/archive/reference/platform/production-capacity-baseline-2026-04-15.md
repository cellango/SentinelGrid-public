# SentinelGrid Production Capacity Baseline

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 15, 2026  
**Status:** Phase 4 launch baseline

## Purpose

Define the initial production sizing, scale triggers, patch windows, and ownership expectations for the approved launch boundary.

This is a starting baseline, not a claim that capacity tuning is finished.

## Baseline Launch Footprint

### Customer-facing / core release services

- `frontend`: 2 replicas, HPA enabled, CPU target 70%
- `api-gateway`: 1 replica minimum, 3 max via HPA, CPU target 70%
- `iam-agent`: 1 replica minimum, 3 max via HPA, CPU target 70%
- `model-gateway`: 1 replica baseline, KEDA enabled, scale-to-zero allowed, max 3
- `orchestrator`: 1 replica baseline
- `siem-agent`: 1 replica baseline, KEDA enabled, max 2

### Internal monitored dependency

- `ingestion-service`: internal pipeline service; monitor queue depth and embeddings pressure even where it is not part of the initial six-service Helm release workflow

## Current Resource Baseline

### From launch Helm values

- `api-gateway`: `100m/256Mi` request, `500m/512Mi` limit
- `iam-agent`: `100m/256Mi` request, `500m/512Mi` limit
- `model-gateway`: `250m/512Mi` request, `1000m/1Gi` limit
- `orchestrator`: `150m/256Mi` request, `750m/768Mi` limit
- `siem-agent`: `200m/512Mi` request, `750m/1Gi` limit

## Capacity Watchpoints

Escalate capacity review if any of these stay true for more than one business day:

- `api-gateway` or `iam-agent` HPA remains at max replicas during normal business traffic
- `ingestion_pending_events` remains above `500`
- `scanner_jobs_last{status="queued"}` grows while `scanner_jobs_last{status="running"}` stays flat
- `source_health_component_up` drops for `opensearch`, `siem_agent`, or `ingestion_service`
- `model-gateway` repeatedly cold-starts during normal customer workflows

## Patch Windows

### Critical security fixes

- Target rollout within 24 hours of approval
- Examples: actively exploited auth, tenant isolation, TLS trust, secrets, or remote-code issues

### High severity platform patches

- Target rollout within 7 calendar days
- Examples: base-image CVEs, critical package updates without active exploitation evidence, Keycloak / Postgres / OpenSearch security patches

### Standard maintenance window

- Weekly scheduled patch window for dependency refresh, non-breaking runtime updates, and observability stack maintenance

## Ownership Baseline

- Platform / DevOps owner: deployment workflow, cluster policy, backups, restore drills, patch cadence
- Security owner: security patch prioritization, auth / trust-boundary review, production alert review
- Application owner: readiness contracts, runbooks, rollback safety, on-call fix ownership for service regressions

Use `docs/PRODUCTION_OWNER_MATRIX_2026-04-15.md` for named owners. This file defines the operational baseline, not the people table.

## Evidence Required Before Raising Scale Limits

- 7-day CPU and memory history
- queue or backlog history for the affected service
- request/error trend for the affected workflow
- reason the current HPA / KEDA policy is insufficient
- rollback plan if the scaling change regresses cost or stability

## Residual Risks

- `model-gateway` and `siem-agent` are still relatively small-footprint defaults and may need rapid tuning under real load.
- `ingestion-service` is monitored, but deployment automation is still narrower than the full internal pipeline surface.
- Capacity assumptions should be re-ratified after the first production dry run and again after the first 30 days of customer traffic.
