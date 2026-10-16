#!/usr/bin/env bash
set -euo pipefail

# Apply a tenant seed file after schema migrations.
# Usage: DB_URL=... ./scripts/seed_tenant.sh seeds/tenant/demo_protect.sql

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <seed-sql-file>" >&2
  exit 1
fi

SEED_FILE="$1"
DB_URL=${DB_URL:-postgresql://sg:sg@localhost:5432/sg}

if [[ ! -f "${SEED_FILE}" ]]; then
  echo "❌ Seed file not found: ${SEED_FILE}" >&2
  exit 1
fi

echo "🌱 Applying tenant seed: ${SEED_FILE}"
echo "🔌 DB: ${DB_URL}"

psql "${DB_URL}" -v ON_ERROR_STOP=1 -f "${SEED_FILE}"

echo "✅ Tenant seed applied."
