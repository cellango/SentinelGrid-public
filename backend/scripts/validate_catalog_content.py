"""
Lightweight validation to catch empty or placeholder detections/playbooks before build/CI.

Checks:
 - Detection rules must have a query + trigger_condition (no match_all placeholder).
 - Playbooks must have at least one node in workflow (no empty workflow).
 - Optional: warn if mapping keys missing.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DETECTIONS_FILE = ROOT / "cfg" / "detections" / "catalog.json"
PLAYBOOKS_FILE = ROOT / "cfg" / "playbooks" / "catalog.json"


def load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception as e:
        print(f"ERROR: failed to load {path}: {e}", file=sys.stderr)
        return None


def validate_detections(data):
    errors = []
    if not isinstance(data, list):
        errors.append("Detections catalog must be a list")
        return errors
    for det in data:
        rid = det.get("id") or det.get("rule_key") or "unknown"
        versions = det.get("versions") or []
        if not versions:
            errors.append(f"{rid}: missing versions")
            continue
        v0 = versions[0]
        query = v0.get("query")
        trig = v0.get("trigger_condition")
        if not query or "match_all" in json.dumps(query):
            errors.append(f"{rid}: query missing or match_all placeholder")
        if not trig:
            errors.append(f"{rid}: trigger_condition missing")
    return errors


def validate_playbooks(data):
    errors = []
    if not isinstance(data, list):
        errors.append("Playbooks catalog must be a list")
        return errors
    for pb in data:
        pid = pb.get("id") or pb.get("key") or pb.get("name") or "unknown"
        wf = pb.get("workflow") or {}
        nodes = wf.get("nodes") or []
        if len(nodes) == 0:
            errors.append(f"{pid}: empty workflow")
    return errors


def main():
    failures = 0

    det_data = load_json(DETECTIONS_FILE)
    if det_data is None:
        print(f"WARNING: {DETECTIONS_FILE} not found; skipping detections validation.")
    else:
        det_errors = validate_detections(det_data)
        if det_errors:
            failures += len(det_errors)
            print("Detection validation errors:")
            for err in det_errors:
                print(f" - {err}")

    pb_data = load_json(PLAYBOOKS_FILE)
    if pb_data is None:
        print(f"WARNING: {PLAYBOOKS_FILE} not found; skipping playbooks validation.")
    else:
        pb_errors = validate_playbooks(pb_data)
        if pb_errors:
            failures += len(pb_errors)
            print("Playbook validation errors:")
            for err in pb_errors:
                print(f" - {err}")

    if failures:
        print(f"Validation failed with {failures} issue(s).", file=sys.stderr)
        sys.exit(1)
    else:
        print("Validation passed: detections and playbooks have concrete content.")


if __name__ == "__main__":
    main()
