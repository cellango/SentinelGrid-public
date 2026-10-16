#!/bin/bash
# Docker Health Check Script for SentinelGrid
# Shows status of all Docker resources and identifies issues

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        SentinelGrid Docker Health Check                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Overall system status
echo -e "${YELLOW}═══ Docker System Status ═══${NC}"
docker system df
echo ""

# Critical 3rd-party images status
echo -e "${YELLOW}═══ Critical 3rd-Party Images ═══${NC}"
CRITICAL_IMAGES=(
    "vllm/vllm-openai:latest"
    "opensearchproject/opensearch:2.11.0"
    "quay.io/keycloak/keycloak:latest"
    "postgres:15-alpine"
    "redis:7-alpine"
)

for img in "${CRITICAL_IMAGES[@]}"; do
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${img}$"; then
        SIZE=$(docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}" | grep "$img" | awk '{print $2}')
        echo -e "${GREEN}✓${NC} $img ${BLUE}($SIZE)${NC}"
    else
        echo -e "${RED}✗${NC} $img ${RED}(MISSING)${NC}"
    fi
done
echo ""

# Critical volumes status
echo -e "${YELLOW}═══ Critical Volumes ═══${NC}"
CRITICAL_VOLUMES=(
    "model_cache"
    "postgres_data"
    "opensearch_data"
    "keycloak_db_data"
)

for vol in "${CRITICAL_VOLUMES[@]}"; do
    # Check with and without sentinelgrid prefix
    FOUND=false
    for prefix in "" "sentinelgrid_" "sentinelgrid-"; do
        FULL_VOL="${prefix}${vol}"
        if docker volume ls -q | grep -q "^${FULL_VOL}$"; then
            SIZE=$(docker system df -v 2>/dev/null | grep "$FULL_VOL" | awk '{print $3}' || echo "unknown")
            MOUNT=$(docker system df -v 2>/dev/null | grep "$FULL_VOL" | awk '{print $4}' || echo "0")
            echo -e "${GREEN}✓${NC} $FULL_VOL ${BLUE}($SIZE, mounted: $MOUNT)${NC}"
            FOUND=true
            break
        fi
    done
    
    if [ "$FOUND" = false ]; then
        echo -e "${YELLOW}⚠${NC} $vol ${YELLOW}(not created yet)${NC}"
    fi
done
echo ""

# Running containers
echo -e "${YELLOW}═══ SentinelGrid Services Status ═══${NC}"
if docker-compose -f docker-compose.dev.yml ps --format json >/dev/null 2>&1; then
    RUNNING=$(docker-compose -f docker-compose.dev.yml ps --services --filter "status=running" 2>/dev/null | wc -l | tr -d ' ')
    TOTAL=$(docker-compose -f docker-compose.dev.yml config --services 2>/dev/null | wc -l | tr -d ' ')
    echo -e "Running: ${GREEN}$RUNNING${NC} / $TOTAL services"
    echo ""
    
    # Show stopped services
    STOPPED=$(docker-compose -f docker-compose.dev.yml ps --services --filter "status=exited" 2>/dev/null || true)
    if [ -n "$STOPPED" ]; then
        echo -e "${RED}Stopped services:${NC}"
        echo "$STOPPED" | while read svc; do
            echo -e "  ${RED}✗${NC} $svc"
        done
        echo ""
    fi
else
    echo -e "${YELLOW}No services currently managed by docker-compose${NC}"
    echo ""
fi

# Disk usage breakdown
echo -e "${YELLOW}═══ Disk Usage Breakdown ═══${NC}"
echo "Images:"
IMAGES_SIZE=$(docker images --format "{{.Size}}" | sed 's/[^0-9.]//g' | awk '{sum+=$1} END {print sum " MB"}')
IMAGES_COUNT=$(docker images -q | wc -l | tr -d ' ')
echo -e "  ${BLUE}$IMAGES_COUNT${NC} images using ${BLUE}$IMAGES_SIZE${NC}"

echo "Containers:"
CONTAINERS_RUNNING=$(docker ps -q | wc -l | tr -d ' ')
CONTAINERS_TOTAL=$(docker ps -aq | wc -l | tr -d ' ')
echo -e "  ${GREEN}$CONTAINERS_RUNNING${NC} running, ${BLUE}$CONTAINERS_TOTAL${NC} total"

echo "Volumes:"
VOLUMES_COUNT=$(docker volume ls -q | wc -l | tr -d ' ')
echo -e "  ${BLUE}$VOLUMES_COUNT${NC} volumes"

echo "Build Cache:"
BUILD_CACHE=$(docker system df | grep "Build Cache" | awk '{print $4}')
echo -e "  ${BLUE}$BUILD_CACHE${NC}"
echo ""

# Recommendations
echo -e "${YELLOW}═══ Recommendations ═══${NC}"
RECLAIMABLE=$(docker system df | tail -1 | awk '{print $4}' | sed 's/[()]//g')
if [ "$RECLAIMABLE" != "0B" ]; then
    echo -e "${YELLOW}⚠${NC} Can reclaim ${YELLOW}$RECLAIMABLE${NC} by running:"
    echo -e "  ${BLUE}./scripts/docker-safe-prune.sh${NC}"
else
    echo -e "${GREEN}✓${NC} System is clean"
fi

# Check for old containers
OLD_CONTAINERS=$(docker ps -a --filter "status=exited" --filter "status=created" -q | wc -l | tr -d ' ')
if [ "$OLD_CONTAINERS" -gt 0 ]; then
    echo -e "${YELLOW}⚠${NC} Found ${YELLOW}$OLD_CONTAINERS${NC} stopped containers"
    echo -e "  Run: ${BLUE}docker container prune${NC}"
fi

# Check for dangling images
DANGLING=$(docker images -f "dangling=true" -q | wc -l | tr -d ' ')
if [ "$DANGLING" -gt 0 ]; then
    echo -e "${YELLOW}⚠${NC} Found ${YELLOW}$DANGLING${NC} dangling images"
    echo -e "  Run: ${BLUE}docker image prune${NC}"
fi
echo ""

echo -e "${GREEN}Health check complete!${NC}"

