# Phase 6 Slice 6A Closeout: Readiness, Metrics, And Alerting Proof

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 18, 2026  
**Scope:** Narrowed launch-scope readiness probes, runtime metrics, Grafana dashboard coverage, and alert ownership contract  
**Decision:** Closed for the narrowed launch scope  
**Gate impact:** Advances `G-10` with repo-backed observability proof; `G-10` remains open until restore, rollback, and support rehearsals are also closed

## Goal

Make the narrowed launch package operable without guessing:

1. verify `livenessProbe`, `readinessProbe`, and `startupProbe` coverage for all launch services
2. confirm the launch operations metrics and dashboard cover:
   - auth failures
   - token validation failures
   - upstream dependency health
   - queue pressure and queue-adjacent failure signals
3. define explicit alert ownership and escalation routes

## Repo-Backed Changes

### Token validation failures are now emitted as a first-class launch metric

The shared auth helper now increments explicit failure counters when bearer-token validation fails against IAM:

- `backend/libs/sg_core/security.py`

That change distinguishes:

- `invalid_token`
- `iam_agent_unreachable`
- `iam_agent_error`
- `token_validation_error`

It also keeps `auth_failures_total` and `token_validation_success_total` aligned with the same runtime path instead of leaving token validation failure reasons partially invisible.

Focused regression coverage now exists in:

- `backend/services/api_gateway/tests/test_metrics.py`

The tests prove both the in-process counters and the Prometheus text endpoint export the new `token_validation_failures_total` series.

### The launch alert set now covers the required operator failure modes

The narrowed launch alert pack now explicitly covers:

- readiness probe failure
- critical upstream dependency health degradation
- gateway auth-failure spikes
- gateway token-validation failure spikes
- scan failure detection
- ingestion queue backlog

That landed in:

- `observability/alerts/launch-scope-alerts.yml`

Each launch alert now also carries:

- `owner_name: Clement Ellango`
- `owner_role: ...`

That matters because the current operating model is a one-person company. The alert contract now says that explicitly instead of implying a larger on-call structure that does not exist.

### The launch dashboard now shows the signals needed to run the narrowed scope

The canonical launch dashboard now includes or strengthens panels for:

- `auth_failures_total`
- `token_validation_failures_total`
- `dependency_critical_unhealthy`
- `source_health_component_up`
- `scanner_jobs_last`
- `ingestion_pending_events`
- `ingestion_embedding_summaries_total`
- `llm_provider_failures_total`

That landed in:

- `observability/grafana/dashboards/sentinelgrid-launch-operations.json`

The queue panel now reflects both pressure and failure-adjacent behavior, and the dashboard now includes explicit token-validation and critical-dependency panels instead of relying on inference.

### The runbooks now encode the observability contract and a repeatable verifier

Operational proof for this slice is now encoded directly into the repo in:

- `scripts/phase6/verify-launch-scope-observability.sh`
- `docs/archive/operations/monitoring-and-alerting.md`
- `docs/archive/operations/production-release-and-deploy.md`

That work adds:

- a portable verifier for launch-scope Helm probe rendering, Prometheus scrape annotations, alert presence, and dashboard signal coverage
- an explicit launch probe contract in the monitoring runbook
- named launch alert ownership and escalation notes
- a pre-deploy observability gate in the production deploy runbook
- a post-deploy probe verification command for the actual Kubernetes rollout path

## Verification

### Focused API gateway metrics regression

- `pytest backend/services/api_gateway/tests/test_metrics.py -q`
- result: `5 passed`

The only notable output was existing non-blocking deprecation warnings in shared SQLAlchemy, FastAPI event hooks, and Pydantic config patterns.

### Launch-scope observability verifier

- `bash scripts/phase6/verify-launch-scope-observability.sh`
- result: `PASS`

The verifier now confirms:

- all narrowed launch services render with `livenessProbe`, `readinessProbe`, and `startupProbe`
- backend launch services render Prometheus scrape annotations
- `observability/prometheus.yml` contains the required launch scrape jobs
- `observability/alerts/launch-scope-alerts.yml` contains the required launch alerts
- the launch dashboard contains the required metric coverage strings

### Dashboard and alert syntax validation

- `python3 - <<'PY' ... json.loads(...) ... PY`
- result: `dashboard json ok`
- `python3 - <<'PY' ... yaml.safe_load(...) ... PY`
- result: `alerts yaml ok`

## Residuals

- This slice is repo-backed and render-backed. It does not prove live cluster alert delivery, live Grafana rendering, or pager fan-out behavior in a running environment.
- The one-person ownership model is now explicit, but it remains a concentration risk. There is no secondary on-call path yet.
- `G-10` remains open. Backup, restore, rollback, support rehearsal, and final dry-run evidence still need to close `Slice 6B`, `Slice 6C`, and `Slice 6D`.

## Decision

For the narrowed launch scope:

- Phase 6 Slice 6A is closed
- the launch observability contract is explicit enough to operate without guessing at the repo and runbook level
- Phase 6 should continue with `Slice 6B`
