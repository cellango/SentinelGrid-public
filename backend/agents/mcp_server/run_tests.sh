#!/bin/bash
# Run MCP Server test suite

set -e

echo "==================================="
echo "SentinelGrid MCP Server Test Suite"
echo "==================================="
echo ""

# Change to script directory
cd "$(dirname "$0")"

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "Installing test dependencies..."
    pip install -r requirements.txt
fi

echo "Running tests..."
echo ""

# Run tests with coverage
pytest \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=html \
    -v \
    "$@"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    echo ""
    echo "Coverage report generated: htmlcov/index.html"
else
    echo ""
    echo "❌ Some tests failed"
    exit $EXIT_CODE
fi

