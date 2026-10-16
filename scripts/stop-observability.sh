#!/usr/bin/env bash
set -euo pipefail

# Stop the observability stack without affecting the main stack.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.observability.yml"
PROJECT_NAME="sentinelgrid-observability"

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "Compose file not found at ${COMPOSE_FILE}" >&2
  exit 1
fi

echo "Stopping observability stack (${PROJECT_NAME})..."
docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" down
echo "Observability stack stopped."
