#!/bin/bash
# Create User Profile component for a Keycloak realm
# This enables unmanaged attributes so custom attributes like tenant_id can be set

set -e

REALM=${1:-}
KEYCLOAK_CONTAINER=${KEYCLOAK_CONTAINER:-sentinelgrid-keycloak-1}

if [ -z "$REALM" ]; then
    echo "Usage: $0 <realm-name>"
    echo "Example: $0 agribotsai"
    exit 1
fi

echo "Creating User Profile component for realm: $REALM"

# Use Python script if available
if [ -f "../../../../scripts/create-user-profile-component.py" ]; then
    cd "$(dirname "$0")"
    python3 ../../../../scripts/create-user-profile-component.py "$REALM"
elif [ -f "scripts/create-user-profile-component.py" ]; then
    python3 scripts/create-user-profile-component.py "$REALM"
else
    echo "⚠️  Python script not found. Component may need manual creation."
    echo "Run: python3 scripts/create-user-profile-component.py $REALM"
    exit 1
fi

