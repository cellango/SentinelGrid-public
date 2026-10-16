#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/audit/multi-tenancy/lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"
# shellcheck source=scripts/audit/multi-tenancy/lib/logging.sh
source "$SCRIPT_DIR/lib/logging.sh"

if [[ -z "${AUDIT_ARTIFACT_DIR:-}" ]]; then
  echo "AUDIT_ARTIFACT_DIR is required" >&2
  exit 2
fi

audit_require_cmd git python3

mkdir -p "$AUDIT_ARTIFACT_DIR"

audit_log "INFO" "Preparing audit environment"

postgres_url_configured="false"
tenant_pair_present="false"
if [[ -n "${POSTGRES_URL:-}" ]]; then
  postgres_url_configured="true"
fi
if [[ -n "${AUDIT_TENANT_A_ID:-}" && -n "${AUDIT_TENANT_B_ID:-}" ]]; then
  tenant_pair_present="true"
fi

git rev-parse HEAD >"$AUDIT_ARTIFACT_DIR/git-revision.txt"
{
  echo "timestamp_utc=${AUDIT_TIMESTAMP_UTC:-}"
  echo "environment=${AUDIT_ENV_NAME:-}"
  echo "profile=${AUDIT_PROFILE:-}"
  echo "operator=${AUDIT_OPERATOR:-}"
  echo "artifact_dir=${AUDIT_ARTIFACT_DIR:-}"
  echo "api_gateway_url=${API_GATEWAY_URL:-}"
  echo "iam_agent_url=${IAM_AGENT_URL:-}"
  echo "keycloak_url=${KEYCLOAK_URL:-}"
  echo "postgres_url_configured=${postgres_url_configured}"
  echo "live_rls_required=${AUDIT_REQUIRE_LIVE_RLS:-false}"
  echo "tenant_pair_present=${tenant_pair_present}"
} >"$AUDIT_ARTIFACT_DIR/environment.txt"

python3 - "$AUDIT_ARTIFACT_DIR/preflight.json" <<'PY'
import json
import os
import pathlib
import sys

out = pathlib.Path(sys.argv[1])
payload = {
    "status": "stub",
    "environment": os.environ.get("AUDIT_ENV_NAME"),
    "profile": os.environ.get("AUDIT_PROFILE"),
    "operator": os.environ.get("AUDIT_OPERATOR"),
    "tenant_pair_present": bool(os.environ.get("AUDIT_TENANT_A_ID") and os.environ.get("AUDIT_TENANT_B_ID")),
    "postgres_url_configured": bool(os.environ.get("POSTGRES_URL")),
    "live_rls_required": os.environ.get("AUDIT_REQUIRE_LIVE_RLS", "false").lower() in {"1", "true", "yes", "on"},
    "notes": [
        "Service reachability and credential issuance checks are not implemented yet."
    ],
}
out.write_text(json.dumps(payload, indent=2) + "\n")
PY

audit_log "INFO" "Prepared audit environment metadata"
