#!/usr/bin/env bash

set -euo pipefail

curl -X POST http://localhost:8024/api/v1/ai-apps/ \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "11111111-1111-1111-1111-111111111111",
    "name": "demo-app",
    "environment": "dev",
    "allowed_models": ["gpt-4o-mini"]
  }'
echo
