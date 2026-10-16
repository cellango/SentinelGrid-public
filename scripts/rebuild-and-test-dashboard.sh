#!/bin/bash

# Script to rebuild Docker containers without cache and run welcome dashboard Selenium test
# Usage: ./scripts/rebuild-and-test-dashboard.sh

set -e

echo "=========================================="
echo "Rebuild Containers & Run Dashboard Test"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

# Step 1: Stop existing containers
echo -e "${BLUE}Step 1: Stopping existing containers...${NC}"
docker-compose -f docker-compose.dev.yml down
echo -e "${GREEN}✅ Containers stopped${NC}"
echo ""

# Step 2: Rebuild all containers without cache
echo -e "${BLUE}Step 2: Rebuilding all containers without cache...${NC}"
echo "This may take several minutes..."
echo ""

docker-compose -f docker-compose.dev.yml build --no-cache

echo -e "${GREEN}✅ Containers rebuilt${NC}"
echo ""

# Step 3: Start services
echo -e "${BLUE}Step 3: Starting services...${NC}"
docker-compose -f docker-compose.dev.yml up -d

echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
echo "This may take 1-2 minutes..."
echo ""

# Wait for postgres to be healthy
echo -e "${YELLOW}  Waiting for PostgreSQL...${NC}"
timeout=60
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker-compose -f docker-compose.dev.yml ps postgres | grep -q "healthy"; then
        echo -e "${GREEN}  ✅ PostgreSQL is healthy${NC}"
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
    echo -n "."
done
echo ""

if [ $elapsed -ge $timeout ]; then
    echo -e "${RED}❌ PostgreSQL did not become healthy in time${NC}"
    exit 1
fi

# Wait for keycloak to be healthy
echo -e "${YELLOW}  Waiting for Keycloak...${NC}"
timeout=90
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker-compose -f docker-compose.dev.yml ps keycloak | grep -q "healthy"; then
        echo -e "${GREEN}  ✅ Keycloak is healthy${NC}"
        break
    fi
    sleep 3
    elapsed=$((elapsed + 3))
    echo -n "."
done
echo ""

if [ $elapsed -ge $timeout ]; then
    echo -e "${YELLOW}⚠️  Keycloak may still be starting, continuing anyway...${NC}"
fi

# Wait for frontend to be healthy
echo -e "${YELLOW}  Waiting for Frontend...${NC}"
timeout=120
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker-compose -f docker-compose.dev.yml ps frontend | grep -q "healthy"; then
        echo -e "${GREEN}  ✅ Frontend is healthy${NC}"
        break
    fi
    sleep 3
    elapsed=$((elapsed + 3))
    echo -n "."
done
echo ""

if [ $elapsed -ge $timeout ]; then
    echo -e "${YELLOW}⚠️  Frontend may still be starting, continuing anyway...${NC}"
fi

# Give services a bit more time to fully initialize
echo -e "${YELLOW}  Giving services additional time to initialize...${NC}"
sleep 10

echo -e "${GREEN}✅ Services started${NC}"
echo ""

# Step 4: Check service status
echo -e "${BLUE}Step 4: Checking service status...${NC}"
docker-compose -f docker-compose.dev.yml ps
echo ""

# Step 5: Verify frontend is accessible
echo -e "${BLUE}Step 5: Verifying frontend is accessible...${NC}"
FRONTEND_URL="${WEBSITE_URL:-https://localhost:3443}"

if command -v curl &> /dev/null; then
    echo "  Checking $FRONTEND_URL..."
    max_attempts=10
    attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -k -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL" | grep -q "200\|301\|302"; then
            echo -e "${GREEN}  ✅ Frontend is accessible${NC}"
            break
        fi
        attempt=$((attempt + 1))
        echo "  Attempt $attempt/$max_attempts failed, retrying in 5 seconds..."
        sleep 5
    done
    
    if [ $attempt -ge $max_attempts ]; then
        echo -e "${RED}  ❌ Frontend is not accessible after $max_attempts attempts${NC}"
        echo "  Check logs with: docker-compose -f docker-compose.dev.yml logs frontend"
        exit 1
    fi
else
    echo -e "${YELLOW}  ⚠️  curl not available, skipping connectivity check${NC}"
fi
echo ""

# Step 6: Run the Selenium test
echo -e "${BLUE}Step 6: Running Selenium test...${NC}"
echo ""

# Run the existing test script
"$SCRIPT_DIR/run-welcome-dashboard-test.sh"

TEST_EXIT_CODE=$?

echo ""
echo "=========================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Test passed successfully!${NC}"
    echo "=========================================="
else
    echo -e "${RED}❌ Test failed!${NC}"
    echo "=========================================="
    echo ""
    echo "To debug:"
    echo "  1. Check service logs: docker-compose -f docker-compose.dev.yml logs"
    echo "  2. Check frontend logs: docker-compose -f docker-compose.dev.yml logs frontend"
    echo "  3. Check test screenshots in /tmp/"
fi

exit $TEST_EXIT_CODE

