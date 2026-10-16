#!/usr/bin/env bash
set -euo pipefail

# Start the observability stack with an isolated project name so it doesn't touch the main stack.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.observability.yml"
PROJECT_NAME="sentinelgrid-observability"

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "Compose file not found at ${COMPOSE_FILE}" >&2
  exit 1
fi

echo "Starting observability stack (${PROJECT_NAME})..."
docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" up -d
echo "Observability stack started."
docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" ps
