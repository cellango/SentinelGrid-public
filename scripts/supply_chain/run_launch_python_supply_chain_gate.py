#!/usr/bin/env python3
"""Build effective launch requirement plans, run pip-audit, and emit artifacts."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def _normalize_name(requirement: str) -> str:
    token = requirement.split(";", 1)[0].strip()
    token = token.split("[", 1)[0]
    for marker in ("==", ">=", "<=", "~=", "!=", ">", "<"):
        if marker in token:
            token = token.split(marker, 1)[0]
            break
    return token.strip().lower().replace("_", "-").replace(".", "-")


def _iter_requirement_lines(path: Path):
    for raw_line in path.read_text().splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-r "):
            continue
        yield stripped


def _build_effective_manifest(plan_name: str, manifests: list[str], output_dir: Path) -> Path:
    merged: dict[str, str] = {}
    ordered_keys: list[str] = []
    for manifest in manifests:
        path = Path(manifest)
        for requirement in _iter_requirement_lines(path):
            key = _normalize_name(requirement)
            if key not in merged:
                ordered_keys.append(key)
            merged[key] = requirement

    manifest_path = output_dir / f"{plan_name}.requirements.txt"
    lines = [f"# Effective install plan for {plan_name}"]
    lines.extend(merged[key] for key in ordered_keys)
    manifest_path.write_text("\n".join(lines) + "\n")
    return manifest_path


def _run_pip_audit(requirements_file: Path, output_file: Path) -> int:
    command = [
        "pip-audit",
        "-r",
        str(requirements_file),
        "-f",
        "json",
        "-o",
        str(output_file),
    ]
    result = subprocess.run(command, check=False)
    if result.returncode != 0 and not output_file.exists():
        output_file.write_text(
            json.dumps(
                {
                    "error": "pip-audit failed",
                    "requirements_file": str(requirements_file),
                    "returncode": result.returncode,
                },
                indent=2,
            )
            + "\n"
        )
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run pip-audit against launch install plans.")
    parser.add_argument(
        "--policy-file",
        default="scripts/supply_chain/launch_scope_dependency_policy.json",
        help="Path to the machine-readable dependency policy.",
    )
    parser.add_argument(
        "--artifacts-dir",
        default="artifacts/supply-chain",
        help="Directory for generated audit artifacts.",
    )
    args = parser.parse_args()

    if shutil.which("pip-audit") is None:
        print("pip-audit must be installed before running this gate.", file=sys.stderr)
        return 1

    policy = json.loads(Path(args.policy_file).read_text())
    artifacts_dir = Path(args.artifacts_dir)
    manifests_dir = artifacts_dir / "effective-manifests"
    audits_dir = artifacts_dir / "pip-audit"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    audits_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, dict[str, object]] = {}
    failures = 0

    for plan_name, manifests in policy["python"]["effective_install_plans"].items():
        manifest_path = _build_effective_manifest(plan_name, manifests, manifests_dir)
        audit_output = audits_dir / f"{plan_name}-pip-audit.json"
        exit_code = _run_pip_audit(manifest_path, audit_output)
        summary[plan_name] = {
            "source_manifests": manifests,
            "effective_manifest": str(manifest_path),
            "audit_output": str(audit_output),
            "passed": exit_code == 0,
        }
        if exit_code != 0:
            failures += 1

    summary_path = artifacts_dir / "launch-python-supply-chain-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")

    summary_md = artifacts_dir / "launch-python-supply-chain-summary.md"
    lines = ["# Launch Python Supply Chain Summary", ""]
    for plan_name, result in summary.items():
        status = "passed" if result["passed"] else "failed"
        lines.append(f"- `{plan_name}`: {status}")
        lines.append(f"  - effective manifest: `{result['effective_manifest']}`")
        lines.append(f"  - audit output: `{result['audit_output']}`")
    summary_md.write_text("\n".join(lines) + "\n")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
