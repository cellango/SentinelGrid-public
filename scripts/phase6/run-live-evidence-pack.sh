#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"

MODE="plan"
AUDIT_PROFILE="${PHASE6_AUDIT_PROFILE:-full}"
AUDIT_ENV="${PHASE6_AUDIT_ENV:-audit}"
RESTORE_COMPONENT="${PHASE6_RESTORE_COMPONENT:-all}"
ROLLBACK_RELEASE="${PHASE6_ROLLBACK_RELEASE:-api-gateway}"
ROLLBACK_REVISION="${PHASE6_ROLLBACK_REVISION:-1}"
ROLLBACK_NAMESPACE="${PHASE6_ROLLBACK_NAMESPACE:-sg-core}"
ROLLBACK_READY_URL="${PHASE6_ROLLBACK_READY_URL:-}"
RUN_ID=""
EVIDENCE_DIR=""

usage() {
  cat <<'EOF'
Usage: run-live-evidence-pack.sh [options]

Options:
  --mode <plan|live>              plan: run non-destructive prep and drill plans
                                  live: execute the full audit and live drills
  --audit-profile <profile>       audit profile, defaults to full
  --audit-env <env>               audit environment label, defaults to audit
  --restore-component <value>     postgres, keycloak, or all; defaults to all
  --rollback-release <name>       Helm release for rollback drill, defaults to api-gateway
  --rollback-revision <number>    Helm revision for rollback drill, defaults to 1
  --rollback-namespace <name>     Kubernetes namespace, defaults to sg-core
  --rollback-ready-url <url>      Optional readiness URL for rollback verification
  --run-id <value>                Optional explicit run identifier
  --evidence-dir <path>           Optional explicit artifact directory
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --audit-profile)
      AUDIT_PROFILE="${2:-}"
      shift 2
      ;;
    --audit-env)
      AUDIT_ENV="${2:-}"
      shift 2
      ;;
    --restore-component)
      RESTORE_COMPONENT="${2:-}"
      shift 2
      ;;
    --rollback-release)
      ROLLBACK_RELEASE="${2:-}"
      shift 2
      ;;
    --rollback-revision)
      ROLLBACK_REVISION="${2:-}"
      shift 2
      ;;
    --rollback-namespace)
      ROLLBACK_NAMESPACE="${2:-}"
      shift 2
      ;;
    --rollback-ready-url)
      ROLLBACK_READY_URL="${2:-}"
      shift 2
      ;;
    --run-id)
      RUN_ID="${2:-}"
      shift 2
      ;;
    --evidence-dir)
      EVIDENCE_DIR="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "$MODE" in
  plan|live) ;;
  *)
    echo "--mode must be plan or live" >&2
    exit 1
    ;;
esac

case "$RESTORE_COMPONENT" in
  postgres|keycloak|all) ;;
  *)
    echo "--restore-component must be postgres, keycloak, or all" >&2
    exit 1
    ;;
esac

DATE_DIR="$(date -u +%F)"
RUN_ID="${RUN_ID:-$(date -u +%H%M%S)-phase6-${MODE}}"
DEFAULT_EVIDENCE_DIR="$REPO_ROOT/artifacts/phase6/live-evidence/$DATE_DIR/$RUN_ID"
EVIDENCE_DIR="${EVIDENCE_DIR:-$DEFAULT_EVIDENCE_DIR}"
mkdir -p "$EVIDENCE_DIR"

COMMANDS_LOG="$EVIDENCE_DIR/commands.log"
SUMMARY_MD="$EVIDENCE_DIR/summary.md"
RESULT_JSON="$EVIDENCE_DIR/result.json"
GATE_REVIEW_JSON="$EVIDENCE_DIR/gate-review.json"
GATE_REVIEW_MD="$EVIDENCE_DIR/gate-review.md"
ENVIRONMENT_TXT="$EVIDENCE_DIR/environment.txt"

timestamp_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
git_sha="$(git -C "$REPO_ROOT" rev-parse HEAD)"
git_ref="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)"

{
  echo "timestamp_utc=$timestamp_utc"
  echo "mode=$MODE"
  echo "audit_profile=$AUDIT_PROFILE"
  echo "audit_env=$AUDIT_ENV"
  echo "restore_component=$RESTORE_COMPONENT"
  echo "rollback_release=$ROLLBACK_RELEASE"
  echo "rollback_revision=$ROLLBACK_REVISION"
  echo "rollback_namespace=$ROLLBACK_NAMESPACE"
  echo "rollback_ready_url=$ROLLBACK_READY_URL"
  echo "postgres_url_configured=${POSTGRES_URL:+true}"
  echo "git_sha=$git_sha"
  echo "git_ref=$git_ref"
} >"$ENVIRONMENT_TXT"

log_cmd() {
  printf '[CMD] %s\n' "$*" | tee -a "$COMMANDS_LOG"
}

