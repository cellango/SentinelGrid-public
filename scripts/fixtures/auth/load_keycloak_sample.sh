#!/usr/bin/env bash
# Quick helper to load the sample Keycloak auth login-error event into OpenSearch with the keycloak-auth-pipeline.
set -euo pipefail

OS_URL="${OPENSEARCH_URL:-http://localhost:9200}"
INDEX="${OPENSEARCH_INDEX:-sg-demo-auth}"
FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/keycloak_login_error.ndjson"

if [[ ! -f "$FILE" ]]; then
  echo "Sample file not found: $FILE" >&2
  exit 1
fi

curl -sS -XPOST "${OS_URL}/_bulk?pipeline=keycloak-auth-pipeline" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @"$FILE"
echo ""
