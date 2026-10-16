"""Helpers for generalized compliance coverage status semantics."""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from app.schemas.coverage import (
    ControlCoverage,
    CoverageSeverity,
    CoverageStatus,
    EvidenceRequirementStatus,
    FrameworkCoverage,
)


LEGACY_STATUS_TO_COVERAGE_STATUS = {
    "compliant": CoverageStatus.ACCEPTED,
    "implemented": CoverageStatus.ACCEPTED,
    "accepted": CoverageStatus.ACCEPTED,
    "partial": CoverageStatus.PARTIALLY_SUPPORTED,
    "partially": CoverageStatus.PARTIALLY_SUPPORTED,
    "partially_supported": CoverageStatus.PARTIALLY_SUPPORTED,
    "non_compliant": CoverageStatus.NEEDS_EVIDENCE,
    "not_implemented": CoverageStatus.NEEDS_EVIDENCE,
    "not_assessed": CoverageStatus.NOT_STARTED,
    "unknown": CoverageStatus.NOT_STARTED,
    "not_applicable": CoverageStatus.NOT_APPLICABLE,
    "exception": CoverageStatus.EXCEPTION,
}

SEVERITY_RANK = {
    CoverageSeverity.CRITICAL: 0,
    CoverageSeverity.HIGH: 1,
    CoverageSeverity.MEDIUM: 2,
    CoverageSeverity.LOW: 3,
    CoverageSeverity.INFO: 4,
}


def normalize_coverage_status(value: str | CoverageStatus | None) -> CoverageStatus:
    if isinstance(value, CoverageStatus):
        return value
    normalized = (value or "").strip().lower()
    return LEGACY_STATUS_TO_COVERAGE_STATUS.get(normalized, CoverageStatus.NOT_STARTED)


def most_severe(values: Iterable[CoverageSeverity | None]) -> CoverageSeverity | None:
    severities = [value for value in values if value is not None]
    if not severities:
        return None
    return sorted(severities, key=lambda value: SEVERITY_RANK[value])[0]


def derive_control_status(
    evidence_requirements: Iterable[EvidenceRequirementStatus],
    signal_count: int = 0,
    gap_count: int = 0,
    explicit_status: CoverageStatus | None = None,
) -> CoverageStatus:
    if explicit_status in {CoverageStatus.EXCEPTION, CoverageStatus.NOT_APPLICABLE}:
        return explicit_status

    requirements = list(evidence_requirements)
    if gap_count > 0 and signal_count > 0:
        return CoverageStatus.PARTIALLY_SUPPORTED
    if gap_count > 0:
        return CoverageStatus.NEEDS_EVIDENCE
    if not requirements:
        return CoverageStatus.READY_FOR_REVIEW if signal_count > 0 else CoverageStatus.NOT_STARTED

    statuses = [item.status for item in requirements]
    if any(status == CoverageStatus.NEEDS_EVIDENCE for status in statuses):
        return CoverageStatus.NEEDS_EVIDENCE
    if any(status == CoverageStatus.PARTIALLY_SUPPORTED for status in statuses):
        return CoverageStatus.PARTIALLY_SUPPORTED
    if all(status in {CoverageStatus.ACCEPTED, CoverageStatus.NOT_APPLICABLE} for status in statuses):
        return CoverageStatus.ACCEPTED
    if all(status == CoverageStatus.READY_FOR_REVIEW for status in statuses):
        return CoverageStatus.READY_FOR_REVIEW
    if any(status == CoverageStatus.READY_FOR_REVIEW for status in statuses):
        return CoverageStatus.PARTIALLY_SUPPORTED
    return CoverageStatus.NOT_STARTED


def summarize_framework_coverage(
    tenant_id: str,
    framework_id: str,
    controls: Iterable[ControlCoverage],
) -> FrameworkCoverage:
    control_list = list(controls)
    counts = Counter(control.status.value for control in control_list)
    accepted_count = counts[CoverageStatus.ACCEPTED.value] + counts[CoverageStatus.NOT_APPLICABLE.value]

    if not control_list:
        framework_status = CoverageStatus.NOT_STARTED
        average_confidence = 0.0
    else:
        average_confidence = round(
            sum(control.confidence for control in control_list) / len(control_list),
            4,
        )
        if accepted_count == len(control_list):
            framework_status = CoverageStatus.ACCEPTED
        elif counts[CoverageStatus.NEEDS_EVIDENCE.value] > 0:
            framework_status = CoverageStatus.NEEDS_EVIDENCE
        elif counts[CoverageStatus.PARTIALLY_SUPPORTED.value] > 0:
            framework_status = CoverageStatus.PARTIALLY_SUPPORTED
        elif counts[CoverageStatus.READY_FOR_REVIEW.value] > 0:
            framework_status = CoverageStatus.READY_FOR_REVIEW
        else:
            framework_status = CoverageStatus.NOT_STARTED

    return FrameworkCoverage(
        tenant_id=tenant_id,
        framework_id=framework_id,
        status=framework_status,
        controls=control_list,
        status_counts=dict(counts),
        average_confidence=average_confidence,
    )
