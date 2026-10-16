#!/bin/bash
# Run SentinelGrid tests with conda environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_NAME="SentinelTest"

echo "=========================================="
echo "Running SentinelGrid Tests"
echo "=========================================="
echo ""

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "❌ Conda is not installed"
    echo "   Please install Miniconda or Anaconda"
    echo "   Or run: cd backend/tests && python3 -m pytest $@"
    exit 1
fi

# Check if environment exists
if ! conda env list | grep -q "^${ENV_NAME} "; then
    echo "⚠️  Conda environment '$ENV_NAME' does not exist"
    echo "   Creating it now..."
    cd "$PROJECT_ROOT/backend/tests"
    ./setup-conda-env.sh
fi

# Activate conda environment
echo "Activating conda environment: $ENV_NAME"
eval "$(conda shell.bash hook)"
conda activate "$ENV_NAME"

# Set default test environment variables if not set
export KEYCLOAK_URL=${KEYCLOAK_URL:-http://localhost:8081}
export IAM_AGENT_URL=${IAM_AGENT_URL:-http://localhost:8005}
export API_GATEWAY_URL=${API_GATEWAY_URL:-http://localhost:8082}
export TEST_REALM=${TEST_REALM:-agribotsai}
export TEST_CLIENT_ID=${TEST_CLIENT_ID:-agribotsai-web}
export TEST_USERNAME=${TEST_USERNAME:-admin@agribotsai.com}
export TEST_PASSWORD=${TEST_PASSWORD:-ChangeMe123!}

echo ""
echo "Test Environment:"
echo "  KEYCLOAK_URL: $KEYCLOAK_URL"
echo "  IAM_AGENT_URL: $IAM_AGENT_URL"
echo "  API_GATEWAY_URL: $API_GATEWAY_URL"
echo "  TEST_REALM: $TEST_REALM"
echo ""

# Check if services are running
echo "Checking services..."
check_service() {
  local url=$1
  local name=$2
  
  if curl -s -f "$url/health" > /dev/null 2>&1 || curl -s -f "$url" > /dev/null 2>&1; then
    echo "  ✅ $name"
    return 0
  else
    echo "  ❌ $name (not available)"
    return 1
  fi
}

KEYCLOAK_OK=$(check_service "$KEYCLOAK_URL" "Keycloak" && echo "yes" || echo "no")
IAM_OK=$(check_service "$IAM_AGENT_URL" "IAM Agent" && echo "yes" || echo "no")
API_OK=$(check_service "$API_GATEWAY_URL" "API Gateway" && echo "yes" || echo "no")

if [ "$KEYCLOAK_OK" != "yes" ] || [ "$IAM_OK" != "yes" ] || [ "$API_OK" != "yes" ]; then
    echo ""
    echo "⚠️  Some services are not available"
    echo "   Start them with: docker-compose -f docker-compose.dev.yml up -d"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Run tests
cd "$PROJECT_ROOT/backend/tests"
echo ""
echo "Running tests..."
echo ""

if [ $# -eq 0 ]; then
    # Run all tests
    pytest -v
else
    # Run with provided arguments
    pytest "$@"
fi

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "=========================================="
    echo "✅ All tests passed!"
    echo "=========================================="
else
    echo "=========================================="
    echo "❌ Some tests failed (exit code: $EXIT_CODE)"
    echo "=========================================="
fi

exit $EXIT_CODE

