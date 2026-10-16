#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/audit/multi-tenancy/lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"
# shellcheck source=scripts/audit/multi-tenancy/lib/logging.sh
source "$SCRIPT_DIR/lib/logging.sh"
# shellcheck source=scripts/audit/multi-tenancy/lib/manifest.sh
source "$SCRIPT_DIR/lib/manifest.sh"

PROFILE="standard"
ENV_NAME="local"
RUN_ID=""
KEEP_GOING="false"
FAILED_ANY="false"
STOP_REQUESTED="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="$2"
      shift 2
      ;;
    --env)
      ENV_NAME="$2"
      shift 2
      ;;
    --run-id)
      RUN_ID="$2"
      shift 2
      ;;
    --keep-going)
      KEEP_GOING="true"
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

audit_validate_profile "$PROFILE"
audit_validate_env_name "$ENV_NAME"
audit_require_cmd git python3 bash

REPO_ROOT="$(audit_repo_root)"
set -a
if [[ -f "$SCRIPT_DIR/config/profiles/$PROFILE.env" ]]; then
  # shellcheck disable=SC1090
  source "$SCRIPT_DIR/config/profiles/$PROFILE.env"
fi
if [[ -f "$SCRIPT_DIR/config/audit-pack.env" ]]; then
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/config/audit-pack.env"
fi
set +a

export AUDIT_PROFILE="$PROFILE"
export AUDIT_ENV_NAME="$ENV_NAME"
export AUDIT_OPERATOR="${AUDIT_OPERATOR:-$(whoami)}"
export AUDIT_TIMESTAMP_UTC="$(audit_now_utc)"
export AUDIT_GIT_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD)"
export AUDIT_GIT_REF="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)"
export AUDIT_RUN_ID="${RUN_ID:-$(audit_default_run_id "$ENV_NAME" "$PROFILE")}"
export AUDIT_ARTIFACT_DIR="$REPO_ROOT/artifacts/audit/multi-tenancy/$(date -u +%F)/$AUDIT_RUN_ID"
export AUDIT_COMMANDS_LOG="$AUDIT_ARTIFACT_DIR/commands.log"

mkdir -p "$AUDIT_ARTIFACT_DIR" "$AUDIT_ARTIFACT_DIR/_step-status"
touch "$AUDIT_COMMANDS_LOG"

MANIFEST_PATH="$AUDIT_ARTIFACT_DIR/manifest.json"
audit_manifest_init "$MANIFEST_PATH"

run_step() {
  local step_name="$1"
  shift
  local step_cmd=("$@")
  if [[ "$STOP_REQUESTED" == "true" ]]; then
    audit_log "WARN" "Skipping $step_name because a prior step failed"
    audit_manifest_step "$MANIFEST_PATH" "$step_name" "skipped"
    return 0
  fi
  audit_log_cmd "$step_name" "${step_cmd[*]}"
  audit_manifest_append_command "$MANIFEST_PATH" "${step_cmd[*]}"

  if "${step_cmd[@]}"; then
    audit_manifest_step "$MANIFEST_PATH" "$step_name" "passed"
  else
    FAILED_ANY="true"
    audit_manifest_step "$MANIFEST_PATH" "$step_name" "failed"
    if [[ "$KEEP_GOING" != "true" ]]; then
      STOP_REQUESTED="true"
    fi
  fi
}

run_finalizer_step() {
  local step_name="$1"
  shift
  local step_cmd=("$@")
  audit_log_cmd "$step_name" "${step_cmd[*]}"
  audit_manifest_append_command "$MANIFEST_PATH" "${step_cmd[*]}"

  if "${step_cmd[@]}"; then
    audit_manifest_step "$MANIFEST_PATH" "$step_name" "passed"
  else
    FAILED_ANY="true"
    audit_manifest_step "$MANIFEST_PATH" "$step_name" "failed"
  fi
}

run_step "prepare_audit_env" "$SCRIPT_DIR/prepare-audit-env.sh"

if [[ "${AUDIT_ENABLE_LIVE_RLS_PREP:-true}" == "true" && "${AUDIT_ENABLE_RLS:-true}" == "true" ]]; then
  run_step "prepare_live_rls_inputs" "$SCRIPT_DIR/prepare-live-rls-inputs.sh"
  if [[ -f "$AUDIT_ARTIFACT_DIR/rls-report/live-inputs.env" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$AUDIT_ARTIFACT_DIR/rls-report/live-inputs.env"
    set +a
  fi
fi

if [[ "${AUDIT_ENABLE_CONTROL_INVENTORY:-true}" == "true" ]]; then
  run_step "verify_tenant_control_inventory" python3 "$SCRIPT_DIR/verify-tenant-control-inventory.py"
fi
if [[ "${AUDIT_ENABLE_RLS:-true}" == "true" ]]; then
  run_step "verify_rls_coverage" python3 "$SCRIPT_DIR/verify-rls-coverage.py"
fi
if [[ "${AUDIT_ENABLE_NEGATIVE_SUITE:-true}" == "true" ]]; then
  run_step "run_two_tenant_negative_suite" "$SCRIPT_DIR/run-two-tenant-negative-suite.sh"
fi
if [[ "${AUDIT_ENABLE_LOG_COLLECTION:-true}" == "true" ]]; then
  run_step "collect_blocked_violation_evidence" "$SCRIPT_DIR/collect-blocked-violation-evidence.sh"
fi
if [[ "${AUDIT_ENABLE_REMEDIATION_REPORT:-true}" == "true" ]]; then
  run_finalizer_step "generate_remediation_report" python3 "$SCRIPT_DIR/generate-remediation-report.py"
fi
if [[ "${AUDIT_ENABLE_OWNER_QUEUES:-true}" == "true" ]]; then
  run_finalizer_step "generate_owner_remediation_queues" python3 "$SCRIPT_DIR/generate-owner-remediation-queues.py"
fi
if [[ "${AUDIT_ENABLE_REMEDIATION_PROGRAM:-true}" == "true" ]]; then
  run_finalizer_step "generate_remediation_program" python3 "$SCRIPT_DIR/generate-remediation-program.py"
fi
if [[ "${AUDIT_ENABLE_BINDER:-true}" == "true" ]]; then
  run_finalizer_step "package_audit_binder" python3 "$SCRIPT_DIR/package-audit-binder.py"
fi

if [[ "$FAILED_ANY" == "true" ]]; then
  audit_manifest_overall "$MANIFEST_PATH" "failed"
  audit_log "ERROR" "Audit pack completed with failures: $AUDIT_ARTIFACT_DIR"
  printf '%s\n' "$AUDIT_ARTIFACT_DIR"
  exit 1
fi

audit_manifest_overall "$MANIFEST_PATH" "passed"
audit_log "INFO" "Audit pack completed: $AUDIT_ARTIFACT_DIR"
printf '%s\n' "$AUDIT_ARTIFACT_DIR"
