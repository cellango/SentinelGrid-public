#!/bin/bash
#
# Reset and Initialize Realm Architecture
# 
# This script provides a clean slate by:
# 1. Dropping Keycloak database and volumes
# 2. Dropping realm architecture tables from SentinelGrid database
# 3. Restarting Keycloak with fresh state
# 4. Running database migration
# 5. Seeding initial realms
# 6. Verifying complete setup
#
# SAFE TO RUN MULTIPLE TIMES during development
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MIGRATIONS_DIR="$PROJECT_ROOT/backend/migrations"
DB_URL="${DB_URL:-postgresql://sg:sg@localhost:5432/sg}"
KEYCLOAK_URL="${KEYCLOAK_URL:-https://localhost:8443}"
KEYCLOAK_ADMIN_USER="${KEYCLOAK_ADMIN_USER:-admin}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.dev.yml}"

compose() {
    if docker compose version >/dev/null 2>&1; then
        docker compose -f "$COMPOSE_FILE" "$@"
    elif command -v docker-compose >/dev/null 2>&1; then
        docker-compose -f "$COMPOSE_FILE" "$@"
    else
        echo -e "${RED}❌ Neither 'docker compose' nor 'docker-compose' is available${NC}"
        exit 1
    fi
}

# Parse arguments
SKIP_CONFIRMATION=false
KEEP_TENANTS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -y|--yes)
            SKIP_CONFIRMATION=true
            shift
            ;;
        --keep-tenants)
            KEEP_TENANTS=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -y, --yes           Skip confirmation prompt"
            echo "  --keep-tenants      Keep existing tenant records (only reset realms)"
            echo "  -h, --help          Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  DB_URL                    PostgreSQL connection URL"
            echo "  KEYCLOAK_URL              Keycloak server URL"
            echo "  KEYCLOAK_ADMIN_USER       Keycloak admin username"
            echo "  KEYCLOAK_ADMIN_PASSWORD   Keycloak admin password"
            echo "  COMPOSE_FILE              Compose file to use (default: docker-compose.dev.yml)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${MAGENTA}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║                                                        ║${NC}"
echo -e "${MAGENTA}║   ${CYAN}SentinelGrid Realm Architecture Reset & Init${MAGENTA}       ║${NC}"
echo -e "${MAGENTA}║                                                        ║${NC}"
echo -e "${MAGENTA}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Warning message
echo -e "${RED}⚠️  WARNING: This will DELETE ALL DATA! ⚠️${NC}"
echo ""
echo -e "${YELLOW}This script will:${NC}"
echo -e "  1. ${RED}DROP${NC} Keycloak database and volumes"
echo -e "  2. ${RED}DROP${NC} realm architecture tables"
if [ "$KEEP_TENANTS" = false ]; then
    echo -e "  3. ${RED}DROP${NC} all tenant, customer, and organization records"
fi
echo -e "  4. ${GREEN}Restart${NC} Keycloak with clean state"
echo -e "  5. ${GREEN}Create${NC} new database schema"
echo -e "  6. ${GREEN}Seed${NC} initial realms (sg-admin, sg-mt-us-1, sg-mt-eu-1)"
echo ""

if [ "$SKIP_CONFIRMATION" = false ]; then
    echo -e "${YELLOW}Are you sure you want to continue? (yes/no)${NC}"
    read -r response
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo -e "${BLUE}Operation cancelled.${NC}"
        exit 0
    fi
