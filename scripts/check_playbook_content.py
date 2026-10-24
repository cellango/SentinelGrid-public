#!/usr/bin/env python3
"""Read-only content gate. Never executes a playbook or falls back to fixtures."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend/libs"))

from sg_agent_runtime.playbook_ir_compiler import compile_playbook_irs
from sg_agent_runtime.playbook_ir_loader import (
    default_ootb_playbooks_path, load_crosswalk_entries, load_executor_aliases,
    load_ootb_playbooks,
)
from sg_agent_runtime.playbook_catalog import load_playbook_catalog


def content_failures(source, keys):
    """Check requested catalog mappings against an explicitly selected source."""
    source = Path(source)
    if not source.is_file():
        return ["Required playbook source is missing; no fallback is permitted."]
    mappings = load_crosswalk_entries()
    known = {row.canonical_playbook_key for row in mappings}
    if not keys or set(keys) - known:
        return ["Requested keys must be nonempty and present in the canonical crosswalk."]
    try:
        # Avoid cached source bytes when a developer reruns this gate in-process.
        load_ootb_playbooks.cache_clear()
        sources = load_ootb_playbooks(str(source))
        ids = [row.get("id") for row in sources]
        if len(ids) != len(set(ids)):
            return ["Duplicate source definition IDs are not permitted."]
        compiled = compile_playbook_irs(
            catalog_playbooks=load_playbook_catalog(), ootb_playbooks=sources,
            crosswalk_entries=[row for row in mappings if row.canonical_playbook_key in keys],
            executor_aliases=load_executor_aliases(),
        )
    except Exception as exc:
        # Do not print source payloads or parser excerpts.
        return [f"Unable to validate source content ({type(exc).__name__})."]
    return [f"{row.playbook_key}: {row.status}; " + ",".join(issue.code for issue in row.validation_issues)
            for row in compiled if row.status != "ready"]



def packaging_failures(source, root=ROOT):
    """A developer's ignored local copy must not mask an export omission."""
    try:
        relative = Path(source).resolve().relative_to(root.resolve()).as_posix()
        selected = json.loads((root / "publication/source-files.json").read_text())["files"]
        if relative not in selected:
            return ["Default playbook source is not in the reviewed publication inventory."]
    except (ValueError, OSError, KeyError, TypeError):
        return ["Unable to verify default playbook source packaging."]
    return []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=default_ootb_playbooks_path())
    parser.add_argument("--key", action="append", dest="keys")
    args = parser.parse_args()
    keys = args.keys or [row.canonical_playbook_key for row in load_crosswalk_entries()]
    failures = content_failures(args.source, keys)
    if args.source.resolve() == default_ootb_playbooks_path().resolve():
        failures.extend(packaging_failures(args.source))
    for failure in failures:
        print("BLOCKED: " + failure)
    print(f"Content input check: {len(failures)} blockers. No execution, authority, or E2E qualification.")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
