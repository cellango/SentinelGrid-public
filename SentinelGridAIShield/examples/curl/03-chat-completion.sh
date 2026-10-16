#!/usr/bin/env bash

set -euo pipefail

curl -X POST http://localhost:8023/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: 11111111-1111-1111-1111-111111111111" \
  -H "X-Realm: demo" \
  -H "X-App-ID: demo-app" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "Summarize prompt injection in one paragraph."}
    ]
  }'
echo
