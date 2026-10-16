#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

ARTIFACTS_DIR=""
IMAGE_TAG="local"
REGISTRY=""
PUSH=false
SKIP_BUILD=false
SKIP_BASE_IMAGES=false
NEXT_PUBLIC_API_BASE_VALUE="${NEXT_PUBLIC_API_BASE:-/api}"
NEXT_PUBLIC_API_URL_VALUE="${NEXT_PUBLIC_API_URL:-/api}"
NEXT_PUBLIC_IAM_AGENT_URL_VALUE="${NEXT_PUBLIC_IAM_AGENT_URL:-/api/v1/iam}"

usage() {
  cat <<'EOF'
Usage: build_launch_scope_images.sh [options]

Options:
  --artifacts-dir DIR
  --image-tag TAG
  --registry REGISTRY
  --push
  --skip-build
  --skip-base-images
  --frontend-api-base VALUE
  --frontend-api-url VALUE
  --frontend-iam-url VALUE
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --artifacts-dir)
      ARTIFACTS_DIR="$2"
      shift 2
      ;;
    --image-tag)
      IMAGE_TAG="$2"
      shift 2
      ;;
    --registry)
      REGISTRY="$2"
      shift 2
      ;;
    --push)
      PUSH=true
      shift
      ;;
    --skip-build)
      SKIP_BUILD=true
      shift
      ;;
    --skip-base-images)
      SKIP_BASE_IMAGES=true
      shift
      ;;
    --frontend-api-base)
      NEXT_PUBLIC_API_BASE_VALUE="$2"
      shift 2
      ;;
    --frontend-api-url)
      NEXT_PUBLIC_API_URL_VALUE="$2"
      shift 2
      ;;
    --frontend-iam-url)
      NEXT_PUBLIC_IAM_AGENT_URL_VALUE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

mkdir -p "${ARTIFACTS_DIR}"

RUNTIME_IMAGE_LOCAL="sentinelgrid/runtime-python:${IMAGE_TAG}"
API_BASE_IMAGE_LOCAL="sentinelgrid/api-base:${IMAGE_TAG}"
API_ML_IMAGE_LOCAL="sentinelgrid/api-ml:${IMAGE_TAG}"

RUNTIME_IMAGE_STABLE="sentinelgrid/runtime-python:3.11"
API_BASE_IMAGE_STABLE="sentinelgrid/api-base:latest"
API_ML_IMAGE_STABLE="sentinelgrid/api-ml:latest"

declare -a IMAGE_REFS=(
  "${RUNTIME_IMAGE_LOCAL}"
  "${API_BASE_IMAGE_LOCAL}"
  "${API_ML_IMAGE_LOCAL}"
  "sentinelgrid/frontend:${IMAGE_TAG}"
  "sentinelgrid/api_gateway:${IMAGE_TAG}"
  "sentinelgrid/iam_agent:${IMAGE_TAG}"
  "sentinelgrid/model_gateway:${IMAGE_TAG}"
  "sentinelgrid/orchestrator:${IMAGE_TAG}"
  "sentinelgrid/siem_agent:${IMAGE_TAG}"
)

build_if_needed() {
  if [[ "${SKIP_BUILD}" == "true" ]]; then
    return
  fi

  if [[ "${SKIP_BASE_IMAGES}" != "true" ]]; then
    docker build \
      -f "${ROOT_DIR}/backend/docker/base-images/Dockerfile.runtime-python" \
      -t "${RUNTIME_IMAGE_LOCAL}" \
      -t "${RUNTIME_IMAGE_STABLE}" \
      "${ROOT_DIR}/backend/docker/base-images"

    docker build \
      -f "${ROOT_DIR}/backend/docker/base-images/Dockerfile.api-base" \
      --build-arg "SENTINELGRID_RUNTIME_PYTHON_IMAGE=${RUNTIME_IMAGE_LOCAL}" \
      -t "${API_BASE_IMAGE_LOCAL}" \
      -t "${API_BASE_IMAGE_STABLE}" \
      "${ROOT_DIR}/backend/docker/base-images"

    docker build \
      -f "${ROOT_DIR}/backend/docker/base-images/Dockerfile.api-ml" \
      --build-arg "SENTINELGRID_API_BASE_IMAGE=${API_BASE_IMAGE_LOCAL}" \
      -t "${API_ML_IMAGE_LOCAL}" \
      -t "${API_ML_IMAGE_STABLE}" \
      "${ROOT_DIR}/backend/docker/base-images"
  fi

  docker build \
    -f "${ROOT_DIR}/frontend/Dockerfile" \
    --build-arg "NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE_VALUE}" \
    --build-arg "NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL_VALUE}" \
    --build-arg "NEXT_PUBLIC_IAM_AGENT_URL=${NEXT_PUBLIC_IAM_AGENT_URL_VALUE}" \
    -t "sentinelgrid/frontend:${IMAGE_TAG}" \
    "${ROOT_DIR}/frontend"

  docker build \
    -f "${ROOT_DIR}/backend/services/api_gateway/Dockerfile" \
    --build-arg "SENTINELGRID_API_BASE_IMAGE=${API_BASE_IMAGE_LOCAL}" \
    -t "sentinelgrid/api_gateway:${IMAGE_TAG}" \
    "${ROOT_DIR}/backend"

  docker build \
    -f "${ROOT_DIR}/backend/agents/iam_agent/Dockerfile" \
    --build-arg "SENTINELGRID_API_ML_IMAGE=${API_ML_IMAGE_LOCAL}" \
    -t "sentinelgrid/iam_agent:${IMAGE_TAG}" \
    "${ROOT_DIR}/backend"

  docker build \
    -f "${ROOT_DIR}/backend/services/model_gateway/Dockerfile" \
    --build-arg "SENTINELGRID_API_ML_IMAGE=${API_ML_IMAGE_LOCAL}" \
    -t "sentinelgrid/model_gateway:${IMAGE_TAG}" \
    "${ROOT_DIR}/backend/services/model_gateway"

  docker build \
    -f "${ROOT_DIR}/backend/services/orchestrator/Dockerfile" \
    --build-arg "SENTINELGRID_API_BASE_IMAGE=${API_BASE_IMAGE_LOCAL}" \
    -t "sentinelgrid/orchestrator:${IMAGE_TAG}" \
    "${ROOT_DIR}/backend"

  docker build \
    -f "${ROOT_DIR}/backend/agents/siem_agent/Dockerfile" \
    --build-arg "SENTINELGRID_API_BASE_IMAGE=${API_BASE_IMAGE_LOCAL}" \
    -t "sentinelgrid/siem_agent:${IMAGE_TAG}" \
    "${ROOT_DIR}/backend"
}

