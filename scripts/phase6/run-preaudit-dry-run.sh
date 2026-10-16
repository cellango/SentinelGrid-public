#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"

RUN_ID=""
ARTIFACT_DIR=""

usage() {
  cat <<'EOF'
Usage: run-preaudit-dry-run.sh [options]

Options:
  --run-id <value>        Optional explicit run identifier
  --artifact-dir <path>   Optional explicit artifact directory
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-id)
      RUN_ID="${2:-}"
      shift 2
      ;;
    --artifact-dir)
      ARTIFACT_DIR="${2:-}"
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

DATE_DIR="$(date -u +%F)"
RUN_ID="${RUN_ID:-$(date -u +%H%M%S)-phase6-preaudit-dry-run}"
DEFAULT_ARTIFACT_DIR="$REPO_ROOT/artifacts/phase6/preaudit-dry-run/$DATE_DIR/$RUN_ID"
ARTIFACT_DIR="${ARTIFACT_DIR:-$DEFAULT_ARTIFACT_DIR}"
mkdir -p "$ARTIFACT_DIR"

COMMANDS_LOG="$ARTIFACT_DIR/commands.log"
SUMMARY_MD="$ARTIFACT_DIR/summary.md"
RESULT_JSON="$ARTIFACT_DIR/result.json"
MANIFEST_JSON="$ARTIFACT_DIR/evidence-manifest.json"
RECOVERY_VALIDATION_JSON="$ARTIFACT_DIR/recovery-validation.json"
PHASE7_ENTRY_JSON="$ARTIFACT_DIR/phase7-entry-review.json"
PHASE7_ENTRY_MD="$ARTIFACT_DIR/phase7-entry-review.md"
ENVIRONMENT_TXT="$ARTIFACT_DIR/environment.txt"

timestamp_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
git_sha="$(git -C "$REPO_ROOT" rev-parse HEAD)"
git_ref="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)"

{
  echo "timestamp_utc=$timestamp_utc"
  echo "git_sha=$git_sha"
  echo "git_ref=$git_ref"
  echo "artifact_dir=$ARTIFACT_DIR"
} >"$ENVIRONMENT_TXT"

STEP_NAMES=()
STEP_STATUSES=()
STEP_ARTIFACTS=()
STEP_NOTES=()

log_cmd() {
  printf '[CMD] %s\n' "$*" | tee -a "$COMMANDS_LOG"
}

record_step() {
  STEP_NAMES+=("$1")
  STEP_STATUSES+=("$2")
  STEP_ARTIFACTS+=("$3")
  STEP_NOTES+=("$4")
}

run_logged_step() {
  local step_name="$1"
  local artifact_subdir="$2"
  shift 2

  local artifact_dir="$ARTIFACT_DIR/$artifact_subdir"
  mkdir -p "$artifact_dir"
  log_cmd "$*"

  if "$@" >"$artifact_dir/run.log" 2>&1; then
    record_step "$step_name" "passed" "$artifact_dir" "$step_name passed."
  else
    record_step "$step_name" "failed" "$artifact_dir" "$step_name failed. Inspect run.log."
  fi
}

run_logged_step \
  "verify_launch_scope_observability" \
  "verify-launch-scope-observability" \
  bash "$REPO_ROOT/scripts/phase6/verify-launch-scope-observability.sh"

run_logged_step \
  "verify_launch_support_alignment" \
  "verify-launch-support-alignment" \
  bash "$REPO_ROOT/scripts/phase6/verify-launch-support-alignment.sh"

run_logged_step \
  "verify_production_default_secrets" \
  "verify-production-default-secrets" \
  bash "$REPO_ROOT/scripts/lint_production_default_secrets.sh"

run_logged_step \
  "verify_launch_no_go_regressions" \
  "verify-launch-no-go-regressions" \
  bash "$REPO_ROOT/scripts/phase6/verify-launch-no-go-regressions.sh"

log_cmd "python3 <inline> \"$RECOVERY_VALIDATION_JSON\" \"$REPO_ROOT\""
if python3 - <<'PY' "$RECOVERY_VALIDATION_JSON" "$REPO_ROOT"
import json
import pathlib
import sys

output_path = pathlib.Path(sys.argv[1])
repo_root = pathlib.Path(sys.argv[2])

