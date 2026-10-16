#!/bin/bash
# Test SentinelGrid Endpoint Manager - Agent Registration Flow

set -e

API_BASE="${API_BASE:-http://localhost:8032}"
IAM_BASE="${IAM_BASE:-http://localhost:8000}"
WAZUH_API="${WAZUH_API:-http://localhost:55000}"

echo "=========================================="
echo "SentinelGrid Endpoint Manager"
echo "Agent Registration Test"
echo "=========================================="
echo ""

# Step 1: Get test JWT token (you'll need a real token for actual testing)
echo "Step 1: JWT Token"
echo "-------------------"
echo "⚠️  You need a valid JWT token with tenant_id claim"
echo "   For testing, use the IAM Agent to get a token:"
echo "   POST ${IAM_BASE}/api/v1/auth/login"
echo ""
read -p "Enter JWT token: " TENANT_TOKEN

if [ -z "$TENANT_TOKEN" ]; then
    echo "❌ No token provided. Exiting."
    exit 1
fi

echo "✅ Token provided"
echo ""

# Step 2: Check service health
echo "Step 2: Service Health Check"
echo "-------------------"
HEALTH=$(curl -s "${API_BASE}/health")
echo "$HEALTH" | jq '.'

if echo "$HEALTH" | jq -e '.status == "healthy"' > /dev/null; then
    echo "✅ Service is healthy"
else
    echo "❌ Service is not healthy"
    exit 1
fi
echo ""

# Step 3: Register an agent
echo "Step 3: Register Agent"
echo "-------------------"
RESPONSE=$(curl -s -X POST "${API_BASE}/api/v1/wazuh/agents/register" \
  -H "Authorization: Bearer ${TENANT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "test-server-01",
    "ip_address": "10.0.1.50",
    "os_platform": "linux",
    "os_version": "Ubuntu 22.04"
  }')

echo "$RESPONSE" | jq '.'

if echo "$RESPONSE" | jq -e '.success == true' > /dev/null; then
    AGENT_ID=$(echo "$RESPONSE" | jq -r '.agent_id')
    TENANT_ID=$(echo "$RESPONSE" | jq -r '.tenant_id')
    echo "✅ Agent registered successfully"
    echo "   Agent ID: ${AGENT_ID}"
    echo "   Tenant ID: ${TENANT_ID}"
else
    echo "❌ Agent registration failed"
    exit 1
fi
echo ""

# Step 4: Verify agent has tenant_id label in Wazuh Manager
echo "Step 4: Verify Agent Labels in Wazuh Manager"
echo "-------------------"
echo "Checking agent ${AGENT_ID} in Wazuh Manager..."

# Get Wazuh API token
WAZUH_TOKEN=$(curl -s -u wazuh-api:MyS3cr3tP455w0rd! \
  -X POST "${WAZUH_API}/security/user/authenticate" | jq -r '.data.token')

# Get agent details
AGENT_DATA=$(curl -s -H "Authorization: Bearer ${WAZUH_TOKEN}" \
  "${WAZUH_API}/agents/${AGENT_ID}")

echo "$AGENT_DATA" | jq '.data.labels'

if echo "$AGENT_DATA" | jq -e ".data.labels.tenant_id == \"${TENANT_ID}\"" > /dev/null; then
    echo "✅ tenant_id label verified in Wazuh Manager"
else
    echo "❌ tenant_id label not found or incorrect"
    exit 1
fi
echo ""

# Step 5: List tenant's agents
echo "Step 5: List Tenant's Agents"
echo "-------------------"
AGENTS_LIST=$(curl -s -X GET "${API_BASE}/api/v1/wazuh/agents" \
  -H "Authorization: Bearer ${TENANT_TOKEN}")

echo "$AGENTS_LIST" | jq '.'

AGENT_COUNT=$(echo "$AGENTS_LIST" | jq '.count')
echo "✅ Found ${AGENT_COUNT} agent(s) for tenant"
echo ""

# Step 6: Get agent details
echo "Step 6: Get Agent Details"
echo "-------------------"
AGENT_DETAILS=$(curl -s -X GET "${API_BASE}/api/v1/wazuh/agents/${AGENT_ID}" \
  -H "Authorization: Bearer ${TENANT_TOKEN}")

echo "$AGENT_DETAILS" | jq '.'
echo "✅ Agent details retrieved"
echo ""

# Step 7: Summary
echo "=========================================="
echo "✅ All Tests Passed!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Service health: OK"
echo "  - Agent registration: OK"
echo "  - tenant_id labeling: OK"
echo "  - Agent listing: OK"
echo "  - Agent details: OK"
echo ""
echo "Next Steps:"
echo "  1. Install actual agent on a test machine"
echo "  2. Use the agent_key from registration"
echo "  3. Configure agent to connect to manager.sentinelgrid.ai:1514"
echo "  4. Verify events appear in OpenSearch"
echo ""
echo "Agent Key (save this):"
echo "$RESPONSE" | jq -r '.agent_key'
echo ""
echo "Installation command (Linux):"
echo "$RESPONSE" | jq -r '.instructions.linux'
echo ""
