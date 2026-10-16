"""Generalized compliance coverage domain schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class CoverageStatus(str, Enum):
    NOT_STARTED = "not_started"
    NEEDS_EVIDENCE = "needs_evidence"
    PARTIALLY_SUPPORTED = "partially_supported"
    READY_FOR_REVIEW = "ready_for_review"
    ACCEPTED = "accepted"
    EXCEPTION = "exception"
    NOT_APPLICABLE = "not_applicable"


class CoverageSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ControlSignal(BaseModel):
    id: str
    source: str
    source_type: str
    title: str
    description: Optional[str] = None
    severity: Optional[CoverageSeverity] = None
    confidence: float = Field(default=1.0, ge=0, le=1)
    detected_at: Optional[datetime] = None
    href: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ControlGap(BaseModel):
    id: str
    control_id: str
    title: str
    description: Optional[str] = None
    severity: CoverageSeverity = CoverageSeverity.MEDIUM
    remediation_hint: Optional[str] = None
    source_signal_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceRequirementStatus(BaseModel):
    requirement_key: str
    title: str
    status: CoverageStatus = CoverageStatus.NOT_STARTED
    evidence_item_ids: list[str] = Field(default_factory=list)
    missing_reason: Optional[str] = None
    last_collected_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class ControlCoverage(BaseModel):
    tenant_id: str
    framework_id: str
    control_id: str
    title: str
    status: CoverageStatus = CoverageStatus.NOT_STARTED
    severity: Optional[CoverageSeverity] = None
    confidence: float = Field(default=0, ge=0, le=1)
    signals: list[ControlSignal] = Field(default_factory=list)
    gaps: list[ControlGap] = Field(default_factory=list)
    evidence_requirements: list[EvidenceRequirementStatus] = Field(default_factory=list)
    last_activity: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FrameworkCoverage(BaseModel):
    tenant_id: str
    framework_id: str
    status: CoverageStatus = CoverageStatus.NOT_STARTED
    controls: list[ControlCoverage] = Field(default_factory=list)
    status_counts: dict[str, int] = Field(default_factory=dict)
    average_confidence: float = Field(default=0, ge=0, le=1)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

