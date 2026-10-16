#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/audit/multi-tenancy/lib/logging.sh
source "$SCRIPT_DIR/lib/logging.sh"

if [[ -z "${AUDIT_ARTIFACT_DIR:-}" ]]; then
  echo "AUDIT_ARTIFACT_DIR is required" >&2
  exit 5
fi

audit_log "INFO" "Running curated two-tenant negative-suite evidence targets"
exec python3 "$SCRIPT_DIR/run-two-tenant-negative-suite.py"
