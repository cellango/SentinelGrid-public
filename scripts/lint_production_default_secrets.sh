#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

fail() {
  echo "production-default-secret lint failed: $1" >&2
  exit 1
}

assert_pattern() {
  local file="$1"
  local pattern="$2"
  local label="$3"
  if ! rg -U -q "${pattern}" "${file}"; then
    fail "${label} missing in ${file}"
  fi
}

production_targets=(
  ".github/workflows/build-push-deploy.yml.disabled"
  "charts/values/api-gateway.yaml"
  "charts/values/iam-agent.yaml"
  "charts/values/model-gateway.yaml"
  "charts/values/orchestrator.yaml"
  "charts/values/siem-agent.yaml"
  "infra/eks/variables.tf"
  "infra/vault/scripts/vault-prod-entrypoint.sh"
  "backend/scripts/init_vault_prod.sh"
)

placeholder_regex=':-internal-service-token-change-in-production|:-sentinelgrid-prod-root-token-change-me|=\s*"changeme123!"|postgresql://sg:sg@|postgresql://postgres:postgres@|redis://redis:6379(/0)?|redis://localhost:6379(/0)?|http://keycloak:8080|http://vault:8200|http://opensearch:9200'
if rg -n -S "${placeholder_regex}" "${production_targets[@]}"; then
  fail "production deployment path still contains placeholder credentials or local-service defaults"
fi

assert_pattern "charts/values/api-gateway.yaml" 'name: ENVIRONMENT\n\s+value: production' "api-gateway production environment"
assert_pattern "charts/values/iam-agent.yaml" 'name: ENVIRONMENT\n\s+value: production' "iam-agent production environment"
assert_pattern "charts/values/model-gateway.yaml" 'name: ENVIRONMENT\n\s+value: production' "model-gateway production environment"
assert_pattern "charts/values/orchestrator.yaml" 'name: ENVIRONMENT\n\s+value: production' "orchestrator production environment"
assert_pattern "charts/values/siem-agent.yaml" 'name: ENVIRONMENT\n\s+value: production' "siem-agent production environment"

assert_pattern "charts/values/api-gateway.yaml" 'secretRef:\n\s+name: api-gateway-runtime' "api-gateway runtime secretRef"
assert_pattern "charts/values/iam-agent.yaml" 'secretRef:\n\s+name: iam-agent-runtime' "iam-agent runtime secretRef"
assert_pattern "charts/values/model-gateway.yaml" 'secretRef:\n\s+name: model-gateway-runtime' "model-gateway runtime secretRef"
assert_pattern "charts/values/orchestrator.yaml" 'secretRef:\n\s+name: orchestrator-runtime' "orchestrator runtime secretRef"
assert_pattern "charts/values/siem-agent.yaml" 'secretRef:\n\s+name: siem-agent-runtime' "siem-agent runtime secretRef"

assert_pattern "charts/values/api-gateway.yaml" 'name: UPSTREAM_TLS_VERIFY\n\s+value: "true"' "api-gateway upstream TLS verify"
assert_pattern "charts/values/iam-agent.yaml" 'name: KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT\n\s+value: "true"' "iam-agent service account mode"
assert_pattern "charts/values/iam-agent.yaml" 'name: KEYCLOAK_VERIFY_TLS\n\s+value: "true"' "iam-agent keycloak TLS verify"
assert_pattern "charts/values/iam-agent.yaml" 'name: VAULT_VERIFY_TLS\n\s+value: "true"' "iam-agent vault TLS verify"
assert_pattern "charts/values/iam-agent.yaml" 'name: PAYMENT_DEV_MODE\n\s+value: "false"' "iam-agent payment dev mode disabled"
assert_pattern "charts/values/siem-agent.yaml" 'name: OPENSEARCH_USE_SSL\n\s+value: "true"' "siem-agent OpenSearch TLS"
assert_pattern "charts/values/siem-agent.yaml" 'name: OPENSEARCH_VERIFY_CERTS\n\s+value: "true"' "siem-agent OpenSearch cert verification"

for secret_name in \
  api-gateway-runtime \
  iam-agent-runtime \
  model-gateway-runtime \
  orchestrator-runtime \
  siem-agent-runtime; do
  assert_pattern ".github/workflows/build-push-deploy.yml.disabled" "${secret_name}" "deploy workflow secret validation for ${secret_name}"
done

echo "production-default-secret lint passed"
