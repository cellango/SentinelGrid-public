#!/usr/bin/env python3
"""Verify launch-scope automation uses canonical agent build targets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


CANONICAL_BUILD_TARGETS = {
    "backend/agents/iam_agent/Dockerfile",
    "backend/agents/siem_agent/Dockerfile",
}

CANONICAL_STAGE_TARGETS = {
    "backend/agents/iam_agent/Dockerfile",
    "backend/agents/iam_agent/requirements-specific.txt",
    "backend/agents/siem_agent/Dockerfile",
    "backend/agents/siem_agent/requirements-specific.txt",
    "scripts/supply_chain/verify_launch_scope_agent_targets.py",
}

FORBIDDEN_PATTERNS = {
    "backend/services/siem_agent",
    "backend/services/entitlement_agent",
    "backend/services/ai_enrichment_agent",
    "services/siem_agent",
    "services/entitlement_agent",
    "services/ai_enrichment_agent",
    "http://entitlement_agent:",
    "http://ai_enrichment_agent:",
}

FILES_TO_SCAN = {
    ".github/workflows/build-push-deploy.yml",
    ".github/workflows/supply-chain-evidence.yml",
    ".github/workflows/test.yml",
    "scripts/supply_chain/build_launch_scope_images.sh",
    "scripts/supply_chain/stage_launch_scope_filesystem.sh",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="Repository root.",
    )
    args = parser.parse_args()
    root = args.root.resolve()

    failures: list[str] = []
    files = _read_files(root, FILES_TO_SCAN, failures)
    _check_forbidden_patterns(files, failures)
    _check_required_targets(
        files.get("scripts/supply_chain/build_launch_scope_images.sh", ""),
        CANONICAL_BUILD_TARGETS,
        "build_launch_scope_images.sh",
        failures,
    )
    _check_required_targets(
        files.get("scripts/supply_chain/stage_launch_scope_filesystem.sh", ""),
        CANONICAL_STAGE_TARGETS,
        "stage_launch_scope_filesystem.sh",
        failures,
    )

    if failures:
        for failure in failures:
            print(f"launch-scope agent target check failed: {failure}", file=sys.stderr)
        return 1

    print("launch-scope agent target check passed")
    return 0


def _read_files(
    root: Path,
    relative_paths: set[str],
    failures: list[str],
) -> dict[str, str]:
    files: dict[str, str] = {}
    for relative_path in sorted(relative_paths):
        path = root / relative_path
        if not path.exists():
            failures.append(f"missing required automation file: {relative_path}")
            continue
        files[relative_path] = path.read_text(encoding="utf-8")
    return files


def _check_forbidden_patterns(files: dict[str, str], failures: list[str]) -> None:
    for relative_path, text in files.items():
        for pattern in sorted(FORBIDDEN_PATTERNS):
            if pattern in text:
                failures.append(f"{relative_path} references legacy agent target {pattern!r}")


def _check_required_targets(
    text: str,
    required_targets: set[str],
    label: str,
    failures: list[str],
) -> None:
    for target in sorted(required_targets):
        if target not in text:
            failures.append(f"{label} is missing canonical target {target!r}")


if __name__ == "__main__":
    raise SystemExit(main())
