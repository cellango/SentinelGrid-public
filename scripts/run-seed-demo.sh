#!/bin/bash
# Run the demo seed script with proper Docker network access

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.dev.yml}"

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose -f "$COMPOSE_FILE" "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose -f "$COMPOSE_FILE" "$@"
  else
    echo "❌ Neither 'docker compose' nor 'docker-compose' is available" >&2
    exit 1
  fi
}

echo "🌱 Running Demo Data Seed Script..."
echo ""

cd "$PROJECT_ROOT"

# Default DB URL needs the multi-schema search_path (security_ops, orchestration, public)
DB_URL="${DB_URL:-postgresql://sg:sg@postgres:5432/sg?options=-csearch_path%3Dsecurity_ops,orchestration,public}"

# Run seed script from within Docker network using only the already-started infra services.
compose run --rm --no-deps \
  -v "$(pwd)/backend/scripts:/app/scripts:ro" \
  -v "$(pwd)/backend/libs:/app/libs:ro" \
  -v "$(pwd)/cfg:/app/cfg:ro" \
  -e KEYCLOAK_URL=http://keycloak:8080 \
  -e DB_URL="$DB_URL" \
  -e KEYCLOAK_ADMIN_USER=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=${KEYCLOAK_ADMIN_PASSWORD:-admin} \
  -e REPO_ROOT=/app \
  -e PYTHONPATH=/app \
  iam_agent \
  python3 /app/scripts/seed_demo_data.py

echo ""
echo "✅ Seed script completed!"
echo ""
echo "⚠️  IMPORTANT: If Keycloak connection failed, check:"
echo "   1. Keycloak is running: docker compose -f ${COMPOSE_FILE} ps keycloak"
echo "   2. Admin credentials are correct (default: admin/admin)"
echo "   3. Users need to log out and log back in to get new tokens with tenant_id"
