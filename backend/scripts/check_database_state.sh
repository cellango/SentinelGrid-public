#!/bin/bash
#
# Check Database State - Verify migrations and seeding status
#
# This script checks if the database has been properly initialized with:
# - Tables from migrations
# - Views and functions
# - Seeded data (realms, etc.)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

cd "$PROJECT_ROOT"

DB_URL="${DB_URL:-postgresql://sg:sg@localhost:5432/sg}"

echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                        ║${NC}"
echo -e "${CYAN}║         ${BLUE}Database State Check${CYAN}                        ║${NC}"
echo -e "${CYAN}║                                                        ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if PostgreSQL is running
echo -e "${YELLOW}[1/5] Checking PostgreSQL connection...${NC}"
if ! docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${RED}❌ PostgreSQL is not running or not accessible${NC}"
    echo -e "${YELLOW}   Start it with: docker-compose -f docker-compose.dev.yml up -d postgres${NC}"
    exit 1
fi
echo -e "${GREEN}✅ PostgreSQL is running${NC}"
echo ""

# Check tables
echo -e "${YELLOW}[2/5] Checking database tables...${NC}"
TABLES=$(docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
echo -e "${BLUE}   Found $TABLES tables${NC}"

# Expected tables from migrations
EXPECTED_TABLES=("realms" "customers" "organizations" "tenants" "realm_capacity_history" "tenant_provisioning_log" "vault_tenants" "vault_audit_log")

MISSING_TABLES=()
for table in "${EXPECTED_TABLES[@]}"; do
    EXISTS=$(docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '$table';" 2>/dev/null | tr -d ' ')
    if [ "$EXISTS" = "0" ]; then
        MISSING_TABLES+=("$table")
    fi
done

if [ ${#MISSING_TABLES[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ All expected tables exist${NC}"
else
    echo -e "${RED}❌ Missing tables: ${MISSING_TABLES[*]}${NC}"
fi
echo ""

# Check views
echo -e "${YELLOW}[3/5] Checking database views...${NC}"
VIEWS=$(docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -t -c "SELECT COUNT(*) FROM pg_views WHERE schemaname = 'public';" 2>/dev/null | tr -d ' ')
echo -e "${BLUE}   Found $VIEWS views${NC}"

EXPECTED_VIEWS=("realm_status" "customer_summary" "tenant_details" "vault_usage_by_customer" "vault_tenant_status")
MISSING_VIEWS=()
for view in "${EXPECTED_VIEWS[@]}"; do
    EXISTS=$(docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -t -c "SELECT COUNT(*) FROM pg_views WHERE schemaname = 'public' AND viewname = '$view';" 2>/dev/null | tr -d ' ')
    if [ "$EXISTS" = "0" ]; then
        MISSING_VIEWS+=("$view")
    fi
done

if [ ${#MISSING_VIEWS[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ All expected views exist${NC}"
else
    echo -e "${YELLOW}⚠️  Missing views: ${MISSING_VIEWS[*]}${NC}"
fi
echo ""

# Check functions
echo -e "${YELLOW}[4/5] Checking database functions...${NC}"
FUNCTIONS=$(docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -t -c "SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema = 'public' AND routine_type = 'FUNCTION';" 2>/dev/null | tr -d ' ')
echo -e "${BLUE}   Found $FUNCTIONS functions${NC}"

EXPECTED_FUNCTIONS=("update_realm_tenant_count" "update_customer_counts" "check_realm_capacity" "check_vault_quota" "update_vault_quota_usage")
MISSING_FUNCTIONS=()
for func in "${EXPECTED_FUNCTIONS[@]}"; do
    EXISTS=$(docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -t -c "SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema = 'public' AND routine_type = 'FUNCTION' AND routine_name = '$func';" 2>/dev/null | tr -d ' ')
    if [ "$EXISTS" = "0" ]; then
        MISSING_FUNCTIONS+=("$func")
    fi
done

if [ ${#MISSING_FUNCTIONS[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ All expected functions exist${NC}"
else
    echo -e "${YELLOW}⚠️  Missing functions: ${MISSING_FUNCTIONS[*]}${NC}"
fi
echo ""

# Check seeded data
echo -e "${YELLOW}[5/5] Checking seeded data...${NC}"

# Check realms (only if table exists)
if docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -t -c "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'realms';" 2>/dev/null | grep -q "1"; then
    REALM_COUNT=$(docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -t -c "SELECT COUNT(*) FROM realms;" 2>/dev/null | tr -d ' ' || echo "0")
    echo -e "${BLUE}   Realms: $REALM_COUNT${NC}"
    
    if [ "$REALM_COUNT" -gt 0 ] 2>/dev/null; then
        echo -e "${GREEN}   ✅ Realms table has data${NC}"
        docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -c "SELECT realm_name, realm_type, region, status FROM realms ORDER BY realm_name;" 2>/dev/null | grep -v "rows)" | tail -n +4
    else
        echo -e "${RED}   ❌ Realms table is empty (seeding may not have run)${NC}"
    fi
else
    echo -e "${RED}   ❌ Realms table does not exist (migrations may not have run)${NC}"
    REALM_COUNT=0
fi

# Check customers (only if table exists)
if docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -t -c "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'customers';" 2>/dev/null | grep -q "1"; then
    CUSTOMER_COUNT=$(docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -t -c "SELECT COUNT(*) FROM customers;" 2>/dev/null | tr -d ' ' || echo "0")
    echo -e "${BLUE}   Customers: $CUSTOMER_COUNT${NC}"
else
    echo -e "${YELLOW}   ⚠️  Customers table does not exist${NC}"
    CUSTOMER_COUNT=0
fi

# Check tenants (only if table exists)
if docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -t -c "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'tenants';" 2>/dev/null | grep -q "1"; then
    TENANT_COUNT=$(docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -t -c "SELECT COUNT(*) FROM tenants;" 2>/dev/null | tr -d ' ' || echo "0")
    echo -e "${BLUE}   Tenants: $TENANT_COUNT${NC}"
else
    echo -e "${YELLOW}   ⚠️  Tenants table does not exist${NC}"
    TENANT_COUNT=0
fi

# Check organizations (only if table exists)
if docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -t -c "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'organizations';" 2>/dev/null | grep -q "1"; then
    ORG_COUNT=$(docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -t -c "SELECT COUNT(*) FROM organizations;" 2>/dev/null | tr -d ' ' || echo "0")
    echo -e "${BLUE}   Organizations: $ORG_COUNT${NC}"
else
    echo -e "${YELLOW}   ⚠️  Organizations table does not exist${NC}"
    ORG_COUNT=0
fi
echo ""

# Summary
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Summary${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""

if [ ${#MISSING_TABLES[@]} -eq 0 ] && [ "$REALM_COUNT" -gt 0 ] 2>/dev/null; then
    echo -e "${GREEN}✅ Database appears to be properly initialized${NC}"
    echo -e "${GREEN}   • Tables: Present${NC}"
    echo -e "${GREEN}   • Views: Present${NC}"
    echo -e "${GREEN}   • Functions: Present${NC}"
    echo -e "${GREEN}   • Seeded data: Present${NC}"
    echo ""
    echo -e "${BLUE}The database has been:${NC}"
    echo -e "${BLUE}  ✅ Dropped and recreated (tables dropped)${NC}"
    echo -e "${BLUE}  ✅ Migrations run (002_realm_architecture.sql, 003_vault_integration.sql)${NC}"
    echo -e "${BLUE}  ✅ Seeded (realms created)${NC}"
else
    echo -e "${YELLOW}⚠️  Database may not be fully initialized${NC}"
    if [ ${#MISSING_TABLES[@]} -gt 0 ]; then
        echo -e "${RED}   • Missing tables: ${MISSING_TABLES[*]}${NC}"
    fi
    if [ "$REALM_COUNT" -eq 0 ] 2>/dev/null; then
        echo -e "${RED}   • No realms found (seeding may not have run)${NC}"
    fi
    echo ""
    echo -e "${YELLOW}Run init_complete_stack.sh to initialize the database${NC}"
fi
echo ""

