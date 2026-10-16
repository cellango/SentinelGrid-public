#!/usr/bin/env bash
set -euo pipefail

# Simple helper to apply ingest pipelines to OpenSearch

OS_URL="${OPENSEARCH_URL:-http://localhost:9200}"
OS_USER="${OPENSEARCH_USERNAME:-}"
OS_PASS="${OPENSEARCH_PASSWORD:-}"

auth_opts=()
if [[ -n "$OS_USER" && -n "$OS_PASS" ]]; then
  auth_opts=(-u "$OS_USER:$OS_PASS")
fi

apply_pipeline() {
  local name="$1"
  local file="$2"
  echo "Applying pipeline ${name} from ${file}"
  curl -sS -X PUT "${OS_URL}/_ingest/pipeline/${name}" \
    -H 'Content-Type: application/json' \
    ${auth_opts+"${auth_opts[@]}"} \
    --data-binary "@${file}"
  echo ""
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINE_DIR="${SCRIPT_DIR}/../pipelines"

apply_pipeline "pipeline-cloudtrail" "${PIPELINE_DIR}/cloudtrail.json"
apply_pipeline "pipeline-vpcflow" "${PIPELINE_DIR}/vpcflow.json"
apply_pipeline "pipeline-dns" "${PIPELINE_DIR}/dns.json"
apply_pipeline "pipeline-waf" "${PIPELINE_DIR}/waf.json"
apply_pipeline "pipeline-guardduty" "${PIPELINE_DIR}/guardduty.json"
apply_pipeline "keycloak-auth-pipeline" "${PIPELINE_DIR}/keycloak-auth.json"

echo "Done."
