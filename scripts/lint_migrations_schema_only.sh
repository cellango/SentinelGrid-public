#!/usr/bin/env bash
set -euo pipefail

# Lint migrations to ensure they are schema-only (no DML) except for an allowlist
# of legacy data-bearing migrations that have been moved to seeds.
#
# Usage: ./scripts/lint_migrations_schema_only.sh

MIG_DIR="backend/migrations"
ALLOWED=(
  "V001__baseline_audit.sql"
  "V002__baseline_reporting.sql"
  "V003__baseline_orchestration.sql"
  "V004__baseline_public.sql"
  "V005__baseline_security_ops.sql"
  "V006__baseline_llm_training.sql"
  "V007__seed_demo_data.sql"
  "V122__seed_demo_compliance_reports.sql"
  "V123__seed_more_compliance_reports.sql"
  "V124__normalize_report_formats.sql"
  "V125__normalize_report_status.sql"
  "V127__add_plan_tier.sql"
  "V128__seed_sg_admin_policies.sql"
  "V129__add_plan_tier_default.sql"
  "V130__set_plan_tier_default_protect.sql"
  "V131__set_demo_plan_tier_comply.sql"
)

allow_re='('$(IFS='|'; echo "${ALLOWED[*]}")')'

echo "🔎 Linting migrations in ${MIG_DIR} for schema-only rule..."

if command -v rg >/dev/null 2>&1; then
  matches=$(rg -g 'V*.sql' --pcre2 '^\s*(INSERT|UPDATE|DELETE|UPSERT|MERGE|COPY)\b' "${MIG_DIR}" || true)
else
  matches=$(grep -REn --include='V*.sql' '^[[:space:]]*(INSERT|UPDATE|DELETE|UPSERT|MERGE|COPY)\b' "${MIG_DIR}" || true)
fi

violations=$(printf '%s\n' "${matches}" | grep -Ev "${allow_re}" || true)

if [[ -n "${violations}" ]]; then
  echo "❌ Found data statements in migrations (schema-only rule violated):"
  echo "${violations}"
  exit 1
fi

echo "✅ Migrations are schema-only (DML only in allowlisted legacy files)."
