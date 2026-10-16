#!/usr/bin/env python3
"""Check whether legacy agent service trees are isolated enough to remove."""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path


LEGACY_TREES = {
    "backend/services/siem_agent": {
        "replacement": "backend/agents/siem_agent",
        "required_paths": [
            "backend/agents/siem_agent/Dockerfile",
            "backend/agents/siem_agent/app",
        ],
    },
    "backend/services/entitlement_agent": {
        "replacement": "backend/agents/iam_agent",
        "required_paths": [
            "backend/agents/iam_agent/Dockerfile",
            "backend/agents/iam_agent/app",
            "backend/agents/iam_agent/migrations",
        ],
        "migration_mirror": "backend/agents/iam_agent/migrations",
    },
    "backend/services/ai_enrichment_agent": {
        "replacement": "backend/agents/soar_agent/app/api/enrichment.py",
        "required_paths": [
            "backend/agents/soar_agent/Dockerfile",
            "backend/agents/soar_agent/app/api/enrichment.py",
        ],
    },
}

FORBIDDEN_ACTIVE_REFERENCES = {
    "backend/services/siem_agent",
    "backend/services/entitlement_agent",
    "backend/services/ai_enrichment_agent",
    "services/siem_agent",
    "services/entitlement_agent",
    "services/ai_enrichment_agent",
    "http://entitlement_agent:",
    "http://ai_enrichment_agent:",
}

EXCLUDED_DIRS = {
    ".git",
    ".claude",
    ".claire",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "__pycache__",
    "artifacts",
    "build",
    "node_modules",
    "coverage",
    "dist",
    "htmlcov",
}

EXCLUDED_PREFIXES = (
    "docs/",
    "frontend/.next/",
    "frontend/out/",
    "backend/services/siem_agent/",
    "backend/services/entitlement_agent/",
    "backend/services/ai_enrichment_agent/",
)

EXCLUDED_FILES = {
    "scripts/check_agent_module_drift.sh",
    "scripts/check_agent_runtime_compose_wiring.py",
    "scripts/check_agent_legacy_cleanup_readiness.py",
    "scripts/supply_chain/verify_launch_scope_agent_targets.py",
}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    failures: list[str] = []

    for legacy_tree, metadata in LEGACY_TREES.items():
        _check_legacy_tree(root, legacy_tree, metadata, failures)

    _check_active_references(root, failures)

    if failures:
        for failure in failures:
            print(f"agent legacy cleanup readiness check failed: {failure}", file=sys.stderr)
        return 1

    print("agent legacy cleanup readiness check passed")
    return 0


def _check_legacy_tree(
    root: Path,
    legacy_tree: str,
    metadata: dict[str, object],
    failures: list[str],
) -> None:
    legacy_path = root / legacy_tree
    if not legacy_path.exists():
        return
    if not legacy_path.is_dir():
        failures.append(f"{legacy_tree} exists but is not a directory")
        return

    readme = legacy_path / "README_DEPRECATED.md"
    if not readme.exists():
        failures.append(f"{legacy_tree} is present without README_DEPRECATED.md")

    dockerfile = legacy_path / "Dockerfile"
    if dockerfile.exists():
        dockerfile_text = dockerfile.read_text(encoding="utf-8", errors="ignore")
        if "DO_NOT_BUILD_LEGACY_SERVICE_TREE" not in dockerfile_text:
            failures.append(f"{legacy_tree}/Dockerfile is not quarantined")

    for required_path in metadata.get("required_paths", []):
        if not (root / str(required_path)).exists():
            failures.append(
                f"{legacy_tree} cannot be removed until canonical replacement exists: {required_path}"
            )

    migration_mirror = metadata.get("migration_mirror")
    if migration_mirror:
        _check_migration_mirror(root, legacy_path / "migrations", root / str(migration_mirror), failures)


def _check_migration_mirror(
    root: Path,
    legacy_migrations: Path,
    canonical_migrations: Path,
    failures: list[str],
) -> None:
    if not legacy_migrations.exists():
        return
    if not canonical_migrations.exists():
        failures.append(
            f"{_relative(root, legacy_migrations)} cannot be removed until mirrored at {_relative(root, canonical_migrations)}"
        )
        return

    for legacy_file in sorted(legacy_migrations.glob("*")):
        if not legacy_file.is_file():
            continue
        canonical_file = canonical_migrations / legacy_file.name
        if not canonical_file.exists():
            failures.append(f"missing mirrored migration: {_relative(root, canonical_file)}")
            continue
        if _sha256(legacy_file) != _sha256(canonical_file):
            failures.append(
                f"mirrored migration differs: {_relative(root, legacy_file)} -> {_relative(root, canonical_file)}"
            )


def _check_active_references(root: Path, failures: list[str]) -> None:
    for current_root, dirnames, filenames in os.walk(root):
        current_path = Path(current_root)
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if not _is_excluded_dir(root, current_path / dirname)
        ]

        for filename in filenames:
            path = current_path / filename
            relative = _relative(root, path)
            if _is_excluded_file(relative, path):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for forbidden in sorted(FORBIDDEN_ACTIVE_REFERENCES):
                if forbidden in text:
                    failures.append(f"active file references legacy agent target {forbidden!r}: {relative}")


def _is_excluded_dir(root: Path, path: Path) -> bool:
    relative = _relative(root, path)
    if _has_excluded_prefix(relative):
        return True
    return path.name in EXCLUDED_DIRS


def _is_excluded_file(relative: str, path: Path) -> bool:
    if relative in EXCLUDED_FILES:
        return True
    if _has_excluded_prefix(relative):
        return True
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return True
    if not path.is_file():
        return True
    return False


def _has_excluded_prefix(relative: str) -> bool:
    for prefix in EXCLUDED_PREFIXES:
        normalized = prefix.rstrip("/")
        if relative == normalized or relative.startswith(prefix):
            return True
    return False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
