#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARTIFACTS_DIR=""
TRIVY_IMAGE="${TRIVY_IMAGE:-aquasec/trivy:0.64.1}"
SEVERITY="${TRIVY_SEVERITY:-HIGH,CRITICAL}"

usage() {
  cat <<'EOF'
Usage: scan_launch_scope_images.sh --artifacts-dir DIR
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --artifacts-dir)
      ARTIFACTS_DIR="$2"
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

if [[ -z "${ARTIFACTS_DIR}" ]]; then
  usage >&2
  exit 1
fi

TARGETS_FILE="${ARTIFACTS_DIR}/launch-image-scan-targets.txt"
SCANS_DIR="${ARTIFACTS_DIR}/launch-image-scans"
SUMMARY_JSON="${ARTIFACTS_DIR}/launch-image-scan-summary.json"
SUMMARY_MD="${ARTIFACTS_DIR}/launch-image-scan-summary.md"
DEFAULT_CACHE_DIR="${ROOT_DIR}/.cache/trivy"
CACHE_DIR="${TRIVY_CACHE_DIR:-${DEFAULT_CACHE_DIR}}"

if [[ ! -f "${TARGETS_FILE}" ]]; then
  echo "Missing scan target list: ${TARGETS_FILE}" >&2
  exit 1
fi

mkdir -p "${SCANS_DIR}"
mkdir -p "${CACHE_DIR}"
CACHE_DIR_ABS="$(cd "${CACHE_DIR}" && pwd)"

run_trivy_scan() {
  local image_ref="$1"
  local output_path="$2"

  docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "${ROOT_DIR}:/workspace" \
    -v "${CACHE_DIR_ABS}:/root/.cache/trivy" \
    -w /workspace \
    "${TRIVY_IMAGE}" image \
    --scanners vuln \
    --skip-version-check \
    --severity "${SEVERITY}" \
    --format json \
    --output "/workspace/${output_path}" \
    "${image_ref}"
}

status=0
while IFS= read -r image_ref; do
  [[ -z "${image_ref}" ]] && continue
  safe_name="${image_ref//\//_}"
  safe_name="${safe_name//:/_}"
  output_path="${SCANS_DIR}/${safe_name}.json"
  if ! run_trivy_scan "${image_ref}" "${output_path}"; then
    status=1
  fi
done < "${TARGETS_FILE}"

summary_status="$(
python3 - "${TARGETS_FILE}" "${SCANS_DIR}" "${SUMMARY_JSON}" "${SUMMARY_MD}" <<'PY'
import json
import pathlib
import sys

targets_file = pathlib.Path(sys.argv[1])
scans_dir = pathlib.Path(sys.argv[2])
summary_json = pathlib.Path(sys.argv[3])
summary_md = pathlib.Path(sys.argv[4])

summary = {}
for image_ref in [line.strip() for line in targets_file.read_text().splitlines() if line.strip()]:
    safe_name = image_ref.replace("/", "_").replace(":", "_")
    scan_path = scans_dir / f"{safe_name}.json"
    findings = []
    if scan_path.exists():
        payload = json.loads(scan_path.read_text())
        for result in payload.get("Results", []):
            findings.extend(result.get("Vulnerabilities") or [])
    severity_counts = {}
    for finding in findings:
        severity = finding.get("Severity", "UNKNOWN")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    summary[image_ref] = {
        "scan_output": str(scan_path),
        "findings": len(findings),
        "severity_counts": severity_counts,
        "passed": len(findings) == 0,
    }

summary_json.write_text(json.dumps(summary, indent=2) + "\n")

lines = ["# Launch Image Scan Summary", ""]
has_findings = False
for image_ref, details in summary.items():
    status = "passed" if details["passed"] else "failed"
    has_findings = has_findings or not details["passed"]
    lines.append(f"- `{image_ref}`: {status}, findings={details['findings']}, severities={details['severity_counts']}")
summary_md.write_text("\n".join(lines) + "\n")
print("1" if has_findings else "0")
PY
)"

if [[ "${summary_status}" == "1" ]]; then
  status=1
fi

exit "${status}"
