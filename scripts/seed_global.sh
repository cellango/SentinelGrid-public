#!/usr/bin/env bash
set -euo pipefail

# Apply global seed (sg_admin) after schema migrations.

DB_URL=${DB_URL:-postgresql://sg:sg@localhost:5432/sg}
SEED_FILE="seeds/global/seed_sg_admin.sql"

if [[ ! -f "${SEED_FILE}" ]]; then
  echo "❌ Seed file not found: ${SEED_FILE}" >&2
  exit 1
fi

echo "🌱 Applying global seed: ${SEED_FILE}"
echo "🔌 DB: ${DB_URL}"

psql "${DB_URL}" -v ON_ERROR_STOP=1 -f "${SEED_FILE}"

echo "✅ Global seed applied."
