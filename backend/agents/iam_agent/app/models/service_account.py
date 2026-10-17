"""IAM-local identity registry; not a Keycloak client or an API permission grant."""

import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    UniqueConstraint,
    CheckConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class ServiceAccount(Base):
    __tablename__ = "iam_service_accounts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="iam_service_account_name"),
        UniqueConstraint("client_id", name="iam_service_account_client"),
        CheckConstraint(
            "status IN ('active','inactive','deleted')",
            name="iam_service_account_status",
        ),
        CheckConstraint(
            "rotation_days BETWEEN 1 AND 365", name="iam_service_account_rotation"
        ),
        CheckConstraint("credential_version >= 1", name="iam_service_account_version"),
        CheckConstraint(
            "(status='active' AND secret_hash IS NOT NULL AND secret_hash ~ '^[0-9a-f]{64}$' AND credential_expires_at IS NOT NULL) OR (status IN ('inactive','deleted') AND secret_hash IS NULL AND credential_expires_at IS NULL)",
            name="iam_service_account_credential",
        ),
        {"schema": "public"},
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    client_id = Column(String(40), nullable=False)
    owner_user_id = Column(UUID(as_uuid=True), nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String(20), nullable=False, server_default="active")
    rotation_days = Column(Integer, nullable=False, server_default="90")
    credential_version = Column(Integer, nullable=False, server_default="1")
    secret_hash = Column(String(64))
    credential_expires_at = Column(DateTime(timezone=True))
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
    "ix_iam_service_account_expiry",
    ServiceAccount.tenant_id,
    ServiceAccount.status,
    ServiceAccount.credential_expires_at,
)