push_if_requested() {
  if [[ "${PUSH}" != "true" ]]; then
    return
  fi
  if [[ -z "${REGISTRY}" ]]; then
    echo "--registry is required when --push is set" >&2
    exit 1
  fi

  local image_name local_ref remote_ref stable_ref

  for image_name in runtime-python api-base api-ml; do
    case "${image_name}" in
      runtime-python)
        local_ref="${RUNTIME_IMAGE_LOCAL}"
        remote_ref="${REGISTRY}/runtime-python:${IMAGE_TAG}"
        stable_ref="${REGISTRY}/runtime-python:3.11"
        ;;
      api-base)
        local_ref="${API_BASE_IMAGE_LOCAL}"
        remote_ref="${REGISTRY}/api-base:${IMAGE_TAG}"
        stable_ref="${REGISTRY}/api-base:latest"
        ;;
      api-ml)
        local_ref="${API_ML_IMAGE_LOCAL}"
        remote_ref="${REGISTRY}/api-ml:${IMAGE_TAG}"
        stable_ref="${REGISTRY}/api-ml:latest"
        ;;
    esac
    docker tag "${local_ref}" "${remote_ref}"
    docker push "${remote_ref}"
    docker tag "${local_ref}" "${stable_ref}"
    docker push "${stable_ref}"
  done

  for image_name in frontend api_gateway iam_agent model_gateway orchestrator siem_agent; do
    local_ref="sentinelgrid/${image_name}:${IMAGE_TAG}"
    remote_ref="${REGISTRY}/${image_name}:${IMAGE_TAG}"
    docker tag "${local_ref}" "${remote_ref}"
    docker push "${remote_ref}"
  done
}

write_artifacts() {
  local targets_file="${ARTIFACTS_DIR}/launch-image-scan-targets.txt"
  local summary_md="${ARTIFACTS_DIR}/launch-image-build-summary.md"
  local inspect_json="${ARTIFACTS_DIR}/launch-image-build-inspect.json"

  printf "%s\n" "${IMAGE_REFS[@]}" > "${targets_file}"

  cat > "${summary_md}" <<EOF
# Launch Image Build Summary

Image tag: \`${IMAGE_TAG}\`

## Base Images

- \`${RUNTIME_IMAGE_LOCAL}\` from \`backend/docker/base-images/Dockerfile.runtime-python\`
- \`${API_BASE_IMAGE_LOCAL}\` from \`backend/docker/base-images/Dockerfile.api-base\`, extends \`${RUNTIME_IMAGE_LOCAL}\`
- \`${API_ML_IMAGE_LOCAL}\` from \`backend/docker/base-images/Dockerfile.api-ml\`, extends \`${API_BASE_IMAGE_LOCAL}\`

## Launch Service Images

- \`sentinelgrid/frontend:${IMAGE_TAG}\` from \`frontend/Dockerfile\`
- \`sentinelgrid/api_gateway:${IMAGE_TAG}\` from \`backend/services/api_gateway/Dockerfile\`, extends \`${API_BASE_IMAGE_LOCAL}\`
- \`sentinelgrid/iam_agent:${IMAGE_TAG}\` from \`backend/agents/iam_agent/Dockerfile\`, extends \`${API_ML_IMAGE_LOCAL}\`
- \`sentinelgrid/model_gateway:${IMAGE_TAG}\` from \`backend/services/model_gateway/Dockerfile\`, extends \`${API_ML_IMAGE_LOCAL}\`
- \`sentinelgrid/orchestrator:${IMAGE_TAG}\` from \`backend/services/orchestrator/Dockerfile\`, extends \`${API_BASE_IMAGE_LOCAL}\`
- \`sentinelgrid/siem_agent:${IMAGE_TAG}\` from \`backend/agents/siem_agent/Dockerfile\`, extends \`${API_BASE_IMAGE_LOCAL}\`
EOF

  docker image inspect "${IMAGE_REFS[@]}" > "${inspect_json}"
}

build_if_needed
write_artifacts
push_if_requested
