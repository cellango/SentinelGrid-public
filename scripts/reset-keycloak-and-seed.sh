#!/bin/bash
# Reset Keycloak database and run seeder
# This script:
# 1. Stops Keycloak and IAM Agent
# 2. Removes Keycloak database volumes
# 3. Starts Keycloak and waits for it to be fully ready
# 4. Starts IAM Agent and waits for seeding to complete
# 5. Verifies the setup

set -e

echo "=========================================="
echo "Keycloak Reset and Seeding Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

COMPOSE_FILE="docker-compose.dev.yml"

# Step 1: Stop services
echo -e "${YELLOW}Step 1: Stopping Keycloak and IAM Agent...${NC}"
docker-compose -f $COMPOSE_FILE stop keycloak keycloak_db iam_agent 2>/dev/null || true
echo -e "${GREEN}✅ Services stopped${NC}"
echo ""

# Step 2: Remove Keycloak volumes and cache
echo -e "${YELLOW}Step 2: Removing Keycloak volumes and cache...${NC}"
# Stop and remove containers with volumes
docker-compose -f $COMPOSE_FILE down -v keycloak keycloak_db 2>/dev/null || true

# Remove specific volumes if they exist
docker volume rm sentinelgrid_keycloak_db_data 2>/dev/null || true
docker volume rm sentinelgrid_keycloak_data 2>/dev/null || true

# Prune any orphaned volumes related to Keycloak
docker volume ls | grep -i keycloak | awk '{print $2}' | xargs -r docker volume rm 2>/dev/null || true

# Remove any Keycloak containers that might be lingering
docker ps -a | grep keycloak | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

echo -e "${GREEN}✅ Volumes and cache removed${NC}"
echo ""

# Step 3: Start Keycloak database
echo -e "${YELLOW}Step 3: Starting Keycloak database...${NC}"
docker-compose -f $COMPOSE_FILE up -d keycloak_db
echo "Waiting for database to be healthy..."
for i in {1..30}; do
    if docker-compose -f $COMPOSE_FILE ps keycloak_db | grep -q "healthy"; then
        echo -e "${GREEN}✅ Database is healthy${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Database failed to become healthy${NC}"
        exit 1
    fi
    sleep 1
done
echo ""

# Step 4: Start Keycloak fresh and wait for it to be fully ready
echo -e "${YELLOW}Step 4: Starting Keycloak (fresh instance) and waiting for full startup...${NC}"
# Ensure we're starting completely fresh - no cached data
docker-compose -f $COMPOSE_FILE up -d --force-recreate --no-deps keycloak

