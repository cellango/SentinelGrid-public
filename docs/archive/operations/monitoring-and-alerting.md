# Monitoring And Alerting

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Purpose

Turn the Phase 4 health, readiness, tracing, and metrics work into a consistent operator procedure.

## Core Endpoints

### Liveness

- `frontend`: `/`
- `api-gateway`: `/health`
- `iam-agent`: `/health`
- `model-gateway`: `/health`
- `orchestrator`: `/health`
- `siem-agent`: `/health`
- `compliance-service`: `/health`
- `reporting-service`: `/health`

### Readiness

- `api-gateway`: `/ready`
- `iam-agent`: `/ready`
- `model-gateway`: `/ready`
- `orchestrator`: `/ready`
- `siem-agent`: `/ready`
- `ingestion-service`: `/ready`

### Metrics

- `api-gateway`: `/metrics`
- `iam-agent`: `/metrics`
- `model-gateway`: `/metrics`
- `orchestrator`: `/metrics`
- `siem-agent`: `/metrics`
- `ingestion-service`: `/metrics`
- `compliance-service`: `/metrics`
- `reporting-service`: `/metrics`

### Prometheus Scrape Paths

- `api-gateway`: `/metrics/prometheus`
- `iam-agent`: `/metrics/prometheus`
- `model-gateway`: `/metrics/prometheus`
- `orchestrator`: `/metrics/prometheus`
- `siem-agent`: `/metrics/prometheus`
- `ingestion-service`: `/metrics/prometheus`
- `compliance-service`: `/metrics/prometheus`
- `reporting-service`: `/metrics/prometheus`

## Repo-Local Monitoring Assets

- Prometheus config: `observability/prometheus.yml`
- Alert rules: `observability/alerts/launch-scope-alerts.yml`
- Compliance alert rules: `observability/alerts/compliance-production-alerts.yml`
- Launch dashboard: `observability/grafana/dashboards/sentinelgrid-launch-operations.json`
- Legacy overview dashboard: `observability/grafana/dashboards/observability-overview.json`
- Compliance operations runbook: `docs/archive/operations/compliance-operations.md`
- Launch observability verifier: `scripts/phase6/verify-launch-scope-observability.sh`

## Launch Probe Contract

The narrowed launch services must all render and deploy with:

- `livenessProbe`
- `readinessProbe`
- `startupProbe`

For repo-local proof before deployment, run:

```bash
bash scripts/phase6/verify-launch-scope-observability.sh
```

This verifier checks the rendered Helm deployments for:

- `frontend`
- `api-gateway`
- `iam-agent`
- `model-gateway`
- `orchestrator`
- `siem-agent`

It also checks that the launch Prometheus config, alert rules, and launch dashboard still cover the required Slice 6A signal classes.

## Request Tracing

The platform now uses:

- `X-Request-ID`
- `X-Correlation-ID`

Use these to trace one failing request across gateway, IAM, orchestrator, ingestion, model-gateway, and SIEM logs.

## Minimum Alerts

Configure alerts for:

- `SentinelGridServiceReadyProbeFailing`
- `SentinelGridCriticalDependencyUnhealthy`
- `SentinelGridGatewayAuthFailuresSpike`
- `SentinelGridGatewayTokenValidationFailuresSpike`
- `SentinelGridSourceHealthComponentDown`
- `SentinelGridScannerOrchestratorUnavailable`
- `SentinelGridScanFailuresDetected`
- `SentinelGridIngestionQueueBacklogHigh`
- `SentinelGridEmbeddingFailuresDetected`
- `SentinelGridLLMProviderFailures`
- `SentinelGridComplianceEvidenceCollectionFailuresDetected`
- `SentinelGridComplianceReportGenerationFailuresDetected`
- `SentinelGridComplianceStaleEvidenceDetected`

## Required Launch Dashboard Signals

The launch dashboard must visibly cover these signal classes:

| Required signal | Launch dashboard coverage | Primary metric |
| --- | --- | --- |
| auth failures | `Gateway Auth Failures (15m)` | `auth_failures_total` |
| token validation failures | `Gateway Token Validation Failures (15m)` | `token_validation_failures_total` |
| upstream dependency health | `Critical Dependency Health`, `Source Health Components`, `Service Ready Gauge` | `dependency_critical_unhealthy`, `source_health_component_up`, `service_ready` |
| queue failures and queue pressure | `Queue Pressure And Failures`, `Ingestion Pending Events` | `scanner_jobs_last`, `ingestion_embedding_summaries_total`, `ingestion_pending_events` |
| provider degradation that can affect auth-adjacent launch flows | `IAM Provider Failures (15m)` | `llm_provider_failures_total` |
| compliance evidence collection health | compliance operations alert rules and metrics endpoint | `compliance_evidence_collection_total`, `compliance_evidence_collection_tasks_total` |
| compliance evidence freshness | compliance operations alert rules and metrics endpoint | `compliance_stale_evidence_items` |
| compliance report generation health | compliance operations alert rules and metrics endpoint | `compliance_report_generation_failures_total` |

