#!/usr/bin/env python3
"""Validate the launch-scope dependency policy and emit a readable summary."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


PINNED_OPERATOR_RE = re.compile(r"(===|==)")
RANGE_OPERATOR_RE = re.compile(r"(~=|!=|<=|>=|<|>)")


def _iter_requirement_lines(path: Path):
    for line_no, raw_line in enumerate(path.read_text().splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-r "):
            continue
        yield line_no, stripped


def _validate_pinned_file(path: Path) -> list[str]:
    errors: list[str] = []
    for line_no, requirement in _iter_requirement_lines(path):
        if not PINNED_OPERATOR_RE.search(requirement):
            errors.append(f"{path}:{line_no} must use an exact pin: {requirement}")
            continue
        if RANGE_OPERATOR_RE.search(requirement.replace("==", "")):
            errors.append(f"{path}:{line_no} must not include ranged operators: {requirement}")
    return errors


def _build_markdown_summary(policy: dict) -> str:
    lines = [
        "# Launch-Scope Dependency Policy Summary",
        "",
        "## Exact-Pin Manifests",
        "",
    ]
    for item in policy["python"]["pinned_exact"]:
        lines.append(f"- `{item}`")

    lines.extend(
        [
            "",
            "## Ranged Manifests Allowed Only With Same-Run Audit Evidence",
            "",
        ]
    )
    for item in policy["python"]["ranged_allowed"]:
        lines.append(f"- `{item}`")

    lines.extend(
        [
            "",
            "## Effective Launch Install Plans",
            "",
        ]
    )
    for service, manifests in policy["python"]["effective_install_plans"].items():
        lines.append(f"- `{service}`")
        for manifest in manifests:
            lines.append(f"  - `{manifest}`")

    lines.extend(
        [
            "",
            "## Node Lockfiles",
            "",
        ]
    )
    for item in policy["node"]["lockfiles"]:
        lines.append(f"- `{item}`")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate launch-scope dependency policy.")
    parser.add_argument(
        "--policy-file",
        default="scripts/supply_chain/launch_scope_dependency_policy.json",
        help="Path to the machine-readable dependency policy.",
    )
    parser.add_argument(
        "--artifacts-dir",
        default="artifacts/supply-chain",
        help="Directory for generated summary artifacts.",
    )
    args = parser.parse_args()

    policy_path = Path(args.policy_file)
    artifacts_dir = Path(args.artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    policy = json.loads(policy_path.read_text())
    errors: list[str] = []

    for manifest in policy["python"]["pinned_exact"]:
        manifest_path = Path(manifest)
        if not manifest_path.exists():
            errors.append(f"Missing pinned manifest: {manifest}")
            continue
        errors.extend(_validate_pinned_file(manifest_path))

    summary = {
        "policy_file": str(policy_path),
        "pinned_exact": policy["python"]["pinned_exact"],
        "ranged_allowed": policy["python"]["ranged_allowed"],
        "effective_install_plans": policy["python"]["effective_install_plans"],
        "node_lockfiles": policy["node"]["lockfiles"],
        "errors": errors,
    }

    (artifacts_dir / "launch-scope-dependency-policy-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    (artifacts_dir / "launch-scope-dependency-policy-summary.md").write_text(
        _build_markdown_summary(policy)
    )

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("Launch-scope dependency policy is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