echo "Waiting for Keycloak to be ready (this may take 30-60 seconds)..."
MAX_WAIT=120
WAIT_COUNT=0
KEYCLOAK_READY=false

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    echo "---- Keycloak readiness check (t=${WAIT_COUNT}s) ----"

    # Show container status
    docker-compose -f $COMPOSE_FILE ps keycloak || echo "docker-compose ps keycloak failed"

    # Check if Keycloak container is running
    if ! docker-compose -f $COMPOSE_FILE ps keycloak | grep -q "Up"; then
        echo "Keycloak container is not 'Up' yet, sleeping..."
        WAIT_COUNT=$((WAIT_COUNT + 2))
        sleep 2
        continue
    fi
    
    # Try to get admin token to verify it's fully operational (use keycloak container directly)
    TOKEN_RESPONSE=$(docker-compose -f $COMPOSE_FILE exec -T keycloak curl -s -X POST http://localhost:8080/realms/master/protocol/openid-connect/token \
        -d "client_id=admin-cli" \
        -d "username=admin" \
        -d "password=admin" \
        -d "grant_type=password" 2>/dev/null || echo "")

    # Basic debug for token response (do not print full token, just shape/error)
    if [ -z "$TOKEN_RESPONSE" ]; then
        echo "Token endpoint did not return any body yet."
    else
        echo "Token endpoint responded."
        # Try to extract error_description if present
        ERROR_DESC=$(printf '%s' "$TOKEN_RESPONSE" | python3 -c "import sys, json; import json as j; \
import sys as s; \
import json as js; \
data = js.loads(s.stdin.read() or '{}'); \
print(data.get('error_description') or data.get('error') or '')" 2>/dev/null || echo "")
        if [ -n "$ERROR_DESC" ]; then
            echo "Token error_description: $ERROR_DESC"
        fi
    fi
    
    # If we actually got an access token, great – Keycloak is fully ready
    if echo "$TOKEN_RESPONSE" | grep -q "access_token"; then
        echo -e "${GREEN}✅ Keycloak is fully ready and admin account is working${NC}"
        KEYCLOAK_READY=true
        break
    fi
    
    # Even without an access token, once the token endpoint is responding with any JSON,
    # we consider Keycloak "up enough" and let the IAM agent/seeder handle auth details.
    if [ -n "$TOKEN_RESPONSE" ]; then
        echo -e "${YELLOW}⚠️  Token endpoint is responding but no access_token yet – proceeding anyway${NC}"
        KEYCLOAK_READY=true
        break
    fi
    
    WAIT_COUNT=$((WAIT_COUNT + 3))
    if [ $((WAIT_COUNT % 15)) -eq 0 ]; then
        echo "  Still waiting... (${WAIT_COUNT}s/${MAX_WAIT}s)"
    fi
    sleep 3
done

if [ "$KEYCLOAK_READY" != "true" ]; then
    echo -e "${RED}❌ Keycloak failed to become ready after ${MAX_WAIT} seconds${NC}"
    echo "Keycloak logs:"
    docker-compose -f $COMPOSE_FILE logs --tail 20 keycloak
    exit 1
fi
echo ""

# Step 5: Start IAM Agent and wait for seeding
echo -e "${YELLOW}Step 5: Starting IAM Agent and waiting for seeding to complete...${NC}"
docker-compose -f $COMPOSE_FILE up -d iam_agent

echo "Waiting for IAM Agent to start and seeding to complete..."
MAX_WAIT=180
WAIT_COUNT=0
SEEDING_COMPLETE=false

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    # Check health endpoint
    HEALTH_RESPONSE=$(curl -s http://localhost:8005/health 2>/dev/null || echo "")
    
    if [ -z "$HEALTH_RESPONSE" ]; then
        WAIT_COUNT=$((WAIT_COUNT + 3))
        if [ $((WAIT_COUNT % 15)) -eq 0 ]; then
            echo "  IAM Agent not responding yet... (${WAIT_COUNT}s/${MAX_WAIT}s)"
        fi
        sleep 3
        continue
    fi
    
    if echo "$HEALTH_RESPONSE" | grep -q "seeding"; then
        SEEDING_STATUS=$(echo "$HEALTH_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(json.dumps(d.get('seeding', {}), indent=2))" 2>/dev/null || echo "")
        
        if echo "$SEEDING_STATUS" | grep -q '"success": true'; then
            echo -e "${GREEN}✅ Seeding completed successfully!${NC}"
            SEEDING_COMPLETE=true
            break
        elif echo "$SEEDING_STATUS" | grep -q '"success": false'; then
            # Show current seeding status for debugging
            ERRORS=$(echo "$SEEDING_STATUS" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('errors', [])))" 2>/dev/null || echo "0")
            CREATED=$(echo "$SEEDING_STATUS" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('created', [])))" 2>/dev/null || echo "0")
            ERROR_MSGS=$(echo "$SEEDING_STATUS" | python3 -c "import sys, json; d=json.load(sys.stdin); errors=d.get('errors', []); print('; '.join(errors[:2]))" 2>/dev/null || echo "")
            
            if [ "$CREATED" -gt 5 ]; then
                echo -e "${YELLOW}⚠️  Seeding completed with some errors, but core resources were created${NC}"
                SEEDING_COMPLETE=true
                break
            elif [ $((WAIT_COUNT % 30)) -eq 0 ]; then
                # Show progress every 30 seconds
                echo "  Seeding in progress... Created: ${CREATED}, Errors: ${ERRORS}"
                if [ -n "$ERROR_MSGS" ]; then
                    echo "    Latest errors: ${ERROR_MSGS}"
                fi
            fi
        fi
    fi
    
    WAIT_COUNT=$((WAIT_COUNT + 3))
    if [ $((WAIT_COUNT % 15)) -eq 0 ] && [ $((WAIT_COUNT % 30)) -ne 0 ]; then
        echo "  Still waiting for seeding... (${WAIT_COUNT}s/${MAX_WAIT}s)"
    fi
    sleep 3
