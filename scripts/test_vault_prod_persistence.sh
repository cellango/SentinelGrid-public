#!/bin/bash
#
# Test Vault Production Persistence
# 
# This script tests that Vault secrets persist across container restarts.
# It can be run independently without affecting the dev environment.
#
# Usage: ./scripts/test_vault_prod_persistence.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
VAULT_PROD_ADDR="http://localhost:8210"
VAULT_ROOT_TOKEN="${VAULT_ROOT_TOKEN:-sentinelgrid-prod-root-token-change-me}"
TEST_SECRET_PATH="sentinelgrid/test/persistence-test"
TEST_SECRET_VALUE="test-value-$(date +%s)"
COMPOSE_FILE="docker-compose.dev.yml"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

export VAULT_ADDR="$VAULT_PROD_ADDR"
export VAULT_TOKEN="$VAULT_ROOT_TOKEN"

echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                        ║${NC}"
echo -e "${CYAN}║     ${BLUE}Vault Production Persistence Test${CYAN}                  ║${NC}"
echo -e "${CYAN}║                                                        ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to check if vault container is running
is_vault_running() {
    docker ps --format '{{.Names}}' | grep -q "^vault$" || return 1
}

# Function to wait for Vault to be ready
wait_for_vault() {
    echo -e "${YELLOW}⏳ Waiting for Vault to be ready...${NC}"
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if vault status >/dev/null 2>&1; then
            if vault status 2>/dev/null | grep -q "Sealed.*false"; then
                echo -e "${GREEN}✅ Vault is ready and unsealed${NC}"
                return 0
            fi
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    
    echo -e "${RED}❌ Vault failed to become ready${NC}"
    return 1
}

# Step 1: Start Vault
echo -e "${YELLOW}[1/5] Starting production Vault...${NC}"
if is_vault_running; then
    echo -e "${BLUE}   Vault is already running, restarting to test persistence...${NC}"
    docker-compose -f "$COMPOSE_FILE" restart vault
else
    echo -e "${BLUE}   Starting Vault container...${NC}"
    docker-compose -f "$COMPOSE_FILE" up -d vault
fi

sleep 5
wait_for_vault || {
    echo -e "${RED}❌ Failed to start Vault${NC}"
    docker-compose -f "$COMPOSE_FILE" logs vault
    exit 1
}

# Step 2: Check if initialized and get actual root token if needed
echo ""
echo -e "${YELLOW}[2/5] Checking Vault initialization...${NC}"

# Check if Vault was just initialized and get the actual root token
if [ -f "$PROJECT_ROOT/.vault-root-token" ]; then
    ACTUAL_ROOT_TOKEN=$(cat "$PROJECT_ROOT/.vault-root-token")
    export VAULT_TOKEN="$ACTUAL_ROOT_TOKEN"
    echo -e "${GREEN}   Using stored root token${NC}"
else
    # Try to read from container volume (for testing, we'll check)
    CONTAINER_TOKEN_FILE=$(docker exec vault cat /vault/file/.vault_root_token 2>/dev/null || echo "")
    if [ -n "$CONTAINER_TOKEN_FILE" ]; then
        export VAULT_TOKEN="$CONTAINER_TOKEN_FILE"
        echo "$CONTAINER_TOKEN_FILE" > "$PROJECT_ROOT/.vault-root-token"
        echo -e "${GREEN}   Found root token in persistent storage${NC}"
    else
        echo -e "${YELLOW}   Using provided root token${NC}"
    fi
fi

# Step 3: Enable KV and store test secret
echo ""
echo -e "${YELLOW}[3/5] Storing test secret...${NC}"

# Enable KV v2 if not already enabled
if ! vault secrets list -format=json 2>/dev/null | grep -q "sentinelgrid/"; then
    echo -e "${BLUE}   Enabling KV v2 secrets engine...${NC}"
    vault secrets enable -path=sentinelgrid -version=2 kv || {
        echo -e "${YELLOW}   KV engine may already be enabled${NC}"
    }
fi

# Store test secret
echo -e "${BLUE}   Storing secret: $TEST_SECRET_PATH${NC}"
echo -e "${BLUE}   Value: $TEST_SECRET_VALUE${NC}"

vault kv put "$TEST_SECRET_PATH" value="$TEST_SECRET_VALUE" || {
    echo -e "${RED}❌ Failed to store secret${NC}"
    exit 1
}

# Verify secret was stored
RETRIEVED_VALUE=$(vault kv get -format=json "$TEST_SECRET_PATH" 2>/dev/null | jq -r '.data.data.value // empty')

if [ "$RETRIEVED_VALUE" != "$TEST_SECRET_VALUE" ]; then
    echo -e "${RED}❌ Secret verification failed${NC}"
    echo -e "${RED}   Expected: $TEST_SECRET_VALUE${NC}"
    echo -e "${RED}   Got: $RETRIEVED_VALUE${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Secret stored and verified${NC}"

# Step 4: Restart container
echo ""
echo -e "${YELLOW}[4/5] Restarting Vault container to test persistence...${NC}"
docker-compose -f "$COMPOSE_FILE" restart vault

sleep 5
wait_for_vault || {
    echo -e "${RED}❌ Vault failed to restart${NC}"
    docker-compose -f "$COMPOSE_FILE" logs vault
    exit 1
}

# Step 5: Verify secret still exists after restart
echo ""
echo -e "${YELLOW}[5/5] Verifying secret persistence...${NC}"

# Re-authenticate if needed
if [ -f "$PROJECT_ROOT/.vault-root-token" ]; then
    export VAULT_TOKEN=$(cat "$PROJECT_ROOT/.vault-root-token")
fi

RETRIEVED_VALUE_AFTER_RESTART=$(vault kv get -format=json "$TEST_SECRET_PATH" 2>/dev/null | jq -r '.data.data.value // empty')

if [ -z "$RETRIEVED_VALUE_AFTER_RESTART" ]; then
    echo -e "${RED}❌ Secret was lost after restart!${NC}"
    echo -e "${RED}   Persistence test FAILED${NC}"
    exit 1
fi

if [ "$RETRIEVED_VALUE_AFTER_RESTART" != "$TEST_SECRET_VALUE" ]; then
    echo -e "${RED}❌ Secret value changed after restart!${NC}"
    echo -e "${RED}   Expected: $TEST_SECRET_VALUE${NC}"
    echo -e "${RED}   Got: $RETRIEVED_VALUE_AFTER_RESTART${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Secret persisted correctly after restart!${NC}"
echo -e "${GREEN}   Retrieved value: $RETRIEVED_VALUE_AFTER_RESTART${NC}"

# Cleanup test secret
echo ""
echo -e "${BLUE}Cleaning up test secret...${NC}"
vault kv delete "$TEST_SECRET_PATH" 2>/dev/null || true

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                        ║${NC}"
echo -e "${GREEN}║        ${CYAN}✅ Persistence Test PASSED!${GREEN}                    ║${NC}"
echo -e "${GREEN}║                                                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Vault production setup is working correctly!${NC}"
echo -e "${CYAN}Secrets persist across container restarts.${NC}"
echo ""
