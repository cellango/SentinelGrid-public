#!/bin/bash
#
# SentinelGrid Base Images - Build Script
# ========================================
#
# Builds all SentinelGrid base images in correct order
# 
# Usage:
#   ./build-all.sh              # Build all images
#   ./build-all.sh --no-cache   # Force rebuild without cache
#   ./build-all.sh runtime      # Build only runtime tier
#   ./build-all.sh api          # Build runtime + api-base
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="sentinelgrid"
BUILD_ARGS=""

# Parse arguments
if [[ "$1" == "--no-cache" ]]; then
    BUILD_ARGS="--no-cache"
    shift
fi

TARGET="${1:-all}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}SentinelGrid Base Images Build${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to build an image
build_image() {
    local name=$1
    local dockerfile=$2
    local tag=$3
    local size_estimate=$4
    
    echo -e "${YELLOW}Building: ${REGISTRY}/${name}:${tag}${NC}"
    echo "  Dockerfile: ${dockerfile}"
    echo "  Estimated size: ${size_estimate}"
    echo ""
    
    start_time=$(date +%s)
    
    if docker build ${BUILD_ARGS} \
        -t ${REGISTRY}/${name}:${tag} \
        -f ${dockerfile} \
        . ; then
        
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        actual_size=$(docker images ${REGISTRY}/${name}:${tag} --format "{{.Size}}")
        
        echo -e "${GREEN}✓ Built: ${REGISTRY}/${name}:${tag}${NC}"
        echo "  Actual size: ${actual_size}"
        echo "  Build time: ${duration}s"
        echo ""
    else
        echo -e "${RED}✗ Failed to build ${REGISTRY}/${name}:${tag}${NC}"
        exit 1
    fi
}

# Build Tier 1: Runtime Python
if [[ "$TARGET" == "all" || "$TARGET" == "runtime" ]]; then
    echo -e "${BLUE}=== TIER 1: Runtime ===${NC}"
    build_image "runtime-python" "Dockerfile.runtime-python" "3.11" "~300 MB"
fi

# Build Tier 2: API Base
if [[ "$TARGET" == "all" || "$TARGET" == "api" ]]; then
    # Ensure runtime-python is built first (required dependency)
    if ! docker images ${REGISTRY}/runtime-python:3.11 --format "{{.Repository}}:{{.Tag}}" | grep -q "${REGISTRY}/runtime-python:3.11"; then
        echo -e "${YELLOW}runtime-python:3.11 not found, building it first...${NC}"
        build_image "runtime-python" "Dockerfile.runtime-python" "3.11" "~300 MB"
    fi
    
    echo -e "${BLUE}=== TIER 2: API Base ===${NC}"
    build_image "api-base" "Dockerfile.api-base" "latest" "~450 MB"
    
    # Also tag with version
    docker tag ${REGISTRY}/api-base:latest ${REGISTRY}/api-base:1.0
    echo -e "${GREEN}✓ Tagged as ${REGISTRY}/api-base:1.0${NC}"
    echo ""
fi

# Build Tier 3: API ML
if [[ "$TARGET" == "all" || "$TARGET" == "ml" ]]; then
    echo -e "${BLUE}=== TIER 3: API ML ===${NC}"
    build_image "api-ml" "Dockerfile.api-ml" "latest" "~1.5 GB"
    
    # Also tag with version
    docker tag ${REGISTRY}/api-ml:latest ${REGISTRY}/api-ml:1.0
    echo -e "${GREEN}✓ Tagged as ${REGISTRY}/api-ml:1.0${NC}"
    echo ""
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Build Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Images created:"
docker images | grep sentinelgrid | grep -E "(runtime-python|api-base|api-ml)"
echo ""
echo "Next steps:"
echo "1. Test images: docker run sentinelgrid/api-base:latest python -c 'import fastapi; print(fastapi.__version__)'"
echo "2. Push to registry: ./push-to-registry.sh"
echo "3. Update service Dockerfiles to use these bases"
echo ""

