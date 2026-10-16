"""Database setup for CMDB Service."""

import os
import sys
from uuid import UUID

from fastapi import Depends, Query
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Add libs to path
libs_path = os.path.join(os.path.dirname(__file__), "../../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

from app.models import Base

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_tenant_db(tenant_id: str):
    """Yield a tenant-scoped session when PostgreSQL RLS variables are available."""
    db = SessionLocal()
    is_postgres = getattr(getattr(db.bind, "dialect", None), "name", "") == "postgresql"

    try:
        if is_postgres:
            db.execute(text("SET LOCAL app.current_tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            db.execute(text("SET LOCAL app.is_superadmin = 'false'"))
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        if is_postgres:
            try:
                db.execute(text("RESET app.current_tenant_id"))
                db.execute(text("RESET app.is_superadmin"))
            except Exception:
                pass
        db.close()


def resolve_query_tenant_id(
    tenant_id: UUID = Query(..., description="Tenant ID"),
) -> str:
    """Resolve the tenant scope for query-tenant routes."""
    return str(tenant_id)


def get_query_tenant_session(
    tenant_id: str = Depends(resolve_query_tenant_id),
):
    """Return a tenant-scoped DB session for query-tenant routes."""
    yield from get_tenant_db(tenant_id)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
