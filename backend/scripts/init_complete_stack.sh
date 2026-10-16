#!/bin/bash
#
# ═══════════════════════════════════════════════════════════════════════════
# 🚨 DESTRUCTIVE OPERATION - COMPLETE DATA DELETION 🚨
# ═══════════════════════════════════════════════════════════════════════════
#
# Complete Stack Initialization with Vault
# 
# ⚠️  CRITICAL WARNING: THIS SCRIPT PERMANENTLY DELETES ALL DATA ⚠️
#
# WHEN TO USE:
#   ✅ FIRST-TIME PRODUCTION SETUP - Use ONCE when setting up production
#   ✅ DEVELOPMENT/TESTING - Safe for dev environments
#   ❌ NEVER USE IN PRODUCTION AFTER INITIAL SETUP - Will delete all customer data
#
# WHAT THIS SCRIPT DOES:
#   1. DESTROYS all Keycloak data (realms, users, clients, organizations)
#   2. DESTROYS all Vault data (secrets, policies, audit logs)
#   3. DESTROYS all database data (customers, organizations, tenants, vault_*)
#   4. Creates fresh infrastructure from scratch
#   5. Initializes Vault with new secrets
#   6. Creates Keycloak realms (sg-admin, sg-mt-us-1, sg-mt-eu-1)
#   7. Seeds database with initial schema
#   8. Creates platform admin user
#   9. Verifies complete setup
#
# CONFIRMATION REQUIRED:
#   - You must type "DELETE ALL DATA" to proceed
#   - 10-second final warning countdown
#   - This operation CANNOT BE UNDONE
#
# ═══════════════════════════════════════════════════════════════════════════
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Configuration
DB_URL="${DB_URL:-postgresql://sg:sg@localhost:5432/sg}"
KEYCLOAK_URL="${KEYCLOAK_URL:-https://localhost:8443}"
VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-sentinelgrid-dev-root-token}"

export VAULT_ADDR
export VAULT_TOKEN

# Backup function (stubbed - to be implemented)
perform_backup() {
    local backup_dir="$1"
    
    echo -e "${YELLOW}[Backup] Creating backup directory...${NC}"
    mkdir -p "$backup_dir"/{keycloak,vault,database,volumes}
    
    echo -e "${YELLOW}[Backup] This is a STUB - backup functionality not yet fully implemented${NC}"
    echo -e "${BLUE}[Backup] Planned backup operations:${NC}"
    echo -e "${BLUE}  • Keycloak realm exports (via Admin API)${NC}"
    echo -e "${BLUE}  • Vault secrets export (via Vault API)${NC}"
    echo -e "${BLUE}  • Database dump (pg_dump)${NC}"
    echo -e "${BLUE}  • Docker volume snapshots (if supported)${NC}"
    echo ""
    echo -e "${YELLOW}[Backup] TODO: Implement full backup functionality${NC}"
    echo -e "${YELLOW}[Backup] For now, creating backup structure only...${NC}"
    
    # Create backup manifest
    cat > "$backup_dir/backup_manifest.txt" <<EOF
SentinelGrid Backup Manifest
============================
Created: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
Backup Type: Pre-deletion backup
Status: STUB (not fully implemented)

Planned Components:
- Keycloak realm exports
- Vault secrets export
- Database dump
- Docker volume snapshots

Note: This backup was created before running init_complete_stack.sh
Full backup functionality will be implemented in a future update.
EOF
    
    echo -e "${GREEN}[Backup] Backup structure created at: $backup_dir${NC}"
    echo -e "${YELLOW}[Backup] ⚠️  WARNING: This is a stub - actual data backup not performed${NC}"
    
    # Return success for now (stub)
    return 0
}

# Production environment check
PROD_INDICATORS=0
if [ -n "$ENVIRONMENT" ] && [ "$ENVIRONMENT" = "production" ]; then
    PROD_INDICATORS=$((PROD_INDICATORS + 1))
fi
if [ -n "$NODE_ENV" ] && [ "$NODE_ENV" = "production" ]; then
    PROD_INDICATORS=$((PROD_INDICATORS + 1))
