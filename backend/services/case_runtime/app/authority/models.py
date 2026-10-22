"""Paired with V018; application-owned records, never engine scheduling state."""

from sqlalchemy import (
    Column,
    Text,
    Integer,
    Boolean,
    DateTime,
    UniqueConstraint,
    ForeignKeyConstraint,
    CheckConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()
SCHEMA = "case_runtime"


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_cases_tenant_id"),
        CheckConstraint("revision > 0 AND plan_revision > 0", name="ck_cases_revision"),
        {"schema": SCHEMA},
    )
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    revision = Column(Integer, nullable=False, server_default=text("1"))
    plan_revision = Column(Integer, nullable=False, server_default=text("1"))
    policy_version = Column(Text, nullable=False)
    status = Column(Text, nullable=False, server_default=text("'open'"))
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class CaseAccessGrant(Base):
    __tablename__ = "case_access_grants"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "case_id"],
            ["case_runtime.cases.tenant_id", "case_runtime.cases.id"],
        ),
        UniqueConstraint(
            "tenant_id", "case_id", "subject_id", "permission", name="uq_case_grant"
        ),
        CheckConstraint(
            "permission IN ('propose','approve','execute','verify','read')",
            name="ck_case_grant_permission",
        ),
        {"schema": SCHEMA},
    )
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    case_id = Column(UUID(as_uuid=True), nullable=False)
    subject_id = Column(UUID(as_uuid=True), nullable=False)
    permission = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class ActionProposal(Base):
    __tablename__ = "action_proposals"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "case_id"],
            ["case_runtime.cases.tenant_id", "case_runtime.cases.id"],
        ),
        UniqueConstraint("tenant_id", "id", name="uq_proposal_tenant_id"),
        UniqueConstraint(
            "tenant_id",
            "id",
            "proposal_hash",
            "action_id",
            name="uq_proposal_action_binding",
        ),
        CheckConstraint(
            "octet_length(canonical_payload) <= 32768", name="ck_proposal_payload_bound"
        ),
        UniqueConstraint(
            "tenant_id", "id", "proposal_hash", name="uq_proposal_hash_binding"
        ),
        UniqueConstraint(
            "tenant_id",
            "action_id",
            "proposal_revision",
            name="uq_action_proposal_revision",
        ),
        UniqueConstraint(
            "tenant_id", "case_id", "request_key", name="uq_proposal_request"
        ),
        CheckConstraint(
            "proposal_revision > 0 AND case_revision > 0 AND plan_revision > 0",
            name="ck_proposal_revision",
        ),
        CheckConstraint(
            "proposal_hash ~ '^[a-f0-9]{64}$' AND request_hash ~ '^[a-f0-9]{64}$'",
            name="ck_proposal_hashes",
        ),
        {"schema": SCHEMA},
    )
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    case_id = Column(UUID(as_uuid=True), nullable=False)
    action_id = Column(UUID(as_uuid=True), nullable=False)
    proposal_revision = Column(Integer, nullable=False)
    case_revision = Column(Integer, nullable=False)
    plan_revision = Column(Integer, nullable=False)
    policy_version = Column(Text, nullable=False)
    tool_id = Column(Text, nullable=False)
    tool_version = Column(Text, nullable=False)
    proposed_by = Column(UUID(as_uuid=True), nullable=False)
    request_key = Column(UUID(as_uuid=True), nullable=False)
    request_hash = Column(Text, nullable=False)
    proposal_hash = Column(Text, nullable=False)
    canonical_payload = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "proposal_id", "proposal_hash"],
            [
                "case_runtime.action_proposals.tenant_id",
                "case_runtime.action_proposals.id",
                "case_runtime.action_proposals.proposal_hash",
            ],
        ),
        UniqueConstraint(
            "tenant_id", "proposal_id", name="uq_approval_request_proposal"
        ),
        {"schema": SCHEMA},
    )
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    proposal_id = Column(UUID(as_uuid=True), nullable=False)
    proposal_hash = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "proposal_id", "proposal_hash"],
            [
                "case_runtime.action_proposals.tenant_id",
                "case_runtime.action_proposals.id",
                "case_runtime.action_proposals.proposal_hash",
            ],
        ),
        UniqueConstraint(
            "tenant_id", "proposal_id", "sequence", name="uq_approval_sequence"
        ),
        UniqueConstraint(
            "tenant_id",
            "id",
            "proposal_id",
            "proposal_hash",
            name="uq_decision_hash_binding",
        ),
        CheckConstraint(
            "decision IN ('approve','reject','revoke') AND sequence > 0",
            name="ck_approval_decision",
        ),
        {"schema": SCHEMA},
    )
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    proposal_id = Column(UUID(as_uuid=True), nullable=False)
    proposal_hash = Column(Text, nullable=False)
    sequence = Column(Integer, nullable=False)
    decided_by = Column(UUID(as_uuid=True), nullable=False)
    decision = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class PolicyDecision(Base):
    __tablename__ = "policy_decisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "proposal_id", "proposal_hash"],
            [
                "case_runtime.action_proposals.tenant_id",
                "case_runtime.action_proposals.id",
                "case_runtime.action_proposals.proposal_hash",
            ],
        ),
        CheckConstraint(
            "decision IN ('allow','deny','approval_required')",
            name="ck_policy_decision",
        ),
        {"schema": SCHEMA},
    )
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    proposal_id = Column(UUID(as_uuid=True), nullable=False)
    actor_id = Column(UUID(as_uuid=True), nullable=False)
    policy_version = Column(Text, nullable=False)
    proposal_hash = Column(Text, nullable=False)
    decision = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ActionClaim(Base):
    __tablename__ = "action_claims"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "proposal_id", "proposal_hash", "action_id"],
            [
                "case_runtime.action_proposals.tenant_id",
                "case_runtime.action_proposals.id",
                "case_runtime.action_proposals.proposal_hash",
                "case_runtime.action_proposals.action_id",
            ],
        ),
        UniqueConstraint("tenant_id", "id", name="uq_claim_tenant_id"),
        ForeignKeyConstraint(
            ["tenant_id", "approval_id", "proposal_id", "proposal_hash"],
            [
                "case_runtime.approval_decisions.tenant_id",
                "case_runtime.approval_decisions.id",
                "case_runtime.approval_decisions.proposal_id",
                "case_runtime.approval_decisions.proposal_hash",
            ],
        ),
        UniqueConstraint("tenant_id", "action_id", name="uq_action_claim"),
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_effect_key"),
        {"schema": SCHEMA},
    )
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    proposal_id = Column(UUID(as_uuid=True), nullable=False)
    action_id = Column(UUID(as_uuid=True), nullable=False)
    actor_id = Column(UUID(as_uuid=True), nullable=False)
    approval_id = Column(UUID(as_uuid=True), nullable=False)
    proposal_hash = Column(Text, nullable=False)
    idempotency_key = Column(Text, nullable=False)
    resource_fences = Column(JSONB, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ResourceFence(Base):
    __tablename__ = "resource_fences"
    __table_args__ = (
        CheckConstraint("generation > 0", name="ck_resource_fence_generation"),
        {"schema": SCHEMA},
    )
    tenant_id = Column(UUID(as_uuid=True), primary_key=True)
    resource_key = Column(Text, primary_key=True)
    generation = Column(Integer, nullable=False)


class ActionAttempt(Base):
    __tablename__ = "action_attempts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "claim_id"],
            ["case_runtime.action_claims.tenant_id", "case_runtime.action_claims.id"],
        ),
        UniqueConstraint(
            "tenant_id", "claim_id", "attempt_number", name="uq_action_attempt"
        ),
        CheckConstraint("attempt_number > 0", name="ck_attempt_number"),
        {"schema": SCHEMA},
    )
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    claim_id = Column(UUID(as_uuid=True), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ActionReceipt(Base):
    __tablename__ = "action_receipts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "claim_id"],
            ["case_runtime.action_claims.tenant_id", "case_runtime.action_claims.id"],
        ),
        UniqueConstraint("tenant_id", "claim_id", name="uq_action_receipt"),
        CheckConstraint(
            "outcome IN ('executed','failed','ambiguous','unsupported','cancelled')",
            name="ck_receipt_outcome",
        ),
        {"schema": SCHEMA},
    )
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    claim_id = Column(UUID(as_uuid=True), nullable=False)
    outcome = Column(Text, nullable=False)
    provider_request_id = Column(Text)
    evidence_reference = Column(Text)
    simulated = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ActionVerification(Base):
    __tablename__ = "action_verifications"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "claim_id"],
            ["case_runtime.action_claims.tenant_id", "case_runtime.action_claims.id"],
        ),
        CheckConstraint(
            "outcome IN ('passed','failed','inconclusive')",
            name="ck_verification_outcome",
        ),
        {"schema": SCHEMA},
    )
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    claim_id = Column(UUID(as_uuid=True), nullable=False)
    verified_by = Column(UUID(as_uuid=True), nullable=False)
    outcome = Column(Text, nullable=False)
    evidence_reference = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        Index("ix_action_outbox_tenant_created", "tenant_id", "created_at"),
        {"schema": SCHEMA},
    )
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    aggregate_id = Column(UUID(as_uuid=True), nullable=False)
    event_type = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
