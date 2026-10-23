"""Paired model for test-only V022; no runtime metadata registration."""
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class EffectivePolicy(Base):
    __tablename__ = "policies"
    __table_args__ = (CheckConstraint("approval_status IN ('pending', 'approved', 'rejected')", name="ck_policies_approval_status"), {"schema": "public"})
    id = Column(UUID, primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id = Column(UUID, nullable=False)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    policy_type = Column(String(100), nullable=False)
    scope = Column(String(100), nullable=False, server_default=text("'tenant'"))
    scope_id = Column(UUID)
    policy_data = Column(JSONB, nullable=False)
    is_active = Column(Boolean, server_default=text("true"))
    priority = Column(Integer, server_default=text("100"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    created_by = Column(Text)
    is_template = Column(Boolean, server_default=text("false"))
    approval_required = Column(Boolean, server_default=text("false"))
    approval_status = Column(Text, server_default=text("'approved'"))


class EffectivePolicyRule(Base):
    __tablename__ = "policy_rules"
    __table_args__ = {"schema": "public"}
    id = Column(UUID, primary_key=True, server_default=text("gen_random_uuid()"))
    policy_id = Column(UUID, ForeignKey("public.policies.id", name="qualification_policy_parent"), nullable=False)
    rule_id = Column(String(255), nullable=False)
    name = Column(String(255))
    description = Column(Text)
    conditions = Column(JSONB, nullable=False)
    actions = Column(JSONB, nullable=False)
    priority = Column(Integer, server_default=text("100"))
    is_active = Column(Boolean, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
