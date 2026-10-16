#!/bin/bash
#
# Initialize Vault in Production Mode (for dev with TLS)
#
# This script initializes Vault if not already initialized,
# unseals it, and sets up the root token.
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

VAULT_ADDR="${VAULT_ADDR:-https://localhost:8200}"
VAULT_ROOT_TOKEN="${VAULT_ROOT_TOKEN:-sentinelgrid-dev-root-token}"

echo -e "${BLUE}Initializing Vault (Production Mode with TLS)...${NC}"
echo ""

# Wait for Vault to be ready
echo -e "${YELLOW}Waiting for Vault to be ready...${NC}"
RETRY_COUNT=0
MAX_RETRIES=30

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s -k -f "$VAULT_ADDR/v1/sys/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Vault is ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "   Still waiting... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Vault failed to start${NC}"
    exit 1
fi

# Check if Vault is initialized
INIT_STATUS=$(curl -s -k "$VAULT_ADDR/v1/sys/init" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('initialized', False))" 2>/dev/null || echo "false")

if [ "$INIT_STATUS" = "true" ]; then
    echo -e "${BLUE}Vault is already initialized${NC}"
    
    # Check if it's sealed
    SEAL_STATUS=$(curl -s -k "$VAULT_ADDR/v1/sys/seal-status" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('sealed', True))" 2>/dev/null || echo "true")
    
    if [ "$SEAL_STATUS" = "true" ]; then
        echo -e "${YELLOW}Vault is sealed. Attempting to unseal...${NC}"
        echo -e "${YELLOW}⚠️  Note: In production, you would need unseal keys.${NC}"
        echo -e "${YELLOW}   For dev, we'll use the root token to unseal if possible.${NC}"
    else
        echo -e "${GREEN}✅ Vault is unsealed${NC}"
    fi
else
    echo -e "${YELLOW}Initializing Vault...${NC}"
    
    # Initialize Vault (this generates unseal keys and root token)
    INIT_RESPONSE=$(docker exec -e VAULT_ADDR="https://127.0.0.1:8200" -e VAULT_SKIP_VERIFY="true" vault vault operator init -format=json 2>/dev/null || echo "")
    
    if [ -z "$INIT_RESPONSE" ]; then
        echo -e "${RED}❌ Failed to initialize Vault${NC}"
        exit 1
    fi
    
    # Extract unseal keys and root token
    UNSEAL_KEYS=$(echo "$INIT_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(' '.join(d['unseal_keys_b64']))" 2>/dev/null || echo "")
    ROOT_TOKEN=$(echo "$INIT_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['root_token'])" 2>/dev/null || echo "")
    
    if [ -z "$UNSEAL_KEYS" ] || [ -z "$ROOT_TOKEN" ]; then
        echo -e "${RED}❌ Failed to extract unseal keys or root token${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Vault initialized${NC}"
    echo -e "${YELLOW}⚠️  IMPORTANT: Save these unseal keys securely!${NC}"
    echo ""
    echo -e "${CYAN}Unseal Keys:${NC}"
    for key in $UNSEAL_KEYS; do
        echo -e "  ${YELLOW}$key${NC}"
    done
    echo ""
    echo -e "${CYAN}Root Token:${NC} ${YELLOW}$ROOT_TOKEN${NC}"
    echo ""
    
    # Unseal Vault (need 3 of 5 keys by default)
    echo -e "${YELLOW}Unsealing Vault...${NC}"
    KEY_COUNT=0
    for key in $UNSEAL_KEYS; do
        KEY_COUNT=$((KEY_COUNT + 1))
        if [ $KEY_COUNT -le 3 ]; then
            docker exec -e VAULT_ADDR="https://127.0.0.1:8200" -e VAULT_SKIP_VERIFY="true" vault vault operator unseal "$key" > /dev/null 2>&1
        fi
    done
    
    # Verify unsealed
    sleep 2
    SEAL_STATUS=$(curl -s -k "$VAULT_ADDR/v1/sys/seal-status" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('sealed', True))" 2>/dev/null || echo "true")
    
    if [ "$SEAL_STATUS" = "false" ]; then
        echo -e "${GREEN}✅ Vault unsealed${NC}"
    else
        echo -e "${RED}❌ Failed to unseal Vault${NC}"
        exit 1
    fi
    
    # Update root token if needed
    if [ "$ROOT_TOKEN" != "$VAULT_ROOT_TOKEN" ]; then
        echo -e "${YELLOW}⚠️  Root token from initialization: $ROOT_TOKEN${NC}"
        echo -e "${YELLOW}⚠️  Expected token: $VAULT_ROOT_TOKEN${NC}"
        echo -e "${YELLOW}   You may need to update VAULT_ROOT_TOKEN environment variable${NC}"
    fi
fi

echo ""
echo -e "${GREEN}✅ Vault initialization complete${NC}"
echo ""
echo -e "${CYAN}Vault Information:${NC}"
echo -e "  ${BLUE}URL:${NC}   $VAULT_ADDR"
echo -e "  ${BLUE}UI:${NC}    $VAULT_ADDR/ui"
echo -e "  ${BLUE}Token:${NC} $VAULT_ROOT_TOKEN"
echo ""

