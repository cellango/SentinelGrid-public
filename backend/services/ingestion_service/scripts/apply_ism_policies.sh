#!/usr/bin/env bash
set -euo pipefail

# Apply ISM policies for ingest indices and (optionally) attach to existing indices.
# Usage: OPENSEARCH_URL=http://localhost:9200 OPENSEARCH_USERNAME=... OPENSEARCH_PASSWORD=... ./apply_ism_policies.sh

OS_URL="${OPENSEARCH_URL:-http://localhost:9200}"
OS_USER="${OPENSEARCH_USERNAME:-}"
OS_PASS="${OPENSEARCH_PASSWORD:-}"

auth_opts=()
if [[ -n "$OS_USER" && -n "$OS_PASS" ]]; then
  auth_opts=(-u "$OS_USER:$OS_PASS")
fi
use_auth=0
if [[ ${#auth_opts[@]} -gt 0 ]]; then
  use_auth=1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POLICY_DIR="${SCRIPT_DIR}/../ism"

put_policy() {
  local policy_id="$1"
  local file="$2"
  echo "Applying ISM policy ${policy_id} from ${file}"
  if [[ $use_auth -eq 1 ]]; then
    curl -sS -X PUT "${OS_URL}/_plugins/_ism/policies/${policy_id}" \
      "${auth_opts[@]}" \
      -H 'Content-Type: application/json' \
      --data-binary @"${file}"
  else
    curl -sS -X PUT "${OS_URL}/_plugins/_ism/policies/${policy_id}" \
      -H 'Content-Type: application/json' \
      --data-binary @"${file}"
  fi
  echo ""
}

put_policy "sg-ism-cloudtrail" "${POLICY_DIR}/cloudtrail_policy.json"
put_policy "sg-ism-net" "${POLICY_DIR}/net_policy.json"
put_policy "sg-ism-dns" "${POLICY_DIR}/dns_policy.json"
put_policy "sg-ism-waf" "${POLICY_DIR}/waf_policy.json"
put_policy "sg-ism-alerts" "${POLICY_DIR}/alerts_policy.json"

echo "Done. Note: new indices pick up policies via templates. Attach to existing indices with:"
echo "  curl -X POST ${OS_URL}/_plugins/_ism/add/<index> -H 'Content-Type: application/json' -d '{\"policy_id\":\"sg-ism-<source>\"}'"
