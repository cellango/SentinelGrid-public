#!/usr/bin/env bash
set -euo pipefail

# Simple smoke check: fail if any ingested docs carry the _ingest_failure tag.
# Usage: OPENSEARCH_URL=http://localhost:9200 TENANT_ID=<uuid> ./check_ingest_failures.sh

OS_URL="${OPENSEARCH_URL:-http://localhost:9200}"
OS_USER="${OPENSEARCH_USERNAME:-}"
OS_PASS="${OPENSEARCH_PASSWORD:-}"
TENANT_ID="${TENANT_ID:-c6d82f67-36f1-4c7e-af66-d1333e45cde7}"

auth_opts=()
if [[ -n "$OS_USER" && -n "$OS_PASS" ]]; then
  auth_opts=(-u "$OS_USER:$OS_PASS")
fi
use_auth=0
if [[ ${#auth_opts[@]} -gt 0 ]]; then
  use_auth=1
fi

sources=(cloudtrail net dns waf alerts)
failed=0

for src in "${sources[@]}"; do
  idx="${TENANT_ID}-${src}"
  echo "Checking ${idx} for _ingest_failure tags..."
  if [[ $use_auth -eq 1 ]]; then
    resp=$(curl -sS "${auth_opts[@]}" \
      -H 'Content-Type: application/json' \
      -X GET "${OS_URL}/${idx}/_search" \
      -d '{"size":0,"query":{"term":{"tags":"_ingest_failure"}}}')
  else
    resp=$(curl -sS \
      -H 'Content-Type: application/json' \
      -X GET "${OS_URL}/${idx}/_search" \
      -d '{"size":0,"query":{"term":{"tags":"_ingest_failure"}}}')
  fi
  count=$(echo "$resp" | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('hits',{}).get('total',{}).get('value',0))")
  echo "  failures: ${count}"
  if [[ "${count:-0}" -gt 0 ]]; then
    failed=1
  fi
done

if [[ $failed -ne 0 ]]; then
  echo "❌ Ingest smoke check failed: one or more indices contain _ingest_failure docs."
  exit 1
fi

echo "✅ Ingest smoke check passed: no _ingest_failure tags found."
