#!/usr/bin/env bash
set -euo pipefail

# Create the SentinelGridIAM database (if missing) and run entitlement migrations via Flyway.
# Usage: ./scripts/init_sentinelgridiam_db.sh
# Env overrides:
#   DB_NAME (default: SentinelGridIAM)
#   DB_USER (default: sg)
#   DB_HOST (default: postgres)  # service name in docker-compose.dev.yml
#   DB_PORT (default: 5432)

DB_NAME="${DB_NAME:-SentinelGridIAM}"
DB_USER="${DB_USER:-sg}"
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"

echo "🛠  Ensuring database \"$DB_NAME\" exists (host=$DB_HOST port=$DB_PORT user=$DB_USER)..."

# Create DB inside the postgres container (idempotent, using bash guard)
if ! docker-compose -f docker-compose.dev.yml exec -T postgres psql -U "$DB_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
  docker-compose -f docker-compose.dev.yml exec -T postgres psql -U "$DB_USER" -d postgres -c "CREATE DATABASE \"$DB_NAME\""
fi
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U "$DB_USER" -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE \"$DB_NAME\" TO \"$DB_USER\""

echo "🚀 Running IAM entitlement migrations against $DB_NAME..."

# Run Flyway in a disposable container, mounting IAM Agent migrations.
docker run --rm \
  --network sentinelgrid_default \
  -v "$(pwd)/backend/agents/iam_agent/migrations":/flyway/sql:ro \
  flyway/flyway:10 \
  -url="jdbc:postgresql://$DB_HOST:$DB_PORT/$DB_NAME" \
  -user="$DB_USER" \
  -password="$DB_USER" \
  -schemas="public" \
  -baselineOnMigrate=true \
  -baselineVersion=0 \
  migrate

echo "✅ SentinelGridIAM DB initialized and IAM migrations applied."
