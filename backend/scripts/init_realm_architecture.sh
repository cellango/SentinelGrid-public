#!/bin/bash
#
# Initialize Realm Architecture
# This script:
# 1. Runs database migration (002_realm_architecture.sql)
# 2. Seeds initial realms (sg-admin, sg-mt-us-1, sg-mt-eu-1)
# 3. Verifies setup
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATIONS_DIR="$(cd "$SCRIPT_DIR/../migrations" && pwd)"
DB_URL="${DB_URL:-postgresql://sg:sg@localhost:5432/sg}"
KEYCLOAK_URL="${KEYCLOAK_URL:-https://localhost:8443}"
KEYCLOAK_ADMIN_USER="${KEYCLOAK_ADMIN_USER:-admin}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  SentinelGrid Realm Architecture Init${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 1: Check prerequisites
echo -e "${YELLOW}[1/4] Checking prerequisites...${NC}"

# Check if PostgreSQL is accessible
if ! psql "$DB_URL" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${RED}❌ Cannot connect to PostgreSQL at $DB_URL${NC}"
    echo -e "${YELLOW}   Make sure PostgreSQL is running and accessible${NC}"
    exit 1
fi
echo -e "${GREEN}✅ PostgreSQL is accessible${NC}"

# Check if Keycloak is accessible
if ! curl -k -s "$KEYCLOAK_URL/health/ready" > /dev/null 2>&1; then
    echo -e "${RED}❌ Cannot connect to Keycloak at $KEYCLOAK_URL${NC}"
    echo -e "${YELLOW}   Make sure Keycloak is running and accessible${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Keycloak is accessible${NC}"

echo ""

# Step 2: Run database migration
echo -e "${YELLOW}[2/4] Running database migration...${NC}"

MIGRATION_FILE="$MIGRATIONS_DIR/002_realm_architecture.sql"

if [ ! -f "$MIGRATION_FILE" ]; then
    echo -e "${RED}❌ Migration file not found: $MIGRATION_FILE${NC}"
    exit 1
fi

echo -e "   Applying migration: 002_realm_architecture.sql"

if psql "$DB_URL" -f "$MIGRATION_FILE" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Database migration completed successfully${NC}"
else
    echo -e "${RED}❌ Database migration failed${NC}"
    echo -e "${YELLOW}   Check the migration file for errors${NC}"
    exit 1
fi

echo ""

# Step 3: Seed realms in Keycloak and database
echo -e "${YELLOW}[3/4] Seeding realms...${NC}"

SEED_SCRIPT="$SCRIPT_DIR/seed_realms.py"

if [ ! -f "$SEED_SCRIPT" ]; then
    echo -e "${RED}❌ Seed script not found: $SEED_SCRIPT${NC}"
    exit 1
fi

echo -e "   Creating platform admin realm (sg-admin)..."
echo -e "   Creating multi-tenant realms (sg-mt-us-1, sg-mt-eu-1)..."

if python3 "$SEED_SCRIPT" \
    --keycloak-url "$KEYCLOAK_URL" \
    --admin-user "$KEYCLOAK_ADMIN_USER" \
    --admin-password "$KEYCLOAK_ADMIN_PASSWORD" \
    --db-url "$DB_URL"; then
    echo -e "${GREEN}✅ Realms seeded successfully${NC}"
else
    echo -e "${RED}❌ Realm seeding failed${NC}"
    echo -e "${YELLOW}   Check the seed script logs for details${NC}"
    exit 1
fi

echo ""

# Step 4: Verify setup
echo -e "${YELLOW}[4/4] Verifying setup...${NC}"

# Check if realms exist in database
REALM_COUNT=$(psql "$DB_URL" -t -c "SELECT COUNT(*) FROM realms WHERE realm_type IN ('platform_admin', 'multi_tenant')" | tr -d ' ')

if [ "$REALM_COUNT" -ge 3 ]; then
    echo -e "${GREEN}✅ Database: Found $REALM_COUNT realms${NC}"
else
    echo -e "${RED}❌ Database: Expected at least 3 realms, found $REALM_COUNT${NC}"
    exit 1
fi

# Check if tables exist
TABLES=("customers" "organizations" "realm_capacity_history" "tenant_provisioning_log")
for table in "${TABLES[@]}"; do
    if psql "$DB_URL" -t -c "SELECT 1 FROM information_schema.tables WHERE table_name='$table'" | grep -q 1; then
        echo -e "${GREEN}✅ Table '$table' exists${NC}"
    else
        echo -e "${RED}❌ Table '$table' not found${NC}"
        exit 1
    fi
done

# Check if tenants table has new columns
NEW_COLUMNS=("realm_name" "customer_id" "organization_id" "pricing_tier" "realm_strategy")
for column in "${NEW_COLUMNS[@]}"; do
    if psql "$DB_URL" -t -c "SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='$column'" | grep -q 1; then
        echo -e "${GREEN}✅ Column 'tenants.$column' exists${NC}"
    else
        echo -e "${RED}❌ Column 'tenants.$column' not found${NC}"
        exit 1
    fi
done

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✅ Realm Architecture Initialized!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Summary:${NC}"
echo -e "  • Database migration: ${GREEN}✅ Complete${NC}"
echo -e "  • Realms created: ${GREEN}✅ sg-admin, sg-mt-us-1, sg-mt-eu-1${NC}"
echo -e "  • Tables created: ${GREEN}✅ customers, organizations, realms, etc.${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "  1. Test signup flow: POST /api/v1/signup"
echo -e "  2. Verify realm assignment logic"
echo -e "  3. Test multi-tenant realm capacity"
echo ""
echo -e "${YELLOW}Note: Existing 'sentinelgrid' realm is still present.${NC}"
echo -e "${YELLOW}      You can migrate it to 'sg-mt-us-1' or keep it for legacy support.${NC}"
echo ""

