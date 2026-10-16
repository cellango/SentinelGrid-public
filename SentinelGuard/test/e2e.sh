#!/usr/bin/env bash
set -euo pipefail

# End-to-end smoke: bring up the SentinelGuard compose stack, ingest a sample batch,
# verify OpenSearch stores it, and ensure the embedding stub is reachable.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT}/deploy/docker-compose.yml"

info() { printf '==> %s\n' "$*"; }
section() { printf '\n--- %s ---\n' "$*"; }

cleanup() {
  info "Tearing down compose stack"
  docker compose -f "$COMPOSE_FILE" down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT

info "Building and starting stack"
docker compose -f "$COMPOSE_FILE" up -d --build

info "Waiting for OpenSearch to become healthy"
for i in {1..30}; do
  if curl -sf "http://localhost:19200/_cluster/health?wait_for_status=yellow&timeout=1s" >/dev/null; then
    break
  fi
  sleep 2
  if [[ $i -eq 30 ]]; then
    echo "OpenSearch did not become healthy in time" >&2
    exit 1
  fi
done

info "Pinging embedding stub"
curl -sf "http://localhost:18081/health" >/dev/null || curl -sf "http://localhost:18081" >/dev/null

info "Posting sample ingest batch"
PAYLOAD=$(cat <<'JSON'
{
  "tenant_id": "tenant-123",
  "agent_id": "agent-abc",
  "events": [
    {
      "@timestamp": "2024-01-01T00:00:00Z",
      "event": {"type": ["alert"], "category": ["malware"], "severity": 5},
      "host": {"id": "host-xyz"},
      "rule": {"id": "r1", "name": "test alert"}
    }
  ]
}
JSON
)

section "Payload"
echo "$PAYLOAD" | python -m json.tool || echo "$PAYLOAD"

STATUS=$(echo "$PAYLOAD" | curl -s -o /tmp/ingest_resp.json -w "%{http_code}" \
  -H "Content-Type: application/json" \
  -X POST "http://localhost:8085/ingest" -d @-)
section "Ingest response"
printf "HTTP %s\n" "$STATUS"
cat /tmp/ingest_resp.json || true
if [[ "$STATUS" != "202" ]]; then
  echo "Ingest failed with status $STATUS" >&2
  cat /tmp/ingest_resp.json >&2 || true
  exit 1
fi

info "Verifying document landed in OpenSearch"
curl -sf -XPOST "http://localhost:19200/sentinelguard-events/_refresh" >/dev/null || true
COUNT=$(curl -sf "http://localhost:19200/sentinelguard-events/_count?q=organization.id:tenant-123%20AND%20agent.id:agent-abc" \
  | python -c "import sys,json; print(json.load(sys.stdin).get('count', 0))")
section "Count in OpenSearch"
echo "$COUNT"
if [[ "${COUNT:-0}" -lt 1 ]]; then
  echo "Expected at least 1 document in OpenSearch; got $COUNT" >&2
  exit 1
fi

section "Sample stored document"
curl -sf "http://localhost:19200/sentinelguard-events/_search?q=organization.id:tenant-123%20AND%20agent.id:agent-abc&size=1&pretty=true" || true

info "E2E ingest succeeded (count=${COUNT})"
