#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import pathlib
import shlex
from dataclasses import dataclass


APPROVER_ROLES = [
    "Security Lead",
    "Platform / DevOps Lead",
    "IAM / Identity Lead",
    "Frontend Lead",
    "Product / Launch Owner",
]

PASS_STATUSES = {"passed"}
FAIL_STATUSES = {"failed"}


@dataclass(frozen=True)
class GateDefinition:
    key: str
    label: str
    step_name: str | None = None


GATE_DEFINITIONS = [
    GateDefinition(
        key="evidence_pack_live_mode",
        label="Evidence pack executed in live mode",
    ),
    GateDefinition(
        key="live_multi_tenant_audit",
        label="Live multi-tenant RLS proof completed",
        step_name="run_live_multi_tenant_audit",
    ),
    GateDefinition(
        key="restore_drill",
        label="Restore drill completed",
        step_name="restore_drill",
    ),
    GateDefinition(
        key="rollback_drill",
        label="Rollback drill completed",
        step_name="rollback_drill",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a Phase 6 live evidence pack.")
    parser.add_argument("--result-json", required=True, help="Path to phase6 result.json")
    parser.add_argument("--output-json", required=True, help="Path to write gate-review.json")
    parser.add_argument("--output-md", required=True, help="Path to write gate-review.md")
    return parser.parse_args()


def map_gate_status(raw_status: str) -> str:
    if raw_status in PASS_STATUSES:
        return "pass"
    if raw_status in FAIL_STATUSES:
        return "fail"
    return "pending"


def format_gate_status(status: str) -> str:
    mapping = {
        "pass": "Pass",
        "fail": "Fail",
        "pending": "Pending",
    }
    return mapping.get(status, status.title())


def format_decision(decision: str) -> str:
    return "Go" if decision == "go" else "No-Go"


def build_live_rerun_command(payload: dict) -> str:
    rollback = payload.get("rollback", {})
    command = [
        "bash",
        "scripts/phase6/run-live-evidence-pack.sh",
        "--mode",
        "live",
        "--audit-profile",
        str(payload.get("audit_profile", "full")),
        "--audit-env",
        str(payload.get("audit_env", "audit")),
        "--restore-component",
        str(payload.get("restore_component", "all")),
        "--rollback-release",
        str(rollback.get("release", "api-gateway")),
        "--rollback-revision",
        str(rollback.get("revision", "1")),
        "--rollback-namespace",
        str(rollback.get("namespace", "sg-core")),
    ]
    ready_url = rollback.get("ready_url")
    if ready_url:
        command.extend(["--rollback-ready-url", str(ready_url)])
    return shlex.join(command)


def evaluate(payload: dict, result_path: pathlib.Path) -> dict:
    steps = payload.get("steps", [])
    steps_by_name = {step.get("name"): step for step in steps}

    gates: list[dict] = []
    blockers: list[str] = []
    next_actions: list[str] = []

    mode = str(payload.get("mode", "unknown"))
    live_rerun_command = build_live_rerun_command(payload)

    for definition in GATE_DEFINITIONS:
        artifact_dir = ""
        notes = ""
        raw_status = ""

        if definition.step_name is None:
            raw_status = "passed" if mode == "live" else "planned"
            if mode == "live":
                notes = "The evidence pack was executed in live mode."
            else:
                notes = "The evidence pack was not executed in live mode."
        else:
            step = steps_by_name.get(definition.step_name, {})
            raw_status = str(step.get("status", ""))
            artifact_dir = str(step.get("artifact_dir", ""))
            notes = str(step.get("notes", ""))

        gate_status = map_gate_status(raw_status)
        gates.append(
            {
                "key": definition.key,
                "label": definition.label,
                "status": gate_status,
                "raw_status": raw_status or "unknown",
                "artifact_dir": artifact_dir,
                "notes": notes,
            }
        )

    for gate in gates:
        if gate["status"] == "pass":
            continue
        if gate["key"] == "evidence_pack_live_mode":
            blockers.append("the evidence pack was only executed in plan mode")
            next_actions.append(f"rerun the Phase 6 evidence pack in live mode: `{live_rerun_command}`")
        elif gate["key"] == "live_multi_tenant_audit":
            blockers.append("live multi-tenant RLS proof is not captured in the evidence pack")
            next_actions.append("run the full multi-tenancy audit against a reachable Postgres target and keep the resulting artifact directory")
        elif gate["key"] == "restore_drill":
            blockers.append("restore drill evidence is missing or failed")
            next_actions.append("run the restore drill in live mode and attach the result.json and summary.md outputs")
        elif gate["key"] == "rollback_drill":
            blockers.append("rollback drill evidence is missing or failed")
            next_actions.append("run the rollback drill in live mode and attach the result.json and summary.md outputs")

    overall_status = str(payload.get("overall_status", "unknown"))
    if overall_status == "failed" and "the evidence pack contains failed steps" not in blockers:
        blockers.append("the evidence pack contains failed steps")

    recommended_decision = "go" if not blockers else "no-go"
    ready_for_signoff = recommended_decision == "go"

    return {
        "generated_from": str(result_path),
        "artifact_root": payload.get("artifact_root", ""),
        "timestamp_utc": payload.get("timestamp_utc", ""),
        "git_sha": payload.get("git_sha", ""),
        "git_ref": payload.get("git_ref", ""),
        "mode": mode,
        "overall_status": overall_status,
        "recommended_decision": recommended_decision,
        "ready_for_signoff": ready_for_signoff,
        "human_signoff_required": True,
        "approver_roles": APPROVER_ROLES,
        "live_rerun_command": live_rerun_command,
        "gates": gates,
        "blocking_items": blockers,
        "next_actions": next_actions,
    }


def render_markdown(review: dict) -> str:
    lines: list[str] = []
    lines.append("# Phase 6 Gate Review")
    lines.append("")
    lines.append(f"- Recommended decision: `{format_decision(review['recommended_decision'])}`")
    lines.append(f"- Ready for human signoff: `{str(review['ready_for_signoff']).lower()}`")
    lines.append(f"- Mode: `{review['mode']}`")
    lines.append(f"- Evidence root: `{review['artifact_root']}`")
    lines.append(f"- Source result: `{review['generated_from']}`")
    lines.append("")
    lines.append("## Gates")
    lines.append("")
    lines.append("| Gate | Status | Raw Status | Evidence |")
    lines.append("| --- | --- | --- | --- |")
    for gate in review["gates"]:
        evidence = gate.get("artifact_dir") or "n/a"
        lines.append(
            f"| {gate['label']} | {format_gate_status(gate['status'])} | `{gate['raw_status']}` | `{evidence}` |"
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
    if review["next_actions"]:
        for item in review["next_actions"]:
            lines.append(f"1. {item}")
    else:
        lines.append("1. present this gate review to the named approvers for final go / no-go signoff")

    lines.append("")
    lines.append("## Suggested Live Rerun Command")
    lines.append("")
    lines.append("```bash")
    lines.append(review["live_rerun_command"])
    lines.append("```")
    lines.append("")
    lines.append("## Approver Roles")
    lines.append("")
    for role in review["approver_roles"]:
        lines.append(f"- {role}")
    lines.append("")
    lines.append("This artifact is a tooling recommendation. Final release approval still requires named human signoff.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    result_path = pathlib.Path(args.result_json)
    output_json = pathlib.Path(args.output_json)
    output_md = pathlib.Path(args.output_md)

    payload = json.loads(result_path.read_text())
    review = evaluate(payload, result_path)

    output_json.write_text(json.dumps(review, indent=2) + "\n")
    output_md.write_text(render_markdown(review))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
