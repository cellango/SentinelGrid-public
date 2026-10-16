#!/usr/bin/env bash

set -euo pipefail

audit_log() {
  local level="${1:-INFO}"
  shift
  local message="$*"
  local timestamp
  timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  printf '[%s] [%s] %s\n' "$timestamp" "$level" "$message"
  if [[ -n "${AUDIT_COMMANDS_LOG:-}" ]]; then
    printf '[%s] [%s] %s\n' "$timestamp" "$level" "$message" >>"$AUDIT_COMMANDS_LOG"
  fi
}

audit_log_cmd() {
  local label="${1:-command}"
  shift
  audit_log "CMD" "$label :: $*"
}

