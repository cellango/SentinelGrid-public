"""Database configuration for Email Ingestion Service."""

import sys
import os
from uuid import UUID

from fastapi import Depends, Query
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

# Add libs to path
libs_path = os.path.join(os.path.dirname(__file__), "../../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

from sg_core.db import Base, get_tenant_db
from sg_core.models import PhishingReport, PhishingObservable
from app.core.config import settings

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,
    echo=settings.DEBUG_MODE
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
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
    # Import all models to ensure they're registered
    from sg_core.models import PhishingReport, PhishingObservable
    
    # Create tables
    Base.metadata.create_all(bind=engine)
