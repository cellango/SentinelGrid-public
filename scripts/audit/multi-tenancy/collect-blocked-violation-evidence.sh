#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/audit/multi-tenancy/lib/logging.sh
source "$SCRIPT_DIR/lib/logging.sh"

if [[ -z "${AUDIT_ARTIFACT_DIR:-}" ]]; then
  echo "AUDIT_ARTIFACT_DIR is required" >&2
  exit 6
fi

audit_log "INFO" "Collecting blocked-violation evidence artifacts"
python3 "$SCRIPT_DIR/collect-blocked-violation-evidence.py"