checks = [
    {
        "name": "postgres_restore",
        "artifact_dir": "artifacts/drills/restore/2026-04-18/165655-postgres-live",
        "result_json": "artifacts/drills/restore/2026-04-18/165655-postgres-live/result.json",
        "backup_required": True,
    },
    {
        "name": "keycloak_restore",
        "artifact_dir": "artifacts/drills/restore/2026-04-18/165858-keycloak-live",
        "result_json": "artifacts/drills/restore/2026-04-18/165858-keycloak-live/result.json",
        "backup_required": True,
    },
    {
        "name": "helm_rollback",
        "artifact_dir": "artifacts/drills/rollback/2026-04-18/170133-phase6-rollback-smoke-rollback-live",
        "result_json": "artifacts/drills/rollback/2026-04-18/170133-phase6-rollback-smoke-rollback-live/result.json",
        "backup_required": False,
    },
]

items = []
overall_status = "passed"

for check in checks:
    result_path = repo_root / check["result_json"]
    item = {
        "name": check["name"],
        "artifact_dir": str(repo_root / check["artifact_dir"]),
        "result_json": str(result_path),
        "status": "failed",
        "within_timebox": False,
        "notes": "",
    }

    if not result_path.exists():
        item["notes"] = "result.json is missing"
        overall_status = "failed"
        items.append(item)
        continue

    payload = json.loads(result_path.read_text())
    backup_file = payload.get("backup_file")
    operator_actions_file = payload.get("operator_actions_file", "")
    operator_actions_path = pathlib.Path(operator_actions_file) if operator_actions_file else pathlib.Path()
    backup_exists = True
    if check["backup_required"]:
        backup_exists = bool(backup_file) and pathlib.Path(str(backup_file)).exists()

    status = str(payload.get("status", "failed"))
    within_timebox = bool(payload.get("within_timebox", False))
    mode = str(payload.get("mode", ""))
    operator_actions_exists = bool(operator_actions_file) and operator_actions_path.exists()

    item.update(
        {
            "status": "passed"
            if status == "passed" and within_timebox and mode == "live" and operator_actions_exists and backup_exists
            else "failed",
            "mode": mode,
            "within_timebox": within_timebox,
            "duration_seconds": payload.get("duration_seconds"),
            "timebox_minutes": payload.get("timebox_minutes"),
            "backup_file": backup_file,
            "backup_exists": backup_exists,
            "operator_actions_file": operator_actions_file,
            "operator_actions_exists": operator_actions_exists,
            "notes": payload.get("notes", ""),
        }
    )

    if item["status"] != "passed":
        overall_status = "failed"

    items.append(item)

output_path.write_text(json.dumps({"status": overall_status, "items": items}, indent=2) + "\n")
PY
then
  record_step "validate_recovery_evidence" "passed" "$RECOVERY_VALIDATION_JSON" "Fresh recovery evidence is present, passed, and within timebox."
else
  record_step "validate_recovery_evidence" "failed" "$RECOVERY_VALIDATION_JSON" "Recovery evidence validation failed."
fi

log_cmd "python3 <inline> \"$MANIFEST_JSON\" \"$REPO_ROOT\""
if python3 - <<'PY' "$MANIFEST_JSON" "$REPO_ROOT"
import json
import pathlib
import sys

output_path = pathlib.Path(sys.argv[1])
repo_root = pathlib.Path(sys.argv[2])