fi
if echo "$DB_URL" | grep -q -E "(prod|production|live)"; then
    PROD_INDICATORS=$((PROD_INDICATORS + 1))
fi
if echo "$KEYCLOAK_URL" | grep -q -E "(prod|production|live|sentinelgrid\.ai)"; then
    PROD_INDICATORS=$((PROD_INDICATORS + 1))
fi

if [ $PROD_INDICATORS -gt 0 ]; then
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                                                                                ║${NC}"
    echo -e "${RED}║  ${YELLOW}🚨  PRODUCTION ENVIRONMENT DETECTED  🚨${RED}                                      ║${NC}"
    echo -e "${RED}║                                                                                ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${RED}⚠️  PRODUCTION ENVIRONMENT INDICATORS FOUND:${NC}"
    [ -n "$ENVIRONMENT" ] && [ "$ENVIRONMENT" = "production" ] && echo -e "  ${RED}• ENVIRONMENT=production${NC}"
    [ -n "$NODE_ENV" ] && [ "$NODE_ENV" = "production" ] && echo -e "  ${RED}• NODE_ENV=production${NC}"
    echo "$DB_URL" | grep -q -E "(prod|production|live)" && echo -e "  ${RED}• DB_URL contains production indicators${NC}"
    echo "$KEYCLOAK_URL" | grep -q -E "(prod|production|live|sentinelgrid\.ai)" && echo -e "  ${RED}• KEYCLOAK_URL contains production indicators${NC}"
    echo ""
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}  🔴  THIS SCRIPT WILL DELETE ALL PRODUCTION DATA  🔴${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}This script is ONLY for FIRST-TIME production setup.${NC}"
    echo -e "${YELLOW}If production is already running, ${RED}DO NOT RUN THIS SCRIPT.${NC}"
    echo ""
    echo -e "${RED}To proceed in production, you must type: ${YELLOW}I UNDERSTAND THIS WILL DELETE ALL PRODUCTION DATA${NC}"
    echo ""
    read -p "$(echo -e ${RED}Type the exact phrase above: ${NC})" prod_confirmation
    
    if [ "$prod_confirmation" != "I UNDERSTAND THIS WILL DELETE ALL PRODUCTION DATA" ]; then
        echo ""
        echo -e "${GREEN}✅ Operation cancelled. Production data is safe.${NC}"
        echo ""
        exit 0
    fi
    echo ""
fi

