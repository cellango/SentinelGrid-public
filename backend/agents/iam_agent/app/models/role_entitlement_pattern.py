"""IAM V1 role definitions, with V016's explicit opt-in and actor provenance."""

import uuid
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    UniqueConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base


class RoleEntitlementPattern(Base):
    __tablename__ = "role_entitlement_patterns"
    __table_args__ = (
        UniqueConstraint(
            "role_name", "tenant_id", "entitlement_pattern", name="unique_role_pattern"
        ),
        {"schema": "public"},
    )
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    role_name = Column(String(100), nullable=False)
    tenant_id = Column(UUID(as_uuid=True))
    entitlement_pattern = Column(String(500), nullable=False)
    priority = Column(Integer, default=0, server_default=text("0"))
    enabled = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    auto_grant = Column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_by = Column(UUID(as_uuid=True))
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_role_patterns_role",
    RoleEntitlementPattern.role_name,
    RoleEntitlementPattern.enabled,
)
Index(
    "idx_role_patterns_tenant",
    RoleEntitlementPattern.tenant_id,
    postgresql_where=RoleEntitlementPattern.tenant_id.is_not(None),
)
