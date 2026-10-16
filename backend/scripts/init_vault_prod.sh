#!/bin/bash
#
# Initialize HashiCorp Vault (Production Mode)
# 
# This script:
# 1. Waits for Vault to be ready
# 2. Checks if Vault is initialized
# 3. Enables secrets engines (KV, Transit, Database, PKI)
# 4. Creates platform admin policy
# 5. Stores initial secrets
#
# This version works with production Vault (port 8210)
# For dev Vault (port 8200), use init_vault.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
VAULT_ADDR="${VAULT_ADDR:-http://localhost:8210}"
VAULT_TOKEN="${VAULT_TOKEN:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Try to get root token from persistent storage
if [ -z "$VAULT_TOKEN" ]; then
    if [ -f "$PROJECT_ROOT/.vault-root-token" ]; then
        VAULT_TOKEN=$(cat "$PROJECT_ROOT/.vault-root-token")
        echo -e "${BLUE}Using stored root token${NC}"
    else
        # Try to read from container
        if docker ps --format '{{.Names}}' | grep -q "^vault$"; then
            CONTAINER_TOKEN=$(docker exec vault cat /vault/file/.vault_root_token 2>/dev/null || echo "")
            if [ -n "$CONTAINER_TOKEN" ]; then
                VAULT_TOKEN="$CONTAINER_TOKEN"
                echo "$CONTAINER_TOKEN" > "$PROJECT_ROOT/.vault-root-token"
                echo -e "${BLUE}Retrieved root token from container${NC}"
            else
                VAULT_TOKEN="${VAULT_ROOT_TOKEN:-}"
            fi
        else
            VAULT_TOKEN="${VAULT_ROOT_TOKEN:-}"
        fi
    fi
fi

if [ "$VAULT_TOKEN" = "sentinelgrid-prod-root-token-change-me" ]; then
    echo -e "${RED}❌ VAULT_TOKEN is using a retired placeholder value${NC}"
    exit 1
fi

if [ -z "$VAULT_TOKEN" ]; then
    echo -e "${RED}❌ VAULT_TOKEN is required. Export VAULT_TOKEN or VAULT_ROOT_TOKEN, or initialize Vault first.${NC}"
    exit 1
fi

export VAULT_ADDR
export VAULT_TOKEN

echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                        ║${NC}"
echo -e "${CYAN}║     ${BLUE}HashiCorp Vault Initialization (Production)${CYAN}      ║${NC}"
echo -e "${CYAN}║                                                        ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 0: Ensure Vault container is running
echo -e "${YELLOW}[0/6] Ensuring Vault container is running...${NC}"

# Check if Vault container exists and is running
if docker ps --format '{{.Names}}' | grep -q "^vault$"; then
    echo -e "${GREEN}✅ Vault container is running${NC}"
elif docker ps -a --format '{{.Names}}' | grep -q "^vault$"; then
    echo -e "${YELLOW}   Vault container exists but is stopped. Starting...${NC}"
    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.vault.yml start vault || docker-compose -f docker-compose.vault.yml up -d vault
    sleep 5
else
    echo -e "${YELLOW}   Vault container not found. Starting...${NC}"
    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.vault.yml up -d vault
    sleep 5
fi

# Step 1: Wait for Vault to be ready
echo -e "${YELLOW}[1/6] Waiting for Vault to be ready...${NC}"

RETRY_COUNT=0
MAX_RETRIES=30

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    # Check if container is running first
    if ! docker ps --format '{{.Names}}' | grep -q "^vault$"; then
        echo "   Container not running yet... ($RETRY_COUNT/$MAX_RETRIES)"
        RETRY_COUNT=$((RETRY_COUNT + 1))
        sleep 2
        continue
    fi
    
    # Check if Vault HTTP endpoint is responding
    if curl -s -f "$VAULT_ADDR/v1/sys/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Vault is ready${NC}"
        break
    fi
    
    if [ $((RETRY_COUNT % 5)) -eq 0 ]; then
        echo -e "${BLUE}   Waiting for Vault to be ready... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Vault failed to start${NC}"
    exit 1
fi

# Step 2: Check Vault status
echo ""
echo -e "${YELLOW}[2/6] Checking Vault status...${NC}"

VAULT_HEALTH=$(curl -s "$VAULT_ADDR/v1/sys/health" 2>/dev/null)
if [ $? -eq 0 ]; then
    if echo "$VAULT_HEALTH" | grep -q '"sealed":false'; then
        echo -e "${GREEN}✅ Vault is unsealed and ready${NC}"
    elif echo "$VAULT_HEALTH" | grep -q '"sealed":true'; then
        echo -e "${RED}❌ Vault is sealed${NC}"
        echo -e "${YELLOW}   Attempting to unseal...${NC}"
        
        # Try to unseal using stored key
        if docker ps --format '{{.Names}}' | grep -q "^vault$"; then
            UNSEAL_KEY=$(docker exec vault cat /vault/file/.vault_unseal_key 2>/dev/null || echo "")
            if [ -n "$UNSEAL_KEY" ]; then
                vault operator unseal "$UNSEAL_KEY"
                echo -e "${GREEN}✅ Vault unsealed${NC}"
            else
                echo -e "${RED}❌ Cannot unseal: unseal key not found${NC}"
                exit 1
            fi
        else
            echo -e "${RED}❌ Cannot unseal: container not running${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✅ Vault is responding${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Could not check Vault status via API${NC}"
