#!/usr/bin/env bash
set -euo pipefail

# One-shot bootstrap for a fresh environment:
# 1) Apply schema-only migrations (skipping data-bearing files)
# 2) Apply seeds (global + demo tenants)
# 3) Run validation smoke checks
#
# Usage:
#   DB_HOST=localhost DB_PORT=5432 DB_NAME=sg DB_USER=sg DB_PASSWORD=sg ./scripts/bootstrap_fresh_env.sh
# or
#   DB_URL=postgresql://sg:sg@localhost:5432/sg ./scripts/bootstrap_fresh_env.sh

DB_URL=${DB_URL:-}
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-sg}
DB_USER=${DB_USER:-sg}
DB_PASSWORD=${DB_PASSWORD:-sg}
BOOTSTRAP_LOG_SEED=${BOOTSTRAP_LOG_SEED:-auto}
API_URL=${API_URL:-http://localhost:8082}
KEYCLOAK_URL=${KEYCLOAK_URL:-https://localhost:8443}
REALM=${REALM:-demo}

if [[ -z "${DB_URL}" ]]; then
  DB_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
fi

export DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD

should_seed_logs() {
  case "${BOOTSTRAP_LOG_SEED}" in
    1|true|TRUE|yes|YES|always|ALWAYS)
      return 0
      ;;
    0|false|FALSE|no|NO|never|NEVER)
      return 1
      ;;
    auto|AUTO)
      ;;
    *)
      echo "❌ Invalid BOOTSTRAP_LOG_SEED=${BOOTSTRAP_LOG_SEED} (expected auto|always|never)" >&2
      exit 1
      ;;
  esac

  if ! command -v curl >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
    echo "ℹ️  Skipping log seed: curl/jq not available"
    return 1
  fi

  if ! curl -k -fsS --max-time 5 "${KEYCLOAK_URL}/realms/${REALM}" >/dev/null 2>&1; then
    echo "ℹ️  Skipping log seed: Keycloak realm ${REALM} not reachable at ${KEYCLOAK_URL}"
    return 1
  fi

  if ! curl -fsS --max-time 5 "${API_URL}/health" >/dev/null 2>&1; then
    echo "ℹ️  Skipping log seed: API Gateway not reachable at ${API_URL}"
    return 1
  fi

  return 0
}

echo "🔧 Step 1: schema-only migrations"
./scripts/flyway_schema_only.sh

echo "🌱 Step 2: seeds (global + demo tenants)"
DB_URL="${DB_URL}" ./scripts/seed_global.sh
DB_URL="${DB_URL}" ./scripts/seed_tenant.sh seeds/tenant/demo_protect.sql
DB_URL="${DB_URL}" ./scripts/seed_tenant.sh seeds/tenant/demo_protect_defend.sql
DB_URL="${DB_URL}" ./scripts/seed_tenant.sh seeds/tenant/demo_protect_defend_comply.sql

echo "👥 Step 3: IAM seed (birthrights + baseline policies)"
TENANTS="${TENANTS:-demo_protect demo2 demo}" DB_URL="${DB_URL}" ./scripts/seed_iam.sh

echo "🛰️ Step 4: seed scan instances (all supported types) per tenant"
TENANTS="${TENANTS:-demo_protect demo2 demo}" DB_URL="${DB_URL}" ./scripts/seed_scans.sh

echo "🪵 Step 5: seed sample logs (demo realm)"
if should_seed_logs; then
  API_URL="${API_URL}" KEYCLOAK_URL="${KEYCLOAK_URL}" REALM="${REALM}" ./scripts/seed_logs.sh
else
  echo "ℹ️  Sample log seeding skipped."
fi

echo "🧪 Step 6: validation"
DB_URL="${DB_URL}" ./scripts/validate_seeds.sh

echo "✅ Fresh environment bootstrap completed."
