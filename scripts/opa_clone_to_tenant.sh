#!/usr/bin/env bash
set -euo pipefail

# Clone a built OPA bundle into a tenant-specific path.
# Usage: ./scripts/opa_clone_to_tenant.sh <bundle_tar.gz> <tenant_id>
#
# This is a stopgap helper until the Policy Service/API is wired.

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <bundle_tar.gz> <tenant_id>" >&2
  exit 1
fi

BUNDLE="$1"
TENANT="$2"

if [ ! -f "$BUNDLE" ]; then
  echo "Bundle not found: $BUNDLE" >&2
  exit 1
fi

TARGET_DIR="bundles/${TENANT}"
mkdir -p "$TARGET_DIR"
cp "$BUNDLE" "${TARGET_DIR}/"

echo "Cloned bundle to ${TARGET_DIR}/$(basename "$BUNDLE")"
