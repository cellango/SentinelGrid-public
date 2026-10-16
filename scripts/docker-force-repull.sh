#!/bin/bash
# Force Repull Script for SentinelGrid
# Only use when you need to update 3rd-party images to latest versions

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║           ⚠️  FORCE REPULL - USE WITH CAUTION ⚠️           ║${NC}"
echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}This will repull large 3rd-party images (8GB+ total)${NC}"
echo -e "${YELLOW}Only do this if:${NC}"
echo -e "  • Images are corrupted"
echo -e "  • You need to update to latest versions"
echo -e "  • Troubleshooting image issues"
echo ""

read -p "Are you sure you want to continue? (yes/NO): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo -e "${GREEN}Aborted - no changes made${NC}"
    exit 0
fi
echo ""

# Image categories with sizes
declare -A IMAGE_GROUPS=(
    ["LLM Server"]="vllm/vllm-openai:latest"
    ["Search (OpenSearch)"]="opensearchproject/opensearch:2.11.0 opensearchproject/opensearch-dashboards:2.11.0"
    ["Auth (Keycloak)"]="quay.io/keycloak/keycloak:latest"
    ["Security (Wazuh)"]="quay.io/wazuh/wazuh-manager:latest"
    ["Automation (N8N)"]="docker.n8n.io/n8nio/n8n:latest"
    ["SOAR (StackStorm)"]="stackstorm/stackstorm:latest"
    ["Observability (Cortex)"]="cortexproject/cortex:latest"
    ["Databases"]="postgres:15-alpine redis:7-alpine"
)

# Show menu
echo -e "${BLUE}Select what to repull:${NC}"
echo "  [1] LLM Server only (8.3GB)"
echo "  [2] Search (OpenSearch) (1.2GB)"
echo "  [3] Auth (Keycloak) (600MB)"
echo "  [4] Security (Wazuh) (2GB)"
echo "  [5] Databases (Postgres, Redis) (300MB)"
echo "  [6] All automation tools (N8N, StackStorm, Cortex) (2GB)"
echo "  [7] ALL 3rd-party images (14GB+)"
echo "  [0] Cancel"
echo ""
read -p "Enter choice [0-7]: " -n 1 -r
echo ""

pull_images() {
    local images=$1
    for img in $images; do
        echo -e "${BLUE}Pulling $img...${NC}"
        if docker pull "$img"; then
            echo -e "${GREEN}✓ Successfully pulled $img${NC}"
        else
            echo -e "${RED}✗ Failed to pull $img${NC}"
        fi
        echo ""
    done
}

case $REPLY in
    1)
        echo -e "${YELLOW}Pulling LLM Server (8.3GB - this will take a while)...${NC}"
        pull_images "${IMAGE_GROUPS["LLM Server"]}"
        ;;
    2)
        echo -e "${YELLOW}Pulling OpenSearch stack...${NC}"
        pull_images "${IMAGE_GROUPS["Search (OpenSearch)"]}"
        ;;
    3)
        echo -e "${YELLOW}Pulling Keycloak...${NC}"
        pull_images "${IMAGE_GROUPS["Auth (Keycloak)"]}"
        ;;
    4)
        echo -e "${YELLOW}Pulling Wazuh Manager...${NC}"
        pull_images "${IMAGE_GROUPS["Security (Wazuh)"]}"
        ;;
    5)
        echo -e "${YELLOW}Pulling database images...${NC}"
        pull_images "${IMAGE_GROUPS["Databases"]}"
        ;;
    6)
        echo -e "${YELLOW}Pulling automation tools...${NC}"
        pull_images "${IMAGE_GROUPS["Automation (N8N)"]}"
        pull_images "${IMAGE_GROUPS["SOAR (StackStorm)"]}"
        pull_images "${IMAGE_GROUPS["Observability (Cortex)"]}"
        ;;
    7)
        echo -e "${RED}Pulling ALL images (14GB+)...${NC}"
        for group in "${!IMAGE_GROUPS[@]}"; do
            echo -e "${YELLOW}═══ $group ═══${NC}"
            pull_images "${IMAGE_GROUPS[$group]}"
        done
        ;;
    0|*)
        echo -e "${GREEN}Cancelled${NC}"
        exit 0
        ;;
esac

echo -e "${GREEN}═════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Repull complete!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "  • Run: ${BLUE}./scripts/docker-health-check.sh${NC} to verify"
echo -e "  • Run: ${BLUE}docker-compose -f docker-compose.dev.yml up -d${NC} to restart"
echo ""

