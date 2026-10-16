#!/bin/bash
#
# Push SentinelGrid Base Images to Registry
# ==========================================
#
# Usage:
#   ./push-to-registry.sh                    # Push all images
#   ./push-to-registry.sh runtime            # Push only runtime
#   ./push-to-registry.sh --registry ghcr.io # Use different registry
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
REGISTRY="${REGISTRY:-sentinelgrid}"
TARGET="${1:-all}"

# Parse registry flag
if [[ "$1" == "--registry" ]]; then
    REGISTRY="$2"
    TARGET="${3:-all}"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Push SentinelGrid Base Images${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Registry: ${REGISTRY}"
echo "Target: ${TARGET}"
echo ""

# Function to push image
push_image() {
    local name=$1
    local tag=$2
    
    echo -e "${YELLOW}Pushing: ${REGISTRY}/${name}:${tag}${NC}"
    
    if docker push ${REGISTRY}/${name}:${tag}; then
        echo -e "${GREEN}✓ Pushed: ${REGISTRY}/${name}:${tag}${NC}"
        echo ""
    else
        echo -e "${RED}✗ Failed to push ${REGISTRY}/${name}:${tag}${NC}"
        exit 1
    fi
}

# Check if logged in
echo "Checking registry authentication..."
if ! docker info | grep -q "Username"; then
    echo -e "${YELLOW}⚠ Not logged in to registry${NC}"
    echo "Run: docker login ${REGISTRY}"
    exit 1
fi

# Push images
if [[ "$TARGET" == "all" || "$TARGET" == "runtime" ]]; then
    push_image "runtime-python" "3.11"
fi

if [[ "$TARGET" == "all" || "$TARGET" == "api" ]]; then
    push_image "api-base" "latest"
    push_image "api-base" "1.0"
fi

if [[ "$TARGET" == "all" || "$TARGET" == "ml" ]]; then
    push_image "api-ml" "latest"
    push_image "api-ml" "1.0"
fi

echo -e "${GREEN}✓ All images pushed successfully!${NC}"
echo ""
echo "Images available:"
echo "  - ${REGISTRY}/runtime-python:3.11"
echo "  - ${REGISTRY}/api-base:latest (and :1.0)"
echo "  - ${REGISTRY}/api-ml:latest (and :1.0)"
echo ""

