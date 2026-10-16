#!/bin/bash
# Script to run end-to-end authentication tests
# Usage: ./scripts/run-e2e-tests.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "Running End-to-End Authentication Tests"
echo "=========================================="
echo ""

# Check if services are running
echo "Checking service availability..."

check_service() {
  local url=$1
  local name=$2
  
  if curl -s -f "$url" > /dev/null 2>&1; then
    echo "✅ $name is available"
    return 0
  else
    echo "❌ $name is not available at $url"
    return 1
  fi
}

KEYCLOAK_URL=${KEYCLOAK_URL:-http://localhost:8081}
IAM_AGENT_URL=${IAM_AGENT_URL:-http://localhost:8005}
API_GATEWAY_URL=${API_GATEWAY_URL:-http://localhost:8082}

check_service "$KEYCLOAK_URL/health" "Keycloak" || exit 1
check_service "$IAM_AGENT_URL/health" "IAM Agent" || exit 1
check_service "$API_GATEWAY_URL/health" "API Gateway" || exit 1

echo ""
echo "All services are available!"
echo ""

# Set environment variables
export KEYCLOAK_URL
export IAM_AGENT_URL
export API_GATEWAY_URL
export TEST_REALM=${TEST_REALM:-agribotsai}
export TEST_CLIENT_ID=${TEST_CLIENT_ID:-agribotsai-web}
export TEST_USERNAME=${TEST_USERNAME:-admin@agribotsai.com}
export TEST_PASSWORD=${TEST_PASSWORD:-ChangeMe123!}

# Run tests
echo "Running tests..."
echo ""

cd "$PROJECT_ROOT/backend/tests"

# Install test dependencies if needed
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
else
  source .venv/bin/activate
fi

# Run pytest
pytest test_auth_flow_e2e.py -v --tb=short --color=yes "$@"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo ""
  echo "=========================================="
  echo "✅ All tests passed!"
  echo "=========================================="
else
  echo ""
  echo "=========================================="
  echo "❌ Some tests failed (exit code: $EXIT_CODE)"
  echo "=========================================="
fi

exit $EXIT_CODE

