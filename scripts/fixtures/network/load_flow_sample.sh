#!/usr/bin/env bash
# Load a small network/flow sample into OpenSearch with a flow pipeline if present.
set -euo pipefail

OS_URL="${OPENSEARCH_URL:-http://localhost:9200}"
INDEX="${OPENSEARCH_INDEX:-sg-demo-network}"
PIPELINE="${FLOW_PIPELINE:-pipeline-vpcflow}"

read -r -d '' DOC <<'JSON'
{ "index": { "_index": "sg-demo-network" } }
{ "@timestamp": "2025-12-17T00:00:00Z", "src_ip": "10.0.0.10", "dst_ip": "8.8.8.8", "src_port": 49722, "dst_port": 53, "protocol": "udp", "bytes": 1200, "packets": 3, "action": "ACCEPT", "vpc": "demo-vpc", "account_id": "123456789012", "sg": { "tenant_id": "demo" } }
{ "index": { "_index": "sg-demo-network" } }
{ "@timestamp": "2025-12-17T00:00:05Z", "src_ip": "10.0.1.5", "dst_ip": "198.51.100.10", "src_port": 443, "dst_port": 53412, "protocol": "tcp", "bytes": 4500, "packets": 15, "action": "REJECT", "vpc": "demo-vpc", "account_id": "123456789012", "sg": { "tenant_id": "demo" } }
JSON

echo "$DOC" | curl -sS -XPOST "${OS_URL}/_bulk?pipeline=${PIPELINE}" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @-
echo ""
