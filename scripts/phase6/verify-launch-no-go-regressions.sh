#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

SAMPLE_CERTIFICATE_ARN="arn:aws:acm:us-east-1:123456789012:certificate/preaudit-verifier"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

assert_no_match() {
  local pattern="$1"
  local label="$2"
  shift 2
  local output_file="$TMP_DIR/assert_no_match.txt"
  if rg -n "$pattern" "$@" >"$output_file"; then
    cat "$output_file" >&2
    fail "$label"
  fi
}

assert_match() {
  local pattern="$1"
  local file="$2"
  local label="$3"
  if ! rg -q "$pattern" "$file"; then
    fail "$label"
  fi
}

echo "Scanning launch paths for unsigned JWT trust bypass patterns..."
assert_no_match 'verify_signature\s*=\s*False' \
  "launch-scope code still contains verify_signature=False" \
  "$REPO_ROOT/backend" \
  "$REPO_ROOT/SentinelGridAIShield"

echo "Scanning launch paths for placeholder tenant dependencies..."
assert_no_match 'Depends\(lambda:\s*"default"\)' \
  "launch-scope code still contains Depends(lambda: \"default\")" \
  "$REPO_ROOT/backend" \
  "$REPO_ROOT/SentinelGridAIShield"

echo "Checking frontend edge for wildcard CORS regression..."
assert_no_match 'Access-Control-Allow-Origin\s+"?\*"?|Access-Control-Allow-Headers\s+"\*"' \
  "frontend edge still exposes wildcard CORS headers" \
  "$REPO_ROOT/frontend/nginx.conf"

echo "Rendering public ingresses and verifying HTTPS-only entry..."

for entry in \
  "frontend:charts/values/frontend.yaml" \
  "api-gateway:charts/values/api-gateway.yaml" \
  "iam-agent:charts/values/iam-agent.yaml"; do
  service="${entry%%:*}"
  values_file="${entry#*:}"
  rendered_file="$TMP_DIR/${service}.yaml"

  helm template "$service" "$REPO_ROOT/charts/common-service" \
    -f "$REPO_ROOT/$values_file" \
    --set "ingress.alb.certificateArn=$SAMPLE_CERTIFICATE_ARN" \
    >"$rendered_file"

  assert_match '^kind: Ingress$' "$rendered_file" "$service did not render a public Ingress"
  assert_match 'certificate-arn: arn:aws:acm:' "$rendered_file" "$service ingress is missing an ACM certificate ARN"
  assert_match 'listen-ports: .*\{"HTTPS":443\}' "$rendered_file" "$service ingress is not pinned to HTTPS 443"
  assert_no_match '\{"HTTP":80\}' "$service ingress still renders an HTTP listener" "$rendered_file"
  echo "  OK ingress: $service"
done

echo "Checking that model gateway stays internal-only..."
model_gateway_rendered="$TMP_DIR/model-gateway.yaml"
helm template model-gateway "$REPO_ROOT/charts/common-service" \
  -f "$REPO_ROOT/charts/values/model-gateway.yaml" \
  >"$model_gateway_rendered"
assert_no_match '^kind: Ingress$' "model-gateway still renders a public Ingress" "$model_gateway_rendered"

echo "PASS: launch-scope automatic No-Go regressions are not present in the current repo-backed baseline."
