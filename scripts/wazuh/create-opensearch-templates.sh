#!/bin/bash
# Create OpenSearch index templates for SentinelGrid Endpoint Manager (Wazuh)

set -e

OPENSEARCH_URL="${OPENSEARCH_URL:-http://localhost:9200}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_FILE="${SCRIPT_DIR}/../../infra/wazuh/opensearch-index-template.json"

echo "=========================================="
echo "Creating OpenSearch Index Templates"
echo "=========================================="
echo "OpenSearch URL: ${OPENSEARCH_URL}"
echo ""

# Check if OpenSearch is available
echo "Checking OpenSearch connectivity..."
if ! curl -s -f "${OPENSEARCH_URL}/_cluster/health" > /dev/null 2>&1; then
    echo "❌ OpenSearch is not available at ${OPENSEARCH_URL}"
    echo "   Please start OpenSearch first: docker-compose up opensearch"
    exit 1
fi

echo "✅ OpenSearch is available"
echo ""

# Create Wazuh alerts index template
echo "Creating wazuh-alerts index template..."
curl -X PUT "${OPENSEARCH_URL}/_index_template/wazuh-alerts-template" \
  -H 'Content-Type: application/json' \
  -d @"${TEMPLATE_FILE}" \
  -w "\nHTTP Status: %{http_code}\n"

echo ""
echo "=========================================="
echo "✅ Index template created successfully!"
echo "=========================================="
echo ""
echo "Verification:"
echo "  curl ${OPENSEARCH_URL}/_index_template/wazuh-alerts-template | jq '.'"
echo ""
echo "Test index creation:"
echo "  curl -X PUT '${OPENSEARCH_URL}/wazuh-alerts-test-tenant-2025.12.03'"
echo ""

