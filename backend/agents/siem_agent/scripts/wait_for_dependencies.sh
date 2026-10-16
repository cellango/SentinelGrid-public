#!/usr/bin/env bash
set -euo pipefail

OPENSEARCH_URL=${OPENSEARCH_URL:-http://opensearch:9200}
DB_HOST=${DB_HOST:-postgres}
DB_PORT=${DB_PORT:-5432}
KEYCLOAK_URL=${KEYCLOAK_URL:-http://keycloak:8080}
MAX_ATTEMPTS=${STARTUP_WAIT_ATTEMPTS:-60}
SLEEP_SECS=${STARTUP_WAIT_SLEEP:-5}

log() {
  echo "[startup-wait] $*"
}

check_opensearch() {
  curl -sf --max-time 5 "${OPENSEARCH_URL}/_cluster/health" >/dev/null
}

check_postgres() {
  python - "$DB_HOST" "$DB_PORT" <<'PY'
import socket, sys

host = sys.argv[1]
port = int(sys.argv[2])

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(3)
    sys.exit(0 if sock.connect_ex((host, port)) == 0 else 1)
PY
}

check_keycloak() {
  python - <<'PY'
import os, sys, socket, urllib.parse, http.client

url = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
parsed = urllib.parse.urlparse(url)
host = parsed.hostname or "keycloak"
port = parsed.port or (443 if parsed.scheme == "https" else 80)

try:
    socket.getaddrinfo(host, port)
except Exception:
    sys.exit(1)

conn_cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
try:
    conn = conn_cls(host, port, timeout=5)
    path = parsed.path or "/"
    conn.request("GET", path)
    resp = conn.getresponse()
    conn.close()
    if resp.status < 500:
        sys.exit(0)
except Exception:
    sys.exit(1)

sys.exit(1)
PY
}

log "Waiting for OpenSearch at ${OPENSEARCH_URL}, Postgres at ${DB_HOST}:${DB_PORT}, and Keycloak at ${KEYCLOAK_URL}"
for attempt in $(seq 1 "${MAX_ATTEMPTS}"); do
  if check_opensearch && check_postgres && check_keycloak; then
    log "Dependencies are up (attempt ${attempt}/${MAX_ATTEMPTS})"
    break
  fi
  if [[ "${attempt}" -eq "${MAX_ATTEMPTS}" ]]; then
    log "Dependencies did not become ready after ${MAX_ATTEMPTS} attempts"
    exit 1
  fi
  sleep "${SLEEP_SECS}"
done

CMD=("$@")
if [[ "${#CMD[@]}" -eq 0 ]]; then
  CMD=(uvicorn app.main:app --host 0.0.0.0 --port 8000)
fi

log "Starting service: ${CMD[*]}"
exec "${CMD[@]}"
