#!/bin/bash
# Bump version numbers (major/minor/patch)
# This script increments version numbers for agents or images

set -e

TYPE="${1:-}"  # agent or image
VERSION_TYPE="${2:-}"  # major, minor, patch
CURRENT_VERSION="${3:-}"

if [ -z "$TYPE" ] || [ -z "$VERSION_TYPE" ] || [ -z "$CURRENT_VERSION" ]; then
    echo "Usage: $0 <type> <version_type> <current_version>"
    echo "  type: agent or image"
    echo "  version_type: major, minor, or patch"
    echo "  current_version: Current version (e.g., 1.2.3)"
    exit 1
fi

# Validate version format (semantic versioning)
if ! echo "$CURRENT_VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+'; then
    echo "❌ Invalid version format. Expected: MAJOR.MINOR.PATCH (e.g., 1.2.3)"
    exit 1
fi

# Extract version components
MAJOR=$(echo "$CURRENT_VERSION" | cut -d. -f1)
MINOR=$(echo "$CURRENT_VERSION" | cut -d. -f2)
PATCH=$(echo "$CURRENT_VERSION" | cut -d. -f3)

# Bump version
case $VERSION_TYPE in
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    patch)
        PATCH=$((PATCH + 1))
        ;;
    *)
        echo "❌ Invalid version_type. Must be: major, minor, or patch"
        exit 1
        ;;
esac

NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"

echo "=========================================="
echo "Bumping ${TYPE} Version"
echo "=========================================="
echo "Current Version: ${CURRENT_VERSION}"
echo "Version Type: ${VERSION_TYPE}"
echo "New Version: ${NEW_VERSION}"
echo ""

# Update version in appropriate location
if [ "$TYPE" = "agent" ]; then
    echo "To update agent version:"
    echo "1. Update SENTINELGRID_VERSION in build scripts"
    echo "2. Register new version in database:"
    echo "   INSERT INTO agent_versions (version, ...) VALUES ('${NEW_VERSION}', ...);"
elif [ "$TYPE" = "image" ]; then
    echo "To update image version:"
    echo "1. Update version in Packer templates"
    echo "2. Register new image version in database"
fi

echo ""
echo "New version: ${NEW_VERSION}"

