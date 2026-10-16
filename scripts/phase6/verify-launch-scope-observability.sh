#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

SAMPLE_CERTIFICATE_ARN="arn:aws:acm:us-east-1:123456789012:certificate/launch-scope-verifier"

SERVICE_MATRIX=(
  "frontend:charts/values/frontend.yaml"
  "api-gateway:charts/values/api-gateway.yaml"
  "iam-agent:charts/values/iam-agent.yaml"
  "model-gateway:charts/values/model-gateway.yaml"
  "orchestrator:charts/values/orchestrator.yaml"
  "siem-agent:charts/values/siem-agent.yaml"
)

BACKEND_METRIC_SERVICES=(
  "api-gateway"
  "iam-agent"
  "model-gateway"
  "orchestrator"
  "siem-agent"
)

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

require_rg() {
  local pattern="$1"
  local file="$2"
  local error_message="$3"
  if ! rg -q "$pattern" "$file"; then
    fail "$error_message"
  fi
}

echo "Verifying launch-scope probes from rendered Helm manifests..."

for entry in "${SERVICE_MATRIX[@]}"; do
  service="${entry%%:*}"
  values_file="${entry#*:}"
  rendered_file="$TMP_DIR/${service}.yaml"

  helm template "$service" "$REPO_ROOT/charts/common-service" \
    -f "$REPO_ROOT/$values_file" \
    --set "ingress.alb.certificateArn=$SAMPLE_CERTIFICATE_ARN" \
    >"$rendered_file"

  require_rg '^kind: Deployment$' "$rendered_file" "Rendered manifest for $service does not include a Deployment"
  require_rg 'livenessProbe:' "$rendered_file" "$service is missing a livenessProbe in rendered Deployment"
  require_rg 'readinessProbe:' "$rendered_file" "$service is missing a readinessProbe in rendered Deployment"
  require_rg 'startupProbe:' "$rendered_file" "$service is missing a startupProbe in rendered Deployment"

  echo "  OK probes: $service"
done

echo "Verifying backend metrics scrape annotations..."

for service in "${BACKEND_METRIC_SERVICES[@]}"; do
  rendered_file="$TMP_DIR/${service}.yaml"
  require_rg 'prometheus\.io/scrape: "true"' "$rendered_file" "$service is missing prometheus scrape annotation"
  require_rg 'prometheus\.io/path: /metrics/prometheus' "$rendered_file" "$service is missing /metrics/prometheus scrape path"
  echo "  OK metrics scrape: $service"
done

echo "Verifying Prometheus scrape jobs..."

require_rg 'job_name: sentinelgrid-services' "$REPO_ROOT/observability/prometheus.yml" "Prometheus config is missing sentinelgrid-services scrape job"
require_rg 'job_name: blackbox-ready' "$REPO_ROOT/observability/prometheus.yml" "Prometheus config is missing blackbox-ready job"
require_rg 'job_name: blackbox-http' "$REPO_ROOT/observability/prometheus.yml" "Prometheus config is missing blackbox-http job"

echo "Verifying launch alert rules..."

require_rg 'alert: SentinelGridServiceReadyProbeFailing' "$REPO_ROOT/observability/alerts/launch-scope-alerts.yml" "Missing readiness alert rule"
require_rg 'alert: SentinelGridCriticalDependencyUnhealthy' "$REPO_ROOT/observability/alerts/launch-scope-alerts.yml" "Missing critical dependency health alert rule"
require_rg 'alert: SentinelGridGatewayAuthFailuresSpike' "$REPO_ROOT/observability/alerts/launch-scope-alerts.yml" "Missing gateway auth failure alert rule"
require_rg 'alert: SentinelGridGatewayTokenValidationFailuresSpike' "$REPO_ROOT/observability/alerts/launch-scope-alerts.yml" "Missing token validation failure alert rule"
require_rg 'alert: SentinelGridScanFailuresDetected' "$REPO_ROOT/observability/alerts/launch-scope-alerts.yml" "Missing scanner failure alert rule"
require_rg 'alert: SentinelGridIngestionQueueBacklogHigh' "$REPO_ROOT/observability/alerts/launch-scope-alerts.yml" "Missing ingestion backlog alert rule"

echo "Verifying launch dashboard signal coverage..."

require_rg 'auth_failures_total' "$REPO_ROOT/observability/grafana/dashboards/sentinelgrid-launch-operations.json" "Launch dashboard is missing auth failure metric coverage"
require_rg 'token_validation_failures_total' "$REPO_ROOT/observability/grafana/dashboards/sentinelgrid-launch-operations.json" "Launch dashboard is missing token validation failure metric coverage"
require_rg 'dependency_critical_unhealthy|source_health_component_up' "$REPO_ROOT/observability/grafana/dashboards/sentinelgrid-launch-operations.json" "Launch dashboard is missing upstream dependency health coverage"
require_rg 'scanner_jobs_last|ingestion_pending_events|ingestion_embedding_summaries_total' "$REPO_ROOT/observability/grafana/dashboards/sentinelgrid-launch-operations.json" "Launch dashboard is missing queue pressure/failure coverage"

echo "PASS: launch-scope observability contracts are present in Helm, Prometheus, alerts, and dashboard assets."
