#!/usr/bin/env bash
# Bulk load AI Shield fixture events into OpenSearch.
set -euo pipefail
OS_URL="${OPENSEARCH_URL:-http://localhost:9200}"
FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/aishield_events_bulk.ndjson"

if [[ ! -f "$FILE" ]]; then
  echo "Missing fixture file: $FILE" >&2
  exit 1
fi

curl -sS -XPOST "$OS_URL/_bulk" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @"$FILE"
echo ""