gate_map = [
    {
        "gate": "G-01",
        "label": "Current production truth is unambiguous",
        "paths": [
            "docs/archive/reference/platform/production-truth-baseline-2026-04-15.md",
            "docs/README.md",
        ],
    },
    {
        "gate": "G-02",
        "label": "Launch boundary equals shipped and supported surface",
        "paths": [
            "docs/archive/reference/platform/production-launch-scope-decision-2026-04-15.md",
            "docs/archive/reference/infrastructure/production-launch-scope-deployment-matrix-2026-04-16.md",
            "docs/archive/reference/platform/phase5-gated-feature-inventory-2026-04-16.md",
        ],
    },
    {
        "gate": "G-03",
        "label": "IAM public auth paths no longer trust unsigned token claims",
        "paths": [
            "docs/archive/validation/phase1-slice-1a-unsigned-token-trust-closeout-2026-04-16.md",
            "docs/archive/validation/phase1-slice-1b-bff-session-boundary-closeout-2026-04-16.md",
            "docs/archive/validation/phase1-slice-1c-keycloak-admin-pattern-closeout-2026-04-16.md",
            "docs/archive/validation/phase1-slice-1d-frontend-security-header-proxy-closeout-2026-04-16.md",
        ],
    },
    {
        "gate": "G-04",
        "label": "SOAR no longer accepts unsigned, fallback, or placeholder tenant context",
        "paths": [
            "docs/archive/validation/phase2-slice-2a-soar-tenant-trust-closeout-2026-04-16.md",
        ],
    },
    {
        "gate": "G-05",
        "label": "Orchestrator response/remediation endpoints no longer use placeholder tenants",
        "paths": [
            "docs/archive/validation/phase2-slice-2b-orchestrator-response-auth-closeout-2026-04-16.md",
        ],
    },
    {
        "gate": "G-06",
        "label": "AI Shield is hardened or fully gated",
        "paths": [
            "docs/archive/validation/phase2-slice-2c-ai-shield-auth-closeout-2026-04-16.md",
            "docs/archive/validation/phase2-slice-2d-internal-token-standardization-closeout-2026-04-16.md",
        ],
    },
    {
        "gate": "G-07",
        "label": "Public ingress is HTTPS-only and runtime/network hardening is enforced",
        "paths": [
            "docs/archive/validation/phase3-slice-3a-https-only-public-edge-closeout-2026-04-17.md",
            "docs/archive/validation/phase3-slice-3b-kubernetes-network-containment-closeout-2026-04-17.md",
            "docs/archive/validation/phase3-slice-3c-runtime-hardening-closeout-2026-04-17.md",
            "docs/archive/validation/phase3-slice-3d-secret-and-default-credential-elimination-closeout-2026-04-17.md",
        ],
    },
    {
        "gate": "G-08",
        "label": "Launch dependencies have no unresolved high or critical findings without approved exceptions",
        "paths": [
            "docs/archive/validation/phase4-slice-4a-frontend-dependency-remediation-closeout-2026-04-17.md",
            "docs/archive/validation/phase4-slice-4b-model-gateway-dependency-remediation-closeout-2026-04-17.md",
            "docs/archive/validation/phase4-slice-4c-reproducible-dependency-policy-closeout-2026-04-17.md",
            "docs/archive/validation/phase4-slice-4d-base-image-and-image-scan-discipline-closeout-2026-04-18.md",
            "docs/archive/reference/platform/production-approved-exception-register-2026-04-16.md",
            "artifacts/slice4d-pruned/launch-image-scan-summary.md",
        ],
    },
    {
        "gate": "G-09",
        "label": "No marketed launch workflow silently falls back to stub/mock/placeholder behavior",
        "paths": [
            "docs/archive/validation/phase5-slice-5a-non-launch-surface-gate-closeout-2026-04-18.md",
            "docs/archive/validation/phase5-slice-5b-workflow-truthfulness-closeout-2026-04-18.md",
            "docs/PHASE5_SLICE_5C_LAUNCH_PACKAGING_AND_GTM_ALIGNMENT_CLOSEOUT_2026-04-18.md",
            "docs/PHASE5_SLICE_5D_DIFFERENTIATE_ON_SIMPLICITY_NOT_BREADTH_CLOSEOUT_2026-04-18.md",
        ],
    },
    {
        "gate": "G-10",
        "label": "Restore, rollback, readiness, and support rehearsals are proven",
        "paths": [
            "docs/archive/validation/phase6-slice-6a-readiness-metrics-alerting-closeout-2026-04-18.md",
            "docs/archive/validation/phase6-slice-6b-backup-restore-rollback-drills-closeout-2026-04-18.md",
            "docs/archive/validation/phase6-slice-6c-production-support-and-incident-rehearsal-closeout-2026-04-18.md",
            "docs/archive/validation/phase6-slice-6d-final-pre-audit-dry-run-closeout-2026-04-18.md",
            "docs/archive/operations/production-release-and-deploy.md",
            "docs/archive/operations/backup-restore-and-dr.md",
            "docs/archive/operations/production-support-and-incident-response.md",
            "artifacts/drills/restore/2026-04-18/165655-postgres-live/result.json",
            "artifacts/drills/restore/2026-04-18/165858-keycloak-live/result.json",
            "artifacts/drills/rollback/2026-04-18/170133-phase6-rollback-smoke-rollback-live/result.json",
        ],
    },
]

