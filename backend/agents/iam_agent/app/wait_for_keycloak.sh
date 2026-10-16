#!/bin/sh
# Block until Keycloak is resolvable and responsive to a simple HTTP request.

set -e

KEYCLOAK_URL="${KEYCLOAK_URL:-http://keycloak:8080}"
MAX_ATTEMPTS="${KEYCLOAK_WAIT_MAX_ATTEMPTS:-30}"
SLEEP_SECONDS="${KEYCLOAK_WAIT_SLEEP_SECONDS:-2}"

echo "🔎 Waiting for Keycloak at ${KEYCLOAK_URL} (max ${MAX_ATTEMPTS} attempts)..."

attempt=1
while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
  if python - <<'PY'
import os, sys, socket, time, urllib.parse, http.client

url = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
parsed = urllib.parse.urlparse(url)
host = parsed.hostname or "keycloak"
port = parsed.port or (443 if parsed.scheme == "https" else 80)

# DNS resolution
try:
    socket.getaddrinfo(host, port)
except Exception as exc:
    sys.exit(1)

# TCP + HTTP check
conn_cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
try:
    conn = conn_cls(host, port, timeout=5)
    path = parsed.path or "/"
    conn.request("GET", path)
    resp = conn.getresponse()
    conn.close()
    if resp.status < 500:  # treat 2xx/3xx/4xx as "up"
        sys.exit(0)
except Exception:
    sys.exit(1)

sys.exit(1)
PY
  then
    echo "✅ Keycloak is reachable."
    break
  fi
  attempt=$((attempt + 1))
  echo "⏳ Keycloak not ready yet (attempt ${attempt}/${MAX_ATTEMPTS}), retrying in ${SLEEP_SECONDS}s..."
  sleep "$SLEEP_SECONDS"
done

if [ "$attempt" -gt "$MAX_ATTEMPTS" ]; then
  echo "❌ Keycloak did not become reachable in time; exiting."
  exit 1
fi
