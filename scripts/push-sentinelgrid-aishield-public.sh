#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SYNC_SCRIPT="$SCRIPT_DIR/sync-sentinelgrid-aishield-public.sh"

TARGET_REPO="${PUBLIC_REPO_PATH:-}"
BRANCH="${PUBLIC_REPO_BRANCH:-main}"
COMMIT_MESSAGE="${PUBLIC_REPO_COMMIT_MESSAGE:-}"

usage() {
  cat <<EOF
Usage: $0 --target /path/to/public-repo [--branch main] [--message "msg"]

Environment variables:
  PUBLIC_REPO_PATH
  PUBLIC_REPO_BRANCH
  PUBLIC_REPO_COMMIT_MESSAGE
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET_REPO=${2:-}
      shift 2
      ;;
    --branch)
      BRANCH=${2:-}
      shift 2
      ;;
    --message)
      COMMIT_MESSAGE=${2:-}
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$TARGET_REPO" ]]; then
  echo "A target public repo path is required." >&2
  usage
  exit 1
fi

ARGS=(--target "$TARGET_REPO" --branch "$BRANCH" --commit --push)
if [[ -n "$COMMIT_MESSAGE" ]]; then
  ARGS+=(--message "$COMMIT_MESSAGE")
fi

"$SYNC_SCRIPT" "${ARGS[@]}"
