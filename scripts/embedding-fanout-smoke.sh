#!/usr/bin/env bash
set -euo pipefail

# Smoke test: ingest one high-severity event and verify embeddings fan-out increments metrics
# Usage: TENANT_ID=<uuid> INGEST_URL=http://localhost:8009 CHECK_DB=true ./scripts/embedding-fanout-smoke.sh

TENANT_ID="${TENANT_ID:-ff1c2b60-1fd6-46d1-8458-b0484f5d58f8}" # demo tenant by default
INGEST_URL="${INGEST_URL:-http://localhost:8009}"
CHECK_DB="${CHECK_DB:-true}"
EVENT_ID="emb-smoke-$(date +%s)"
export TENANT_ID

echo "🔸 Ingesting test event id=${EVENT_ID} tenant=${TENANT_ID}"
EVENT_PAYLOAD=$(cat <<'JSON'
{
  "events": [
    {
      "event_type": "alert",
      "source": "demo_siem",
      "timestamp": "2025-01-01T00:00:00Z",
      "raw_data": {
        "source": "siem_agent",
        "id": "emb-smoke-placeholder",
        "severity": "high",
        "message": "embedding fan-out smoke",
        "host": { "hostname": "smoke-host" }
      }
    }
  ]
}
JSON
)
EVENT_PAYLOAD=${EVENT_PAYLOAD//emb-smoke-placeholder/${EVENT_ID}}
EVENT_PAYLOAD=$(echo "${EVENT_PAYLOAD}" | sed "s/embedding fan-out smoke/embedding fan-out smoke ${EVENT_ID}/")

HTTP_CODE=$(echo "${EVENT_PAYLOAD}" | curl -s -o /tmp/ingest-smoke.out -w "%{http_code}" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: ${TENANT_ID}" \
  -d @- \
  "${INGEST_URL}/ingest/events")
if [[ "${HTTP_CODE}" != "202" ]]; then
  echo "❌ Ingest failed (status ${HTTP_CODE}): $(cat /tmp/ingest-smoke.out)"
  exit 1
fi

echo "🔸 Flushing batch"
HTTP_CODE=$(curl -s -o /tmp/ingest-smoke.out -w "%{http_code}" \
  -X POST \
  -H "X-Tenant-ID: ${TENANT_ID}" \
  "${INGEST_URL}/ingest/events/flush")
if [[ "${HTTP_CODE}" != "200" ]]; then
  echo "❌ Flush failed (status ${HTTP_CODE}): $(cat /tmp/ingest-smoke.out)"
  exit 1
fi

sleep 1

echo "🔸 Checking /health for embedding metrics"
curl -s "${INGEST_URL}/health" > /tmp/ingest-health.json

python - <<'PY'
import json, os, sys
TENANT_ID = os.environ.get("TENANT_ID")
if not TENANT_ID:
    print("❌ TENANT_ID missing in environment")
    sys.exit(1)
with open("/tmp/ingest-health.json") as f:
    data = json.load(f)
emb = data.get("embeddings", {})
if TENANT_ID not in emb:
    print(f"❌ No embedding metrics for tenant {TENANT_ID}")
    sys.exit(1)
m = emb[TENANT_ID]
if m.get("attempted", 0) <= 0:
    print(f"❌ Embedding attempts not incremented: {m}")
    sys.exit(1)
print(f"✅ Embedding metrics ok for {TENANT_ID}: {m}")
PY

if [[ "${CHECK_DB}" == "true" ]]; then
  echo "🔸 Checking Postgres for ${EVENT_ID}"
  COUNT=$(docker exec sentinelgrid-postgres-1 psql -U sg -d sg -t -A -c \
    "select count(*) from security_event_embeddings where os_id_ref='${EVENT_ID}'" 2>/dev/null || echo "0")
  if [[ "${COUNT}" -eq "0" ]]; then
    echo "⚠️  Row not found yet for ${EVENT_ID} (fan-out is async); re-run after a few seconds if needed."
  else
    echo "✅ Row found in security_event_embeddings for ${EVENT_ID}"
  fi
fi

echo "✅ Embedding fan-out smoke completed"