## Manual Triage Commands

Examples:

```bash
curl -fsS https://api.example.com/ready | jq
curl -fsS https://auth.example.com/ready | jq
curl -fsS http://api-gateway.internal:8000/metrics | jq '.counters.auth_failures_total'
curl -fsS http://api-gateway.internal:8000/metrics | jq '.counters.token_validation_failures_total'
curl -fsS http://api-gateway.internal:8000/metrics | jq '.gauges.source_health_component_up'
curl -fsS http://api-gateway.internal:8000/metrics/prometheus | rg 'dependency_critical_unhealthy|token_validation_failures_total'
curl -fsS http://siem-agent.internal:8000/metrics | jq
curl -fsS http://orchestrator.internal:8000/metrics/prometheus
curl -fsS http://compliance-service.internal:8000/metrics | jq '.counters.compliance_evidence_collection_tasks_total'
curl -fsS http://compliance-service.internal:8000/metrics/prometheus | rg 'compliance_evidence|compliance_stale|compliance_agent'
curl -fsS http://reporting-service.internal:8000/metrics | jq '.counters.compliance_report_generation_failures_total'
curl -fsS http://reporting-service.internal:8000/metrics/prometheus | rg 'compliance_report_generation'
```

## What To Look For

- `ready: false`
- dependency `status: unhealthy`
- large increases in auth failure counters
- large increases in queue depth or failed scan counters
- degraded source-health gauges for ingestion, SIEM, OpenSearch, Wazuh, or EDR collectors
- readiness probe failures from the `blackbox-ready` job
- evidence collection failures, stale evidence gauges, or report generation failure counters in compliance workflows

## Alert Ownership And Escalation Routes

For the current one-person operating model, `Clement Ellango` is the named owner across the required roles.

| Alert or signal class | Named owner | Primary role | Escalation route |
| --- | --- | --- | --- |
| readiness probe failures and critical dependency health | `Clement Ellango` | `DevOps / Platform Lead` | classify severity, inspect `/ready`, decide rollback or containment, then use `production_support_and_incident_response.md` if customer-facing |
| gateway auth failures and token validation failures | `Clement Ellango` | `IAM / Identity Lead` | inspect gateway metrics, IAM readiness, Keycloak dependency state, then escalate to `Security Lead` if tenant or auth trust is suspected |
| source-health component degradation | `Clement Ellango` | `Platform / Backend Lead` | inspect `/api/v1/siem/source-health`, upstream service readiness, and launch dashboard before customer update |
| scanner backlog or queue failures | `Clement Ellango` | `Platform / Backend Lead` | inspect orchestrator metrics, ingestion metrics, and pause new work if backlog is unbounded |
| provider failures affecting launch workflows | `Clement Ellango` | `IAM / Identity Lead` | inspect IAM provider metrics and downstream impact, escalate to `Security Lead` if auth or tenant trust is implicated |
| compliance evidence, framework, agent, or report degradation | `Clement Ellango` | `Compliance / Platform Lead` | inspect compliance and reporting metrics, then use `compliance_operations.md`; escalate to `Security Lead` for tenant isolation or evidence-integrity concerns |

## Dashboard Expectations

External monitoring should show at minimum:

- service liveness
- service readiness
- rollout status
- 5xx rate on gateway and IAM
- auth failure rate
- scan backlog and failure rate
- ingestion queue depth
- token validation failure rate
- critical upstream dependency health
- source-health component status
- IAM provider failure counts
- compliance evidence collection and freshness
- compliance report generation failures

## Escalation Thresholds

- Suspected tenant isolation issue: immediate Sev-1 escalation
- Login/auth outage: Sev-1 if customer-facing and sustained
- API gateway or IAM unready: Sev-1
- SIEM or ingestion degraded with data loss risk: Sev-1
- Model provider degraded without customer outage: Sev-2
- Compliance evidence integrity, tenant leakage, or audit package contamination: Sev-1
- Compliance report generation degraded for one tenant without data exposure: Sev-2

## Evidence To Save During Incidents

- failing request/correlation ID
- `/ready` payloads before and after mitigation
- affected services and timestamps
- rollback or remediation action taken
- affected tenant ID, framework ID, evidence package ID, report ID, and compliance snapshot hash when relevant
