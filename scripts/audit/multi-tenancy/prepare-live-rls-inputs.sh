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

audit_require_cmd python3

OUTPUT_DIR="$AUDIT_ARTIFACT_DIR/rls-report"
mkdir -p "$OUTPUT_DIR"

audit_log "INFO" "Preparing live RLS inputs"

python3 "$SCRIPT_DIR/discover-live-tenant-pair.py"

DISCOVERY_JSON="$OUTPUT_DIR/live-inputs.json"
DISCOVERY_ENV="$OUTPUT_DIR/live-inputs.env"

if [[ "${AUDIT_PROVISION_RLS_VERIFIER:-false}" == "true" ]]; then
  if [[ -n "${POSTGRES_ADMIN_URL:-${POSTGRES_URL:-}}" ]]; then
    audit_log "INFO" "Provisioning or updating the RLS verifier role"
    verifier_url="$(bash "$SCRIPT_DIR/provision-rls-verifier-role.sh" | tail -n 1)"
    {
      echo "AUDIT_RLS_VERIFIER_ROLE=${AUDIT_RLS_VERIFIER_ROLE:-sg_audit_verifier}"
      echo "AUDIT_RLS_VERIFIER_URL=$(printf '%q' "$verifier_url")"
    } >>"$DISCOVERY_ENV"
  else
    audit_log "WARN" "Skipping verifier-role provisioning because POSTGRES_ADMIN_URL/POSTGRES_URL is not configured"
  fi
fi

if [[ -f "$DISCOVERY_JSON" ]]; then
  audit_log "INFO" "Live RLS input discovery output written to $DISCOVERY_JSON"
fi

if [[ -f "$DISCOVERY_ENV" ]]; then
  audit_log "INFO" "Live RLS input environment written to $DISCOVERY_ENV"
fi
