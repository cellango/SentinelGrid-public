#!/usr/bin/env bash
set -euo pipefail

# Run schema-only migrations from backend/migrations_consolidated.
# Preference order:
# 1) local Flyway
# 2) flyway/flyway Docker image
# 3) direct psql application of versioned SQL files
# Usage:
#   DB_HOST=localhost DB_PORT=5432 DB_NAME=sg DB_USER=sg DB_PASSWORD=sg ./scripts/flyway_schema_only.sh
# Optional:
#   SCHEMA_MIGRATION_MODE=auto|flyway|docker|psql

FLYWAY_BIN=${FLYWAY_BIN:-flyway}
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-sg}
DB_USER=${DB_USER:-sg}
DB_PASSWORD=${DB_PASSWORD:-sg}
JDBC_URL=${JDBC_URL:-"jdbc:postgresql://${DB_HOST}:${DB_PORT}/${DB_NAME}"}
DB_URL=${DB_URL:-"postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"}
SCHEMA_MIGRATION_MODE=${SCHEMA_MIGRATION_MODE:-auto}

# Consolidated schema-only baseline lives under backend/migrations_consolidated
MIGRATION_PATH="${MIGRATION_PATH:-backend/migrations_consolidated}"

extract_version() {
  local migration_name="${1:?migration name required}"
  migration_name="${migration_name##*/}"
  migration_name="${migration_name%%__*}"
  migration_name="${migration_name#V}"
  printf '%s\n' "$migration_name"
}

extract_description() {
  local migration_name="${1:?migration name required}"
  migration_name="${migration_name##*/}"
  migration_name="${migration_name#*__}"
  migration_name="${migration_name%.sql}"
  migration_name="${migration_name//_/ }"
  printf '%s\n' "$migration_name"
}

is_local_db_target() {
  case "${DB_HOST}" in
    localhost|127.0.0.1|::1)
      return 0
      ;;
  esac

  case "${DB_URL}" in
    *"@localhost:"*|*"@127.0.0.1:"*|*"@::1:"*)
      return 0
      ;;
  esac

  return 1
}

ensure_flyway_history_table() {
  PGPASSWORD="${DB_PASSWORD}" psql "${DB_URL}" -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS flyway_schema_history (
  installed_rank integer NOT NULL PRIMARY KEY,
  version character varying(50),
  description character varying(200) NOT NULL,
  type character varying(20) NOT NULL,
  script character varying(1000) NOT NULL,
  checksum integer,
  installed_by character varying(100) NOT NULL,
  installed_on timestamp without time zone NOT NULL DEFAULT now(),
  execution_time integer NOT NULL,
  success boolean NOT NULL
);
SQL
}

run_with_psql() {
  if ! command -v psql >/dev/null 2>&1; then
    echo "❌ Neither Flyway nor a usable Docker daemon is available, and psql is not installed." >&2
    exit 1
  fi

  ensure_flyway_history_table

  echo "ℹ️  Applying pending schema-only migrations with psql against ${DB_URL}"
  while IFS= read -r migration; do
    local version description script_name installed_rank execution_time_ms start_ts end_ts migration_abs
    version="$(extract_version "${migration}")"
    description="$(extract_description "${migration}")"
    script_name="$(basename "${migration}")"
    migration_abs="$(cd -- "$(dirname "${migration}")" && pwd)/${script_name}"

    if PGPASSWORD="${DB_PASSWORD}" psql "${DB_URL}" -X -q -A -t -v ON_ERROR_STOP=1 \
      -c "select 1 from flyway_schema_history where version = '${version}' and success = true limit 1;" | grep -q '^1$'; then
      echo "⏭️  Skipping ${script_name} (already applied)"
      continue
    fi

    installed_rank="$(
      PGPASSWORD="${DB_PASSWORD}" psql "${DB_URL}" -X -q -A -t -v ON_ERROR_STOP=1 \
        -c "select coalesce(max(installed_rank), 0) + 1 from flyway_schema_history;"
    )"

    echo "📄 Applying ${script_name}"
    start_ts="$(date +%s)"
    PGPASSWORD="${DB_PASSWORD}" psql "${DB_URL}" -v ON_ERROR_STOP=1 -1 <<SQL
\i ${migration_abs}
INSERT INTO flyway_schema_history (
  installed_rank,
  version,
  description,
  type,
  script,
  checksum,
  installed_by,
  execution_time,
  success
) VALUES (
  ${installed_rank},
  '${version}',
  '${description}',
  'SQL',
  '${script_name}',
  NULL,
  '${DB_USER}',
  0,
  true
);
SQL
    end_ts="$(date +%s)"
    execution_time_ms="$(( (end_ts - start_ts) * 1000 ))"
    PGPASSWORD="${DB_PASSWORD}" psql "${DB_URL}" -v ON_ERROR_STOP=1 \
      -c "update flyway_schema_history set execution_time = ${execution_time_ms} where installed_rank = ${installed_rank};" >/dev/null
  done < <(find "${MIGRATION_PATH}" -maxdepth 1 -type f -name 'V*.sql' | sort)
}

echo "🚀 Running Flyway (schema-only) against ${JDBC_URL}"
case "${SCHEMA_MIGRATION_MODE}" in
  auto)
    if command -v "${FLYWAY_BIN}" >/dev/null 2>&1; then
      "${FLYWAY_BIN}" \
        -url="${JDBC_URL}" \
        -user="${DB_USER}" \
        -password="${DB_PASSWORD}" \
        -locations="filesystem:${MIGRATION_PATH}" \
        migrate
    elif is_local_db_target; then
      run_with_psql
    elif command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
      docker run --rm \
        -v "$(pwd)/${MIGRATION_PATH}":/flyway/sql \
        flyway/flyway:10-alpine \
        -url="${JDBC_URL}" \
        -user="${DB_USER}" \
        -password="${DB_PASSWORD}" \
        -locations=filesystem:/flyway/sql \
        migrate
    else
      run_with_psql
    fi
    ;;
  flyway)
    if ! command -v "${FLYWAY_BIN}" >/dev/null 2>&1; then
      echo "❌ SCHEMA_MIGRATION_MODE=flyway but '${FLYWAY_BIN}' is not installed." >&2
      exit 1
    fi
    "${FLYWAY_BIN}" \
      -url="${JDBC_URL}" \
      -user="${DB_USER}" \
      -password="${DB_PASSWORD}" \
      -locations="filesystem:${MIGRATION_PATH}" \
      migrate
    ;;
  docker)
    if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
      echo "❌ SCHEMA_MIGRATION_MODE=docker but Docker is not available." >&2
      exit 1
    fi
    docker run --rm \
      -v "$(pwd)/${MIGRATION_PATH}":/flyway/sql \
      flyway/flyway:10-alpine \
      -url="${JDBC_URL}" \
      -user="${DB_USER}" \
      -password="${DB_PASSWORD}" \
      -locations=filesystem:/flyway/sql \
      migrate
    ;;
  psql)
    run_with_psql
    ;;
  *)
    echo "❌ Invalid SCHEMA_MIGRATION_MODE=${SCHEMA_MIGRATION_MODE} (expected auto|flyway|docker|psql)" >&2
    exit 1
    ;;
esac

echo "✅ Flyway schema-only migrate completed."