fi

# Verify authentication
if ! vault token lookup >/dev/null 2>&1; then
    echo -e "${RED}❌ Authentication failed${NC}"
    echo -e "${YELLOW}   Please check VAULT_TOKEN or set VAULT_ROOT_TOKEN${NC}"
    exit 1
fi

# Step 3: Enable secrets engines
echo ""
echo -e "${YELLOW}[3/6] Enabling secrets engines...${NC}"

# Enable KV v2 for internal secrets
if vault secrets list -format=json 2>/dev/null | grep -q "sentinelgrid/"; then
    echo -e "${BLUE}   ⏭️  sentinelgrid KV already enabled${NC}"
else
    vault secrets enable -path=sentinelgrid -version=2 kv
    echo -e "${GREEN}   ✅ Enabled sentinelgrid KV secrets engine${NC}"
fi

# Enable Transit encryption engine
if vault secrets list -format=json 2>/dev/null | grep -q "transit/"; then
    echo -e "${BLUE}   ⏭️  Transit engine already enabled${NC}"
else
    vault secrets enable transit
    echo -e "${GREEN}   ✅ Enabled transit encryption engine${NC}"
fi

# Enable Database secrets engine
if vault secrets list -format=json 2>/dev/null | grep -q "database/"; then
    echo -e "${BLUE}   ⏭️  Database engine already enabled${NC}"
else
    vault secrets enable database
    echo -e "${GREEN}   ✅ Enabled database secrets engine${NC}"
fi

# Step 4: Create platform admin policy
echo ""
echo -e "${YELLOW}[4/6] Creating platform admin policy...${NC}"

POLICY_FILE="$SCRIPT_DIR/../../infra/vault/policies/platform-admin-policy.hcl"

if [ -f "$POLICY_FILE" ]; then
    vault policy write platform-admin - < "$POLICY_FILE"
    echo -e "${GREEN}✅ Platform admin policy created${NC}"
else
    echo -e "${YELLOW}⚠️  Policy file not found: $POLICY_FILE${NC}"
    echo -e "${YELLOW}   Creating inline policy...${NC}"
    
    vault policy write platform-admin - <<EOF
# Platform admin policy
path "sentinelgrid/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "transit/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "sys/policy/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "sys/mounts/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
EOF
    echo -e "${GREEN}✅ Platform admin policy created (inline)${NC}"
fi

# Step 5: Store initial secrets
echo ""
echo -e "${YELLOW}[5/6] Generating and storing initial secrets...${NC}"

# Generate secure passwords
generate_password() {
    local length=${1:-32}
    python3 << PYEOF
import secrets
import random

def generate_secure_password(length=32):
    """Generate password that meets Keycloak policy: uppercase, lowercase, digits, special chars"""
    upper = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    lower = "abcdefghijkmnopqrstuvwxyz"
    digits = "23456789"
    special = "!@#\$%^&*()_+-=[]{}|;:,.<>?"
    
    password = [
        secrets.choice(upper),
        secrets.choice(lower),
        secrets.choice(digits),
        secrets.choice(special)
    ]
    
    all_chars = upper + lower + digits + special
    remaining = length - 4
    password.extend(secrets.choice(all_chars) for _ in range(remaining))
    
    random.shuffle(password)
    return ''.join(password)

print(generate_secure_password($length))
PYEOF
}

MASTER_ADMIN_PASS=$(generate_password 32)
PLATFORM_ADMIN_PASS=$(generate_password 24)
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/")
INTERNAL_SERVICE_TOKEN=$(openssl rand -hex 64)

# Store in Vault
vault kv put sentinelgrid/keycloak/master-admin-password value="$MASTER_ADMIN_PASS"
vault kv put sentinelgrid/keycloak/platform-admin-password value="$PLATFORM_ADMIN_PASS"
vault kv put sentinelgrid/database/postgres-password value="$DB_PASSWORD"
vault kv put sentinelgrid/services/internal-service-token value="$INTERNAL_SERVICE_TOKEN"

echo -e "${GREEN}✅ Initial secrets stored in Vault${NC}"

# Step 6: Display secrets info
echo ""
echo -e "${YELLOW}[6/6] Secrets stored in Vault:${NC}"
echo -e "${BLUE}   • sentinelgrid/keycloak/master-admin-password${NC}"
echo -e "${BLUE}   • sentinelgrid/keycloak/platform-admin-password${NC}"
echo -e "${BLUE}   • sentinelgrid/database/postgres-password${NC}"
echo -e "${BLUE}   • sentinelgrid/services/internal-service-token${NC}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                        ║${NC}"
echo -e "${GREEN}║          ${CYAN}✅ Vault Initialized!${GREEN}                       ║${NC}"
echo -e "${GREEN}║                                                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Vault Access${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${GREEN}URL:${NC}   $VAULT_ADDR"
echo -e "  ${GREEN}Token:${NC} $VAULT_TOKEN"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Retrieve Secrets${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${YELLOW}vault kv get sentinelgrid/keycloak/master-admin-password${NC}"
echo -e "  ${YELLOW}vault kv get sentinelgrid/keycloak/platform-admin-password${NC}"
echo ""
