#!/usr/bin/env python3

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def artifact_root() -> Path:
    artifact_dir = os.environ.get("AUDIT_ARTIFACT_DIR")
    if not artifact_dir:
        raise SystemExit("AUDIT_ARTIFACT_DIR is required")
    return Path(artifact_dir)


def audit_profile() -> str:
    return os.environ.get("AUDIT_PROFILE", "standard")


def config_path() -> Path:
    return repo_root() / "scripts/audit/multi-tenancy/config/negative-suite-targets.json"


@dataclass
class ParsedCase:
    classname: str
    name: str
    status: str
    time: str
    detail: str | None = None


def load_targets() -> list[dict[str, Any]]:
    payload = json.loads(config_path().read_text())
    profile = audit_profile()
    target_ids = payload["profiles"].get(profile)
    if not target_ids:
        raise SystemExit(f"No negative-suite targets configured for profile '{profile}'")

    targets_by_id = {item["id"]: item for item in payload["targets"]}
    missing = [target_id for target_id in target_ids if target_id not in targets_by_id]
    if missing:
        raise SystemExit(f"Missing negative-suite target definitions: {', '.join(missing)}")

    return [targets_by_id[target_id] for target_id in target_ids]


def parse_junit_cases(junit_path: Path) -> tuple[list[ParsedCase], dict[str, int]]:
    tree = ET.parse(junit_path)
    root = tree.getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))

    cases: list[ParsedCase] = []
    counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}

    for suite in suites:
        counts["tests"] += int(suite.attrib.get("tests", 0))
        counts["failures"] += int(suite.attrib.get("failures", 0))
        counts["errors"] += int(suite.attrib.get("errors", 0))
        counts["skipped"] += int(suite.attrib.get("skipped", 0))

        for case in suite.findall("testcase"):
            status = "passed"
            detail = None
            if case.find("failure") is not None:
                status = "failed"
                detail = case.find("failure").attrib.get("message") or case.findtext("failure")
            elif case.find("error") is not None:
                status = "error"
                detail = case.find("error").attrib.get("message") or case.findtext("error")
            elif case.find("skipped") is not None:
                status = "skipped"
                detail = case.find("skipped").attrib.get("message") or case.findtext("skipped")

            cases.append(
                ParsedCase(
                    classname=case.attrib.get("classname", ""),
                    name=case.attrib.get("name", ""),
                    status=status,
                    time=case.attrib.get("time", "0"),
                    detail=detail,
                )
            )

    return cases, counts


