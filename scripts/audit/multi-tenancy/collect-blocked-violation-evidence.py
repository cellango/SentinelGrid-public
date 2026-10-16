#!/usr/bin/env python3

from __future__ import annotations

import ast
import csv
import json
import os
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def artifact_root() -> Path:
    artifact_dir = os.environ.get("AUDIT_ARTIFACT_DIR")
    if not artifact_dir:
        raise SystemExit("AUDIT_ARTIFACT_DIR is required")
    return Path(artifact_dir)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def extract_function_source(path: Path, function_name: str) -> str:
    source_text = path.read_text()
    tree = ast.parse(source_text, filename=str(path))
    lines = source_text.splitlines()
    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            start = getattr(node, "lineno", 1) - 1
            end = getattr(node, "end_lineno", getattr(node, "lineno", 1))
            return "\n".join(lines[start:end]) + "\n"
    return ""


def load_config_targets() -> dict[str, dict]:
    path = repo_root() / "scripts/audit/multi-tenancy/config/negative-suite-targets.json"
    payload = load_json(path)
    return {target["id"]: target for target in payload["targets"]}


def relative_path(path: Path) -> str:
    return path.relative_to(repo_root()).as_posix()


def merge_target_metadata(target: dict, config_targets: dict[str, dict]) -> dict:
    config = config_targets.get(target["target_id"], {})
    merged = dict(config)
    merged.update(target)
    if not merged.get("test_file"):
        merged["test_file"] = config.get("test_file", "")
    if not merged.get("blocked_violation_cases"):
        merged["blocked_violation_cases"] = config.get("blocked_violation_cases", [])
    return merged


def build_event(
    target: dict,
    claim: dict,
    case: dict | None,
    excerpt_dir: Path,
) -> dict:
    test_file = repo_root() / target.get("test_file", "")
    excerpt_path = excerpt_dir / f"{claim['claim_id']}.py"
    excerpt = ""
    if target.get("test_file"):
        excerpt = extract_function_source(test_file, claim["testcase"])
        excerpt_path.write_text(excerpt or f"# Source excerpt not found for {claim['testcase']}\n")

    case_status = case["status"] if case else "missing"
    detail = case.get("detail", "") if case else "No matching testcase found in target manifest."
    status = "passed" if case_status == "passed" else "failed"
    summary_statement = (
        f"{claim['auditor_assertion']} Verified by passing testcase `{claim['testcase']}`."
        if status == "passed"
        else f"{claim['auditor_assertion']} Not proven in this run because testcase `{claim['testcase']}` status was `{case_status}`."
    )

    return {
        "claim_id": claim["claim_id"],
        "control_id": claim["control_id"],
        "claim_type": claim["claim_type"],
        "severity": claim["severity"],
        "target_id": target["target_id"],
        "owner": target["owner"],
        "service": target["service"],
        "domain": target["domain"],
        "description": target["description"],
        "auditor_assertion": claim["auditor_assertion"],
        "expected_behavior": claim["expected_behavior"],
        "evidence_surface": claim["evidence_surface"],
        "test_file": target.get("test_file", ""),
        "testcase": claim["testcase"],
        "testcase_status": case_status,
        "collector_status": status,
        "detail": detail,
        "summary_statement": summary_statement,
        "junit_xml": case.get("junit_xml", target.get("junit_xml", "")) if case else target.get("junit_xml", ""),
        "log_file": case.get("log_file", target.get("log_file", "")) if case else target.get("log_file", ""),
        "command": case.get("command", target.get("command", "")) if case else target.get("command", ""),
        "source_excerpt_file": relative_path(excerpt_path),
        "source_excerpt_available": bool(excerpt.strip()),
    }


