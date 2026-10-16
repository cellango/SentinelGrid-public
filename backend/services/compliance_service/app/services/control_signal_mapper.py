"""Generalized platform-signal to compliance-control coverage mapping."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, Optional

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))
from sg_core.models import Alert, IAMFinding, Playbook, PlaybookExecution, PostureFinding  # noqa: E402

from app.schemas.coverage import (
    ControlCoverage,
    ControlGap,
    ControlSignal,
    CoverageSeverity,
    CoverageStatus,
    FrameworkCoverage,
)
from app.services.coverage_domain import derive_control_status, most_severe, summarize_framework_coverage


SOC2_TITLES: Dict[str, str] = {
    "CC1.1": "Control Environment",
    "CC2.1": "Communication and Information",
    "CC3.1": "Risk Assessment",
    "CC4.1": "Monitoring Activities",
    "CC5.1": "Control Activities",
    "CC6.1": "Logical and Physical Access Controls",
    "CC7.1": "System Operations",
    "CC8.1": "Change Management",
    "CC9.1": "Risk Mitigation",
}

SEVERITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}

NIST_PREFIX_TO_SOC2 = {
    "AC": "CC6.1",
    "IA": "CC6.1",
    "PS": "CC6.1",
    "AU": "CC7.1",
    "IR": "CC7.1",
    "SI": "CC7.1",
    "CP": "CC7.1",
    "CM": "CC8.1",
    "SA": "CC8.1",
    "RA": "CC3.1",
    "CA": "CC4.1",
    "PM": "CC2.1",
    "PL": "CC2.1",
    "SC": "CC9.1",
    "MP": "CC9.1",
}

RESOLVED_FINDING_STATUSES = {"resolved", "accepted", "false_positive", "fixed", "closed"}


@dataclass
class ControlCoverageBucket:
    control_id: str
    title: str
    description: str
    open_findings: int = 0
    total_findings: int = 0
    signals: dict[str, ControlSignal] = field(default_factory=dict)
    gaps: dict[str, ControlGap] = field(default_factory=dict)
    key_detections: dict[str, dict[str, Any]] = field(default_factory=dict)
    control_checks: dict[str, dict[str, Any]] = field(default_factory=dict)
    supporting_playbooks: dict[str, dict[str, Any]] = field(default_factory=dict)
    mapped_nist_controls: set[str] = field(default_factory=set)
    playbook_execution_count: int = 0
    last_activity: Optional[datetime] = None


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_iterable(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _extract_soc2_ids(value: Any) -> list[str]:
    criteria: list[str] = []
    seen: set[str] = set()

    for entry in _normalize_iterable(value):
        if isinstance(entry, dict):
            criterion_id = _clean_text(entry.get("criterion_id") or entry.get("id"))
        else:
            criterion_id = _clean_text(entry)
        if not criterion_id or criterion_id in seen:
            continue
        seen.add(criterion_id)
        criteria.append(criterion_id)

    return criteria


def _extract_nist_controls(*values: Any) -> list[str]:
    controls: list[str] = []
    seen: set[str] = set()

    for value in values:
        for entry in _normalize_iterable(value):
            if isinstance(entry, dict):
                control = _clean_text(entry.get("control_id") or entry.get("id") or entry.get("value"))
            else:
                control = _clean_text(entry)
            if not control or control in seen:
                continue
            seen.add(control)
            controls.append(control)

    return controls


def _map_nist_controls_to_soc2(nist_controls: Iterable[str]) -> list[str]:
    criteria: list[str] = []
    seen: set[str] = set()

    for control in nist_controls:
        prefix = control.split("-", 1)[0].upper()
        criterion = NIST_PREFIX_TO_SOC2.get(prefix)
        if criterion and criterion not in seen:
            seen.add(criterion)
            criteria.append(criterion)

    return criteria


def _recommended_playbook_tokens(alert: Alert) -> list[str]:
    raw_payload = alert.raw_payload or {}
    tokens = [
        getattr(alert, "recommended_playbook_id", None),
        getattr(alert, "recommended_playbook", None),
        getattr(alert, "recommended_playbook_key", None),
        raw_payload.get("recommended_playbook_id"),
        raw_payload.get("recommended_playbook"),
        raw_payload.get("recommended_playbook_key"),
        raw_payload.get("playbook_id"),
        raw_payload.get("sg", {}).get("playbook_id") if isinstance(raw_payload.get("sg"), dict) else None,
    ]

    if isinstance(raw_payload.get("recommended_playbooks"), list):
        for item in raw_payload["recommended_playbooks"]:
            if isinstance(item, dict):
                tokens.extend([item.get("id"), item.get("key"), item.get("name")])
            else:
                tokens.append(item)

    results: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        text = _clean_text(token)
        if not text:
            continue
        normalized = text.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        results.append(normalized)
    return results


def _playbook_tokens(playbook: Playbook) -> list[str]:
    values = [
        getattr(playbook, "id", None),
        getattr(playbook, "name", None),
        getattr(playbook, "key", None),
        getattr(playbook, "playbook_key", None),
    ]
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean_text(value)
        if not text:
            continue
        normalized = text.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        results.append(normalized)
    return results


def _coverage_severity(value: Optional[str]) -> CoverageSeverity | None:
    normalized = (value or "").strip().lower()
    try:
        return CoverageSeverity(normalized)
    except ValueError:
        return None


def _severity_rank(value: Optional[str]) -> int:
    return SEVERITY_ORDER.get((value or "").lower(), 99)


def _iso(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return None


def _update_last_activity(current_value: Optional[datetime], *candidates: Any) -> Optional[datetime]:
    latest = current_value
    for candidate in candidates:
        if isinstance(candidate, datetime):
            if latest is None or candidate > latest:
                latest = candidate
    return latest


def _sort_items(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            _severity_rank(item.get("severity")),
            item.get("detected_at") or item.get("updated_at") or "",
            item.get("title") or item.get("id") or "",
        ),
    )


def _make_bucket(control_id: str) -> ControlCoverageBucket:
    title = SOC2_TITLES.get(control_id, control_id)
    return ControlCoverageBucket(
        control_id=control_id,
        title=title,
        description=SOC2_TITLES.get(control_id, "SOC 2 reporting criterion"),
    )


def _resolve_alert_criteria(
    alert: Alert,
    playbook_lookup: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str]]:
    raw_payload = alert.raw_payload or {}

    criteria = _extract_soc2_ids(raw_payload.get("soc2_criteria"))
    supporting_playbooks: list[str] = []

    for token in _recommended_playbook_tokens(alert):
        playbook_meta = playbook_lookup.get(token)
        if not playbook_meta:
            continue
        criteria.extend(playbook_meta["criteria"])
        supporting_playbooks.append(playbook_meta["playbook_id"])

    if not criteria:
        criteria.extend(
            _map_nist_controls_to_soc2(
                _extract_nist_controls(
                    alert.nist_controls,
                    raw_payload.get("nist_controls"),
                    raw_payload.get("control_tags"),
                )
            )
        )

    if not criteria:
        category_text = " ".join(
            filter(
                None,
                [
                    _clean_text(getattr(alert, "source", None)),
                    _clean_text(getattr(alert, "title", None)),
                    _clean_text(raw_payload.get("category")),
                    _clean_text(raw_payload.get("alert_type")),
                ],
            )
        ).lower()
        if any(token in category_text for token in ("identity", "login", "access", "mfa", "credential")):
            criteria.append("CC6.1")
        elif any(token in category_text for token in ("malware", "ransomware", "endpoint", "logging", "beacon")):
            criteria.append("CC7.1")
        elif any(token in category_text for token in ("cloud", "storage", "public", "database")):
            criteria.append("CC9.1")

    unique_criteria = []
    seen_criteria: set[str] = set()
    for criterion in criteria:
        if criterion in SOC2_TITLES and criterion not in seen_criteria:
            seen_criteria.add(criterion)
            unique_criteria.append(criterion)

    unique_playbooks = []
    seen_playbooks: set[str] = set()
    for playbook_id in supporting_playbooks:
        if playbook_id not in seen_playbooks:
            seen_playbooks.add(playbook_id)
            unique_playbooks.append(playbook_id)

    return unique_criteria, unique_playbooks


def _add_signal(bucket: ControlCoverageBucket, signal: ControlSignal) -> None:
    bucket.signals[signal.id] = signal


def _add_gap(bucket: ControlCoverageBucket, gap: ControlGap) -> None:
    bucket.gaps[gap.id] = gap


def _source_type_counter(signals: Iterable[ControlSignal]) -> Counter[str]:
    return Counter(signal.source_type for signal in signals)


def _confidence_for_status(status: CoverageStatus, signal_count: int, gap_count: int) -> float:
    base = {
        CoverageStatus.NOT_STARTED: 0.0,
        CoverageStatus.NEEDS_EVIDENCE: 0.25,
        CoverageStatus.PARTIALLY_SUPPORTED: 0.45,
        CoverageStatus.READY_FOR_REVIEW: 0.65,
        CoverageStatus.ACCEPTED: 0.9,
        CoverageStatus.EXCEPTION: 0.4,
        CoverageStatus.NOT_APPLICABLE: 0.8,
    }[status]
    signal_bump = min(signal_count * 0.03, 0.2)
    gap_penalty = min(gap_count * 0.05, 0.25)
    return round(max(0.0, min(1.0, base + signal_bump - gap_penalty)), 4)


def _trace_for_bucket(bucket: ControlCoverageBucket, status: CoverageStatus) -> list[str]:
    trace: list[str] = []
    source_counts = _source_type_counter(bucket.signals.values())
    if source_counts:
        trace.append(
            "Mapped signals: "
            + ", ".join(f"{source_type}={count}" for source_type, count in sorted(source_counts.items()))
        )
    if bucket.open_findings:
        trace.append(f"{bucket.open_findings} open finding(s) require remediation or reviewer acceptance.")
    if bucket.gaps:
        trace.append(f"{len(bucket.gaps)} coverage gap(s) remain before audit-ready evidence can be claimed.")
    if bucket.mapped_nist_controls:
        trace.append(f"Mapped NIST controls: {', '.join(sorted(bucket.mapped_nist_controls))}.")
    trace.append(f"Derived coverage status: {status.value}.")
    return trace


def _bucket_to_control_coverage(tenant_id: str, bucket: ControlCoverageBucket) -> ControlCoverage:
    signal_list = list(bucket.signals.values())
    gap_list = list(bucket.gaps.values())
    status = derive_control_status([], signal_count=len(signal_list), gap_count=len(gap_list))
    severity = most_severe([signal.severity for signal in signal_list] + [gap.severity for gap in gap_list])
    confidence = _confidence_for_status(status, signal_count=len(signal_list), gap_count=len(gap_list))
    trace = _trace_for_bucket(bucket, status)

    return ControlCoverage(
        tenant_id=tenant_id,
        framework_id="soc2",
        control_id=bucket.control_id,
        title=bucket.title,
        status=status,
        severity=severity,
        confidence=confidence,
        signals=signal_list,
        gaps=gap_list,
        last_activity=bucket.last_activity,
        metadata={
            "description": bucket.description,
            "open_findings": bucket.open_findings,
            "total_findings": bucket.total_findings,
            "mapped_nist_controls": sorted(bucket.mapped_nist_controls),
            "key_detections": _sort_items(bucket.key_detections.values()),
            "control_checks": _sort_items(bucket.control_checks.values()),
            "supporting_playbooks": sorted(
                bucket.supporting_playbooks.values(),
                key=lambda item: str(item.get("name") or "").lower(),
            ),
            "playbook_execution_count": bucket.playbook_execution_count,
            "trace": trace,
        },
    )


def build_soc2_framework_coverage(
    tenant_id: str,
    iam_rows: Iterable[IAMFinding],
    posture_rows: Iterable[PostureFinding],
    alerts: Iterable[Alert],
    playbooks: Iterable[Playbook],
    executions: Iterable[PlaybookExecution],
) -> FrameworkCoverage:
    buckets = {criterion_id: _make_bucket(criterion_id) for criterion_id in SOC2_TITLES}

    playbook_lookup: dict[str, dict[str, Any]] = {}
    playbooks_by_id: dict[str, dict[str, Any]] = {}

    for playbook in playbooks:
        criteria = _extract_soc2_ids(playbook.soc2_criteria)
        if not criteria:
            criteria = _map_nist_controls_to_soc2(_extract_nist_controls(playbook.nist_controls))

        playbook_name = playbook.name or playbook.playbook_key or playbook.key or str(playbook.id)
        playbook_meta = {
            "playbook_id": str(playbook.id),
            "criteria": criteria,
            "name": playbook_name,
            "key": playbook.playbook_key or playbook.key,
        }
        playbooks_by_id[str(playbook.id)] = playbook_meta

        for token in _playbook_tokens(playbook):
            playbook_lookup[token] = playbook_meta

        for criterion in criteria:
            bucket = buckets.get(criterion)
            if not bucket:
                continue
            bucket.supporting_playbooks[str(playbook.id)] = {
                "id": str(playbook.id),
                "name": playbook_name,
                "key": playbook.playbook_key or playbook.key,
                "href": f"/dashboard/playbooks/{playbook.id}/edit",
            }
            _add_signal(
                bucket,
                ControlSignal(
                    id=f"playbook:{playbook.id}",
                    source="playbook",
                    source_type="playbook",
                    title=playbook_name,
                    confidence=0.55,
                    href=f"/dashboard/playbooks/{playbook.id}/edit",
                    metadata={"key": playbook.playbook_key or playbook.key},
                ),
            )

    for row in iam_rows:
        criteria = _extract_soc2_ids(row.soc2_criteria)
        if not criteria and row.nist_control_id:
            criteria = _map_nist_controls_to_soc2([row.nist_control_id])

        check = {
            "id": str(row.id),
            "title": row.finding_type.replace("_", " ").title(),
            "description": row.description,
            "status": row.status,
            "severity": row.severity,
            "source_type": "iam_finding",
            "source_label": "IAM finding",
            "detected_at": _iso(row.detected_at),
            "href": "/dashboard/iam/access-reviews",
            "nist_control_id": row.nist_control_id,
        }

        for criterion in criteria:
            bucket = buckets.get(criterion)
            if not bucket:
                continue
            signal_id = f"iam_finding:{row.id}"
            bucket.total_findings += 1
            bucket.control_checks[str(row.id)] = check
            if row.nist_control_id:
                bucket.mapped_nist_controls.add(row.nist_control_id)
            bucket.last_activity = _update_last_activity(bucket.last_activity, row.updated_at, row.detected_at)
            _add_signal(
                bucket,
                ControlSignal(
                    id=signal_id,
                    source="iam",
                    source_type="iam_finding",
                    title=check["title"],
                    description=row.description,
                    severity=_coverage_severity(row.severity),
                    confidence=0.65,
                    detected_at=row.detected_at,
                    href="/dashboard/iam/access-reviews",
                    metadata={"status": row.status, "nist_control_id": row.nist_control_id},
                ),
            )
            if (row.status or "").lower() not in RESOLVED_FINDING_STATUSES:
                bucket.open_findings += 1
                _add_gap(
                    bucket,
                    ControlGap(
                        id=f"iam_finding_gap:{row.id}",
                        control_id=criterion,
                        title=check["title"],
                        description=row.description,
                        severity=_coverage_severity(row.severity) or CoverageSeverity.MEDIUM,
                        remediation_hint=row.recommendation,
                        source_signal_ids=[signal_id],
                    ),
                )

    for row in posture_rows:
        criteria = _extract_soc2_ids(row.soc2_criteria)
        if not criteria and row.nist_control_id:
            criteria = _map_nist_controls_to_soc2([row.nist_control_id])

        title = row.title or row.check_id or "Control check"
        check = {
            "id": str(row.id),
            "title": title,
            "description": row.description,
            "status": row.status,
            "severity": row.severity,
            "source_type": "posture_finding",
            "source_label": "Control check",
            "detected_at": _iso(row.detected_at),
            "href": "/dashboard/posture",
            "nist_control_id": row.nist_control_id,
        }

        for criterion in criteria:
            bucket = buckets.get(criterion)
            if not bucket:
                continue
            signal_id = f"posture_finding:{row.id}"
            bucket.total_findings += 1
            bucket.control_checks[str(row.id)] = check
            if row.nist_control_id:
                bucket.mapped_nist_controls.add(row.nist_control_id)
            bucket.last_activity = _update_last_activity(bucket.last_activity, row.updated_at, row.detected_at)
            _add_signal(
                bucket,
                ControlSignal(
                    id=signal_id,
                    source="posture",
                    source_type="posture_finding",
                    title=title,
                    description=row.description,
                    severity=_coverage_severity(row.severity),
                    confidence=0.65,
                    detected_at=row.detected_at,
                    href="/dashboard/posture",
                    metadata={"status": row.status, "nist_control_id": row.nist_control_id},
                ),
            )
            if (row.status or "").lower() not in RESOLVED_FINDING_STATUSES:
                bucket.open_findings += 1
                _add_gap(
                    bucket,
                    ControlGap(
                        id=f"posture_finding_gap:{row.id}",
                        control_id=criterion,
                        title=title,
                        description=row.description,
                        severity=_coverage_severity(row.severity) or CoverageSeverity.MEDIUM,
                        remediation_hint=row.remediation,
                        source_signal_ids=[signal_id],
                    ),
                )

    for alert in alerts:
        criteria, supporting_playbooks = _resolve_alert_criteria(alert, playbook_lookup)
        detection = {
            "id": str(alert.id),
            "title": alert.title,
            "severity": (alert.raw_severity or "medium").lower(),
            "status": alert.status,
            "source": alert.source,
            "detection_rule_id": (alert.raw_payload or {}).get("detection_rule_id"),
            "recommended_playbook": next(iter(supporting_playbooks), None),
            "detected_at": _iso(alert.detection_time),
            "href": f"/dashboard/alerts/{alert.id}",
        }
        nist_controls = _extract_nist_controls(alert.nist_controls, (alert.raw_payload or {}).get("nist_controls"))

        for criterion in criteria:
            bucket = buckets.get(criterion)
            if not bucket:
                continue
            bucket.key_detections[str(alert.id)] = detection
            bucket.mapped_nist_controls.update(nist_controls)
            for playbook_id in supporting_playbooks:
                if playbook_id in playbooks_by_id:
                    playbook_meta = playbooks_by_id[playbook_id]
                    bucket.supporting_playbooks[playbook_id] = {
                        "id": playbook_id,
                        "name": playbook_meta["name"],
                        "key": playbook_meta["key"],
                        "href": f"/dashboard/playbooks/{playbook_id}/edit",
                    }
            bucket.last_activity = _update_last_activity(bucket.last_activity, alert.updated_at, alert.detection_time)
            _add_signal(
                bucket,
                ControlSignal(
                    id=f"alert:{alert.id}",
                    source=alert.source,
                    source_type="alert",
                    title=alert.title,
                    description=alert.description,
                    severity=_coverage_severity(alert.raw_severity or "medium"),
                    confidence=0.6,
                    detected_at=alert.detection_time,
                    href=f"/dashboard/alerts/{alert.id}",
                    metadata={"status": alert.status, "detection_rule_id": detection["detection_rule_id"]},
                ),
            )

    for execution in executions:
        playbook_meta = playbooks_by_id.get(str(execution.playbook_id))
        if not playbook_meta:
            continue
        status = (execution.status or "").lower()
        confidence = 0.75 if status in {"completed", "success", "succeeded"} else 0.55
        for criterion in playbook_meta["criteria"]:
            bucket = buckets.get(criterion)
            if not bucket:
                continue
            bucket.playbook_execution_count += 1
            bucket.last_activity = _update_last_activity(
                bucket.last_activity,
                execution.updated_at,
                execution.finished_at,
                execution.started_at,
                execution.created_at,
            )
            _add_signal(
                bucket,
                ControlSignal(
                    id=f"playbook_execution:{execution.id}",
                    source="playbook",
                    source_type="playbook_execution",
                    title=f"{playbook_meta['name']} execution",
                    description=execution.result_summary,
                    confidence=confidence,
                    detected_at=execution.finished_at or execution.started_at or execution.created_at,
                    href=f"/dashboard/playbooks/{execution.playbook_id}/executions/{execution.id}",
                    metadata={
                        "status": execution.status,
                        "approval_status": execution.approval_status,
                        "playbook_id": str(execution.playbook_id),
                    },
                ),
            )

    controls = [_bucket_to_control_coverage(tenant_id, bucket) for bucket in buckets.values()]
    return summarize_framework_coverage(tenant_id=tenant_id, framework_id="soc2", controls=controls)


def _legacy_status(status: CoverageStatus) -> str:
    if status in {CoverageStatus.ACCEPTED, CoverageStatus.READY_FOR_REVIEW, CoverageStatus.NOT_APPLICABLE}:
        return "compliant"
    if status == CoverageStatus.NOT_STARTED:
        return "not_assessed"
    return "partial"


def _control_to_legacy_payload(control: ControlCoverage) -> dict[str, Any]:
    metadata = control.metadata
    detections = metadata.get("key_detections", [])
    checks = metadata.get("control_checks", [])
    playbook_items = metadata.get("supporting_playbooks", [])
    playbook_execution_count = int(metadata.get("playbook_execution_count", 0) or 0)
    evidence_items = len(detections) + len(checks) + len(playbook_items) + playbook_execution_count

    return {
        "id": control.control_id,
        "title": control.title,
        "description": metadata.get("description") or control.title,
        "status": _legacy_status(control.status),
        "coverage_status": control.status.value,
        "coverage_confidence": control.confidence,
        "coverage_severity": control.severity.value if control.severity else None,
        "coverage_trace": metadata.get("trace", []),
        "coverage_gaps": [gap.model_dump(mode="json") for gap in control.gaps],
        "open_findings": int(metadata.get("open_findings", 0) or 0),
        "total_findings": int(metadata.get("total_findings", 0) or 0),
        "detection_count": len(detections),
        "control_check_count": len(checks),
        "playbook_count": len(playbook_items),
        "playbook_execution_count": playbook_execution_count,
        "evidence_items": evidence_items,
        "mapped_nist_controls": metadata.get("mapped_nist_controls", []),
        "key_detections": detections[:4],
        "control_checks": checks[:4],
        "supporting_playbooks": playbook_items[:4],
        "last_activity": _iso(control.last_activity),
    }


def build_soc2_legacy_coverage_payload(
    tenant_id: str,
    iam_rows: Iterable[IAMFinding],
    posture_rows: Iterable[PostureFinding],
    alerts: Iterable[Alert],
    playbooks: Iterable[Playbook],
    executions: Iterable[PlaybookExecution],
) -> Dict[str, Any]:
    framework_coverage = build_soc2_framework_coverage(
        tenant_id=tenant_id,
        iam_rows=iam_rows,
        posture_rows=posture_rows,
        alerts=alerts,
        playbooks=playbooks,
        executions=executions,
    )

    finalized_controls = [_control_to_legacy_payload(control) for control in framework_coverage.controls]
    finalized_controls.sort(
        key=lambda item: (
            0
            if item["status"] == "non_compliant"
            else 1
            if item["status"] == "partial"
            else 2
            if item["status"] == "not_assessed"
            else 3,
            -item["open_findings"],
            item["id"],
        )
    )

    all_detection_items: dict[str, dict[str, Any]] = {}
    all_control_checks: dict[str, dict[str, Any]] = {}
    all_playbooks: dict[str, dict[str, Any]] = {}
    total_playbook_executions = 0
    source_counter: Counter[str] = Counter()

    for control in framework_coverage.controls:
        metadata = control.metadata
        for item in metadata.get("key_detections", []):
            all_detection_items[item["id"]] = item
            source_counter[item.get("source") or "unknown"] += 1
        for item in metadata.get("control_checks", []):
            all_control_checks[item["id"]] = item
        for item in metadata.get("supporting_playbooks", []):
            all_playbooks[item["id"]] = item
        total_playbook_executions += int(metadata.get("playbook_execution_count", 0) or 0)

    criteria_ready = sum(1 for item in finalized_controls if item["status"] == "compliant")
    criteria_partial = sum(1 for item in finalized_controls if item["status"] == "partial")
    criteria_not_assessed = sum(1 for item in finalized_controls if item["status"] == "not_assessed")
    criteria_needing_attention = len(finalized_controls) - criteria_ready - criteria_not_assessed
    total_controls = len(finalized_controls)
    overall_score = (
        round(
            ((criteria_ready * 1.0) + (criteria_partial * 0.6)) / total_controls * 100,
            1,
        )
        if total_controls
        else 0.0
    )

    all_detections = _sort_items(all_detection_items.values())[:8]
    all_checks = _sort_items(all_control_checks.values())[:8]
    evidence_items = len(all_detection_items) + len(all_control_checks) + len(all_playbooks) + total_playbook_executions

    last_assessment = max(
        (item["last_activity"] for item in finalized_controls if item.get("last_activity")),
        default=None,
    )

    summary = {
        "tenant_id": tenant_id,
        "total_criteria": total_controls,
        "open_criteria": sum(1 for item in finalized_controls if item["open_findings"] > 0),
        "total_findings": sum(item["total_findings"] for item in finalized_controls),
        "open_findings": sum(item["open_findings"] for item in finalized_controls),
        "status": "compliant" if criteria_needing_attention == 0 and criteria_not_assessed == 0 else "non_compliant",
        "mapped_detections": len(all_detection_items),
        "control_checks": len(all_control_checks),
        "playbooks": len(all_playbooks),
        "automated_responses": total_playbook_executions,
        "evidence_items": evidence_items,
        "last_assessment": last_assessment,
    }

    reporting_summary = {
        "criteria_ready": criteria_ready,
        "criteria_partial": criteria_partial,
        "criteria_needing_attention": criteria_needing_attention,
        "criteria_not_assessed": criteria_not_assessed,
        "key_detection_count": len(all_detection_items),
        "control_check_count": len(all_control_checks),
        "playbook_count": len(all_playbooks),
        "playbook_execution_count": total_playbook_executions,
        "reportable_evidence_items": evidence_items,
        "top_detection_sources": [
            {"source": source, "count": count}
            for source, count in source_counter.most_common(5)
        ],
    }

    return {
        "summary": summary,
        "controls": finalized_controls,
        "status": summary["status"],
        "reporting_summary": reporting_summary,
        "key_detections": all_detections,
        "control_checks": all_checks,
        "overall_score": overall_score,
        "coverage_model": {
            "framework_id": framework_coverage.framework_id,
            "status": framework_coverage.status.value,
            "status_counts": framework_coverage.status_counts,
            "average_confidence": framework_coverage.average_confidence,
            "generated_at": framework_coverage.generated_at.isoformat(),
        },
    }