gates = []
overall_status = "passed"

for gate in gate_map:
    items = []
    gate_status = "passed"
    for relative_path in gate["paths"]:
        path = repo_root / relative_path
        exists = path.exists()
        items.append({"path": relative_path, "exists": exists})
        if not exists:
            gate_status = "failed"
            overall_status = "failed"
    gates.append(
        {
            "gate": gate["gate"],
            "label": gate["label"],
            "status": gate_status,
            "items": items,
        }
    )

output_path.write_text(json.dumps({"status": overall_status, "gates": gates}, indent=2) + "\n")
PY
then
  record_step "freeze_phase7_evidence_manifest" "passed" "$MANIFEST_JSON" "Phase 7 evidence manifest was frozen from the current narrowed launch baseline."
else
  record_step "freeze_phase7_evidence_manifest" "failed" "$MANIFEST_JSON" "Phase 7 evidence manifest generation failed."
fi

overall_status="passed"
for status in "${STEP_STATUSES[@]}"; do
  if [[ "$status" != "passed" ]]; then
    overall_status="failed"
    break
  fi
done

python3 - <<'PY' \
  "$RESULT_JSON" \
  "$timestamp_utc" \
  "$git_sha" \
  "$git_ref" \
  "$ARTIFACT_DIR" \
  "$MANIFEST_JSON" \
  "$RECOVERY_VALIDATION_JSON" \
  "$overall_status" \
  "${STEP_NAMES[@]}" \
  -- \
  "${STEP_STATUSES[@]}" \
  -- \
  "${STEP_ARTIFACTS[@]}" \
  -- \
  "${STEP_NOTES[@]}"
import json
import pathlib
import sys

output = pathlib.Path(sys.argv[1])
timestamp_utc = sys.argv[2]
git_sha = sys.argv[3]
git_ref = sys.argv[4]
artifact_root = sys.argv[5]
manifest_path = sys.argv[6]
recovery_validation_path = sys.argv[7]
overall_status = sys.argv[8]

rest = sys.argv[9:]
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

manifest_payload = json.loads(pathlib.Path(manifest_path).read_text())
recovery_payload = json.loads(pathlib.Path(recovery_validation_path).read_text())

payload = {
    "timestamp_utc": timestamp_utc,
    "git_sha": git_sha,
    "git_ref": git_ref,
    "artifact_root": artifact_root,
    "result_json": str(output),
    "manifest_path": manifest_path,
    "recovery_validation_path": recovery_validation_path,
    "overall_status": overall_status,
    "steps": steps,
    "recovery_evidence": recovery_payload.get("items", []),
    "gate_evidence": manifest_payload.get("gates", []),
}

output.write_text(json.dumps(payload, indent=2) + "\n")
PY

python3 "$REPO_ROOT/scripts/phase6/evaluate-preaudit-dry-run.py" \
  --result-json "$RESULT_JSON" \
  --output-json "$PHASE7_ENTRY_JSON" \
  --output-md "$PHASE7_ENTRY_MD"

phase7_entry_ready="$(
  python3 - <<'PY' "$PHASE7_ENTRY_JSON"
import json
import pathlib
import sys

payload = json.loads(pathlib.Path(sys.argv[1]).read_text())
print(str(payload.get("phase7_entry_ready", False)).lower())
PY
)"

{
  echo "# Phase 6 Pre-Audit Dry Run"
  echo
  echo "- Status: \`$overall_status\`"
  echo "- Phase 7 entry ready: \`$phase7_entry_ready\`"
  echo "- Evidence root: \`$ARTIFACT_DIR\`"
  echo "- Result: \`$RESULT_JSON\`"
  echo "- Entry review: \`$PHASE7_ENTRY_MD\`"
  echo
  echo "## Steps"
  echo
  for idx in "${!STEP_NAMES[@]}"; do
    echo "- ${STEP_NAMES[$idx]}: \`${STEP_STATUSES[$idx]}\`"
    echo "  artifact: \`${STEP_ARTIFACTS[$idx]}\`"
    echo "  notes: ${STEP_NOTES[$idx]}"
  done
} >"$SUMMARY_MD"

echo "$ARTIFACT_DIR"