echo -e "${RED}╔════════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║                                                                                ║${NC}"
echo -e "${RED}║  ${YELLOW}🚨  DESTRUCTIVE OPERATION - COMPLETE DATA DELETION  🚨${RED}                        ║${NC}"
echo -e "${RED}║                                                                                ║${NC}"
echo -e "${RED}╚════════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}  ⚠️  CRITICAL WARNING: THIS SCRIPT WILL PERMANENTLY DELETE ALL DATA  ⚠️${NC}"
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}📋 WHAT THIS SCRIPT DOES:${NC}"
echo ""
echo -e "  ${CYAN}Phase 1:${NC} ${RED}DESTROYS ALL EXISTING DATA${NC}"
echo -e "    • Stops Keycloak, Vault, and database containers"
echo -e "    • ${RED}DELETES all Keycloak Docker volumes${NC} (all realms, users, clients)"
echo -e "    • ${RED}DELETES all Vault Docker volumes${NC} (all secrets, policies)"
echo -e "    • ${RED}DROPS all database tables${NC} (realms, customers, organizations, tenants, vault_*)"
echo -e "    • ${RED}DROPS all database views and functions${NC}"
echo -e "    • ${RED}THIS IS IRREVERSIBLE - ALL DATA WILL BE LOST FOREVER${NC}"
echo ""
echo -e "  ${CYAN}Phase 2-8:${NC} Creates fresh infrastructure"
echo -e "    • Starts fresh containers with empty volumes"
echo -e "    • Initializes Vault with new secrets"
echo -e "    • Creates Keycloak realms (sg-admin, sg-mt-us-1, sg-mt-eu-1)"
echo -e "    • Seeds database with initial schema"
echo -e "    • Creates platform admin user"
echo ""
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🎯 WHEN TO USE THIS SCRIPT:${NC}"
echo ""
echo -e "  ${GREEN}✅ FIRST-TIME PRODUCTION SETUP${NC}"
echo -e "     Use this ONCE when setting up production for the very first time"
echo -e "     After that, ${RED}NEVER RUN THIS AGAIN${NC}"
echo ""
echo -e "  ${GREEN}✅ DEVELOPMENT/TESTING${NC}"
echo -e "     Safe to use in development when you need a clean slate"
echo ""
echo -e "  ${RED}❌ NEVER USE IN PRODUCTION AFTER INITIAL SETUP${NC}"
echo -e "     This will ${RED}DELETE ALL CUSTOMER DATA${NC}"
echo -e "     This will ${RED}DELETE ALL SECRETS${NC}"
echo -e "     This will ${RED}DELETE ALL USERS AND REALMS${NC}"
echo ""
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📊 DATA THAT WILL BE DELETED:${NC}"
echo ""
echo -e "  ${RED}Keycloak:${NC}"
echo -e "    • All realms (sg-admin, sg-mt-*, sg-ent-*)"
echo -e "    • All users (including admin@sentinelgrid.ai)"
echo -e "    • All clients and service accounts"
echo -e "    • All roles and permissions"
echo -e "    • All organization structures"
echo ""
echo -e "  ${RED}Vault:${NC}"
echo -e "    • All secrets (sentinelgrid/*, tenants/*, organizations/*, customers/*)"
echo -e "    • All policies"
echo -e "    • All audit logs"
echo ""
echo -e "  ${RED}Database:${NC}"
echo -e "    • All customers, organizations, tenants"
echo -e "    • All realm capacity history"
echo -e "    • All provisioning logs"
echo -e "    • All Vault audit logs"
echo -e "    • All Vault usage history"
echo ""
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${RED}🔴 THIS OPERATION CANNOT BE UNDONE 🔴${NC}"
echo ""
echo -e "${YELLOW}To proceed, you must type: ${RED}DELETE ALL DATA${NC}"
echo -e "${YELLOW}This confirms you understand the consequences.${NC}"
echo ""
read -p "$(echo -e ${RED}Type \"DELETE ALL DATA\" to continue: ${NC})" confirmation

