#!/usr/bin/env python3

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
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


def normalize_mismatch_reason(reason: str) -> str:
    if reason == "RLS not enabled":
        return "rls_not_enabled"
    if reason == "FORCE RLS not enabled":
        return "force_rls_not_enabled"
    if reason == "tenant_id column missing":
        return "tenant_id_column_missing"
    if reason.startswith("policy mismatch"):
        return "policy_mismatch"
    return "other"


def summarize_catalog_drift(live_runtime: dict[str, object]) -> dict[str, object]:
    mismatches = live_runtime.get("live_catalog_mismatches", []) or []
    groups: dict[str, list[dict[str, object]]] = {
        "rls_not_enabled": [],
        "force_rls_not_enabled": [],
        "tenant_id_column_missing": [],
        "policy_mismatch": [],
        "other": [],
    }

    for item in mismatches:
        categories = {normalize_mismatch_reason(reason) for reason in item.get("reasons", [])}
        for category in categories:
            groups.setdefault(category, []).append(
                {
                    "key": item.get("key"),
                    "schema": item.get("schema"),
                    "table": item.get("table"),
                    "reasons": item.get("reasons", []),
                    "expected_policies": item.get("expected_policies", []),
                    "live_policies": item.get("live_policies", []),
                }
            )

    return {
        "status": "skipped" if live_runtime.get("status") == "skipped" else "failed" if mismatches else "passed",
        "summary": {
            "mismatch_count": len(mismatches),
            "rls_not_enabled_tables": len(groups["rls_not_enabled"]),
            "force_rls_not_enabled_tables": len(groups["force_rls_not_enabled"]),
            "tenant_id_column_missing_tables": len(groups["tenant_id_column_missing"]),
            "policy_mismatch_tables": len(groups["policy_mismatch"]),
        },
        "groups": groups,
    }


def summarize_live_exposure(live_runtime: dict[str, object]) -> dict[str, object]:
    evaluated_tables = live_runtime.get("evaluated_tables", []) or []
    failed_tables = [table for table in evaluated_tables if table.get("status") != "passed"]
    assertion_counter: Counter[str] = Counter()
    failed_assertion_by_table: list[dict[str, object]] = []

    for table in failed_tables:
        failed_assertions = [
            assertion_name
            for assertion_name, assertion_value in (table.get("assertions", {}) or {}).items()
            if not assertion_value
        ]
        for assertion_name in failed_assertions:
            assertion_counter[assertion_name] += 1
        failed_assertion_by_table.append(
            {
                "key": f"{table.get('schema')}.{table.get('table')}",
                "failed_assertions": failed_assertions,
                "baseline_counts": table.get("baseline_counts", {}),
                "context_counts": table.get("context_counts", {}),
            }
        )

    return {
        "status": live_runtime.get("status", "unknown"),
        "summary": {
            "evaluated_table_count": len(evaluated_tables),
            "failed_table_count": len(failed_tables),
            "failed_assertion_counts": dict(assertion_counter),
        },
        "failed_tables": failed_assertion_by_table,
    }


