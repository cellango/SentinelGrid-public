#!/bin/bash
# Setup conda environment for SentinelGrid tests

set -e

ENV_NAME="SentinelTest"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Setting up Conda Environment: $ENV_NAME"
echo "=========================================="
echo ""

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "❌ Conda is not installed or not in PATH"
    echo "   Please install Miniconda or Anaconda:"
    echo "   https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

echo "✅ Conda found: $(conda --version)"
echo ""

# Remove existing environment if it exists
if conda env list | grep -q "^${ENV_NAME} "; then
    echo "⚠️  Environment '$ENV_NAME' already exists"
    read -p "Do you want to remove and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing environment..."
        conda env remove -n "$ENV_NAME" -y
    else
        echo "Using existing environment. To update dependencies, run:"
        echo "  conda env update -n $ENV_NAME -f environment.yml --prune"
        exit 0
    fi
fi

# Create environment from environment.yml
echo "Creating conda environment from environment.yml..."
conda env create -f "$SCRIPT_DIR/environment.yml"

echo ""
echo "=========================================="
echo "✅ Environment '$ENV_NAME' created successfully!"
echo "=========================================="
echo ""
echo "To activate the environment:"
echo "  conda activate $ENV_NAME"
echo ""
echo "To deactivate:"
echo "  conda deactivate"
echo ""
echo "To install additional packages:"
echo "  conda activate $ENV_NAME"
echo "  pip install <package>"
echo ""
echo "To update environment from environment.yml:"
echo "  conda env update -n $ENV_NAME -f environment.yml --prune"

