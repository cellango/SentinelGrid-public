#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
EXPORT_SCRIPT="$SCRIPT_DIR/export-sentinelgrid-aishield-public.sh"

TARGET_REPO=""
BRANCH="main"
DO_COMMIT=0
DO_PUSH=0
COMMIT_MESSAGE=""

usage() {
  cat <<EOF
Usage: $0 --target /path/to/public-repo [--branch main] [--commit] [--push] [--message "msg"]

Examples:
  $0 --target ~/src/SentinelGridAIShield-public
  $0 --target ~/src/SentinelGridAIShield-public --commit
  $0 --target ~/src/SentinelGridAIShield-public --commit --push --branch main
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
    --commit)
      DO_COMMIT=1
      shift
      ;;
    --push)
      DO_PUSH=1
      shift
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
  echo "--target is required" >&2
  usage
  exit 1
fi

if [[ ! -d "$TARGET_REPO/.git" ]]; then
  echo "Target is not a git repository: $TARGET_REPO" >&2
  exit 1
fi

if [[ $DO_PUSH -eq 1 ]]; then
  DO_COMMIT=1
fi

if [[ -n "$(git -C "$TARGET_REPO" status --porcelain)" ]]; then
  echo "Target repository has uncommitted changes. Commit or stash them before syncing." >&2
  exit 1
fi

WORKDIR=$(mktemp -d /tmp/sentinelgrid-aishield-sync.XXXXXX)
trap 'rm -rf "$WORKDIR"' EXIT

EXPORT_DIR="$WORKDIR/export"
PRESERVE_DIR="$WORKDIR/preserve"
mkdir -p "$EXPORT_DIR" "$PRESERVE_DIR"

"$EXPORT_SCRIPT" "$EXPORT_DIR" >/dev/null

shopt -s nullglob
SOURCE_LICENSES=("$EXPORT_DIR"/LICENSE*)
TARGET_LICENSES=("$TARGET_REPO"/LICENSE*)
if [[ ${#SOURCE_LICENSES[@]} -eq 0 && ${#TARGET_LICENSES[@]} -gt 0 ]]; then
  cp "${TARGET_LICENSES[@]}" "$PRESERVE_DIR"/
fi
shopt -u nullglob

rsync -a --delete --exclude ".git" "$EXPORT_DIR"/ "$TARGET_REPO"/

if [[ -d "$PRESERVE_DIR" ]] && find "$PRESERVE_DIR" -maxdepth 1 -type f | read -r _; then
  rsync -a "$PRESERVE_DIR"/ "$TARGET_REPO"/
fi

echo "Sync complete. Target repository status:"
git -C "$TARGET_REPO" status --short

if [[ -z "$(git -C "$TARGET_REPO" status --porcelain)" ]]; then
  echo "No changes to commit."
  exit 0
fi

echo
git -C "$TARGET_REPO" diff --stat

if [[ $DO_COMMIT -eq 1 ]]; then
  if [[ -z "$COMMIT_MESSAGE" ]]; then
    SOURCE_SHA=$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo "unknown")
    COMMIT_MESSAGE="Sync SentinelGridAIShield from monorepo ${SOURCE_SHA}"
  fi

  git -C "$TARGET_REPO" add -A
  git -C "$TARGET_REPO" commit -m "$COMMIT_MESSAGE"
  echo "Created commit in target repo: $COMMIT_MESSAGE"
fi

if [[ $DO_PUSH -eq 1 ]]; then
  git -C "$TARGET_REPO" push origin "$BRANCH"
  echo "Pushed to origin/$BRANCH"
fi