STEP_NAMES=()
STEP_STATUSES=()
STEP_ARTIFACTS=()
STEP_NOTES=()

record_step() {
  STEP_NAMES+=("$1")
  STEP_STATUSES+=("$2")
  STEP_ARTIFACTS+=("$3")
  STEP_NOTES+=("$4")
}

run_audit_prep() {
  local artifact_dir="$EVIDENCE_DIR/multi-tenancy-prep"
  mkdir -p "$artifact_dir"
  log_cmd "AUDIT_ARTIFACT_DIR=$artifact_dir bash scripts/audit/multi-tenancy/prepare-live-rls-inputs.sh"

  if AUDIT_ARTIFACT_DIR="$artifact_dir" bash "$REPO_ROOT/scripts/audit/multi-tenancy/prepare-live-rls-inputs.sh" >"$artifact_dir/run.log" 2>&1; then
    local status
    status="$(python3 - <<'PY' "$artifact_dir/rls-report/live-inputs.json"
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
if not path.exists():
    print("failed")
else:
    payload = json.loads(path.read_text())
    print(payload.get("status", "unknown"))
PY
)"
    record_step "prepare_live_rls_inputs" "$status" "$artifact_dir" "Prepared live RLS inputs."
  else
    record_step "prepare_live_rls_inputs" "failed" "$artifact_dir" "Live RLS input preparation failed."
  fi
}

run_full_audit() {
  local run_id="${RUN_ID}-audit"
  log_cmd "scripts/audit/multi-tenancy/run-full-audit.sh --profile $AUDIT_PROFILE --env $AUDIT_ENV --run-id $run_id --keep-going"

  local output
  local status
  if output="$(bash "$REPO_ROOT/scripts/audit/multi-tenancy/run-full-audit.sh" --profile "$AUDIT_PROFILE" --env "$AUDIT_ENV" --run-id "$run_id" --keep-going 2>&1)"; then
    printf '%s\n' "$output" >"$EVIDENCE_DIR/multi-tenancy-audit.log"
    local artifact_dir
    artifact_dir="$(printf '%s\n' "$output" | tail -n 1)"
    status="passed"
    record_step "run_live_multi_tenant_audit" "$status" "$artifact_dir" "Full audit completed."
  else
    printf '%s\n' "$output" >"$EVIDENCE_DIR/multi-tenancy-audit.log"
    local artifact_dir
    artifact_dir="$(printf '%s\n' "$output" | tail -n 1)"
    status="failed"
    record_step "run_live_multi_tenant_audit" "$status" "$artifact_dir" "Full audit failed."
  fi
}

run_restore_drill() {
  local mode_arg="$1"
  local output
  log_cmd "infra/shared/scripts/run-restore-drill.sh --component $RESTORE_COMPONENT --mode $mode_arg"
  output="$(bash "$REPO_ROOT/infra/shared/scripts/run-restore-drill.sh" --component "$RESTORE_COMPONENT" --mode "$mode_arg")"
  local artifact_dir
  artifact_dir="$(printf '%s\n' "$output" | tail -n 1)"
  local status
  status="$(python3 - <<'PY' "$artifact_dir/result.json"
import json, pathlib, sys
payload = json.loads(pathlib.Path(sys.argv[1]).read_text())
print(payload.get("status", "unknown"))
PY
)"
  record_step "restore_drill" "$status" "$artifact_dir" "Restore drill ${mode_arg} run."
}

run_rollback_drill() {
  local mode_arg="$1"
  local cmd=(
    bash "$REPO_ROOT/infra/shared/scripts/run-release-rollback-drill.sh"
    --release "$ROLLBACK_RELEASE"
    --revision "$ROLLBACK_REVISION"
    --namespace "$ROLLBACK_NAMESPACE"
    --mode "$mode_arg"
  )
  if [[ -n "$ROLLBACK_READY_URL" ]]; then
    cmd+=(--ready-url "$ROLLBACK_READY_URL")
  fi
  log_cmd "${cmd[*]}"
  local output
  output="$("${cmd[@]}")"
  local artifact_dir
  artifact_dir="$(printf '%s\n' "$output" | tail -n 1)"
  local status
  status="$(python3 - <<'PY' "$artifact_dir/result.json"
import json, pathlib, sys
payload = json.loads(pathlib.Path(sys.argv[1]).read_text())
print(payload.get("status", "unknown"))
PY
)"
  record_step "rollback_drill" "$status" "$artifact_dir" "Rollback drill ${mode_arg} run."
}

run_audit_prep

if [[ "$MODE" == "live" ]]; then
  run_full_audit
  run_restore_drill "live"
  run_rollback_drill "live"
else
  record_step "run_live_multi_tenant_audit" "planned" "" "Full live audit command recorded but not executed in plan mode."
  run_restore_drill "plan"
  run_rollback_drill "plan"
