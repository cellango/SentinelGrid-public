#!/usr/bin/env bash
set -euo pipefail

# Simple health checker for sidecars; exits non-zero if endpoint unhealthy.
# Usage: sidecar-health.sh <endpoint_url> <name> [retries] [sleep_seconds]

endpoint="${1:-}"
name="${2:-sidecar}"
retries="${3:-5}"
sleep_seconds="${4:-2}"

if [[ -z "$endpoint" ]]; then
  echo "[$(date -Is)] ${name}: no health endpoint provided; skipping check"
  exit 0
fi

for ((i=1; i<=retries; i++)); do
  if curl -sSf --max-time 3 "$endpoint" >/dev/null; then
    echo "[$(date -Is)] ${name}: health check succeeded on attempt ${i}/${retries}"
    exit 0
  fi
  echo "[$(date -Is)] ${name}: health check failed (attempt ${i}/${retries}); retrying in ${sleep_seconds}s..."
  sleep "$sleep_seconds"
done

echo "[$(date -Is)] ${name}: health check failed after ${retries} attempts"
exit 1