def aggregate_junit(path: Path, cases: list[dict[str, Any]]) -> None:
    failures = sum(1 for case in cases if case["status"] == "failed")
    errors = sum(1 for case in cases if case["status"] == "error")
    skipped = sum(1 for case in cases if case["status"] == "skipped")

    root = ET.Element(
        "testsuite",
        name="multi-tenancy-audit-negative-suite",
        tests=str(len(cases)),
        failures=str(failures),
        errors=str(errors),
        skipped=str(skipped),
    )

    for case in cases:
        testcase = ET.SubElement(
            root,
            "testcase",
            classname=case["classname"],
            name=case["name"],
            time=str(case.get("time", "0")),
        )
        detail = case.get("detail")
        if case["status"] == "failed":
            failure = ET.SubElement(testcase, "failure")
            if detail:
                failure.text = detail
        elif case["status"] == "error":
            error = ET.SubElement(testcase, "error")
            if detail:
                error.text = detail
        elif case["status"] == "skipped":
            skipped_node = ET.SubElement(testcase, "skipped")
            if detail:
                skipped_node.text = detail

    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def run_target(target: dict[str, Any], results_dir: Path, raw_dir: Path) -> dict[str, Any]:
    root = repo_root()
    workdir = root / target["workdir"]
    junit_path = raw_dir / f"{target['id']}.junit.xml"
    log_path = raw_dir / f"{target['id']}.log"

    env = os.environ.copy()
    env.update(target.get("env", {}))

    command = ["python3", "-m", "pytest", *target["pytest_args"], f"--junitxml={junit_path}"]
    process = subprocess.run(
        command,
        cwd=workdir,
        env=env,
        text=True,
        capture_output=True,
    )

    log_lines = [
        f"target_id={target['id']}",
        f"workdir={workdir}",
        f"command={' '.join(command)}",
        f"exit_code={process.returncode}",
        "",
        "=== STDOUT ===",
        process.stdout,
        "",
        "=== STDERR ===",
        process.stderr,
    ]
    log_path.write_text("\n".join(log_lines))

    if junit_path.exists():
        cases, counts = parse_junit_cases(junit_path)
    else:
        detail = "No JUnit output produced by pytest command"
        cases = [
            ParsedCase(
                classname=target["id"],
                name="pytest_execution",
                status="error",
                time="0",
                detail=detail,
            )
        ]
        counts = {"tests": 1, "failures": 0, "errors": 1, "skipped": 0}

    case_rows: list[dict[str, Any]] = []
    for parsed in cases:
        case_rows.append(
            {
                "scenario_id": f"{target['id']}::{parsed.classname}::{parsed.name}",
                "target_id": target["id"],
                "domain": target["domain"],
                "owner": target["owner"],
                "service": target["service"],
                "description": target["description"],
                "evidence_surfaces": " | ".join(target.get("evidence_surfaces", [])),
                "classname": parsed.classname,
                "name": parsed.name,
                "testcase": f"{parsed.classname}::{parsed.name}",
                "status": parsed.status,
                "detail": parsed.detail or "",
                "junit_xml": str(junit_path),
                "log_file": str(log_path),
                "command": " ".join(command),
                "time": parsed.time,
            }
        )

    target_status = "passed"
    if process.returncode != 0 or counts["failures"] or counts["errors"]:
        target_status = "failed"

    return {
        "target_id": target["id"],
        "domain": target["domain"],
        "owner": target["owner"],
        "service": target["service"],
        "description": target["description"],
        "test_file": target.get("test_file", ""),
        "blocked_violation_cases": target.get("blocked_violation_cases", []),
        "status": target_status,
        "exit_code": process.returncode,
        "tests": counts["tests"],
        "failures": counts["failures"],
        "errors": counts["errors"],
        "skipped": counts["skipped"],
        "workdir": str(workdir),
        "command": " ".join(command),
        "junit_xml": str(junit_path),
        "log_file": str(log_path),
        "evidence_surfaces": target.get("evidence_surfaces", []),
        "cases": case_rows,
    }


def write_scenario_matrix(path: Path, cases: list[dict[str, Any]]) -> None:
    fieldnames = [
        "scenario_id",
        "target_id",
        "domain",
        "owner",
        "service",
        "description",
        "evidence_surfaces",
        "classname",
        "name",
        "testcase",
        "status",
        "detail",
        "junit_xml",
        "log_file",
        "command",
        "time",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for case in cases:
            writer.writerow(case)


def write_summary(path: Path, target_results: list[dict[str, Any]]) -> dict[str, Any]:
    all_cases = [case for target in target_results for case in target["cases"]]
    failures = sum(1 for case in all_cases if case["status"] == "failed")
    errors = sum(1 for case in all_cases if case["status"] == "error")
    skipped = sum(1 for case in all_cases if case["status"] == "skipped")
    passed_targets = sum(1 for target in target_results if target["status"] == "passed")
    failed_targets = len(target_results) - passed_targets

    summary = {
        "status": "passed" if failed_targets == 0 else "failed",
        "profile": audit_profile(),
        "targets": len(target_results),
        "passed_targets": passed_targets,
        "failed_targets": failed_targets,
        "tests": len(all_cases),
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        "target_results": [
            {
                key: value
                for key, value in target.items()
                if key != "cases"
            }
            for target in target_results
        ],
    }
    path.write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> int:
    artifact = artifact_root()
    results_dir = artifact / "test-results"
    raw_dir = results_dir / "raw"
    results_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    targets = load_targets()
    target_results = [run_target(target, results_dir, raw_dir) for target in targets]
    all_cases = [case for target in target_results for case in target["cases"]]

    aggregate_junit(results_dir / "junit.xml", all_cases)
    write_scenario_matrix(results_dir / "scenario-matrix.csv", all_cases)
    (results_dir / "target-manifest.json").write_text(
        json.dumps({"profile": audit_profile(), "targets": target_results}, indent=2) + "\n"
    )
    summary = write_summary(results_dir / "summary.json", target_results)

    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
