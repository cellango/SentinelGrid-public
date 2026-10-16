#!/bin/bash
#
# Force Stop Vault - Kills all Vault containers and processes using port 8200
#
# Use this script when Vault fails to start but still holds port 8200
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

cd "$PROJECT_ROOT"

echo -e "${BLUE}Stopping Vault and freeing port 8200...${NC}"
echo ""

# Step 1: Try graceful stop via docker-compose first
echo -e "${YELLOW}[1/5] Stopping Vault gracefully via docker-compose...${NC}"
# Stop running containers
docker-compose -f docker-compose.dev.yml stop vault 2>/dev/null || true
sleep 2
# Remove both running and stopped containers
docker-compose -f docker-compose.dev.yml rm -f vault 2>/dev/null || true
# Also remove any Vault containers by name (in case they're not managed by compose)
VAULT_CONTAINERS=$(docker ps -a --filter "name=vault" --format "{{.ID}}" 2>/dev/null || echo "")
if [ -n "$VAULT_CONTAINERS" ]; then
    echo "$VAULT_CONTAINERS" | xargs docker rm -f 2>/dev/null || true
    echo -e "${GREEN}✅ Removed all Vault containers (running and stopped)${NC}"
else
    echo -e "${BLUE}   ⏭️  No Vault containers found${NC}"
fi

# Step 2: Check if port is free after graceful stop
echo -e "${YELLOW}[2/5] Checking if port 8200 is free...${NC}"
sleep 1
if ! lsof -i :8200 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Port 8200 is free after graceful stop${NC}"
    echo ""
    echo -e "${GREEN}✅ Vault stopped successfully. Port 8200 is available.${NC}"
    exit 0
fi

# Step 3: Force kill Vault containers if port still in use
echo -e "${YELLOW}[3/5] Port still in use. Force killing Vault containers...${NC}"
VAULT_CONTAINERS=$(docker ps -a --filter "name=vault" --format "{{.ID}}" 2>/dev/null || echo "")
if [ -n "$VAULT_CONTAINERS" ]; then
    echo "$VAULT_CONTAINERS" | xargs docker kill 2>/dev/null || true
    sleep 1
    echo "$VAULT_CONTAINERS" | xargs docker rm -f 2>/dev/null || true
    echo -e "${GREEN}✅ Force killed and removed Vault containers${NC}"
else
    echo -e "${BLUE}   ⏭️  No Vault containers found${NC}"
fi

# Step 4: Kill host processes using port 8200
echo -e "${YELLOW}[4/5] Killing host processes using port 8200...${NC}"
PIDS=$(lsof -ti :8200 2>/dev/null || echo "")
if [ -n "$PIDS" ]; then
    echo "$PIDS" | xargs kill -9 2>/dev/null || true
    echo -e "${GREEN}✅ Killed processes on port 8200: $PIDS${NC}"
else
    echo -e "${BLUE}   ⏭️  No host processes found on port 8200${NC}"
fi

# Step 5: Verify port is free
echo -e "${YELLOW}[5/5] Verifying port 8200 is free...${NC}"
sleep 2
if lsof -i :8200 > /dev/null 2>&1; then
    echo -e "${RED}❌ Port 8200 is still in use!${NC}"
    echo -e "${YELLOW}   Processes using port 8200:${NC}"
    lsof -i :8200
    exit 1
else
    echo -e "${GREEN}✅ Port 8200 is free${NC}"
fi

echo ""
echo -e "${GREEN}✅ Vault force stop complete. Port 8200 is now available.${NC}"
echo ""

