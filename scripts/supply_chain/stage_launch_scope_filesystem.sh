#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <destination-dir>" >&2
  exit 1
fi

dest_dir="$1"
mkdir -p "$dest_dir"

paths=(
  ".github/workflows/build-push-deploy.yml"
  ".github/workflows/supply-chain-evidence.yml"
  ".github/workflows/test.yml"
  "backend/docker/base-images/Dockerfile.api-base"
  "backend/docker/base-images/Dockerfile.api-ml"
  "backend/docker/base-images/Dockerfile.runtime-python"
  "backend/docker/base-images/requirements/api-base.txt"
  "backend/docker/base-images/requirements/api-ml.txt"
  "backend/libs/requirements.txt"
  "backend/services/api_gateway/Dockerfile"
  "backend/agents/iam_agent/Dockerfile"
  "backend/agents/iam_agent/requirements-specific.txt"
  "backend/agents/siem_agent/Dockerfile"
  "backend/agents/siem_agent/requirements-specific.txt"
  "backend/services/model_gateway/Dockerfile"
  "backend/services/model_gateway/requirements-specific.txt"
  "backend/services/orchestrator/Dockerfile"
  "backend/services/orchestrator/requirements.txt"
  "charts/values/api-gateway.yaml"
  "charts/values/iam-agent.yaml"
  "charts/values/model-gateway.yaml"
  "charts/values/orchestrator.yaml"
  "charts/values/siem-agent.yaml"
  "frontend/Dockerfile"
  "frontend/package-lock.json"
  "frontend/package.json"
  "scripts/lint_production_default_secrets.sh"
  "scripts/supply_chain/launch_scope_dependency_policy.json"
  "scripts/supply_chain/run_launch_python_supply_chain_gate.py"
  "scripts/supply_chain/stage_launch_scope_filesystem.sh"
  "scripts/supply_chain/verify_launch_scope_agent_targets.py"
  "scripts/supply_chain/verify_launch_scope_dependency_policy.py"
)

for path in "${paths[@]}"; do
  mkdir -p "${dest_dir}/$(dirname "$path")"
  cp "$path" "${dest_dir}/$path"
done
