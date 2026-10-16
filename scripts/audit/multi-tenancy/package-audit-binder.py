#!/usr/bin/env python3

import json
import os
from pathlib import Path


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def main() -> int:
    artifact_dir = os.environ.get("AUDIT_ARTIFACT_DIR")
    if not artifact_dir:
        raise SystemExit("AUDIT_ARTIFACT_DIR is required")

    root = Path(artifact_dir)
    binder_dir = root / "binder"
    binder_dir.mkdir(parents=True, exist_ok=True)

    control_summary = (root / "control-matrix" / "inventory-summary.md").exists()
    rls_summary = load_json(root / "rls-report" / "summary.json")
    test_summary = load_json(root / "test-results" / "summary.json")
    blocked_summary = load_json(root / "logs" / "blocked-violations.json")
    remediation_summary = load_json(root / "remediation" / "summary.json")
    owner_queue_index = load_json(root / "remediation" / "owner-queues" / "index.json")
    remediation_program = load_json(root / "remediation" / "program-summary.json")
    manifest = load_json(root / "manifest.json")
    step_results = manifest.get("step_results", {})
    overall_status = "failed" if "failed" in step_results.values() else "passed"
    run_id = os.environ.get("AUDIT_RUN_ID") or manifest.get("run_id", "")
    env_name = os.environ.get("AUDIT_ENV_NAME") or manifest.get("environment", "")
    profile = os.environ.get("AUDIT_PROFILE") or manifest.get("profile", "")
    git_sha = os.environ.get("AUDIT_GIT_SHA") or manifest.get("git_sha", "")

    summary = (
        "# Multi-Tenancy Audit Summary\n\n"
        f"- Run ID: {run_id}\n"
        f"- Environment: {env_name}\n"
        f"- Profile: {profile}\n"
        f"- Git SHA: {git_sha}\n"
        f"- Status: {overall_status}\n"
        f"- Control inventory present: {'yes' if control_summary else 'no'}\n"
        f"- RLS report present: {'yes' if rls_summary else 'no'}\n"
        f"- Negative-suite results present: {'yes' if test_summary else 'no'}\n"
        f"- Blocked-violation evidence present: {'yes' if blocked_summary else 'no'}\n"
        f"- Remediation report present: {'yes' if remediation_summary else 'no'}\n"
        f"- Owner remediation queues present: {'yes' if owner_queue_index else 'no'}\n"
        f"- Remediation program present: {'yes' if remediation_program else 'no'}\n"
    )

    if rls_summary:
        schema_summary = rls_summary.get("schema_summary", {})
        runtime_summary = rls_summary.get("runtime_summary", {})
        live_summary = rls_summary.get("live_runtime_summary", {})
        summary += (
            "\n## RLS Snapshot\n\n"
            f"- RLS tables: {schema_summary.get('table_count', 0)}\n"
            f"- FORCE RLS tables: {schema_summary.get('force_rls_tables', 0)}\n"
            f"- Plain DB routes requiring review: {runtime_summary.get('plain_db_routes', 0)}\n"
            f"- Critical plain-session routes: {runtime_summary.get('critical_routes', 0)}\n"
            f"- Live runtime verification status: {live_summary.get('status', 'unknown')}\n"
            f"- Live candidate tables with both tenants: {live_summary.get('candidate_tables_with_both_tenants', 0)}\n"
        )

    if test_summary:
        summary += (
            "\n## Negative-Suite Snapshot\n\n"
            f"- Evidence targets: {test_summary.get('targets', 0)}\n"
            f"- Executed tests: {test_summary.get('tests', 0)}\n"
            f"- Failures: {test_summary.get('failures', 0)}\n"
            f"- Errors: {test_summary.get('errors', 0)}\n"
        )

    if blocked_summary:
        summary += (
            "\n## Blocked-Violation Snapshot\n\n"
            f"- Collector status: {blocked_summary.get('status', 'unknown')}\n"
            f"- Targets covered: {blocked_summary.get('targets_covered', 0)}\n"
            f"- Evidence claims: {len(blocked_summary.get('events', []))}\n"
            f"- Failed or missing claims: {sum(1 for event in blocked_summary.get('events', []) if event.get('collector_status') != 'passed')}\n"
        )

    if remediation_summary:
        summary += (
            "\n## Remediation Snapshot\n\n"
            f"- Report status: {remediation_summary.get('status', 'unknown')}\n"
            f"- Live catalog drift tables: {remediation_summary.get('catalog_drift', {}).get('mismatch_count', 0)}\n"
            f"- Sampled cross-tenant exposure tables: {remediation_summary.get('live_exposure', {}).get('failed_table_count', 0)}\n"
            f"- Critical plain-session routes: {remediation_summary.get('runtime_adoption', {}).get('critical_routes', 0)}\n"
            f"- Review-required routes: {remediation_summary.get('runtime_adoption', {}).get('review_required_routes', 0)}\n"
        )

    if owner_queue_index:
        summary += (
            "\n## Owner Queue Snapshot\n\n"
            f"- Owner queues generated: {owner_queue_index.get('queue_count', 0)}\n"
        )

    if remediation_program:
        summary += (
            "\n## Remediation Program Snapshot\n\n"
            f"- Phases generated: {len(remediation_program.get('phases', []))}\n"
            f"- Current catalog mismatch tables: {remediation_program.get('current_findings', {}).get('catalog_mismatch_tables', 0)}\n"
            f"- Current sampled exposure tables: {remediation_program.get('current_findings', {}).get('sampled_cross_tenant_exposure_tables', 0)}\n"
        )

    summary += (
        "\n## Notes\n\n"
        "- Control inventory, RLS analysis, curated negative-suite evidence, and blocked-violation claim packaging are generated from repo state.\n"
        "- Live RLS proof still depends on a reachable database target and configured tenant pair.\n"
        "- Remediation outputs consolidate live drift, runtime exposure, and route-adoption gaps into an owner-ready report.\n"
        "- Owner remediation queues translate the audit findings into service and platform worklists.\n"
        "- The remediation program converts those queues into an execution sequence with entry and exit criteria.\n"
    )
    (root / "summary.md").write_text(summary)
    (binder_dir / "README.md").write_text(
        "# Audit Binder\n\n"
        "This directory will contain the assembled auditor-ready evidence package.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
