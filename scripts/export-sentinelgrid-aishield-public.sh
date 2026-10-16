#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
SOURCE_DIR="$REPO_ROOT/SentinelGridAIShield"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /path/to/output-directory" >&2
  exit 1
fi

TARGET_DIR=$1

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "Source directory not found: $SOURCE_DIR" >&2
  exit 1
fi

mkdir -p "$TARGET_DIR"

if find "$TARGET_DIR" -mindepth 1 -maxdepth 1 | read -r _; then
  echo "Target directory must be empty: $TARGET_DIR" >&2
  exit 1
fi

rsync -a \
  --exclude ".git" \
  --exclude ".pytest_cache" \
  --exclude "MASTER_SUMMARY.md" \
  --exclude "COMPLETE_IMPLEMENTATION_SUMMARY.md" \
  --exclude "IMPLEMENTATION_STATUS.md" \
  --exclude "FINAL_STATUS.md" \
  --exclude "TEST_RESULTS_SUMMARY.md" \
  --exclude "TESTING_GUIDE.md" \
  --exclude "__pycache__" \
  --exclude "*.pyc" \
  "$SOURCE_DIR"/ "$TARGET_DIR"/

cat <<EOF
Export complete: $TARGET_DIR

Next steps:
1. Review .env.example and CI defaults.
2. Initialize the new repository:
   cd "$TARGET_DIR"
   git init
   git add .
   git commit -m "Initial public release of SentinelGridAIShield"
3. Create a new GitHub repository and push it:
   git remote add origin <new-public-repo-url>
   git branch -M main
   git push -u origin main
EOF
