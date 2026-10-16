#!/usr/bin/env bash
# Load a small CloudTrail-like sample into OpenSearch with cloudtrail pipeline.
set -euo pipefail

OS_URL="${OPENSEARCH_URL:-http://localhost:9200}"
INDEX="${OPENSEARCH_INDEX:-sg-demo-cloudtrail}"
PIPELINE="${CLOUDTRAIL_PIPELINE:-pipeline-cloudtrail}"

read -r -d '' DOC <<'JSON'
{ "index": { "_index": "sg-demo-cloudtrail" } }
{ "@timestamp": "2025-12-17T00:00:00Z", "eventVersion": "1.08", "userIdentity": { "type": "IAMUser", "userName": "alice", "accessKeyId": "AKIA...demo" }, "eventTime": "2025-12-17T00:00:00Z", "eventSource": "signin.amazonaws.com", "eventName": "ConsoleLogin", "awsRegion": "us-east-1", "sourceIPAddress": "198.51.100.20", "userAgent": "signin.amazonaws.com", "responseElements": { "ConsoleLogin": "Failure" }, "additionalEventData": { "MFAUsed": "No" }, "sg": { "tenant_id": "demo" } }
JSON

echo "$DOC" | curl -sS -XPOST "${OS_URL}/_bulk?pipeline=${PIPELINE}" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @-
echo ""