def write_csv(path: Path, events: list[dict]) -> None:
    fieldnames = [
        "claim_id",
        "control_id",
        "claim_type",
        "severity",
        "target_id",
        "owner",
        "service",
        "domain",
        "evidence_surface",
        "test_file",
        "testcase",
        "testcase_status",
        "collector_status",
        "detail",
        "junit_xml",
        "log_file",
        "source_excerpt_file",
        "summary_statement",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for event in events:
            writer.writerow({field: event.get(field, "") for field in fieldnames})


def write_summary(path: Path, payload: dict) -> None:
    events = payload["events"]
    passed = [event for event in events if event["collector_status"] == "passed"]
    failed = [event for event in events if event["collector_status"] != "passed"]

    lines = [
        "# Blocked Violation Evidence Summary",
        "",
        f"- Status: {payload['status']}",
        f"- Profile: {payload.get('profile', '')}",
        f"- Targets covered: {payload.get('targets_covered', 0)}",
        f"- Evidence claims collected: {len(events)}",
        f"- Passing evidence claims: {len(passed)}",
        f"- Failed or missing evidence claims: {len(failed)}",
        "",
        "## Evidence Claims",
        "",
    ]

    for event in events:
        lines.append(
            f"- `{event['claim_id']}` `{event['service']}` `{event['testcase']}` "
            f"status={event['collector_status']} surface=`{event['evidence_surface']}`"
        )

    if payload.get("uncatalogued_cases"):
        lines.extend(["", "## Uncatalogued Negative-Suite Cases", ""])
        for case in payload["uncatalogued_cases"]:
            lines.append(
                f"- `{case['target_id']}` `{case['testcase']}` status={case['status']}"
            )

    if payload.get("notes"):
        lines.extend(["", "## Notes", ""])
        for note in payload["notes"]:
            lines.append(f"- {note}")

    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    artifact = artifact_root()
    logs_dir = artifact / "logs"
    excerpt_dir = logs_dir / "evidence-excerpts"
    logs_dir.mkdir(parents=True, exist_ok=True)
    excerpt_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = artifact / "test-results" / "target-manifest.json"
    if not manifest_path.exists():
        payload = {
            "status": "skipped",
            "profile": os.environ.get("AUDIT_PROFILE", ""),
            "targets_covered": 0,
            "events": [],
            "uncatalogued_cases": [],
            "notes": [
                "Negative-suite target manifest was not found for this run.",
            ],
        }
        write_json(logs_dir / "blocked-violations.json", payload)
        write_csv(logs_dir / "blocked-violations.csv", [])
        write_summary(logs_dir / "log-collection-summary.md", payload)
        (logs_dir / "blocked-violations.log").write_text(
            "status=skipped\nreason=Negative-suite target manifest was not found for this run.\n"
        )
        return 0

    manifest = load_json(manifest_path)
    config_targets = load_config_targets()
    targets = [merge_target_metadata(target, config_targets) for target in manifest.get("targets", [])]

    events: list[dict] = []
    uncatalogued_cases: list[dict] = []
    notes: list[str] = []

    for target in targets:
        case_map = {case["name"]: case for case in target.get("cases", [])}
        configured_claims = target.get("blocked_violation_cases", [])
        configured_testcases = {claim["testcase"] for claim in configured_claims}

        for claim in configured_claims:
            events.append(build_event(target, claim, case_map.get(claim["testcase"]), excerpt_dir))

        for case in target.get("cases", []):
            if case["name"] not in configured_testcases:
                uncatalogued_cases.append(
                    {
                        "target_id": target["target_id"],
                        "testcase": case["name"],
                        "status": case["status"],
                    }
                )

        if not configured_claims:
            notes.append(f"{target['target_id']} has no configured blocked-violation claims.")

    failed_events = [event for event in events if event["collector_status"] != "passed"]
    payload = {
        "status": "passed" if not failed_events else "failed",
        "profile": manifest.get("profile", os.environ.get("AUDIT_PROFILE", "")),
        "targets_covered": len(targets),
        "events": events,
        "uncatalogued_cases": uncatalogued_cases,
        "notes": notes,
    }

    write_json(logs_dir / "blocked-violations.json", payload)
    write_csv(logs_dir / "blocked-violations.csv", events)
    write_summary(logs_dir / "log-collection-summary.md", payload)

    log_lines = [
        f"status={payload['status']}",
        f"targets_covered={payload['targets_covered']}",
        f"evidence_claims={len(events)}",
        f"failed_claims={len(failed_events)}",
    ]
    for event in events:
        log_lines.append(
            f"{event['claim_id']}|{event['collector_status']}|{event['service']}|{event['testcase']}|{event['evidence_surface']}"
        )
    (logs_dir / "blocked-violations.log").write_text("\n".join(log_lines) + "\n")
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
