#!/bin/bash
# Quick API test script for SOAR Agent

set -e

SOAR_AGENT_URL="${SOAR_AGENT_URL:-http://localhost:8004}"
TENANT_ID="${TENANT_ID:-00000000-0000-0000-0000-000000000000}"

echo "🧪 Testing SOAR Agent API at $SOAR_AGENT_URL"
echo ""

# Test health check
echo "1. Testing health check..."
curl -s "$SOAR_AGENT_URL/health" | jq '.' || echo "❌ Health check failed"
echo ""

# Test root endpoint
echo "2. Testing root endpoint..."
curl -s "$SOAR_AGENT_URL/" | jq '.' || echo "❌ Root endpoint failed"
echo ""

# Test list playbooks
echo "3. Testing list playbooks..."
curl -s -H "X-Tenant-ID: $TENANT_ID" "$SOAR_AGENT_URL/soar/playbooks" | jq '.' || echo "❌ List playbooks failed"
echo ""

# Test create playbook
echo "4. Testing create playbook..."
PLAYBOOK_RESPONSE=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{
    "name": "Test Playbook",
    "description": "A test playbook",
    "category": "phishing",
    "version": "1.0.0",
    "workflow": {
      "nodes": [
        {
          "id": "trigger-1",
          "type": "manual_trigger",
          "position": {"x": 0, "y": 0},
          "data": {"label": "Start"}
        }
      ],
      "edges": []
    },
    "is_template": false,
    "requires_approval": false,
    "tags": ["test"]
  }' \
  "$SOAR_AGENT_URL/soar/playbooks")

echo "$PLAYBOOK_RESPONSE" | jq '.' || echo "$PLAYBOOK_RESPONSE"
echo ""

# Extract playbook ID if created successfully
PLAYBOOK_ID=$(echo "$PLAYBOOK_RESPONSE" | jq -r '.id // empty')
if [ -n "$PLAYBOOK_ID" ] && [ "$PLAYBOOK_ID" != "null" ]; then
  echo "✅ Playbook created with ID: $PLAYBOOK_ID"
  echo ""
  
  # Test get playbook
  echo "5. Testing get playbook..."
  curl -s -H "X-Tenant-ID: $TENANT_ID" "$SOAR_AGENT_URL/soar/playbooks/$PLAYBOOK_ID" | jq '.' || echo "❌ Get playbook failed"
  echo ""
  
  # Test validate playbook
  echo "6. Testing validate playbook..."
  curl -s -X POST -H "X-Tenant-ID: $TENANT_ID" "$SOAR_AGENT_URL/soar/playbooks/$PLAYBOOK_ID/validate" | jq '.' || echo "❌ Validate playbook failed"
  echo ""
  
  # Test copy playbook
  echo "7. Testing copy playbook..."
  COPY_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -H "X-Tenant-ID: $TENANT_ID" \
    -d '{"new_name": "Copied Test Playbook"}' \
    "$SOAR_AGENT_URL/soar/playbooks/$PLAYBOOK_ID/copy")
  echo "$COPY_RESPONSE" | jq '.' || echo "$COPY_RESPONSE"
  echo ""
else
  echo "⚠️  Could not create playbook, skipping dependent tests"
fi

echo "✅ API tests completed!"