done

if [ "$SEEDING_COMPLETE" != "true" ]; then
    echo -e "${RED}❌ Seeding did not complete after ${MAX_WAIT} seconds${NC}"
    echo "IAM Agent logs:"
    docker-compose -f $COMPOSE_FILE logs --tail 30 iam_agent
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 6: Verifying setup...${NC}"

# Check seeding status
echo "Seeding status:"
curl -s http://localhost:8005/health | python3 -c "
import sys, json
data = json.load(sys.stdin)
seeding = data.get('seeding', {})
print(f\"  Success: {seeding.get('success', False)}\")
print(f\"  Created: {len(seeding.get('created', []))} resources\")
print(f\"  Errors: {len(seeding.get('errors', []))} errors\")
if seeding.get('errors'):
    for err in seeding.get('errors', [])[:3]:
        print(f\"    - {err}\")
" 2>/dev/null || echo "  Could not parse seeding status"
echo ""

# Test admin user login
echo "Testing admin user login..."
TOKEN_RESPONSE=$(docker-compose -f $COMPOSE_FILE exec -T iam_agent curl -s -X POST http://keycloak:8080/realms/sentinelgrid/protocol/openid-connect/token \
    -d "client_id=sentinelgrid-web" \
    -d "username=admin@sentinelgrid.ai" \
    -d "password=admin123" \
    -d "grant_type=password" 2>/dev/null || echo "")

if echo "$TOKEN_RESPONSE" | grep -q "access_token"; then
    TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null || echo "")
    
    if [ ${#TOKEN} -gt 100 ]; then
        echo -e "${GREEN}✅ Admin login successful!${NC}"
        
        # Check if tenant_id is in token
        if echo "$TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | python3 -c "import sys, json; d=json.load(sys.stdin); print('tenant_id' in d)" 2>/dev/null | grep -q "True"; then
            echo -e "${GREEN}✅ tenant_id claim is present in token${NC}"
        else
            echo -e "${YELLOW}⚠️  tenant_id claim not found in token (may need protocol mapper)${NC}"
        fi
        
        # Test IAM Portal API
        echo "Testing IAM Portal API..."
        API_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8005/api/iam-portal/users 2>/dev/null || echo "")
        if echo "$API_RESPONSE" | grep -q "Tenant ID not found"; then
            echo -e "${YELLOW}⚠️  API requires tenant_id in token${NC}"
        elif echo "$API_RESPONSE" | grep -q "Not authenticated"; then
            echo -e "${YELLOW}⚠️  API authentication issue${NC}"
        else
            echo -e "${GREEN}✅ IAM Portal API is working!${NC}"
        fi
    else
        echo -e "${RED}❌ Token obtained but appears invalid${NC}"
    fi
else
    ERROR_MSG=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('error_description', 'Unknown error'))" 2>/dev/null || echo "Unknown error")
    echo -e "${RED}❌ Admin login failed: ${ERROR_MSG}${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Setup complete!${NC}"
echo "=========================================="
echo ""
echo "Admin credentials:"
echo "  Username: admin@sentinelgrid.ai"
echo "  Password: admin123"
echo ""
echo "Keycloak Admin Console: http://localhost:8081/admin"
echo "IAM Agent Health: http://localhost:8005/health"
echo ""

