#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../../.." && pwd)"

MODE="plan"
RELEASE=""
REVISION=""
NAMESPACE="${K8S_NAMESPACE:-sg-core}"
TIMEOUT="${ROLLBACK_TIMEOUT:-180s}"
READY_URL=""
EVIDENCE_DIR=""
TIMEBOX_MINUTES="${ROLLBACK_TIMEBOX_MINUTES:-15}"

usage() {
  cat <<'EOF'
Usage: run-release-rollback-drill.sh --release <name> --revision <n> [options]

Options:
  --release <name>       Helm release name to roll back
  --revision <number>    Helm revision to roll back to
  --namespace <name>     Kubernetes namespace, defaults to sg-core
  --ready-url <url>      Optional readiness URL to verify after rollback
  --mode <plan|live>     plan: capture the rollback command and context only
                         live: execute helm rollback and rollout verification
  --evidence-dir <path>  Optional explicit evidence directory
  --timebox-minutes <n>  Optional rollback recovery timebox in minutes
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --release)
      RELEASE="${2:-}"
      shift 2
      ;;
    --revision)
      REVISION="${2:-}"
      shift 2
      ;;
    --namespace)
      NAMESPACE="${2:-}"
      shift 2
      ;;
    --ready-url)
      READY_URL="${2:-}"
      shift 2
      ;;
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --evidence-dir)
      EVIDENCE_DIR="${2:-}"
      shift 2
      ;;
    --timebox-minutes)
      TIMEBOX_MINUTES="${2:-}"
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

if [[ -z "$RELEASE" || -z "$REVISION" ]]; then
  echo "--release and --revision are required" >&2
  exit 1
fi

case "$MODE" in
  plan|live) ;;
  *)
    echo "--mode must be plan or live" >&2
    exit 1
    ;;
esac

case "$TIMEBOX_MINUTES" in
  ''|*[!0-9]*)
    echo "--timebox-minutes must be a positive integer" >&2
    exit 1
    ;;
  *)
    if [[ "$TIMEBOX_MINUTES" -le 0 ]]; then
      echo "--timebox-minutes must be greater than zero" >&2
      exit 1
    fi
    ;;
esac

DATE_DIR="$(date -u +%F)"
RUN_ID="$(date -u +%H%M%S)-${RELEASE}-rollback-${MODE}"
DEFAULT_EVIDENCE_DIR="$REPO_ROOT/artifacts/drills/rollback/$DATE_DIR/$RUN_ID"
EVIDENCE_DIR="${EVIDENCE_DIR:-$DEFAULT_EVIDENCE_DIR}"
mkdir -p "$EVIDENCE_DIR"

COMMANDS_LOG="$EVIDENCE_DIR/commands.log"
RUN_LOG="$EVIDENCE_DIR/run.log"
RESULT_JSON="$EVIDENCE_DIR/result.json"
SUMMARY_MD="$EVIDENCE_DIR/summary.md"
OPERATOR_ACTIONS_MD="$EVIDENCE_DIR/operator-actions.md"

ROLLBACK_CMD=(helm rollback "$RELEASE" "$REVISION" -n "$NAMESPACE")
ROLLOUT_CMD=(kubectl rollout status "deployment/$RELEASE" -n "$NAMESPACE" --timeout="$TIMEOUT")

cat >"$OPERATOR_ACTIONS_MD" <<EOF
# Expected Operator Actions

1. Confirm the target Helm release, namespace, and rollback revision.
2. Announce the rollback drill and note the recovery timebox of ${TIMEBOX_MINUTES} minutes.
3. Capture the current Helm history before rollback.
4. Execute the rollback wrapper and capture the resulting artifact directory.
5. Verify deployment rollout completion and the optional readiness URL.
6. Confirm the intended release revision is active after rollback.
7. Record any manual interventions, Helm anomalies, or readiness delays.
EOF

START_EPOCH="$(date -u +%s)"
STARTED_AT_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

{
  echo "timestamp_utc=$STARTED_AT_UTC"
  echo "mode=$MODE"
  echo "release=$RELEASE"
  echo "revision=$REVISION"
  echo "namespace=$NAMESPACE"
  echo "timeout=$TIMEOUT"
  echo "ready_url=$READY_URL"
  echo "timebox_minutes=$TIMEBOX_MINUTES"
} >"$EVIDENCE_DIR/environment.txt"

