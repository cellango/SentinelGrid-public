#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import pathlib


REVIEW_ROLES = [
    "Product / Launch Owner",
    "Security Lead",
    "Engineering / Platform Lead",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate a Phase 6 pre-audit dry-run artifact pack."
    )
    parser.add_argument("--result-json", required=True, help="Path to preaudit result.json")
    parser.add_argument("--output-json", required=True, help="Path to write phase7-entry-review.json")
    parser.add_argument("--output-md", required=True, help="Path to write phase7-entry-review.md")
    return parser.parse_args()


def format_status(status: str) -> str:
    mapping = {
        "passed": "Pass",
        "failed": "Fail",
    }
    return mapping.get(status, status.title())


def evaluate(payload: dict) -> dict:
    blockers: list[str] = []
    next_actions: list[str] = []

    steps = payload.get("steps", [])
    recovery_evidence = payload.get("recovery_evidence", [])
    gate_evidence = payload.get("gate_evidence", [])

    for step in steps:
        status = str(step.get("status", "unknown"))
        if status == "passed":
            continue
        blockers.append(
            f"pre-audit verification step `{step.get('name', 'unknown')}` did not pass"
        )
        notes = str(step.get("notes", "")).strip()
        if notes:
            next_actions.append(notes)

    for item in recovery_evidence:
        status = str(item.get("status", "unknown"))
        if status == "passed" and bool(item.get("within_timebox", False)):
            continue
        blockers.append(
            f"recovery evidence `{item.get('name', 'unknown')}` is missing, failed, or outside its timebox"
        )
        next_actions.append(
            f"rerun or repair `{item.get('name', 'unknown')}` using `{item.get('result_json', 'missing result.json')}` as the expected artifact shape"
        )

    for gate in gate_evidence:
        status = str(gate.get("status", "unknown"))
        if status == "passed":
            continue
        blockers.append(
            f"required frozen evidence for `{gate.get('gate', 'unknown gate')}` is incomplete"
        )
        missing_paths = [
            str(item.get("path", ""))
            for item in gate.get("items", [])
            if not bool(item.get("exists", False))
        ]
        if missing_paths:
            next_actions.append(
                "restore or publish the missing evidence paths: "
                + ", ".join(f"`{path}`" for path in missing_paths)
            )

    overall_status = str(payload.get("overall_status", "unknown"))
    phase7_entry_ready = not blockers and overall_status == "passed"
    if overall_status != "passed":
        blockers.append("the pre-audit dry run does not have an overall passed status")

    if not next_actions and phase7_entry_ready:
        next_actions.append(
            "begin Phase 7 from this frozen evidence pack and keep the artifact directory immutable during the re-audit"
        )

    return {
        "generated_from": str(payload.get("artifact_root", "")),
        "result_json": str(payload.get("result_json", "")),
        "timestamp_utc": str(payload.get("timestamp_utc", "")),
        "git_sha": str(payload.get("git_sha", "")),
        "git_ref": str(payload.get("git_ref", "")),
        "overall_status": overall_status,
        "phase7_entry_ready": phase7_entry_ready,
        "recommended_decision": "phase7-eligible" if phase7_entry_ready else "blocked",
        "review_roles": REVIEW_ROLES,
        "steps": steps,
        "recovery_evidence": recovery_evidence,
        "gate_evidence": gate_evidence,
        "blocking_items": blockers,
        "next_actions": next_actions,
        "manifest_path": str(payload.get("manifest_path", "")),
        "recovery_validation_path": str(payload.get("recovery_validation_path", "")),
    }


def render_markdown(review: dict) -> str:
    lines: list[str] = []
    lines.append("# Phase 7 Entry Review")
    lines.append("")
    lines.append(
        f"- Recommended decision: `{'Eligible' if review['phase7_entry_ready'] else 'Blocked'}`"
    )
    lines.append(f"- Overall status: `{review['overall_status']}`")
    lines.append(f"- Evidence root: `{review['generated_from']}`")
    lines.append(f"- Manifest: `{review['manifest_path']}`")
    lines.append(f"- Recovery validation: `{review['recovery_validation_path']}`")
    lines.append("")
    lines.append("## Verification Steps")
    lines.append("")
    lines.append("| Step | Status | Evidence |")
    lines.append("| --- | --- | --- |")
    for step in review["steps"]:
        lines.append(
            f"| {step.get('name', 'unknown')} | {format_status(str(step.get('status', 'unknown')))} | `{step.get('artifact_dir', '') or 'n/a'}` |"
        )

    lines.append("")
    lines.append("## Recovery Evidence")
    lines.append("")
    lines.append("| Evidence | Status | Within Timebox | Result |")
    lines.append("| --- | --- | --- | --- |")
    for item in review["recovery_evidence"]:
        lines.append(
            f"| {item.get('name', 'unknown')} | {format_status(str(item.get('status', 'unknown')))} | `{str(bool(item.get('within_timebox', False))).lower()}` | `{item.get('result_json', '') or 'n/a'}` |"
        )

    lines.append("")
    lines.append("## Frozen Gate Evidence")
    lines.append("")
    lines.append("| Gate | Status | Evidence Items |")
    lines.append("| --- | --- | --- |")
    for gate in review["gate_evidence"]:
        item_count = len(gate.get("items", []))
        lines.append(
            f"| {gate.get('gate', 'unknown')} | {format_status(str(gate.get('status', 'unknown')))} | `{item_count}` |"
        )

    lines.append("")
    lines.append("## Blocking Items")
    lines.append("")
    if review["blocking_items"]:
        for item in review["blocking_items"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines.append("")
    lines.append("## Next Actions")
    lines.append("")
    for item in review["next_actions"]:
        lines.append(f"1. {item}")

    lines.append("")
    lines.append("## Review Roles")
    lines.append("")
    for role in review["review_roles"]:
        lines.append(f"- {role}")
    lines.append("")
    lines.append(
        "This review only determines whether Phase 7 may begin. It does not itself issue a `Go` recommendation."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    result_path = pathlib.Path(args.result_json)
    output_json = pathlib.Path(args.output_json)
    output_md = pathlib.Path(args.output_md)

    payload = json.loads(result_path.read_text())
    review = evaluate(payload)

    output_json.write_text(json.dumps(review, indent=2) + "\n")
    output_md.write_text(render_markdown(review))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