fi

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Phase 1: Cleanup${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo ""

# Step 1: Stop Keycloak and Keycloak DB
echo -e "${YELLOW}[1/3] Stopping Keycloak containers...${NC}"
cd "$PROJECT_ROOT"

if compose ps | grep -q keycloak; then
    compose stop keycloak keycloak_db
    echo -e "${GREEN}✅ Keycloak containers stopped${NC}"
else
    echo -e "${BLUE}ℹ️  Keycloak containers not running${NC}"
fi

# Step 2: Remove Keycloak volumes
echo -e "${YELLOW}[2/3] Removing Keycloak volumes...${NC}"

# Get the actual volume names (they may have project prefix)
KEYCLOAK_DB_VOLUME=$(docker volume ls --format '{{.Name}}' | grep keycloak_db_data || echo "")
KEYCLOAK_DATA_VOLUME=$(docker volume ls --format '{{.Name}}' | grep keycloak_data || echo "")
KEYCLOAK_CERTS_VOLUME=$(docker volume ls --format '{{.Name}}' | grep keycloak_certs || echo "")

if [ -n "$KEYCLOAK_DB_VOLUME" ]; then
    docker volume rm "$KEYCLOAK_DB_VOLUME" 2>/dev/null || true
    echo -e "${GREEN}✅ Removed volume: $KEYCLOAK_DB_VOLUME${NC}"
fi

if [ -n "$KEYCLOAK_DATA_VOLUME" ]; then
    docker volume rm "$KEYCLOAK_DATA_VOLUME" 2>/dev/null || true
    echo -e "${GREEN}✅ Removed volume: $KEYCLOAK_DATA_VOLUME${NC}"
fi

echo -e "${GREEN}✅ Keycloak volumes cleaned${NC}"

# Step 3: Drop database tables
echo -e "${YELLOW}[3/3] Dropping database tables...${NC}"

if ! psql "$DB_URL" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${RED}❌ Cannot connect to PostgreSQL at $DB_URL${NC}"
    echo -e "${YELLOW}   Make sure PostgreSQL is running${NC}"
    exit 1
fi

# Drop tables in correct order (respecting foreign keys)
psql "$DB_URL" > /dev/null 2>&1 <<EOF
-- Drop tables in correct order
DROP TABLE IF EXISTS tenant_provisioning_log CASCADE;
DROP TABLE IF EXISTS realm_capacity_history CASCADE;

-- Drop tenants table if not keeping tenants
$(if [ "$KEEP_TENANTS" = false ]; then echo "DROP TABLE IF EXISTS tenants CASCADE;"; fi)

DROP TABLE IF EXISTS organizations CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS realms CASCADE;

-- Drop views
DROP VIEW IF EXISTS tenant_details CASCADE;
DROP VIEW IF EXISTS customer_summary CASCADE;
DROP VIEW IF EXISTS realm_status CASCADE;

-- Drop functions
DROP FUNCTION IF EXISTS check_realm_capacity() CASCADE;
DROP FUNCTION IF EXISTS update_customer_counts() CASCADE;
DROP FUNCTION IF EXISTS update_realm_tenant_count() CASCADE;
EOF

echo -e "${GREEN}✅ Database tables dropped${NC}"

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Phase 2: Restart Keycloak${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo ""

# Step 4: Start Keycloak
echo -e "${YELLOW}[1/2] Starting Keycloak...${NC}"

compose up -d keycloak_db keycloak

echo -e "${GREEN}✅ Keycloak containers started${NC}"

# Step 5: Wait for Keycloak to be ready
echo -e "${YELLOW}[2/2] Waiting for Keycloak to be ready...${NC}"
echo -e "${BLUE}This takes about 60 seconds...${NC}"

RETRY_COUNT=0
MAX_RETRIES=60
RETRY_DELAY=2

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -k -s "$KEYCLOAK_URL/health/ready" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Keycloak is ready!${NC}"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $((RETRY_COUNT % 10)) -eq 0 ]; then
        echo -e "${BLUE}   Still waiting... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    fi
    sleep $RETRY_DELAY
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Keycloak failed to start within timeout${NC}"
    echo -e "${YELLOW}   Check logs: $(basename "$0") uses ${COMPOSE_FILE}; inspect with 'docker compose -f ${COMPOSE_FILE} logs keycloak'${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Phase 3: Initialize Realm Architecture${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo ""

# Step 6: Run database migration
echo -e "${YELLOW}[1/2] Running database migration...${NC}"

MIGRATION_FILE="$MIGRATIONS_DIR/002_realm_architecture.sql"

if [ ! -f "$MIGRATION_FILE" ]; then
    echo -e "${RED}❌ Migration file not found: $MIGRATION_FILE${NC}"
    exit 1
fi

if psql "$DB_URL" -f "$MIGRATION_FILE" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Database migration completed${NC}"
else
    echo -e "${RED}❌ Database migration failed${NC}"
    exit 1
fi

# Step 7: Seed realms
echo -e "${YELLOW}[2/2] Seeding realms in Keycloak...${NC}"

SEED_SCRIPT="$SCRIPT_DIR/seed_realms.py"

if [ ! -f "$SEED_SCRIPT" ]; then
    echo -e "${RED}❌ Seed script not found: $SEED_SCRIPT${NC}"
    exit 1
fi

if python3 "$SEED_SCRIPT" \
    --keycloak-url "$KEYCLOAK_URL" \
    --admin-user "$KEYCLOAK_ADMIN_USER" \
    --admin-password "$KEYCLOAK_ADMIN_PASSWORD" \
    --db-url "$DB_URL"; then
    echo -e "${GREEN}✅ Realms seeded successfully${NC}"
else
    echo -e "${RED}❌ Realm seeding failed${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Phase 4: Verification${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo ""

# Step 8: Verify setup
echo -e "${YELLOW}Verifying setup...${NC}"

# Check realm count
REALM_COUNT=$(psql "$DB_URL" -t -c "SELECT COUNT(*) FROM realms" | tr -d ' ')
if [ "$REALM_COUNT" -ge 3 ]; then
    echo -e "${GREEN}✅ Database: Found $REALM_COUNT realms${NC}"
else
    echo -e "${RED}❌ Database: Expected at least 3 realms, found $REALM_COUNT${NC}"
fi

# Check tables
TABLES=("realms" "customers" "organizations" "realm_capacity_history" "tenant_provisioning_log")
for table in "${TABLES[@]}"; do
    if psql "$DB_URL" -t -c "SELECT 1 FROM information_schema.tables WHERE table_name='$table'" | grep -q 1; then
        echo -e "${GREEN}✅ Table '$table' exists${NC}"
    else
        echo -e "${RED}❌ Table '$table' not found${NC}"
    fi
done

# Check Keycloak realms
echo ""
echo -e "${YELLOW}Checking Keycloak realms...${NC}"

KEYCLOAK_REALMS=("sg-admin" "sg-mt-us-1" "sg-mt-eu-1")
for realm in "${KEYCLOAK_REALMS[@]}"; do
    if curl -k -s "$KEYCLOAK_URL/realms/$realm" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Keycloak realm '$realm' exists${NC}"
    else
        echo -e "${RED}❌ Keycloak realm '$realm' not found${NC}"
    fi
done

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                        ║${NC}"
echo -e "${GREEN}║              ${CYAN}✅ Reset & Init Complete!${GREEN}                  ║${NC}"
echo -e "${GREEN}║                                                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${GREEN}✅${NC} Keycloak database and volumes reset"
echo -e "  ${GREEN}✅${NC} Database schema recreated"
echo -e "  ${GREEN}✅${NC} Realms created:"
echo -e "     • ${CYAN}sg-admin${NC} (Platform admin realm)"
echo -e "     • ${CYAN}sg-mt-us-1${NC} (US multi-tenant, capacity: 1000)"
echo -e "     • ${CYAN}sg-mt-eu-1${NC} (EU multi-tenant, capacity: 1000)"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Next Steps${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${YELLOW}1.${NC} View realms in Keycloak:"
echo -e "     ${BLUE}http://localhost:8080/admin${NC} (admin/admin)"
echo ""
echo -e "  ${YELLOW}2.${NC} Check database:"
echo -e "     ${BLUE}psql $DB_URL -c \"SELECT * FROM realms;\"${NC}"
echo ""
echo -e "  ${YELLOW}3.${NC} Test signup API:"
echo -e "     ${BLUE}curl -X POST http://localhost:8008/api/v1/signup \\${NC}"
echo -e "       ${BLUE}-H \"Content-Type: application/json\" \\${NC}"
echo -e "       ${BLUE}-d '{\"company_name\": \"Test Corp\", ...}'${NC}"
echo ""
echo -e "  ${YELLOW}4.${NC} View realm status:"
echo -e "     ${BLUE}psql $DB_URL -c \"SELECT * FROM realm_status;\"${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${GREEN}Ready to test! 🚀${NC}"
echo ""
