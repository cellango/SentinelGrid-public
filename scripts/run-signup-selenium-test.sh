#!/bin/bash

# Script to run Selenium signup test in non-headless mode
# This allows you to see the browser during the test

set -e

# Try to find the test conda environment (could be "test" or "SentinelTest")
CONDA_ENV_NAME=""
if conda env list | grep -q "^test "; then
    CONDA_ENV_NAME="test"
elif conda env list | grep -q "^SentinelTest "; then
    CONDA_ENV_NAME="SentinelTest"
fi

# If not found, default to "test"
if [ -z "$CONDA_ENV_NAME" ]; then
    CONDA_ENV_NAME="test"
fi

echo "🚀 Running Selenium signup test in non-headless mode..."
echo ""

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "❌ Conda is not installed or not in PATH"
    echo "   Please install Miniconda or Anaconda:"
    echo "   https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Initialize conda for bash shell
eval "$(conda shell.bash hook)"

# Check if conda environment exists
if ! conda env list | grep -qE "^(test|SentinelTest) "; then
    echo "❌ Conda environment 'test' or 'SentinelTest' not found"
    echo ""
    echo "Please create it first:"
    echo "  cd backend/tests"
    echo "  ./setup-conda-env.sh"
    echo "  conda activate test"
    exit 1
fi

# Activate conda environment
echo "🔧 Activating conda environment: $CONDA_ENV_NAME"
conda activate "$CONDA_ENV_NAME"

# Verify we're in the right environment
if [[ "$CONDA_DEFAULT_ENV" != "$CONDA_ENV_NAME" ]]; then
    echo "❌ Failed to activate conda environment '$CONDA_ENV_NAME'"
    echo "   Current environment: $CONDA_DEFAULT_ENV"
    exit 1
fi

echo "✅ Activated conda environment: $CONDA_DEFAULT_ENV"
echo ""

# Set environment variables
export WEBSITE_URL="${WEBSITE_URL:-https://localhost:3443}"
export IAM_AGENT_URL="${IAM_AGENT_URL:-http://localhost:8005}"
export HEADLESS="false"  # Force non-headless mode
export CI=""  # Ensure CI mode is not enabled

echo "📝 Note: The browser will be visible so you can watch the test run"
echo ""
echo "🌐 Website URL: $WEBSITE_URL"
echo "🔐 IAM Agent URL: $IAM_AGENT_URL"
echo ""

# Navigate to tests directory
cd "$(dirname "$0")/../backend/tests" || exit 1

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found in conda environment"
    echo "   Please install it:"
    echo "   conda activate $CONDA_ENV_NAME"
    echo "   pip install pytest selenium webdriver-manager"
    exit 1
fi

# Check if selenium is installed
if ! python -c "import selenium" 2>/dev/null; then
    echo "❌ selenium not found. Installing..."
    pip install selenium webdriver-manager
fi

# Run the specific signup test
echo "🧪 Running signup test..."
echo ""

pytest test_auth_selenium.py::TestSignupFlow::test_signup_success -v -s

echo ""
echo "✅ Test completed!"

