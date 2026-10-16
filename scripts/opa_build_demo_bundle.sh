#!/usr/bin/env bash
set -euo pipefail

# Build and package the demo OPA bundle after running tests.
# Requirements: opa CLI in PATH (brew install opa) or use docker (see below).

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT_DIR"

if ! command -v opa >/dev/null 2>&1; then
  echo "opa CLI not found. Install via 'brew install opa' or run with docker:" >&2
  echo "  docker run --rm -v \"$PWD\":/work -w /work openpolicyagent/opa:latest \\" >&2
  echo "    sh -c \"opa test policies/demo && mkdir -p bundles/demo && opa build -b policies/demo -o bundles/demo/demo_bundle.tar.gz\"" >&2
  exit 1
fi

echo "Running opa tests for demo policies..."
opa test policies/demo

echo "Building demo bundle..."
mkdir -p bundles/demo
opa build -b policies/demo -o bundles/demo/demo_bundle.tar.gz

echo "Bundle ready at bundles/demo/demo_bundle.tar.gz"
