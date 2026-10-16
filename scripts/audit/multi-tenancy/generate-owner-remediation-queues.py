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


def slugify(value: str) -> str:
    return value.lower().replace(" ", "-").replace("_", "-")


def owner_label_from_service(service: str) -> str:
    return service.replace("_", " ").title()


def route_record(route: dict[str, object]) -> dict[str, object]:
    return {
        "service": route.get("service"),
        "file": route.get("path") or route.get("file"),
        "line": route.get("line"),
        "methods": route.get("methods", []),
        "route_path": route.get("route_path") or route.get("surface"),
        "risk_level": route.get("risk_level", route.get("status")),
        "risk_reason": route.get("risk_reason", ""),
        "tenant_sources": route.get("tenant_signals", route.get("tenant_sources", [])),
        "override_inputs": route.get("override_inputs", []),
        "source_ref": route.get("source_ref", ""),
        "handler": route.get("function_name") or route.get("handler"),
    }


def summarize_database_platform(
    catalog_drift: dict[str, object],
    cross_exposure: dict[str, object],
) -> dict[str, object]:
    summary = catalog_drift.get("summary", {}) or {}
    drift_groups = catalog_drift.get("groups", {}) or {}
    return {
        "owner_id": "database-platform",
        "owner_label": "Database Platform",
        "summary": {
            "catalog_mismatch_tables": summary.get("mismatch_count", 0),
            "rls_not_enabled_tables": summary.get("rls_not_enabled_tables", 0),
            "force_rls_not_enabled_tables": summary.get("force_rls_not_enabled_tables", 0),
            "tenant_id_column_missing_tables": summary.get("tenant_id_column_missing_tables", 0),
            "policy_mismatch_tables": summary.get("policy_mismatch_tables", 0),
            "sampled_exposure_tables": cross_exposure.get("summary", {}).get("failed_table_count", 0),
        },
        "workstreams": [
            {
                "type": "db_rls_parity",
                "priority": "p0",
                "description": "Apply the migration-derived RLS contract to the live database and verify RLS plus FORCE RLS are enabled.",
                "items": drift_groups.get("rls_not_enabled", [])[:50],
            },
            {
                "type": "db_force_rls_parity",
                "priority": "p0",
                "description": "Enable FORCE RLS on tables where the contract expects it.",
                "items": drift_groups.get("force_rls_not_enabled", [])[:50],
            },
            {
                "type": "db_schema_alignment",
                "priority": "p0",
                "description": "Resolve tenant-scoped tables that are missing a physical tenant_id column.",
                "items": drift_groups.get("tenant_id_column_missing", [])[:50],
            },
            {
                "type": "db_policy_alignment",
                "priority": "p1",
                "description": "Reconcile live policy names with the migration-derived contract.",
                "items": drift_groups.get("policy_mismatch", [])[:50],
            },
            {
                "type": "db_live_exposure",
                "priority": "p0",
                "description": "Eliminate sampled cross-tenant visibility from live seeded tables.",
                "items": cross_exposure.get("failed_tables", [])[:50],
            },
        ],
        "recommended_actions": [
            "Bring the live database to the same RLS state expected by the migration inventory before claiming tenant isolation.",
            "Resolve schema drift for tenant-scoped tables without tenant_id columns.",
            "Re-run the full audit after database fixes and require zero sampled cross-tenant exposure.",
        ],
    }


def summarize_service_owner(
    service: str,
    critical_routes: list[dict[str, object]],
    high_risk_routes: list[dict[str, object]],
    review_required_routes: list[dict[str, object]],
) -> dict[str, object]:
    owner_label = owner_label_from_service(service)
    review_source_counts = Counter(
        str(route.get("primary_tenant_source", "unknown"))
        for route in review_required_routes
    )
    return {
        "owner_id": slugify(service),
        "owner_label": owner_label,
        "service": service,
        "summary": {
            "critical_route_count": len(critical_routes),
            "high_risk_route_count": len(high_risk_routes),
            "review_required_route_count": len(review_required_routes),
            "review_required_tenant_source_counts": dict(
                sorted(review_source_counts.items(), key=lambda item: (-item[1], item[0]))
            ),
        },
        "workstreams": [
            {
                "type": "runtime_db_scoping",
                "priority": "p0" if critical_routes else "p1",
                "description": "Replace plain DB session usage with tenant-scoped DB access or explicit tenant context in critical routes.",
                "items": [route_record(route) for route in critical_routes[:50]],
            },
            {
                "type": "runtime_high_risk_cleanup",
                "priority": "p1",
                "description": "Burn down high-risk routes that still rely on plain DB access without provable tenant scoping.",
                "items": [route_record(route) for route in high_risk_routes[:50]],
            },
            {
                "type": "surface_access_review",
                "priority": "p0" if review_required_routes else "p2",
                "description": "Review public and internal tenant-selection surfaces and remove caller-controlled tenant overrides unless explicitly approved.",
                "items": review_required_routes[:50],
            },
        ],
        "recommended_actions": [
            "Eliminate plain get_db usage on critical routes first.",
            "Prefer tenant-derived identity context over caller-supplied tenant headers, query params, or body fields.",
            "Add or expand two-tenant denial tests for every route changed in this workstream.",
        ],
    }


