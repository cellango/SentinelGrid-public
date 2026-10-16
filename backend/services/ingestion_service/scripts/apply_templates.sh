#!/usr/bin/env bash
set -euo pipefail

# Simple helper to apply index templates to OpenSearch

OS_URL="${OPENSEARCH_URL:-http://localhost:9200}"
OS_USER="${OPENSEARCH_USERNAME:-}"
OS_PASS="${OPENSEARCH_PASSWORD:-}"

auth_opts=()
if [[ -n "$OS_USER" && -n "$OS_PASS" ]]; then
  auth_opts=(-u "$OS_USER:$OS_PASS")
fi

apply_template() {
  local name="$1"
  local file="$2"
  echo "Applying template ${name} from ${file}"
  curl -sS -X PUT "${OS_URL}/_index_template/${name}" \
    -H 'Content-Type: application/json' \
    ${auth_opts+"${auth_opts[@]}"} \
    --data-binary "@${file}"
  echo ""
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="${SCRIPT_DIR}/../templates"

apply_template "template-cloudtrail" "${TEMPLATE_DIR}/cloudtrail.json"
apply_template "template-net" "${TEMPLATE_DIR}/net.json"
apply_template "template-dns" "${TEMPLATE_DIR}/dns.json"
apply_template "template-waf" "${TEMPLATE_DIR}/waf.json"
apply_template "template-alerts" "${TEMPLATE_DIR}/alerts.json"
apply_template "template-logs" "${TEMPLATE_DIR}/logs.json"

echo "Done."
