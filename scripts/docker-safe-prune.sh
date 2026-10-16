#!/bin/bash
# Safe Docker Prune Script for SentinelGrid
# Removes development artifacts while protecting critical 3rd-party resources

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Critical volumes that should NEVER be pruned
PROTECTED_VOLUMES=(
    "sentinelgrid_model_cache"
    "sentinelgrid_postgres_data"
    "sentinelgrid_opensearch_data"
    "sentinelgrid_keycloak_db_data"
    "sentinelgrid_redis_data"
    "sentinelgrid_n8n_data"
    "sentinelgrid_step_ca_data"
    "model_cache"
    "postgres_data"
    "opensearch_data"
)

# Critical 3rd-party images that are expensive to repull (size > 500MB)
PROTECTED_IMAGES=(
    "vllm/vllm-openai"
    "opensearchproject/opensearch"
    "opensearchproject/opensearch-dashboards"
    "quay.io/keycloak/keycloak"
    "quay.io/wazuh/wazuh-manager"
    "docker.n8n.io/n8nio/n8n"
    "stackstorm/stackstorm"
    "cortexproject/cortex"
)

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        SentinelGrid Safe Docker Prune Tool                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to check if volume is protected
is_protected_volume() {
    local vol=$1
    for protected in "${PROTECTED_VOLUMES[@]}"; do
        if [[ "$vol" == *"$protected"* ]]; then
            return 0
        fi
    done
    return 1
}

# Function to check if image is protected
is_protected_image() {
    local img=$1
    for protected in "${PROTECTED_IMAGES[@]}"; do
        if [[ "$img" == *"$protected"* ]]; then
            return 0
        fi
    done
    return 1
}

# Show current Docker usage
echo -e "${YELLOW}Current Docker Usage:${NC}"
docker system df
echo ""

# 1. Remove stopped containers (safe - no data loss)
echo -e "${GREEN}[1/5] Removing stopped containers...${NC}"
STOPPED=$(docker ps -aq -f status=exited 2>/dev/null || true)
if [ -n "$STOPPED" ]; then
    docker rm $STOPPED
    echo -e "${GREEN}✓ Removed stopped containers${NC}"
else
    echo -e "${BLUE}  No stopped containers to remove${NC}"
fi
echo ""

# 2. Remove dangling images (safe - these are untagged layers)
echo -e "${GREEN}[2/5] Removing dangling images...${NC}"
DANGLING=$(docker images -f "dangling=true" -q 2>/dev/null || true)
if [ -n "$DANGLING" ]; then
    docker rmi $DANGLING
    echo -e "${GREEN}✓ Removed dangling images${NC}"
else
    echo -e "${BLUE}  No dangling images to remove${NC}"
fi
echo ""

# 3. Remove unused build cache (safe - can be rebuilt)
echo -e "${GREEN}[3/5] Removing unused build cache...${NC}"
docker builder prune -f --filter "until=24h"
echo -e "${GREEN}✓ Removed build cache older than 24 hours${NC}"
echo ""

# 4. Check for unused SentinelGrid service images (our built images)
echo -e "${GREEN}[4/5] Checking for unused SentinelGrid service images...${NC}"
SENTINELGRID_IMAGES=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep "sentinelgrid" || true)
if [ -n "$SENTINELGRID_IMAGES" ]; then
    echo -e "${YELLOW}Found SentinelGrid service images (safe to rebuild):${NC}"
    echo "$SENTINELGRID_IMAGES" | head -10
    
    read -p "Remove ALL unused SentinelGrid service images? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker images --format "{{.Repository}}:{{.Tag}} {{.ID}}" | \
            grep "sentinelgrid" | \
            awk '{print $2}' | \
            xargs -r docker rmi -f 2>/dev/null || true
        echo -e "${GREEN}✓ Removed unused SentinelGrid images${NC}"
    else
        echo -e "${BLUE}  Skipped SentinelGrid image cleanup${NC}"
    fi
else
    echo -e "${BLUE}  No SentinelGrid images to clean${NC}"
fi
echo ""

# 5. Check volumes (CAREFUL - show what would be removed)
echo -e "${GREEN}[5/5] Checking volumes...${NC}"
echo -e "${YELLOW}Protected volumes (will NEVER be removed):${NC}"
for vol in "${PROTECTED_VOLUMES[@]}"; do
    if docker volume ls -q | grep -q "$vol"; then
        SIZE=$(docker system df -v | grep "$vol" | awk '{print $3}' || echo "unknown")
        echo -e "${GREEN}  ✓ $vol ($SIZE)${NC}"
    fi
done
echo ""

# Show unprotected volumes
UNPROTECTED=$(docker volume ls -q | while read vol; do
    if ! is_protected_volume "$vol"; then
        echo "$vol"
    fi
done)

if [ -n "$UNPROTECTED" ]; then
    echo -e "${YELLOW}Unprotected volumes (candidates for removal):${NC}"
    echo "$UNPROTECTED" | while read vol; do
        SIZE=$(docker system df -v | grep "$vol" | awk '{print $3}' || echo "unknown")
        echo -e "${YELLOW}  ⚠ $vol ($SIZE)${NC}"
    done
    echo ""
    
    read -p "Remove unprotected volumes? This may cause data loss! (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "$UNPROTECTED" | xargs -r docker volume rm
        echo -e "${GREEN}✓ Removed unprotected volumes${NC}"
    else
        echo -e "${BLUE}  Skipped volume cleanup${NC}"
    fi
else
    echo -e "${GREEN}  No unprotected volumes found${NC}"
fi
echo ""

# Summary
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Cleanup Complete!${NC}"
echo ""
echo -e "${YELLOW}After cleanup:${NC}"
docker system df
echo ""

echo -e "${BLUE}Protected Resources:${NC}"
echo -e "  • ${GREEN}${#PROTECTED_VOLUMES[@]}${NC} critical volumes preserved"
echo -e "  • ${GREEN}${#PROTECTED_IMAGES[@]}${NC} expensive images protected"
echo ""

echo -e "${YELLOW}To repull protected images if needed, run:${NC}"
echo -e "  ${BLUE}./scripts/docker-force-repull.sh${NC}"
echo ""

