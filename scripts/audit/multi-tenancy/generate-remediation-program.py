#!/usr/bin/env python3

from __future__ import annotations

import json
import os
from pathlib import Path


def artifact_root() -> Path:
    artifact_dir = os.environ.get("AUDIT_ARTIFACT_DIR")
    if not artifact_dir:
        raise SystemExit("AUDIT_ARTIFACT_DIR is required")
    return Path(artifact_dir)


def load_json(path: Path, default: object) -> object:
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def queue_map(owner_dir: Path) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for path in sorted(owner_dir.glob("*.json")):
        if path.name == "index.json":
            continue
        payload = load_json(path, {})
        if isinstance(payload, dict):
            result[path.stem] = payload
    return result


def summary_value(queue: dict[str, object], key: str) -> int:
    return int((queue.get("summary", {}) or {}).get(key, 0))


def phase(
    phase_id: str,
    title: str,
    objective: str,
    owners: list[str],
    entry_criteria: list[str],
    exit_criteria: list[str],
    workstreams: list[str],
    evidence: list[str],
) -> dict[str, object]:
    return {
        "phase_id": phase_id,
        "title": title,
        "objective": objective,
        "owners": owners,
        "entry_criteria": entry_criteria,
        "exit_criteria": exit_criteria,
        "workstreams": workstreams,
        "evidence": evidence,
    }


def build_program(
    manifest: dict[str, object],
    remediation_summary: dict[str, object],
    owner_index: dict[str, object],
    queues: dict[str, dict[str, object]],
) -> dict[str, object]:
    db = queues.get("database-platform", {})
    api_gateway = queues.get("api-gateway", {})
    iam_agent = queues.get("iam-agent", {})

    phase_1 = phase(
        "P1",
        "Database RLS Parity",
        "Bring the live database to the same tenant-isolation contract expected by the migration inventory.",
        ["database-platform"],
        [
            "Current full audit shows live catalog drift and sampled cross-tenant exposure.",
            "Live audit artifact and owner queue index are available.",
        ],
        [
            "Live catalog mismatch tables = 0.",
            "Live sampled cross-tenant exposure tables = 0.",
            "RLS enabled and FORCE RLS enabled counts match the migration-derived inventory for the audited environment.",
        ],
        [
            f"Apply RLS enablement to {summary_value(db, 'rls_not_enabled_tables')} live tables.",
            f"Apply FORCE RLS to {summary_value(db, 'force_rls_not_enabled_tables')} live tables.",
            f"Resolve {summary_value(db, 'tenant_id_column_missing_tables')} tenant-scoped tables missing tenant_id columns.",
            f"Reconcile policy-name drift on {summary_value(db, 'policy_mismatch_tables')} tables.",
        ],
        [
            "full audit rerun with live-runtime-verification status = passed",
            "remediation/catalog-drift.json showing zero mismatches",
            "remediation/cross-tenant-exposure.json showing zero failed tables",
        ],
    )

    phase_2 = phase(
        "P2",
        "Primary Control Plane Hardening",
        "Eliminate the highest-risk route-level tenant-scoping gaps in API Gateway and IAM Agent.",
        ["api-gateway", "iam-agent"],
        [
            "Phase P1 complete or a dedicated pre-production environment exists with database parity restored.",
        ],
        [
            "API Gateway critical plain-session routes = 0.",
            "IAM Agent critical plain-session routes = 0.",
            "Public tenant-selector routes in API Gateway and IAM Agent have explicit reviewed control status.",
        ],
        [
            f"API Gateway: convert {summary_value(api_gateway, 'critical_route_count')} critical routes off plain DB access.",
            f"API Gateway: review {summary_value(api_gateway, 'review_required_route_count')} review-required surfaces, especially dependency:get_current_tenant and X-Tenant-ID flows.",
            f"IAM Agent: convert {summary_value(iam_agent, 'critical_route_count')} critical routes off plain DB access.",
            f"IAM Agent: review {summary_value(iam_agent, 'review_required_route_count')} review-required surfaces, especially body:tenant_id, query:tenant_id, and helper:get_customer_id_from_token flows.",
        ],
        [
            "owner-queue rerun showing API Gateway critical_route_count = 0",
            "owner-queue rerun showing IAM Agent critical_route_count = 0",
            "expanded two-tenant negative-suite targets for remediated gateway and IAM routes",
        ],
    )

    secondary_owners = []
    for owner in owner_index.get("owners", []):
        owner_id = str(owner.get("owner_id", ""))
        summary = owner.get("summary", {}) or {}
        if owner_id in {"database-platform", "api-gateway", "iam-agent"}:
            continue
        if int(summary.get("critical_route_count", 0)) or int(summary.get("high_risk_route_count", 0)):
            secondary_owners.append(owner_id)

    phase_3 = phase(
        "P3",
        "Secondary Service Scoping Cleanup",
        "Burn down remaining critical and high-risk plain-session routes across the rest of the platform.",
        secondary_owners,
        [
            "Phase P2 complete.",
        ],
        [
            "All service owner queues show critical_route_count = 0.",
            "High-risk route count is reduced to approved exceptions only.",
        ],
        [
            "Prioritize audit-service, entitlement-agent, model-gateway, tenant-service, observables-service, and reporting-service queues first.",
            "Require service-local tests or audit negative-suite expansions for every route family touched.",
        ],
        [
            "owner-queue rerun with zero critical routes across all services",
            "updated review queue showing only approved exceptions or explicitly governed boundaries",
        ],
    )

    phase_4 = phase(
        "P4",
        "Audit Closure And Steady-State",
        "Convert the remediation program into a repeatable control that stays green over time.",
        ["database-platform", "api-gateway", "iam-agent"],
        [
            "Phases P1-P3 complete.",
        ],
        [
            "Full audit passes end to end.",
            "Negative suite and blocked-violation evidence run in the intended profiles.",
            "Auditor binder contains live proof, denial evidence, remediation history, and owner queue summaries.",
        ],
        [
            "Expand the curated negative suite to cover the highest-risk review-required surfaces.",
            "Run a formal full audit in the audit environment and archive the binder.",
            "Define an operational cadence for rerunning the audit pack and reviewing owner queues.",
        ],
        [
            "full audit manifest overall_status = passed",
            "binder summary showing live RLS proof, denial evidence, remediation report, and owner queues present",
        ],
    )

    return {
        "status": "generated",
        "run_id": manifest.get("run_id", ""),
        "environment": manifest.get("environment", ""),
        "profile": manifest.get("profile", ""),
        "git_sha": manifest.get("git_sha", ""),
        "current_findings": {
            "catalog_mismatch_tables": remediation_summary.get("catalog_drift", {}).get("mismatch_count", 0),
            "sampled_cross_tenant_exposure_tables": remediation_summary.get("live_exposure", {}).get(
                "failed_table_count",
                0,
            ),
            "critical_plain_session_routes": remediation_summary.get("runtime_adoption", {}).get(
                "critical_routes",
                0,
            ),
            "review_required_routes": remediation_summary.get("runtime_adoption", {}).get(
                "review_required_routes",
                0,
            ),
            "owner_queue_count": owner_index.get("queue_count", 0),
        },
        "phases": [phase_1, phase_2, phase_3, phase_4],
    }


