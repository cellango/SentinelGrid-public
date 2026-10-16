#!/bin/bash
# Validate Packer template before building
# This script checks for common issues in Packer templates

set -e

TEMPLATE_FILE="${1:-}"
if [ -z "$TEMPLATE_FILE" ]; then
    echo "Usage: $0 <packer-template.json>"
    exit 1
fi

echo "Validating Packer template: $TEMPLATE_FILE"

# Check if file exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "ERROR: Template file not found: $TEMPLATE_FILE"
    exit 1
fi

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "WARNING: jq not installed, skipping JSON validation"
else
    # Validate JSON syntax
    if ! jq empty "$TEMPLATE_FILE" 2>/dev/null; then
        echo "ERROR: Invalid JSON syntax"
        exit 1
    fi
    echo "✓ JSON syntax valid"
fi

# Check if packer validate is available
if ! command -v packer &> /dev/null; then
    echo "WARNING: Packer not installed, skipping packer validate"
else
    # Run packer validate
    if packer validate "$TEMPLATE_FILE" 2>&1; then
        echo "✓ Packer validation passed"
    else
        echo "ERROR: Packer validation failed"
        exit 1
    fi
fi

# Basic checks
echo "Running basic checks..."

# Check for required fields
REQUIRED_FIELDS=("builders" "provisioners")
for field in "${REQUIRED_FIELDS[@]}"; do
    if jq -e ".$field" "$TEMPLATE_FILE" > /dev/null 2>&1; then
        echo "✓ Required field '$field' present"
    else
        echo "ERROR: Required field '$field' missing"
        exit 1
    fi
done

# Check for at least one builder
BUILDER_COUNT=$(jq '.builders | length' "$TEMPLATE_FILE" 2>/dev/null || echo "0")
if [ "$BUILDER_COUNT" -gt 0 ]; then
    echo "✓ Found $BUILDER_COUNT builder(s)"
else
    echo "ERROR: No builders defined"
    exit 1
fi

# Check for CIS hardening script reference
if grep -q "cis-harden" "$TEMPLATE_FILE" || grep -q "cis-hardening" "$TEMPLATE_FILE"; then
    echo "✓ CIS hardening script referenced"
else
    echo "WARNING: CIS hardening script not found in template"
fi

# Check for agent installation script reference
if grep -q "install-sentinelgrid-agent" "$TEMPLATE_FILE"; then
    echo "✓ Agent installation script referenced"
else
    echo "WARNING: Agent installation script not found in template"
fi

echo ""
echo "Validation complete!"