def build_markdown(queue: dict[str, object]) -> str:
    summary = queue.get("summary", {}) or {}
    workstreams = queue.get("workstreams", []) or []
    lines = [
        f"# {queue.get('owner_label', 'Owner')} Remediation Queue",
        "",
        f"- Owner ID: {queue.get('owner_id', '')}",
    ]
    if queue.get("service"):
        lines.append(f"- Service: {queue.get('service')}")
    for key, value in summary.items():
        if isinstance(value, dict):
            continue
        lines.append(f"- {key.replace('_', ' ').title()}: {value}")
    nested_summary = summary.get("review_required_tenant_source_counts", {})
    if nested_summary:
        lines.extend(["", "## Review Source Counts", ""])
        for source, count in list(nested_summary.items())[:10]:
            lines.append(f"- {source}: {count}")
    lines.extend(["", "## Workstreams", ""])
    for workstream in workstreams:
        lines.append(
            f"- `{workstream.get('type', '')}` priority={workstream.get('priority', '')}: {workstream.get('description', '')} "
            f"({len(workstream.get('items', []))} preview items)"
        )
    recommendations = queue.get("recommended_actions", []) or []
    if recommendations:
        lines.extend(["", "## Recommended Actions", ""])
        for action in recommendations:
            lines.append(f"- {action}")
    return "\n".join(lines) + "\n"


def build_index_markdown(manifest: dict[str, object], queues: list[dict[str, object]]) -> str:
    lines = [
        "# Owner Remediation Queue Index",
        "",
        f"- Run ID: {manifest.get('run_id', '')}",
        f"- Environment: {manifest.get('environment', '')}",
        f"- Profile: {manifest.get('profile', '')}",
        f"- Git SHA: {manifest.get('git_sha', '')}",
        "",
        "## Queues",
        "",
    ]
    for queue in queues:
        summary = queue.get("summary", {}) or {}
        lines.append(
            f"- `{queue.get('owner_id', '')}` {queue.get('owner_label', '')}: "
            f"critical={summary.get('critical_route_count', 0)}, "
            f"high_risk={summary.get('high_risk_route_count', 0)}, "
            f"review_required={summary.get('review_required_route_count', 0)}, "
            f"catalog_mismatch={summary.get('catalog_mismatch_tables', 0)}, "
            f"sampled_exposure={summary.get('sampled_exposure_tables', 0)}"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    root = artifact_root()
    remediation_dir = root / "remediation"
    owner_dir = remediation_dir / "owner-queues"
    owner_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_json(root / "manifest.json", {})
    catalog_drift = load_json(remediation_dir / "catalog-drift.json", {"summary": {}, "groups": {}})
    cross_exposure = load_json(remediation_dir / "cross-tenant-exposure.json", {"summary": {}, "failed_tables": []})
    runtime_usage = load_json(root / "rls-report" / "runtime-session-usage.json", {"critical_routes": [], "high_risk_routes": []})
    review_queue = load_json(root / "control-matrix" / "review-queue.json", {"items": []})

    critical_by_service: dict[str, list[dict[str, object]]] = defaultdict(list)
    high_risk_by_service: dict[str, list[dict[str, object]]] = defaultdict(list)
    review_by_service: dict[str, list[dict[str, object]]] = defaultdict(list)

    for route in runtime_usage.get("critical_routes", []) or []:
        critical_by_service[str(route.get("service", "unknown"))].append(route)
    for route in runtime_usage.get("high_risk_routes", []) or []:
        high_risk_by_service[str(route.get("service", "unknown"))].append(route)
    for item in review_queue.get("items", []) or []:
        review_by_service[str(item.get("service", "unknown"))].append(item)

    queues: list[dict[str, object]] = [
        summarize_database_platform(catalog_drift, cross_exposure),
    ]

    all_services = sorted(set(critical_by_service) | set(high_risk_by_service) | set(review_by_service))
    for service in all_services:
        queue = summarize_service_owner(
            service,
            critical_by_service.get(service, []),
            high_risk_by_service.get(service, []),
            review_by_service.get(service, []),
        )
        summary = queue.get("summary", {}) or {}
        if not any(
            [
                summary.get("critical_route_count", 0),
                summary.get("high_risk_route_count", 0),
                summary.get("review_required_route_count", 0),
            ]
        ):
            continue
        queues.append(queue)

    queue_index = {
        "status": "generated",
        "queue_count": len(queues),
        "owners": [
            {
                "owner_id": queue.get("owner_id"),
                "owner_label": queue.get("owner_label"),
                "summary": queue.get("summary", {}),
            }
            for queue in queues
        ],
    }

    for queue in queues:
        owner_id = str(queue.get("owner_id"))
        write_json(owner_dir / f"{owner_id}.json", queue)
        (owner_dir / f"{owner_id}.md").write_text(build_markdown(queue))

    write_json(owner_dir / "index.json", queue_index)
    (owner_dir / "index.md").write_text(
        build_index_markdown(manifest if isinstance(manifest, dict) else {}, queues)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