def build_markdown(program: dict[str, object]) -> str:
    findings = program.get("current_findings", {}) or {}
    lines = [
        "# Multi-Tenancy Remediation Program",
        "",
        f"- Run ID: {program.get('run_id', '')}",
        f"- Environment: {program.get('environment', '')}",
        f"- Profile: {program.get('profile', '')}",
        f"- Git SHA: {program.get('git_sha', '')}",
        "",
        "## Current State",
        "",
        f"- Catalog mismatch tables: {findings.get('catalog_mismatch_tables', 0)}",
        f"- Sampled cross-tenant exposure tables: {findings.get('sampled_cross_tenant_exposure_tables', 0)}",
        f"- Critical plain-session routes: {findings.get('critical_plain_session_routes', 0)}",
        f"- Review-required routes: {findings.get('review_required_routes', 0)}",
        f"- Owner queues generated: {findings.get('owner_queue_count', 0)}",
    ]

    for phase_payload in program.get("phases", []) or []:
        lines.extend(
            [
                "",
                f"## {phase_payload.get('phase_id', '')} {phase_payload.get('title', '')}",
                "",
                f"- Objective: {phase_payload.get('objective', '')}",
                f"- Owners: {', '.join(phase_payload.get('owners', []))}",
                "",
                "Entry criteria:",
            ]
        )
        for item in phase_payload.get("entry_criteria", []) or []:
            lines.append(f"- {item}")
        lines.extend(["", "Workstreams:"])
        for item in phase_payload.get("workstreams", []) or []:
            lines.append(f"- {item}")
        lines.extend(["", "Exit criteria:"])
        for item in phase_payload.get("exit_criteria", []) or []:
            lines.append(f"- {item}")
        lines.extend(["", "Evidence to collect:"])
        for item in phase_payload.get("evidence", []) or []:
            lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Execution Rule",
            "",
            "- Do not claim tenant isolation is auditor-ready until P1 and P2 are complete and a full audit rerun passes live verification.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    root = artifact_root()
    remediation_dir = root / "remediation"
    owner_dir = remediation_dir / "owner-queues"

    manifest = load_json(root / "manifest.json", {})
    remediation_summary = load_json(remediation_dir / "summary.json", {})
    owner_index = load_json(owner_dir / "index.json", {"owners": [], "queue_count": 0})
    queues = queue_map(owner_dir)

    program = build_program(
        manifest if isinstance(manifest, dict) else {},
        remediation_summary if isinstance(remediation_summary, dict) else {},
        owner_index if isinstance(owner_index, dict) else {"owners": [], "queue_count": 0},
        queues,
    )

    write_json(remediation_dir / "program-summary.json", program)
    (remediation_dir / "remediation-program.md").write_text(build_markdown(program))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
