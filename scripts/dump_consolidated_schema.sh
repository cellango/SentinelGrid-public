#!/usr/bin/env bash
set -euo pipefail

# Dump consolidated schema-only baselines per schema into backend/migrations_consolidated/.
# Requires pg_dump available and a database with schema-only migrations applied (no seed data required).
#
# Usage:
#   DB_URL=postgresql://sg:sg@localhost:55432/sg ./scripts/dump_consolidated_schema.sh

DB_URL=${DB_URL:-postgresql://sg:sg@localhost:5432/sg}
OUT_DIR=${OUT_DIR:-backend/migrations_consolidated}
SCHEMAS=(${SCHEMAS:-public audit reporting orchestration security_ops llm_training})

mkdir -p "${OUT_DIR}"

echo "🧱 Dumping schemas to ${OUT_DIR} from ${DB_URL}"
for schema in "${SCHEMAS[@]}"; do
  out_file="${OUT_DIR}/V001__baseline_${schema}.sql"
  echo "• ${schema} -> ${out_file}"
  pg_dump --schema-only --no-owner --no-privileges \
    --schema="${schema}" \
    --file="${out_file}" \
    "${DB_URL}"
done

echo "✅ Consolidated schema dumps written to ${OUT_DIR}"
