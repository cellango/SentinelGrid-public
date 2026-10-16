#!/bin/bash
# Verify tenant isolation for SentinelGrid Endpoint Manager

set -e

OPENSEARCH_URL="${OPENSEARCH_URL:-http://localhost:9200}"
WAZUH_API="${WAZUH_API:-http://localhost:55000}"

echo "=========================================="
echo "Tenant Isolation Verification"
echo "=========================================="
echo ""

# Step 1: Get Wazuh API token
echo "Step 1: Authenticating with Wazuh Manager..."
WAZUH_TOKEN=$(curl -s -u wazuh-api:MyS3cr3tP455w0rd! \
  -X POST "${WAZUH_API}/security/user/authenticate" | jq -r '.data.token')

if [ -z "$WAZUH_TOKEN" ] || [ "$WAZUH_TOKEN" = "null" ]; then
    echo "❌ Failed to get Wazuh API token"
    exit 1
fi

echo "✅ Authenticated with Wazuh Manager"
echo ""

# Step 2: List all agents and their labels
echo "Step 2: Listing All Agents and Labels..."
AGENTS=$(curl -s -H "Authorization: Bearer ${WAZUH_TOKEN}" \
  "${WAZUH_API}/agents")

echo "$AGENTS" | jq '.data.affected_items[] | {id: .id, name: .name, labels: .labels}'
echo ""

# Step 3: Extract unique tenant_ids
echo "Step 3: Unique tenant_ids Found..."
TENANT_IDS=$(echo "$AGENTS" | jq -r '.data.affected_items[].labels.tenant_id' | sort -u)

if [ -z "$TENANT_IDS" ]; then
    echo "⚠️  No agents with tenant_id labels found"
    echo "   Register an agent first using the API"
    exit 0
fi

echo "$TENANT_IDS"
TENANT_COUNT=$(echo "$TENANT_IDS" | wc -l | tr -d ' ')
echo "Found ${TENANT_COUNT} unique tenant(s)"
echo ""

# Step 4: Check OpenSearch indices
echo "Step 4: Checking OpenSearch Indices..."
INDICES=$(curl -s "${OPENSEARCH_URL}/_cat/indices/wazuh-alerts-*?h=index,docs.count" | sort)

if [ -z "$INDICES" ]; then
    echo "⚠️  No wazuh-alerts indices found yet"
    echo "   Indices will be created when agents send their first events"
else
    echo "$INDICES"
    echo ""
    echo "✅ Found Wazuh alert indices"
fi
echo ""

# Step 5: Verify tenant-specific indices
echo "Step 5: Verifying Tenant-Specific Indices..."
for TENANT_ID in $TENANT_IDS; do
    echo "Checking tenant: ${TENANT_ID}"
    
    # Check if index exists for this tenant
    INDEX_PATTERN="wazuh-alerts-${TENANT_ID}-*"
    INDEX_EXISTS=$(curl -s "${OPENSEARCH_URL}/_cat/indices/${INDEX_PATTERN}?h=index" | head -1)
    
    if [ -z "$INDEX_EXISTS" ]; then
        echo "  ⚠️  No index found for ${INDEX_PATTERN}"
        echo "     This is normal if agent hasn't sent events yet"
    else
        echo "  ✅ Index found: ${INDEX_EXISTS}"
        
        # Count documents
        DOC_COUNT=$(curl -s "${OPENSEARCH_URL}/${INDEX_PATTERN}/_count" | jq '.count')
        echo "     Documents: ${DOC_COUNT}"
        
        # Sample one event to verify tenant_id
        SAMPLE=$(curl -s "${OPENSEARCH_URL}/${INDEX_PATTERN}/_search?size=1" | \
          jq '.hits.hits[0]._source | {agent_label_tenant_id: .agent.labels.tenant_id, tenant_id: .tenant_id}')
        echo "     Sample event tenant_id:"
        echo "$SAMPLE" | jq '.'
    fi
    echo ""
done

# Step 6: Verify isolation (try to cross-access)
echo "Step 6: Testing Cross-Tenant Access Prevention..."
if [ "$TENANT_COUNT" -gt 1 ]; then
    TENANT_1=$(echo "$TENANT_IDS" | sed -n 1p)
    TENANT_2=$(echo "$TENANT_IDS" | sed -n 2p)
    
    echo "Tenant 1: ${TENANT_1}"
    echo "Tenant 2: ${TENANT_2}"
    echo ""
    
    # Query tenant 1's index
    COUNT_1=$(curl -s "${OPENSEARCH_URL}/wazuh-alerts-${TENANT_1}-*/_count" | jq '.count // 0')
    echo "Tenant 1 has ${COUNT_1} alerts"
    
    # Query tenant 2's index
    COUNT_2=$(curl -s "${OPENSEARCH_URL}/wazuh-alerts-${TENANT_2}-*/_count" | jq '.count // 0')
    echo "Tenant 2 has ${COUNT_2} alerts"
    
    # Try to query tenant 1's data with tenant 2's filter
    CROSS_QUERY=$(curl -s "${OPENSEARCH_URL}/wazuh-alerts-${TENANT_1}-*/_search" \
      -H 'Content-Type: application/json' \
      -d "{
        \"query\": {
          \"term\": {\"agent.labels.tenant_id\": \"${TENANT_2}\"}
        }
      }" | jq '.hits.total.value')
    
    if [ "$CROSS_QUERY" = "0" ]; then
        echo "✅ Tenant isolation verified - no cross-tenant data leak"
    else
        echo "❌ WARNING: Found ${CROSS_QUERY} documents with wrong tenant_id!"
    fi
else
    echo "⚠️  Only 1 tenant found - cannot test cross-tenant isolation"
    echo "   Register agents from multiple tenants to test"
fi
echo ""

echo "=========================================="
echo "✅ Isolation Verification Complete"
echo "=========================================="