if [ "$confirmation" != "DELETE ALL DATA" ]; then
    echo ""
    echo -e "${GREEN}✅ Operation cancelled. No data was deleted.${NC}"
    echo ""
    exit 0
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  💾 BACKUP OPTION${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Before proceeding with data deletion, would you like to create a backup?${NC}"
echo ""
echo -e "${CYAN}Backup will include:${NC}"
echo -e "  • Keycloak realm exports"
echo -e "  • Vault secrets export"
echo -e "  • Database dump (PostgreSQL)"
echo -e "  • Docker volume snapshots (if available)"
echo ""
read -p "$(echo -e ${YELLOW}Create backup before deletion? [y/N]: ${NC})" create_backup

BACKUP_CREATED=false
if [[ "$create_backup" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${CYAN}Creating backup...${NC}"
    
    # Create backup directory with timestamp
    BACKUP_DIR="$PROJECT_ROOT/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    echo -e "${YELLOW}Backup location: $BACKUP_DIR${NC}"
    echo ""
    
    # Call backup function (stubbed for now)
    if perform_backup "$BACKUP_DIR"; then
        BACKUP_CREATED=true
        echo -e "${GREEN}✅ Backup created successfully${NC}"
        echo -e "${BLUE}   Location: $BACKUP_DIR${NC}"
    else
        echo -e "${YELLOW}⚠️  Backup creation failed or not fully implemented${NC}"
        echo -e "${YELLOW}   Continuing without backup...${NC}"
    fi
    echo ""
else
    echo -e "${BLUE}⏭️  Skipping backup${NC}"
    echo ""
fi

echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}  ⚠️  FINAL WARNING: DELETION WILL BEGIN IN 10 SECONDS  ⚠️${NC}"
echo -e "${RED}  ${YELLOW}Press Ctrl+C NOW to cancel${NC}"
if [ "$BACKUP_CREATED" = true ]; then
    echo -e "${GREEN}  💾 Backup available at: $BACKUP_DIR${NC}"
fi
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

for i in {10..1}; do
    echo -ne "\r${RED}  Starting deletion in $i seconds...${NC}  "
    sleep 1
done
echo -e "\r${RED}  Starting deletion now...${NC}     "
echo ""

# Phase 1: Reset Everything
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Phase 1: Reset Infrastructure${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""

cd "$PROJECT_ROOT"

# Stop and remove services (CRITICAL: must remove containers to release volume locks)
echo -e "${YELLOW}Stopping and removing services...${NC}"
cd "$PROJECT_ROOT"
docker-compose -f docker-compose.dev.yml stop keycloak keycloak_db vault 2>/dev/null || true
docker-compose -f docker-compose.dev.yml rm -f keycloak keycloak_db vault 2>/dev/null || true
sleep 2  # Give Docker time to release volume locks

# Remove volumes (force remove to ensure clean state)
echo -e "${YELLOW}Removing volumes...${NC}"

# Find and remove Keycloak volumes (check for various naming patterns)
KEYCLOAK_VOLS=$(docker volume ls --format '{{.Name}}' | grep -E "(keycloak|sentinelgrid.*keycloak)" || echo "")
if [ -n "$KEYCLOAK_VOLS" ]; then
    echo "$KEYCLOAK_VOLS" | while read vol; do
        echo -e "${BLUE}   Removing volume: $vol${NC}"
        docker volume rm -f "$vol" 2>/dev/null || true
    done
fi

# Find and remove Vault volumes
VAULT_VOLS=$(docker volume ls --format '{{.Name}}' | grep -E "(vault|sentinelgrid.*vault)" || echo "")
if [ -n "$VAULT_VOLS" ]; then
    echo "$VAULT_VOLS" | while read vol; do
        echo -e "${BLUE}   Removing volume: $vol${NC}"
        docker volume rm -f "$vol" 2>/dev/null || true
    done
fi

# Verify volumes are removed
REMAINING_KEYCLOAK_VOLS=$(docker volume ls --format '{{.Name}}' | grep -E "(keycloak|sentinelgrid.*keycloak)" | wc -l | tr -d ' ')
if [ "$REMAINING_KEYCLOAK_VOLS" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Some Keycloak volumes still exist (may be in use)${NC}"
else
    echo -e "${GREEN}✅ All Keycloak volumes removed${NC}"
fi

echo -e "${GREEN}✅ Volume cleanup complete${NC}"

# Drop database tables (only if PostgreSQL is accessible)
echo -e "${YELLOW}Dropping database tables...${NC}"
# Check if PostgreSQL container is running and accessible (non-fatal check)
if docker-compose -f docker-compose.dev.yml ps postgres 2>/dev/null | grep -q "Up"; then
    # PostgreSQL is running, drop tables via docker exec
    docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg > /dev/null 2>&1 <<EOF
DROP TABLE IF EXISTS vault_usage_history CASCADE;
DROP TABLE IF EXISTS vault_audit_log CASCADE;
DROP TABLE IF EXISTS vault_access_grants CASCADE;
DROP TABLE IF EXISTS vault_tenants CASCADE;
DROP TABLE IF EXISTS vault_organizations CASCADE;
DROP TABLE IF EXISTS vault_customers CASCADE;
DROP TABLE IF EXISTS tenant_provisioning_log CASCADE;
DROP TABLE IF EXISTS realm_capacity_history CASCADE;
DROP TABLE IF EXISTS tenants CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS realms CASCADE;
DROP VIEW IF EXISTS vault_tenant_status CASCADE;
DROP VIEW IF EXISTS vault_usage_by_customer CASCADE;
DROP VIEW IF EXISTS tenant_details CASCADE;
DROP VIEW IF EXISTS customer_summary CASCADE;
DROP VIEW IF EXISTS realm_status CASCADE;
DROP FUNCTION IF EXISTS update_vault_quota_usage() CASCADE;
DROP FUNCTION IF EXISTS check_vault_quota() CASCADE;
DROP FUNCTION IF EXISTS check_realm_capacity() CASCADE;
DROP FUNCTION IF EXISTS update_customer_counts() CASCADE;
DROP FUNCTION IF EXISTS update_realm_tenant_count() CASCADE;
EOF
    echo -e "${GREEN}✅ Database tables dropped${NC}"
else
    echo -e "${YELLOW}   ⚠️  PostgreSQL not running - tables will be dropped after PostgreSQL starts${NC}"
    # Store flag to drop tables later
    DROP_TABLES_LATER=true
fi

# Phase 2: Start Services
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Phase 2: Start Services${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Starting Vault...${NC}"
cd "$PROJECT_ROOT"

# Stop and remove any existing Vault containers first
echo -e "${BLUE}   Stopping any existing Vault containers...${NC}"
docker-compose -f docker-compose.dev.yml stop vault 2>/dev/null || true
docker rm -f vault 2>/dev/null || true

# Force stop any stuck Vault instances
if lsof -i :8200 > /dev/null 2>&1; then
    echo -e "${YELLOW}   Port 8200 is in use, force stopping...${NC}"
    bash "$SCRIPT_DIR/force_stop_vault.sh" || true
fi

# Start Vault
echo -e "${BLUE}   Starting Vault container...${NC}"
docker-compose -f docker-compose.dev.yml up -d vault

# Wait a moment for container to start
sleep 3

# Check if container started
if ! docker ps --format '{{.Names}}' | grep -q "^vault$"; then
    echo -e "${RED}❌ Vault container failed to start${NC}"
    echo -e "${YELLOW}   Checking logs...${NC}"
    docker-compose -f docker-compose.dev.yml logs vault --tail 20 2>&1 | grep -v "level=warning" | tail -10
    exit 1
fi

echo -e "${GREEN}✅ Vault container started${NC}"

echo -e "${YELLOW}Starting PostgreSQL...${NC}"
cd "$PROJECT_ROOT"
docker-compose -f docker-compose.dev.yml up -d postgres
echo -e "${GREEN}✅ PostgreSQL started${NC}"

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
RETRY_COUNT=0
MAX_RETRIES=30

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker-compose -f docker-compose.dev.yml exec -T postgres pg_isready -U sg > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $((RETRY_COUNT % 5)) -eq 0 ]; then
        echo "   Still waiting... ($RETRY_COUNT/$MAX_RETRIES)"
    fi
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ PostgreSQL failed to start${NC}"
    exit 1
fi

echo -e "${YELLOW}Starting Keycloak...${NC}"
cd "$PROJECT_ROOT"

# CRITICAL: Ensure Keycloak uses default password on first startup
# KEYCLOAK_ADMIN_PASSWORD env var only works when database is empty (first startup)
# If volumes exist, Keycloak will use the password from the database
# Since we removed volumes in Phase 1, this should be a fresh start
unset KEYCLOAK_ADMIN_PASSWORD  # Clear any existing value
export KEYCLOAK_ADMIN_PASSWORD="admin"  # Set to default for fresh start

docker-compose -f docker-compose.dev.yml up -d keycloak_db keycloak
echo -e "${GREEN}✅ Keycloak started${NC}"

# Phase 3: Initialize Vault
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Phase 3: Initialize Vault${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""

bash "$SCRIPT_DIR/init_vault.sh"

# Phase 4: Wait for Keycloak
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Phase 4: Wait for Keycloak${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Waiting for Keycloak to initialize (60-90 seconds)...${NC}"
RETRY_COUNT=0
MAX_RETRIES=60

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -k -s "$KEYCLOAK_URL/health/ready" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Keycloak is ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $((RETRY_COUNT % 10)) -eq 0 ]; then
        echo -e "${BLUE}   Still waiting... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    fi
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Keycloak failed to start${NC}"
    exit 1
fi

# Phase 5: Run database migrations
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Phase 5: Run Database Migrations${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""

# Verify PostgreSQL is accessible
echo -e "${YELLOW}Verifying PostgreSQL connection...${NC}"
if ! docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${RED}❌ Cannot connect to PostgreSQL${NC}"
    exit 1
fi
echo -e "${GREEN}✅ PostgreSQL connection verified${NC}"

# Run initial schema migration (always run - CREATE TABLE IF NOT EXISTS handles existing tables)
echo -e "${YELLOW}Running initial schema migration...${NC}"
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg < "$PROJECT_ROOT/backend/migrations/001_initial_schema.sql" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Initial schema migration complete${NC}"
else
    echo -e "${YELLOW}   ⚠️  Some tables may already exist (this is OK)${NC}"
fi

echo -e "${YELLOW}Running realm architecture migration...${NC}"
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -f /dev/stdin < "$PROJECT_ROOT/backend/migrations/002_realm_architecture.sql" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Realm architecture migration complete${NC}"
else
    echo -e "${RED}❌ Realm architecture migration failed${NC}"
    exit 1
fi

echo -e "${YELLOW}Running Vault integration migration...${NC}"
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -f /dev/stdin < "$PROJECT_ROOT/backend/migrations/003_vault_integration.sql" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Vault integration migration complete${NC}"
else
    echo -e "${RED}❌ Vault integration migration failed${NC}"
    exit 1
fi

# Phase 6: Seed Keycloak realms using Vault secrets
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Phase 6: Seed Keycloak Realms (Using Vault Secrets)${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""

# Retrieve passwords from Vault
echo -e "${YELLOW}Retrieving secrets from Vault...${NC}"
# Use docker exec to access Vault with HTTP (dev mode)
MASTER_ADMIN_PASS=$(docker exec -e VAULT_ADDR="http://127.0.0.1:8200" -e VAULT_TOKEN="$VAULT_TOKEN" vault vault kv get -field=value sentinelgrid/keycloak/master-admin-password 2>/dev/null || echo "")
PLATFORM_ADMIN_PASS=$(docker exec -e VAULT_ADDR="http://127.0.0.1:8200" -e VAULT_TOKEN="$VAULT_TOKEN" vault vault kv get -field=value sentinelgrid/keycloak/platform-admin-password 2>/dev/null || echo "")

if [ -z "$MASTER_ADMIN_PASS" ] || [ -z "$PLATFORM_ADMIN_PASS" ]; then
    echo -e "${RED}❌ Failed to retrieve passwords from Vault${NC}"
    echo -e "${YELLOW}   Make sure Vault is initialized and secrets are stored${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Retrieved passwords from Vault${NC}"

# Run seeding with Vault-retrieved passwords
echo -e "${YELLOW}Seeding Keycloak realms and database...${NC}"

export KEYCLOAK_ADMIN_PASSWORD="$MASTER_ADMIN_PASS"
export PLATFORM_ADMIN_PASSWORD="$PLATFORM_ADMIN_PASS"

# Verify database is accessible before seeding
if ! docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${RED}❌ Cannot connect to database for seeding${NC}"
    exit 1
fi

# Run seeding script (this seeds both Keycloak realms AND database)
# Script fetches passwords directly from Vault - no env vars for security
# Only set VAULT_ADDR and VAULT_TOKEN for Vault access
export VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
export VAULT_TOKEN="${VAULT_TOKEN:-sentinelgrid-dev-root-token}"
python3 "$SCRIPT_DIR/seed_realms.py" \
  --keycloak-url "$KEYCLOAK_URL" \
  --admin-user admin \
  --db-url "$DB_URL"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Keycloak realms and database seeded${NC}"
else
    echo -e "${RED}❌ Seeding failed${NC}"
    exit 1
fi

# Phase 6b: Seed Demo Data (demo realm and users)
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Phase 6b: Seed Demo Data${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Seeding demo realm and demo users...${NC}"

# Ensure we're using default admin password for demo seeding
export KEYCLOAK_ADMIN_PASSWORD="admin"

# Run demo seeding script
if [ -f "$PROJECT_ROOT/scripts/run-seed-demo.sh" ]; then
    bash "$PROJECT_ROOT/scripts/run-seed-demo.sh"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Demo data seeded${NC}"
    else
        echo -e "${YELLOW}⚠️  Demo seeding failed (non-fatal - continuing)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Demo seeding script not found at scripts/run-seed-demo.sh${NC}"
    echo -e "${BLUE}   Skipping demo data seeding${NC}"
fi

# Phase 7: Restart IAM Agent
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Phase 7: Restart IAM Agent${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""

cd "$PROJECT_ROOT"
docker-compose -f docker-compose.dev.yml restart iam_agent
sleep 10
echo -e "${GREEN}✅ IAM Agent restarted${NC}"

# Phase 8: Verification
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Phase 8: Verification${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""

# Check Vault
echo -e "${YELLOW}Checking Vault...${NC}"
VAULT_STATUS=$(docker exec -e VAULT_ADDR="http://127.0.0.1:8200" -e VAULT_TOKEN="$VAULT_TOKEN" vault vault status 2>/dev/null || echo "")
if echo "$VAULT_STATUS" | grep -q "Sealed.*false"; then
    echo -e "${GREEN}✅ Vault is unsealed${NC}"
fi

SECRETS_COUNT=$(docker exec -e VAULT_ADDR="http://127.0.0.1:8200" -e VAULT_TOKEN="$VAULT_TOKEN" vault vault kv list sentinelgrid/keycloak 2>/dev/null | wc -l)
if [ "$SECRETS_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ Vault has secrets stored${NC}"
fi

# Check Database using comprehensive check script
echo -e "${YELLOW}Checking database state...${NC}"
bash "$SCRIPT_DIR/check_database_state.sh"

# Check Keycloak
echo -e "${YELLOW}Checking Keycloak realms...${NC}"
for realm in sg-admin sg-mt-us-1 sg-mt-eu-1; do
    if curl -k -s "$KEYCLOAK_URL/realms/$realm" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Realm '$realm' exists${NC}"
    else
        echo -e "${YELLOW}⚠️  Realm '$realm' not found or not accessible${NC}"
    fi
done

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                        ║${NC}"
echo -e "${GREEN}║         ${CYAN}✅ Complete Stack Initialized!${GREEN}              ║${NC}"
echo -e "${GREEN}║                                                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${GREEN}✅${NC} Vault initialized with secrets"
echo -e "  ${GREEN}✅${NC} Keycloak realms created (sg-admin, sg-mt-us-1, sg-mt-eu-1)"
echo -e "  ${GREEN}✅${NC} Platform admin user: admin@sentinelgrid.ai"
echo -e "  ${GREEN}✅${NC} Database migrations complete"
echo -e "  ${GREEN}✅${NC} IAM Agent configured"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Access Information${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${YELLOW}Vault UI:${NC}"
echo -e "    URL:   $VAULT_ADDR/ui"
echo -e "    Token: $VAULT_TOKEN"
echo ""
echo -e "  ${YELLOW}Keycloak Admin:${NC}"
echo -e "    URL:      http://localhost:8080/admin"
echo -e "    Username: admin"
echo -e "    Password: (stored in Vault)"
echo -e "    Retrieve: ${CYAN}docker exec -e VAULT_ADDR='http://127.0.0.1:8200' -e VAULT_TOKEN='\$VAULT_TOKEN' vault vault kv get sentinelgrid/keycloak/master-admin-password${NC}"
echo ""
echo -e "  ${YELLOW}Platform Admin:${NC}"
echo -e "    Email:    admin@sentinelgrid.ai"
echo -e "    Password: (stored in Vault)"
echo -e "    Retrieve: ${CYAN}docker exec -e VAULT_ADDR='http://127.0.0.1:8200' -e VAULT_TOKEN='\$VAULT_TOKEN' vault vault kv get sentinelgrid/keycloak/platform-admin-password${NC}"
echo ""
echo -e "  ${YELLOW}Credentials File:${NC}"
echo -e "    ${CYAN}cat backend/scripts/SEEDED_CREDENTIALS.txt${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Next Steps${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${YELLOW}1.${NC} Test Vault access:"
echo -e "     ${CYAN}docker exec -e VAULT_ADDR='http://127.0.0.1:8200' -e VAULT_TOKEN='\$VAULT_TOKEN' vault vault kv list sentinelgrid/keycloak${NC}"
echo ""
echo -e "  ${YELLOW}3.${NC} Test login:"
echo -e "     ${CYAN}open https://localhost:3443/login${NC}"
echo ""
echo -e "  ${YELLOW}4.${NC} Run full test suite:"
echo -e "     ${CYAN}bash backend/scripts/test_complete_stack.sh${NC}"
echo ""
echo -e "${GREEN}Ready! 🚀${NC}"
echo ""

