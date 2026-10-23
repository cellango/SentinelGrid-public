"""V019 storage-only metadata; deliberately separate from action role admission.

No API imports these models. Migrations grant no application access. Source and
manifest content is retained, not executed or treated as authorization.
"""

from sqlalchemy import (
    Column,
    Text,
    DateTime,
    CheckConstraint,
    UniqueConstraint,
    ForeignKeyConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
from app.authority.models import Case

Base = declarative_base()
SCHEMA = "case_runtime"


def bounded(name, size=256):
    return CheckConstraint(
        f"octet_length({name}) BETWEEN 1 AND {size}", name=f"ck_provenance_{name}_bound"
    )


class EvidenceReference(Base):
    __tablename__ = "evidence_references"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_evidence_tenant_id"),
        CheckConstraint(
            "id <> '00000000-0000-0000-0000-000000000000'::uuid AND tenant_id <> '00000000-0000-0000-0000-000000000000'::uuid",
            name="ck_evidence_non_nil",
        ),
        CheckConstraint(
            "(content_sha256 IS NOT NULL AND content_sha256 ~ '^[a-f0-9]{64}$' AND digest_unavailable_reason IS NULL) OR (content_sha256 IS NULL AND octet_length(digest_unavailable_reason) BETWEEN 1 AND 512)",
            name="ck_evidence_digest_or_reason",
        ),
        CheckConstraint(
            "content_sha256 IS NOT NULL OR digest_unavailable_reason IS NOT NULL",
            name="ck_evidence_digest_presence",
        ),
        CheckConstraint(
            "observed_at <= collected_at AND retain_until > collected_at",
            name="ck_evidence_times",
        ),
        bounded("source_type", 80),
        bounded("source_locator", 2048),
        bounded("source_version"),
        bounded("access_class", 80),
        bounded("custody_reference", 2048),
        {"schema": SCHEMA},
    )
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    source_type = Column(Text, nullable=False)
    source_locator = Column(Text, nullable=False)
    source_version = Column(Text, nullable=False)
    content_sha256 = Column(Text)
    digest_unavailable_reason = Column(Text)
    observed_at = Column(DateTime(timezone=True), nullable=False)
    collected_at = Column(DateTime(timezone=True), nullable=False)
    retain_until = Column(DateTime(timezone=True), nullable=False)
    access_class = Column(Text, nullable=False)
    custody_reference = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class CaseEvidenceLink(Base):
    __tablename__ = "case_evidence_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "case_id"], [Case.__table__.c.tenant_id, Case.__table__.c.id]
        ),
        ForeignKeyConstraint(
            ["tenant_id", "evidence_id"],
            [
                "case_runtime.evidence_references.tenant_id",
                "case_runtime.evidence_references.id",
            ],
        ),
        {"schema": SCHEMA},
    )
    tenant_id = Column(UUID(as_uuid=True), primary_key=True)
    case_id = Column(UUID(as_uuid=True), primary_key=True)
    evidence_id = Column(UUID(as_uuid=True), primary_key=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class RunManifest(Base):
    __tablename__ = "run_manifests"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "case_id"], [Case.__table__.c.tenant_id, Case.__table__.c.id]
        ),
        UniqueConstraint(
            "tenant_id", "case_id", "id", name="uq_manifest_tenant_case_run"
        ),
        UniqueConstraint(
            "tenant_id", "case_id", "request_key", name="uq_manifest_request"
        ),
        CheckConstraint(
            "id <> '00000000-0000-0000-0000-000000000000'::uuid AND request_key <> '00000000-0000-0000-0000-000000000000'::uuid AND initiated_by <> '00000000-0000-0000-0000-000000000000'::uuid",
            name="ck_manifest_non_nil",
        ),
        CheckConstraint(
            "mode IN ('recommendation_only','synthetic','live')",
            name="ck_manifest_mode",
        ),
        CheckConstraint(
            "schema_version = 'run-manifest-v1'", name="ck_manifest_schema"
        ),
        CheckConstraint(
            "octet_length(payload) BETWEEN 2 AND 262144 AND jsonb_typeof(payload::jsonb) = 'object'",
            name="ck_manifest_payload",
        ),
        CheckConstraint(
            "payload_sha256 = encode(sha256(convert_to(payload,'UTF8')),'hex')",
            name="ck_manifest_payload_digest",
        ),
        CheckConstraint(
            "payload::jsonb ? 'evidence_ids' AND jsonb_typeof(payload::jsonb->'evidence_ids') = 'array' AND jsonb_array_length(payload::jsonb->'evidence_ids') <= 256",
            name="ck_manifest_evidence_ids",
        ),
        *[
            bounded(n)
            for n in (
                "playbook_version",
                "selection_version",
                "skill_version",
                "model_version",
                "prompt_version",
                "toolset_version",
                "policy_version",
                "runtime_version",
            )
        ],
        bounded("trigger_reference", 2048),
        bounded("source_content_reference", 2048),
        {"schema": SCHEMA},
    )
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    case_id = Column(UUID(as_uuid=True), nullable=False)
    request_key = Column(UUID(as_uuid=True), nullable=False)
    initiated_by = Column(UUID(as_uuid=True), nullable=False)
    mode = Column(Text, nullable=False)
    schema_version = Column(Text, nullable=False)
    trigger_reference = Column(Text, nullable=False)
    source_content_reference = Column(Text, nullable=False)
    playbook_version = Column(Text, nullable=False)
    selection_version = Column(Text, nullable=False)
    skill_version = Column(Text, nullable=False)
    model_version = Column(Text, nullable=False)
    prompt_version = Column(Text, nullable=False)
    toolset_version = Column(Text, nullable=False)
    policy_version = Column(Text, nullable=False)
    runtime_version = Column(Text, nullable=False)
    payload = Column(Text, nullable=False)
    payload_sha256 = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class RunEvidenceLink(Base):
    __tablename__ = "run_evidence_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "case_id", "run_id"],
            [
                "case_runtime.run_manifests.tenant_id",
                "case_runtime.run_manifests.case_id",
                "case_runtime.run_manifests.id",
            ],
        ),
        ForeignKeyConstraint(
            ["tenant_id", "case_id", "evidence_id"],
            [
                "case_runtime.case_evidence_links.tenant_id",
                "case_runtime.case_evidence_links.case_id",
                "case_runtime.case_evidence_links.evidence_id",
            ],
        ),
        {"schema": SCHEMA},
    )
    tenant_id = Column(UUID(as_uuid=True), primary_key=True)
    case_id = Column(UUID(as_uuid=True), primary_key=True)
    run_id = Column(UUID(as_uuid=True), primary_key=True)
    evidence_id = Column(UUID(as_uuid=True), primary_key=True)
