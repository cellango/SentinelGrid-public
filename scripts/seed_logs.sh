#!/usr/bin/env bash
set -euo pipefail

# Seed sample logs into OpenSearch via the API Gateway "load-sample" helper.
# Uses demo realm credentials (admin@demo.sentinelgrid.ai / DemoPassword123!) by default.
# Adds pre-checks (API/OpenSearch/SIEM health) and post-check (selenium UI smoke).
#
# Usage:
#   API_URL=http://localhost:8082 KEYCLOAK_URL=https://localhost:8443 ./scripts/seed_logs.sh

API_URL=${API_URL:-http://localhost:8082}
KEYCLOAK_URL=${KEYCLOAK_URL:-https://localhost:8443}
REALM=${REALM:-demo}
CLIENT_ID=${CLIENT_ID:-sentinelgrid-web}
USERNAME=${USERNAME:-admin@demo.sentinelgrid.ai}
PASSWORD=${PASSWORD:-DemoPassword123!}
HEADLESS=${HEADLESS:-true}
# Only allow supported sample sources; default to a balanced mix.
SOURCES=${SOURCES:-"ai auth network cloud endpoint git"}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "❌ Missing required command: $1"
    exit 1
  fi
}

require_cmd curl
require_cmd jq

echo "🔑 Getting token from ${KEYCLOAK_URL} realm ${REALM} as ${USERNAME}"
TOKEN=$(curl -k -s -X POST "${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token" \
  -d "client_id=${CLIENT_ID}" \
  -d "username=${USERNAME}" \
  -d "password=${PASSWORD}" \
  -d "grant_type=password" | jq -r '.access_token')

if [[ -z "${TOKEN}" || "${TOKEN}" == "null" ]]; then
  echo "❌ Could not obtain access token; aborting log seed"
  exit 1
fi

echo "🔍 Pre-check: API Gateway SIEM source health"
health_json=$(curl -k -s -w "%{http_code}" -o /tmp/source_health.json \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-Realm: ${REALM}" \
  "${API_URL}/api/siem/source-health")
if [[ "${health_json}" != "200" ]]; then
  echo "❌ Source health endpoint failed (HTTP ${health_json})"
  cat /tmp/source_health.json || true
  exit 1
fi
opensearch_status=$(jq -r '.opensearch // "unknown"' /tmp/source_health.json)
siem_status=$(jq -r '.siem_agent // "unknown"' /tmp/source_health.json)
ingestion_status=$(jq -r '.ingestion_service // "unknown"' /tmp/source_health.json)
echo "   OpenSearch: ${opensearch_status}, SIEM agent: ${siem_status}, ingestion: ${ingestion_status}"
for s in "${opensearch_status}" "${siem_status}" "${ingestion_status}"; do
  if [[ "${s}" == "unreachable" || "${s}" == "degraded" || "${s}" == "unknown" ]]; then
    echo "❌ Service health check failed (status=${s}); fix before seeding."
    exit 1
  fi
done

echo "🔍 Pre-check: OpenSearch cluster health"
if ! curl -fsS http://localhost:9200/_cluster/health >/tmp/os_health.json 2>/dev/null; then
  echo "❌ OpenSearch health endpoint unreachable on localhost:9200"
  exit 1
fi
os_status=$(jq -r '.status // "unknown"' /tmp/os_health.json)
echo "   Cluster status: ${os_status}"

for src in ${SOURCES}; do
  case "${src}" in
    ai|auth|network|cloud|endpoint|git) : ;;
    *)
      echo "⚠️  Skipping unsupported source=${src} (allowed: ai auth network cloud endpoint git)"
      continue
      ;;
  esac

  echo "📝 Seeding sample logs for source=${src}"
  http_code=$(curl -k -s -o /tmp/seed_logs_resp.json -w "%{http_code}" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "X-Realm: ${REALM}" \
    -H "Content-Type: application/json" \
    -X POST "${API_URL}/api/siem/ingestion/load-sample" \
    -d "{\"source\": \"${src}\"}")
  if [[ "${http_code}" != "200" && "${http_code}" != "201" ]]; then
    echo "⚠️  Seeding source=${src} failed (HTTP ${http_code}); response:"
    cat /tmp/seed_logs_resp.json
    exit 1
  else
    echo "✅ Seeded logs for ${src}"
  fi
done

echo "✅ Log seeding complete. Running UI visibility check (selenium)..."
HEADLESS=${HEADLESS} WEBSITE_URL=${WEBSITE_URL:-https://localhost:3443} pytest -q backend/tests/test_log_management_ui_selenium.py::test_logs_visible_after_seed
