"""Verified SOAR read sessions; legacy UUID and runtime DDL entrypoints deny."""

from typing import Generator

from fastapi import Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import get_current_tenant
from sg_core.tenant_session import tenant_session, install_tenant_pool_reset

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,  # Set to True for SQL query logging
)

install_tenant_pool_reset(engine)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import Base from database module to ensure models are registered
from app.database import Base


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_tenant_db(tenant_id) -> Generator[Session, None, None]:
    """Legacy raw-UUID entrypoint cannot establish workload request authority."""
    raise HTTPException(503, "Owned SOAR workload context required")
    yield  # Keep the dependency generator shape without opening a session.


def get_tenant_session(
    tenant_id=Depends(get_current_tenant),
) -> Generator[Session, None, None]:
    """Tenant-scoped session wrapper for route-level isolation enforcement."""
    try:
        with tenant_session(SessionLocal, tenant_id) as db:
            yield db
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "Owned playbook store unavailable") from None


def init_db():
    """Legacy initializer: schema changes require the owned Flyway profile."""
    raise RuntimeError("SOAR schema setup requires a reviewed Flyway profile")