def route_summary_by_service(routes: list[dict[str, object]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for route in routes:
        counts[str(route.get("service", "unknown"))] += 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def review_queue_source_counts(items: list[dict[str, object]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in items:
        counts[str(item.get("primary_tenant_source", "unknown"))] += 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def summarize_runtime_adoption(
    runtime_usage: dict[str, object],
    review_queue: dict[str, object],
) -> dict[str, object]:
    critical_routes = runtime_usage.get("critical_routes", []) or []
    high_risk_routes = runtime_usage.get("high_risk_routes", []) or []
    review_items = review_queue.get("items", []) or []

    return {
        "summary": runtime_usage.get("summary", {}),
        "critical_route_counts_by_service": route_summary_by_service(critical_routes),
        "high_risk_route_counts_by_service": route_summary_by_service(high_risk_routes),
        "review_required_counts_by_service": route_summary_by_service(review_items),
        "review_required_counts_by_tenant_source": review_queue_source_counts(review_items),
        "critical_route_preview": critical_routes[:25],
        "review_required_preview": review_items[:25],
    }


def top_services(service_counts: dict[str, int], limit: int = 5) -> list[str]:
    return [f"{service}: {count}" for service, count in list(service_counts.items())[:limit]]


def build_report_markdown(
    manifest: dict[str, object],
    rls_summary: dict[str, object],
    test_summary: dict[str, object],
    blocked_summary: dict[str, object],
    catalog_drift: dict[str, object],
    live_exposure: dict[str, object],
    runtime_adoption: dict[str, object],
) -> str:
    schema_summary = rls_summary.get("schema_summary", {}) or {}
    runtime_summary = rls_summary.get("runtime_summary", {}) or {}
    live_summary = rls_summary.get("live_runtime_summary", {}) or {}
    blocked_events = blocked_summary.get("events", []) or []
    test_executed = bool(test_summary)
    blocked_executed = bool(blocked_summary)
    step_results = manifest.get("step_results", {}) or {}
    overall_status = "failed" if "failed" in step_results.values() else manifest.get("overall_status", "unknown")

    lines = [
        "# Multi-Tenancy Remediation Report",
        "",
        "## Run Context",
        "",
        f"- Run ID: {manifest.get('run_id', '')}",
        f"- Environment: {manifest.get('environment', '')}",
        f"- Profile: {manifest.get('profile', '')}",
        f"- Git SHA: {manifest.get('git_sha', '')}",
        f"- Overall status: {overall_status}",
        "",
        "## Executive Summary",
        "",
        f"- Live RLS verification status: {live_summary.get('status', 'unknown')}",
        f"- Migration inventory expects RLS on {schema_summary.get('table_count', 0)} tables and `FORCE RLS` on {schema_summary.get('force_rls_tables', 0)} tables.",
        f"- Live catalog currently shows RLS enabled on {live_summary.get('live_catalog_summary', {}).get('rls_enabled_tables', 0)} tables and `FORCE RLS` on {live_summary.get('live_catalog_summary', {}).get('force_rls_tables', 0)} tables.",
        f"- Live catalog drift affects {catalog_drift.get('summary', {}).get('mismatch_count', 0)} tables.",
        f"- Cross-tenant runtime exposure was observed on {live_exposure.get('summary', {}).get('failed_table_count', 0)} of {live_exposure.get('summary', {}).get('evaluated_table_count', 0)} sampled tables.",
        f"- Route-level runtime adoption gap remains large: {runtime_summary.get('plain_db_routes', 0)} plain DB routes, including {runtime_summary.get('critical_routes', 0)} critical routes without visible tenant proof.",
        (
            f"- Curated negative suite passed {test_summary.get('tests', 0)} tests with {test_summary.get('failures', 0)} failures."
            if test_executed
            else "- Curated negative suite was not executed in this run."
        ),
        (
            f"- Blocked-violation evidence packaged {len(blocked_events)} control claims."
            if blocked_executed
            else "- Blocked-violation evidence was not executed in this run."
        ),
        "",
        "## Catalog Drift Breakdown",
        "",
        f"- Tables missing RLS enablement: {catalog_drift.get('summary', {}).get('rls_not_enabled_tables', 0)}",
        f"- Tables missing `FORCE RLS`: {catalog_drift.get('summary', {}).get('force_rls_not_enabled_tables', 0)}",
        f"- Tables missing a physical `tenant_id` column: {catalog_drift.get('summary', {}).get('tenant_id_column_missing_tables', 0)}",
        f"- Tables with policy-name drift: {catalog_drift.get('summary', {}).get('policy_mismatch_tables', 0)}",
        "",
        "## Live Cross-Tenant Exposure",
        "",
        f"- Failed sampled tables: {live_exposure.get('summary', {}).get('failed_table_count', 0)}",
    ]

    failed_assertion_counts = live_exposure.get("summary", {}).get("failed_assertion_counts", {}) or {}
    for assertion_name, assertion_count in sorted(
        failed_assertion_counts.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        lines.append(f"- `{assertion_name}` failed on {assertion_count} sampled tables")

    lines.extend(
        [
            "",
            "## Runtime Adoption Gaps",
            "",
            f"- Plain DB routes: {runtime_summary.get('plain_db_routes', 0)}",
            f"- Plain DB routes with tenant signal but no provable DB scoping: {runtime_summary.get('plain_db_routes_with_tenant_signal', 0)}",
            f"- Plain DB routes without visible tenant signal: {runtime_summary.get('plain_db_routes_without_tenant_signal', 0)}",
            f"- Review-required routes from control inventory: {len(runtime_adoption.get('review_required_preview', []))} shown, {sum(runtime_adoption.get('review_required_counts_by_service', {}).values())} total",
            "",
            "Top critical-route services:",
        ]
    )
    for line in top_services(runtime_adoption.get("critical_route_counts_by_service", {})):
        lines.append(f"- {line}")

    lines.extend(["", "Top review-required services:"])
    for line in top_services(runtime_adoption.get("review_required_counts_by_service", {})):
        lines.append(f"- {line}")

    lines.extend(
        [
            "",
            "Top review-required tenant-source patterns:",
        ]
    )
    for source, count in list(runtime_adoption.get("review_required_counts_by_tenant_source", {}).items())[:8]:
        lines.append(f"- {source}: {count}")

    lines.extend(
        [
            "",
            "## Recommended Remediation Order",
            "",
            "1. Restore live database RLS parity with the migration-derived contract. The current live target is materially behind the expected schema state.",
            "2. Resolve tables that are modeled as tenant-scoped in the contract but do not have a physical `tenant_id` column in the live database.",
            "3. Convert critical plain-session routes to tenant-scoped DB access or explicit tenant-context setters, then prove the change with the negative suite and live RLS stage.",
            "4. Review all header-, query-, and body-derived tenant selectors in the route control matrix, especially onboarding and IAM authorization surfaces.",
            "5. Re-run the `full` audit until live catalog drift is zero and sampled cross-tenant exposure is zero.",
            "",
            "## Artifact References",
            "",
            "- `rls-report/live-runtime-verification.json`",
            "- `rls-report/summary.json`",
            "- `rls-report/runtime-session-usage.json`",
            "- `control-matrix/review-queue.json`",
            "- `test-results/summary.json`",
            "- `logs/blocked-violations.json`",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> int:
    root = artifact_root()
    output_dir = root / "remediation"
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_json(root / "manifest.json", {})
    rls_summary = load_json(root / "rls-report" / "summary.json", {})
    live_runtime = load_json(root / "rls-report" / "live-runtime-verification.json", {})
    runtime_usage = load_json(root / "rls-report" / "runtime-session-usage.json", {})
    review_queue = load_json(root / "control-matrix" / "review-queue.json", {})
    test_summary = load_json(root / "test-results" / "summary.json", {})
    blocked_summary = load_json(root / "logs" / "blocked-violations.json", {})

    catalog_drift = summarize_catalog_drift(live_runtime if isinstance(live_runtime, dict) else {})
    live_exposure = summarize_live_exposure(live_runtime if isinstance(live_runtime, dict) else {})
    runtime_adoption = summarize_runtime_adoption(
        runtime_usage if isinstance(runtime_usage, dict) else {},
        review_queue if isinstance(review_queue, dict) else {},
    )

    summary = {
        "status": "failed"
        if (
            catalog_drift.get("summary", {}).get("mismatch_count", 0)
            or live_exposure.get("summary", {}).get("failed_table_count", 0)
            or runtime_adoption.get("summary", {}).get("critical_routes", 0)
        )
        else "passed",
        "catalog_drift": catalog_drift.get("summary", {}),
        "live_exposure": live_exposure.get("summary", {}),
        "runtime_adoption": {
            "plain_db_routes": runtime_adoption.get("summary", {}).get("plain_db_routes", 0),
            "plain_db_routes_without_tenant_signal": runtime_adoption.get("summary", {}).get(
                "plain_db_routes_without_tenant_signal",
                0,
            ),
            "critical_routes": runtime_adoption.get("summary", {}).get("critical_routes", 0),
            "review_required_routes": sum(runtime_adoption.get("review_required_counts_by_service", {}).values()),
        },
    }

    write_json(output_dir / "catalog-drift.json", catalog_drift)
    write_json(output_dir / "cross-tenant-exposure.json", live_exposure)
    write_json(output_dir / "runtime-adoption-gaps.json", runtime_adoption)
    write_json(output_dir / "summary.json", summary)
    (output_dir / "remediation-report.md").write_text(
        build_report_markdown(
            manifest if isinstance(manifest, dict) else {},
            rls_summary if isinstance(rls_summary, dict) else {},
            test_summary if isinstance(test_summary, dict) else {},
            blocked_summary if isinstance(blocked_summary, dict) else {},
            catalog_drift,
            live_exposure,
            runtime_adoption,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
