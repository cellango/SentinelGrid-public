"""Evidence repository API schemas."""

from __future__ import annotations

import base64
import binascii
import hashlib
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


EvidenceSensitivity = Literal["public", "internal", "confidential", "restricted"]
EvidenceItemReviewStatus = Literal[
    "pending",
    "ready_for_review",
    "accepted",
    "rejected",
    "needs_changes",
    "expired",
    "retired",
    "superseded",
]
EvidenceReviewDecision = Literal["accepted", "rejected", "needs_changes", "expired", "retired"]
EvidenceLinkType = Literal["supports", "contradicts", "context", "exception"]
EvidenceExportFormat = Literal["pdf", "zip", "csv"]
EvidenceRetentionSubject = Literal["evidence_item", "evidence_package", "evidence_export", "collection_task"]
EvidenceVerificationStatus = Literal["verified", "mismatch", "missing_observed_hash"]
EvidenceRecollectionReason = Literal["expired", "expiring_soon", "stale", "manual_refresh"]
EvidenceExportFinalizeStatus = Literal["completed", "failed"]


class EvidenceControlLinkRequest(BaseModel):
    control_id: str = Field(..., min_length=1)
    framework_id: str | None = None
    evidence_requirement_id: str | None = None
    package_id: str | None = None
    link_type: EvidenceLinkType = "supports"
    rationale: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceCreateRequest(BaseModel):
    tenant_id: str | None = None
    realm_name: str = "default"
    package_id: str | None = None
    evidence_type: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    source_system: str = Field(..., min_length=1, max_length=100)
    source_resource_id: str = Field(..., min_length=1)
    collector: str = Field(..., min_length=1)
    collection_method: str = Field(..., min_length=1, max_length=80)
    collected_at: datetime | None = None
    valid_from: datetime
    valid_until: datetime
    hash_sha256: str = Field(..., pattern=r"^[0-9a-fA-F]{64}$")
    storage_uri: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    sensitivity: EvidenceSensitivity = "internal"
    review_status: EvidenceItemReviewStatus = "pending"
    created_by: str | None = None
    control_links: list[EvidenceControlLinkRequest] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    integrity_metadata: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, max_length=255)

    @field_validator("valid_until")
    @classmethod
    def valid_until_after_valid_from(cls, value: datetime, info):
        valid_from = info.data.get("valid_from")
        if valid_from and value <= valid_from:
            raise ValueError("valid_until must be after valid_from")
        return value


class EvidenceHashRequest(BaseModel):
    content: str = Field(..., min_length=1)
    encoding: Literal["utf-8", "base64", "hex"] = "utf-8"

    def content_bytes(self) -> bytes:
        try:
            if self.encoding == "base64":
                return base64.b64decode(self.content, validate=True)
            if self.encoding == "hex":
                return bytes.fromhex(self.content)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Invalid encoded evidence content") from exc
        return self.content.encode("utf-8")


class EvidenceHashResponse(BaseModel):
    hash_algorithm: Literal["sha256"] = "sha256"
    hash_sha256: str
    byte_length: int

    @classmethod
    def from_request(cls, request: EvidenceHashRequest) -> "EvidenceHashResponse":
        content = request.content_bytes()
        return cls(hash_sha256=hashlib.sha256(content).hexdigest(), byte_length=len(content))


class EvidenceIntegrityVerificationRequest(BaseModel):
    tenant_id: str | None = None
    observed_hash_sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    verification_method: str = Field(default="hash_compare", max_length=80)
    verified_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceRetentionPolicyUpsertRequest(BaseModel):
    tenant_id: str | None = None
    framework_id: str | None = None
    subject_type: EvidenceRetentionSubject = "evidence_item"
    retention_days: int = Field(..., ge=1, le=3650)
    policy_name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    legal_hold: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceRecollectionTaskRequest(BaseModel):
    tenant_id: str | None = None
    reason: EvidenceRecollectionReason = "manual_refresh"
    due_at: datetime | None = None
    task_status: Literal["pending", "manual_evidence_required"] = "pending"
    requested_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceReviewRequest(BaseModel):
    tenant_id: str | None = None
    review_status: EvidenceReviewDecision
    reviewer: str | None = None
    review_notes: str | None = None
    rejection_reason: str | None = None
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceRetireRequest(BaseModel):
    tenant_id: str | None = None
    reason: str | None = None
    review_notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidencePackageCreateRequest(BaseModel):
    tenant_id: str | None = None
    realm_name: str = "default"
    package_name: str = Field(..., min_length=1, max_length=255)
    framework_id: str | None = None
    report_period_start: date
    report_period_end: date
    created_by: str | None = None
    package_type: str = Field(default="audit_package", max_length=80)
    summary: str | None = None
    description: str | None = None
    sensitivity: EvidenceSensitivity = "internal"
    metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_item_ids: list[str] = Field(default_factory=list)

    @field_validator("report_period_end")
    @classmethod
    def period_end_after_start(cls, value: date, info):
        period_start = info.data.get("report_period_start")
        if period_start and value < period_start:
            raise ValueError("report_period_end must be on or after report_period_start")
        return value


class EvidencePackageExportRequest(BaseModel):
    tenant_id: str | None = None
    export_format: EvidenceExportFormat
    requested_by: str | None = None
    include_sensitive: bool = False
    manifest: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceExportFinalizeRequest(BaseModel):
    tenant_id: str | None = None
    status: EvidenceExportFinalizeStatus
    storage_uri: str | None = None
    hash_sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    file_size_bytes: int | None = Field(default=None, ge=0)
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def completed_exports_require_integrity(self):
        if self.status == "completed" and (not self.storage_uri or not self.hash_sha256):
            raise ValueError("completed evidence exports require storage_uri and hash_sha256")
        return self


class EvidenceCollectionTaskCreateRequest(BaseModel):
    tenant_id: str | None = None
    realm_name: str = "default"
    package_id: str | None = None
    task_name: str = Field(..., min_length=1, max_length=255)
    task_type: str = Field(..., min_length=1, max_length=100)
    status: Literal[
        "pending",
        "running",
        "completed",
        "failed",
        "cancelled",
        "needs_connector",
        "manual_evidence_required",
    ] = "pending"
    source_system: str | None = Field(default=None, max_length=120)
    source_resource_id: str | None = None
    collector: str | None = None
    collection_method: str | None = Field(default=None, max_length=80)
    requested_by: str | None = None
    due_at: datetime | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, max_length=255)
