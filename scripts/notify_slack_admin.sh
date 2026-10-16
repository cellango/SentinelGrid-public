#!/usr/bin/env bash
# Send an infrastructure alert to the SentinelGrid Admin Slack channel via incoming webhook.

set -euo pipefail

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required to send Slack notifications" >&2
  exit 1
fi

WEBHOOK_URL="${SLACK_ADMIN_WEBHOOK_URL:-}"
if [ -z "${WEBHOOK_URL}" ]; then
  echo "SLACK_ADMIN_WEBHOOK_URL is not set; export it to the channel's incoming webhook URL." >&2
  exit 1
fi

MESSAGE="${1:-}"
if [ -z "${MESSAGE}" ]; then
  echo "Usage: $0 \"message text\"" >&2
  exit 1
fi

# Build JSON payload safely even if message contains quotes/newlines.
PAYLOAD="$(MESSAGE_INPUT="${MESSAGE}" python3 - <<'PY'
import json, os, sys
msg = os.environ.get("MESSAGE_INPUT", "")
print(json.dumps({"text": msg}))
PY
)"

curl -sSf -X POST \
  -H 'Content-Type: application/json' \
  --data "${PAYLOAD}" \
  "${WEBHOOK_URL}"
