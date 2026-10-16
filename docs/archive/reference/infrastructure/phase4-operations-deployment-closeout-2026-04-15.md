# Phase 4 Operations And Deployment Closeout

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 15, 2026  
**Status:** Complete for the approved launch boundary

## What Phase 4 Needed To Prove

Phase 4 was not about another feature sprint. It needed to prove SentinelGrid can be operated, released, observed, and recovered as a production system.

That required:

- request tracing and log correlation
- readiness and dependency-aware health contracts
- alertable runtime metrics
- backup and restore procedures
- migration and release discipline
- deploy automation for the real launch surface
- support and incident-response runbooks

## Code And Workflow Outcomes

### Runtime observability

The launch-scope services now expose the same core production contract:

- `api-gateway`
- `iam-agent`
- `orchestrator`
- `ingestion-service`
- `model-gateway`
- `siem-agent`

That contract includes:

- request and correlation IDs
- `/health`
- `/ready`
- `/metrics`
- `/metrics/prometheus`

The last two launch-path gaps closed in this pass were:

- `backend/services/model_gateway/app/main.py`
- `backend/agents/siem_agent/app/main.py`

This pass also tightened SIEM token-validation request context in:

- `backend/agents/siem_agent/app/core/security.py`

The repo-local observability stack is now wired to that contract instead of assuming JSON metrics are Prometheus-safe. Key files:

- `observability/prometheus.yml`
- `observability/alerts/launch-scope-alerts.yml`
- `observability/grafana/dashboards/sentinelgrid-launch-operations.json`
- `docker-compose.observability.yml`

### Release automation

The placeholder release workflow has been replaced with a real launch-scope workflow:

- `.github/workflows/build-push-deploy.yml`

It now:

- lints schema-only migrations
- builds and pushes shared base images
- builds and pushes the six launch-scope service images
- deploys those services through Helm to EKS
- waits for rollout success per service

### Supply-chain evidence

A supply-chain evidence workflow now exists:

- `.github/workflows/supply-chain-evidence.yml`

It adds:

- dependency review on PRs
- frontend `npm audit` artifact generation
- Python `pip-audit` artifact generation for launch-scope requirement sets
- repository SBOM generation
- filesystem vulnerability scan artifact generation

### Helm deploy contract

The reusable chart now supports probes, and launch-scope values files now encode readiness/liveness behavior. This closes the gap between service readiness endpoints and Kubernetes rollout behavior.

Key files:

- `charts/common-service/templates/deployment.yaml`
- `charts/common-service/values.yaml`
- `charts/values/*.yaml`

## Runbook Outcomes

The missing Phase 4 operational pack now exists in `docs/runbooks/`:

- `production_release_and_deploy.md`
- `database_migrations_and_bootstrap.md`
- `backup_restore_and_dr.md`
- `monitoring_and_alerting.md`
- `production_support_and_incident_response.md`

These are tied to repo-native scripts and workflows rather than generic guidance.

The missing topology and capacity baseline docs now also exist:

- `docs/archive/reference/platform/production-operations-topology-2026-04-15.md`
- `docs/archive/reference/platform/production-capacity-baseline-2026-04-15.md`

## Security-Relevant Outcome

The backup and restore tooling no longer has to depend only on password-based Keycloak admin auth. The operational scripts now support a service-account credential path:

- `infra/shared/scripts/backup-keycloak.sh`
- `infra/shared/scripts/restore-system.sh`

Break-glass username/password auth still exists for emergency use, but the preferred operational path is now client-credentials based.

## Remaining Non-Blocking Debt

- The repo still contains a second historical SIEM tree under `backend/services/siem_agent/`.
- Launch deploy and runtime truth are now frozen to `backend/agents/siem_agent/`.
- Consolidating or deleting the historical tree is cleanup work, not a Phase 4 blocker.

## Exit Gate Assessment

Phase 4 exit criteria from the production remediation plan are satisfied for the approved launch boundary:

- deploy evidence exists
- readiness and metrics evidence exists
- backup and restore procedures exist
- migration and release procedures exist
- production dashboards and alert rules exist
- support and incident-response runbooks exist

The next gate is Phase 5: launch readiness, customer activation, and support model rehearsal.