fi

overall_status="passed"
for status in "${STEP_STATUSES[@]}"; do
  case "$status" in
    failed)
      overall_status="failed"
      break
      ;;
    skipped|planned)
      if [[ "$overall_status" != "failed" ]]; then
        overall_status="partial"
      fi
      ;;
  esac
done

python3 - <<'PY' "$RESULT_JSON" "$timestamp_utc" "$git_sha" "$git_ref" "$MODE" "$AUDIT_PROFILE" "$AUDIT_ENV" "$RESTORE_COMPONENT" "$ROLLBACK_RELEASE" "$ROLLBACK_REVISION" "$ROLLBACK_NAMESPACE" "$ROLLBACK_READY_URL" "$EVIDENCE_DIR" "$overall_status" "${STEP_NAMES[@]}" -- "${STEP_STATUSES[@]}" -- "${STEP_ARTIFACTS[@]}" -- "${STEP_NOTES[@]}"
import json
import pathlib
import sys

output = pathlib.Path(sys.argv[1])
timestamp_utc = sys.argv[2]
git_sha = sys.argv[3]
git_ref = sys.argv[4]
mode = sys.argv[5]
audit_profile = sys.argv[6]
audit_env = sys.argv[7]
restore_component = sys.argv[8]
rollback_release = sys.argv[9]
rollback_revision = sys.argv[10]
rollback_namespace = sys.argv[11]
rollback_ready_url = sys.argv[12]
evidence_dir = sys.argv[13]
overall_status = sys.argv[14]

rest = sys.argv[15:]
sections = []
current = []
for item in rest:
    if item == "--":
        sections.append(current)
        current = []
    else:
        current.append(item)
sections.append(current)

step_names, step_statuses, step_artifacts, step_notes = sections
steps = []
for idx, name in enumerate(step_names):
    steps.append(
        {
            "name": name,
            "status": step_statuses[idx] if idx < len(step_statuses) else "",
            "artifact_dir": step_artifacts[idx] if idx < len(step_artifacts) else "",
            "notes": step_notes[idx] if idx < len(step_notes) else "",
        }
    )

payload = {
    "timestamp_utc": timestamp_utc,
    "git_sha": git_sha,
    "git_ref": git_ref,
    "mode": mode,
    "audit_profile": audit_profile,
    "audit_env": audit_env,
    "restore_component": restore_component,
    "rollback": {
        "release": rollback_release,
        "revision": rollback_revision,
        "namespace": rollback_namespace,
        "ready_url": rollback_ready_url,
    },
    "artifact_root": evidence_dir,
    "overall_status": overall_status,
    "steps": steps,
}
output.write_text(json.dumps(payload, indent=2) + "\n")
PY

python3 "$REPO_ROOT/scripts/phase6/evaluate-live-evidence.py" \
  --result-json "$RESULT_JSON" \
  --output-json "$GATE_REVIEW_JSON" \
  --output-md "$GATE_REVIEW_MD"

recommended_decision="$(
  python3 - <<'PY' "$GATE_REVIEW_JSON"
import json
import pathlib
import sys

payload = json.loads(pathlib.Path(sys.argv[1]).read_text())
print(payload.get("recommended_decision", "no-go"))
PY
)"

ready_for_signoff="$(
  python3 - <<'PY' "$GATE_REVIEW_JSON"
import json
import pathlib
import sys

payload = json.loads(pathlib.Path(sys.argv[1]).read_text())
print(str(payload.get("ready_for_signoff", False)).lower())
PY
)"

{
  echo "# Phase 6 Live Evidence Pack"
  echo
  echo "- Status: \`$overall_status\`"
  echo "- Recommended decision: \`$recommended_decision\`"
  echo "- Ready for human signoff: \`$ready_for_signoff\`"
  echo "- Mode: \`$MODE\`"
  echo "- Audit profile: \`$AUDIT_PROFILE\`"
  echo "- Audit env: \`$AUDIT_ENV\`"
  echo "- Evidence root: \`$EVIDENCE_DIR\`"
  echo "- Gate review: \`$GATE_REVIEW_MD\`"
  echo
  echo "## Steps"
  echo
  for idx in "${!STEP_NAMES[@]}"; do
    echo "- ${STEP_NAMES[$idx]}: \`${STEP_STATUSES[$idx]}\`"
    if [[ -n "${STEP_ARTIFACTS[$idx]}" ]]; then
      echo "  artifact: \`${STEP_ARTIFACTS[$idx]}\`"
    fi
    if [[ -n "${STEP_NOTES[$idx]}" ]]; then
      echo "  notes: ${STEP_NOTES[$idx]}"
    fi
  done
} >"$SUMMARY_MD"

echo "$EVIDENCE_DIR"
