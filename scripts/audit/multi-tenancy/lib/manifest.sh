#!/usr/bin/env bash

set -euo pipefail

audit_manifest_init() {
  local manifest_path="${1:?manifest path required}"
  python3 - "$manifest_path" <<'PY'
import json
import os
import pathlib
import sys

manifest_path = pathlib.Path(sys.argv[1])
manifest_path.parent.mkdir(parents=True, exist_ok=True)

manifest = {
    "schema_version": "1.0",
    "run_id": os.environ.get("AUDIT_RUN_ID"),
    "timestamp_utc": os.environ.get("AUDIT_TIMESTAMP_UTC"),
    "git_sha": os.environ.get("AUDIT_GIT_SHA"),
    "git_branch_or_tag": os.environ.get("AUDIT_GIT_REF"),
    "environment": os.environ.get("AUDIT_ENV_NAME"),
    "profile": os.environ.get("AUDIT_PROFILE"),
    "operator": os.environ.get("AUDIT_OPERATOR"),
    "tenant_pair": {
        "tenant_a_id": os.environ.get("AUDIT_TENANT_A_ID", ""),
        "tenant_b_id": os.environ.get("AUDIT_TENANT_B_ID", ""),
        "tenant_a_realm": os.environ.get("AUDIT_TENANT_A_REALM", ""),
        "tenant_b_realm": os.environ.get("AUDIT_TENANT_B_REALM", ""),
    },
    "command_sequence": [],
    "step_results": {},
    "artifact_root": os.environ.get("AUDIT_ARTIFACT_DIR"),
    "overall_status": "running",
}

manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
PY
}

audit_manifest_step() {
  local manifest_path="${1:?manifest path required}"
  local step_name="${2:?step name required}"
  local step_status="${3:?step status required}"
  python3 - "$manifest_path" "$step_name" "$step_status" <<'PY'
import json
import pathlib
import sys

manifest_path = pathlib.Path(sys.argv[1])
step_name = sys.argv[2]
step_status = sys.argv[3]

manifest = json.loads(manifest_path.read_text())
manifest.setdefault("step_results", {})[step_name] = step_status
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
PY
}

audit_manifest_append_command() {
  local manifest_path="${1:?manifest path required}"
  local command_text="${2:?command text required}"
  python3 - "$manifest_path" "$command_text" <<'PY'
import json
import pathlib
import sys

manifest_path = pathlib.Path(sys.argv[1])
command_text = sys.argv[2]

manifest = json.loads(manifest_path.read_text())
manifest.setdefault("command_sequence", []).append(command_text)
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
PY
}

audit_manifest_overall() {
  local manifest_path="${1:?manifest path required}"
  local overall_status="${2:?overall status required}"
  python3 - "$manifest_path" "$overall_status" <<'PY'
import json
import pathlib
import sys

manifest_path = pathlib.Path(sys.argv[1])
overall_status = sys.argv[2]

manifest = json.loads(manifest_path.read_text())
manifest["overall_status"] = overall_status
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
PY
}