{
  printf '%s\n' "${ROLLBACK_CMD[*]}"
  printf '%s\n' "${ROLLOUT_CMD[*]}"
  if [[ -n "$READY_URL" ]]; then
    printf '%s\n' "curl -fsS $READY_URL"
  fi
} >"$COMMANDS_LOG"

STATUS="planned"
NOTES="Rollback drill plan captured."

if [[ "$MODE" == "live" ]]; then
  STATUS="failed"
  NOTES="Rollback drill execution failed."
  if ! command -v helm >/dev/null 2>&1 || ! command -v kubectl >/dev/null 2>&1; then
    echo "helm and kubectl are required for live rollback drills" >"$RUN_LOG"
  else
    {
      printf '[CMD] %s\n' "${ROLLBACK_CMD[*]}"
      "${ROLLBACK_CMD[@]}"
      printf '[CMD] %s\n' "${ROLLOUT_CMD[*]}"
      "${ROLLOUT_CMD[@]}"
      if [[ -n "$READY_URL" ]]; then
        printf '[CMD] curl -fsS %s\n' "$READY_URL"
        curl -fsS "$READY_URL"
      fi
    } >"$RUN_LOG" 2>&1 && {
      STATUS="passed"
      NOTES="Rollback drill executed successfully."
    }
  fi
fi

END_EPOCH="$(date -u +%s)"
ENDED_AT_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DURATION_SECONDS="$((END_EPOCH - START_EPOCH))"
TIMEBOX_SECONDS="$((TIMEBOX_MINUTES * 60))"
WITHIN_TIMEBOX="true"

if [[ "$MODE" == "live" && "$DURATION_SECONDS" -gt "$TIMEBOX_SECONDS" ]]; then
  WITHIN_TIMEBOX="false"
  STATUS="failed"
  NOTES="Rollback drill exceeded the ${TIMEBOX_MINUTES}-minute timebox."
fi

cat >"$RESULT_JSON" <<EOF
{
  "status": "$(printf '%s' "$STATUS")",
  "mode": "$(printf '%s' "$MODE")",
  "release": "$(printf '%s' "$RELEASE")",
  "revision": "$(printf '%s' "$REVISION")",
  "namespace": "$(printf '%s' "$NAMESPACE")",
  "ready_url": "$(printf '%s' "$READY_URL")",
  "notes": "$(printf '%s' "$NOTES")",
  "started_at_utc": "$(printf '%s' "$STARTED_AT_UTC")",
  "ended_at_utc": "$(printf '%s' "$ENDED_AT_UTC")",
  "duration_seconds": $DURATION_SECONDS,
  "timebox_minutes": $TIMEBOX_MINUTES,
  "within_timebox": $WITHIN_TIMEBOX,
  "operator_actions_file": "$(printf '%s' "$OPERATOR_ACTIONS_MD")"
}
EOF

cat >"$SUMMARY_MD" <<EOF
# Rollback Drill

- Status: \`$STATUS\`
- Mode: \`$MODE\`
- Release: \`$RELEASE\`
- Revision: \`$REVISION\`
- Namespace: \`$NAMESPACE\`
- Started: \`$STARTED_AT_UTC\`
- Ended: \`$ENDED_AT_UTC\`
- Duration: \`${DURATION_SECONDS}s\`
- Timebox: \`${TIMEBOX_MINUTES}m\`
- Within timebox: \`$WITHIN_TIMEBOX\`
- Evidence directory: \`$EVIDENCE_DIR\`
- Operator actions: \`$OPERATOR_ACTIONS_MD\`

## Commands

\`\`\`bash
${ROLLBACK_CMD[*]}
${ROLLOUT_CMD[*]}
EOF

if [[ -n "$READY_URL" ]]; then
  cat >>"$SUMMARY_MD" <<EOF
curl -fsS $READY_URL
EOF
fi

cat >>"$SUMMARY_MD" <<EOF
\`\`\`

## Notes

$NOTES
EOF

echo "$EVIDENCE_DIR"
