#!/usr/bin/env bash
# Load a small GuardDuty-like sample into OpenSearch with guardduty pipeline.
set -euo pipefail

OS_URL="${OPENSEARCH_URL:-http://localhost:9200}"
INDEX="${OPENSEARCH_INDEX:-sg-demo-guardduty}"
PIPELINE="${GUARDDUTY_PIPELINE:-pipeline-guardduty}"

read -r -d '' DOC <<'JSON'
{ "index": { "_index": "sg-demo-guardduty" } }
{ "@timestamp": "2025-12-17T00:00:00Z", "service": { "eventLastSeen": "2025-12-17T00:00:00Z", "detectorId": "det-123", "action": { "actionType": "NETWORK_CONNECTION", "networkConnectionAction": { "remoteIpDetails": { "ipAddressV4": "203.0.113.50" }, "remotePortDetails": { "port": 22 }, "remoteConnectionDetails": { "protocol": "TCP" }, "localPortDetails": { "port": 22 } } }, "additionalInfo": { "threatListName": "Blocklist" }, "count": 1 }, "severity": 8, "region": "us-east-1", "title": "Recon:EC2/PortProbe", "type": "Recon:EC2/PortProbe", "resource": { "instanceDetails": { "instanceId": "i-0123456789abcdef0" } }, "sg": { "tenant_id": "demo" } }
JSON

echo "$DOC" | curl -sS -XPOST "${OS_URL}/_bulk?pipeline=${PIPELINE}" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @-
echo ""
