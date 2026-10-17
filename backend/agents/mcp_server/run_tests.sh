#!/usr/bin/env bash
# Run source/protocol checks in an explicitly prepared environment.
set -euo pipefail
MCP_TEST_ROOT="$(cd -- "$(dirname -- "$0")" && pwd)"
exec "${PYTHON:-python3}" -m pytest -c "$MCP_TEST_ROOT/tests/pytest.ini" "$MCP_TEST_ROOT/tests" "$@"
