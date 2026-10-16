#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../../.." && pwd)"

MODE="plan"
COMPONENT=""
BACKUP_FILE=""
EVIDENCE_DIR=""
TIMEBOX_MINUTES=""

usage() {
  cat <<'EOF'
Usage: run-restore-drill.sh --component <postgres|keycloak|all> [options]

Options:
  --component <value>    Component to restore: postgres, keycloak, or all
  --backup-file <path>   Optional explicit backup file
  --mode <plan|live>     plan: capture the drill command and context only
                         live: execute restore-system.sh with auto-confirm enabled
  --evidence-dir <path>  Optional explicit evidence directory
  --timebox-minutes <n>  Optional recovery timebox in minutes
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --component)
      COMPONENT="${2:-}"
      shift 2
      ;;
    --backup-file)
      BACKUP_FILE="${2:-}"
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

case "$COMPONENT" in
  postgres|keycloak|all) ;;
  *)
    echo "--component is required and must be postgres, keycloak, or all" >&2
    exit 1
    ;;
esac

case "$MODE" in
  plan|live) ;;
  *)
    echo "--mode must be plan or live" >&2
    exit 1
    ;;
esac

default_timebox_minutes() {
  case "$1" in
    postgres) echo "20" ;;
    keycloak) echo "30" ;;
    all) echo "45" ;;
    *) echo "30" ;;
  esac
}

TIMEBOX_MINUTES="${TIMEBOX_MINUTES:-$(default_timebox_minutes "$COMPONENT")}"

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
RUN_ID="$(date -u +%H%M%S)-${COMPONENT}-${MODE}"
DEFAULT_EVIDENCE_DIR="$REPO_ROOT/artifacts/drills/restore/$DATE_DIR/$RUN_ID"
EVIDENCE_DIR="${EVIDENCE_DIR:-$DEFAULT_EVIDENCE_DIR}"
mkdir -p "$EVIDENCE_DIR"

COMMANDS_LOG="$EVIDENCE_DIR/commands.log"
RUN_LOG="$EVIDENCE_DIR/run.log"
RESULT_JSON="$EVIDENCE_DIR/result.json"
SUMMARY_MD="$EVIDENCE_DIR/summary.md"
OPERATOR_ACTIONS_MD="$EVIDENCE_DIR/operator-actions.md"

RESTORE_CMD=("$SCRIPT_DIR/restore-system.sh" "$COMPONENT")
if [[ -n "$BACKUP_FILE" ]]; then
  RESTORE_CMD+=("$BACKUP_FILE")
fi

render_operator_actions() {
  case "$COMPONENT" in
    postgres)
      cat <<EOF
# Expected Operator Actions

1. Confirm the latest PostgreSQL backup filename and timestamp.
2. Confirm the target restore database host, port, database, and operator account.
3. Announce the maintenance window and note the recovery timebox of ${TIMEBOX_MINUTES} minutes.
4. Run the restore wrapper and capture the resulting artifact directory.
5. Verify database connectivity and check that public schema tables are present.
6. Bring up or verify launch services that depend on PostgreSQL: IAM, API gateway, orchestrator, model gateway, SIEM, and frontend.
7. Verify login, dashboard, alerts, incidents, and onboarding status.
8. Record any manual fixes, drift corrections, or credential handling performed during the drill.
EOF
      ;;
    keycloak)
      cat <<EOF
# Expected Operator Actions

1. Confirm the latest Keycloak export filename and timestamp.
2. Confirm the Keycloak admin auth mode for the drill and note whether it is service-account or break-glass.
3. Announce the maintenance window and note the recovery timebox of ${TIMEBOX_MINUTES} minutes.
4. Run the restore wrapper and capture the resulting artifact directory.
5. Verify realm import, client presence, and expected identity metadata after restore.
6. Verify login, token issuance, token refresh, and protected route access through the narrowed launch flow.
7. Record any manual fixes, realm import conflicts, or follow-up credential rotation tasks.
EOF
      ;;
    all)
      cat <<EOF
# Expected Operator Actions

1. Confirm both the PostgreSQL and Keycloak backup filenames and timestamps.
2. Announce the maintenance window and note the recovery timebox of ${TIMEBOX_MINUTES} minutes.
3. Run the restore wrapper and capture the resulting artifact directory.
4. Verify PostgreSQL restore success and Keycloak import success separately.
5. Bring up or verify the narrowed launch services and confirm login, dashboard, alerts, incidents, and onboarding status.
6. Record any manual fixes, ordering dependencies, or credential handling tasks.
EOF
      ;;
  esac
}

render_operator_actions >"$OPERATOR_ACTIONS_MD"

START_EPOCH="$(date -u +%s)"
STARTED_AT_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

{
  echo "timestamp_utc=$STARTED_AT_UTC"
  echo "mode=$MODE"
  echo "component=$COMPONENT"
  echo "backup_file=${BACKUP_FILE:-latest}"
  echo "postgres_host=${POSTGRES_HOST:-localhost}"
  echo "postgres_db=${POSTGRES_DB:-sentinelgrid}"
  echo "keycloak_url=${KEYCLOAK_URL:-http://localhost:8080}"
  echo "keycloak_auth_mode=$([[ "${KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT:-false}" == "true" ]] && echo service_account || echo password)"
  echo "backup_dir=${BACKUP_DIR:-/var/backups/sentinelgrid}"
  echo "timebox_minutes=$TIMEBOX_MINUTES"
} >"$EVIDENCE_DIR/environment.txt"

printf '%s\n' "${RESTORE_CMD[*]}" >"$COMMANDS_LOG"

STATUS="planned"
NOTES="Restore drill plan captured."

if [[ "$MODE" == "plan" ]]; then
  bash -n "$SCRIPT_DIR/restore-system.sh"
else
  STATUS="failed"
  NOTES="Restore drill execution failed."
  if RESTORE_AUTO_CONFIRM=true "${RESTORE_CMD[@]}" >"$RUN_LOG" 2>&1; then
    STATUS="passed"
    NOTES="Restore drill executed successfully."
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
  NOTES="Restore drill exceeded the ${TIMEBOX_MINUTES}-minute timebox."
fi

cat >"$RESULT_JSON" <<EOF
{
  "status": "$(printf '%s' "$STATUS")",
  "mode": "$(printf '%s' "$MODE")",
  "component": "$(printf '%s' "$COMPONENT")",
  "backup_file": "$(printf '%s' "${BACKUP_FILE:-latest}")",
  "command": "$(printf '%s' "${RESTORE_CMD[*]}")",
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
# Restore Drill

- Status: \`$STATUS\`
- Mode: \`$MODE\`
- Component: \`$COMPONENT\`
- Backup file: \`${BACKUP_FILE:-latest}\`
- Started: \`$STARTED_AT_UTC\`
- Ended: \`$ENDED_AT_UTC\`
- Duration: \`${DURATION_SECONDS}s\`
- Timebox: \`${TIMEBOX_MINUTES}m\`
- Within timebox: \`$WITHIN_TIMEBOX\`
- Evidence directory: \`$EVIDENCE_DIR\`
- Operator actions: \`$OPERATOR_ACTIONS_MD\`

## Command

\`\`\`bash
${RESTORE_CMD[*]}
\`\`\`

## Notes

$NOTES
EOF

echo "$EVIDENCE_DIR"
