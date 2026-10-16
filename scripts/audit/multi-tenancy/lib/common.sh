#!/usr/bin/env bash

set -euo pipefail

audit_repo_root() {
  git rev-parse --show-toplevel
}

audit_now_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

audit_validate_profile() {
  local profile="${1:-}"
  case "$profile" in
    smoke|standard|full) ;;
    *)
      echo "Invalid profile: $profile" >&2
      return 1
      ;;
  esac
}

audit_validate_env_name() {
  local env_name="${1:-}"
  case "$env_name" in
    local|staging|audit) ;;
    *)
      echo "Invalid env: $env_name" >&2
      return 1
      ;;
  esac
}

audit_require_cmd() {
  local cmd
  for cmd in "$@"; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      echo "Missing required command: $cmd" >&2
      return 1
    fi
  done
}

audit_default_run_id() {
  local env_name="${1:-local}"
  local profile="${2:-standard}"
  printf "%s-%s-%s" "$(date -u +%H%M%S)" "$env_name" "$profile"
}

