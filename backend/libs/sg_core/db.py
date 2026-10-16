"""Database session management and utilities.

Provides plain sessions (get_db) and tenant-scoped sessions (get_tenant_db,
get_tenant_session) that set PostgreSQL session variables so Row-Level Security
policies can enforce tenant isolation transparently.
"""

from __future__ import annotations

from typing import Generator
from sqlalchemy import create_engine
from sg_core.tenant_session import install_tenant_pool_reset, tenant_session
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Depends
import logging
import os

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database URL from environment
# ---------------------------------------------------------------------------
DB_URL = os.getenv("DB_URL", "postgresql://sg:sg@localhost:5432/sg")

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
engine = create_engine(
    DB_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=40,
    echo=os.getenv("LOG_LEVEL", "INFO") == "DEBUG",
)


# ---------------------------------------------------------------------------
# Safety: reset tenant context on every pool checkout
# ---------------------------------------------------------------------------
install_tenant_pool_reset(engine)


# ---------------------------------------------------------------------------
# ORM Base
# ---------------------------------------------------------------------------
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Plain session (no tenant context) -- backward compatible
# ---------------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get a database session **without** tenant context.

    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tenant-scoped session
# ---------------------------------------------------------------------------
def get_tenant_db(tenant_id: str) -> Generator[Session, None, None]:
    """
    Yield a database session with ``app.current_tenant_id`` set for RLS.

    Uses transaction-local ``set_config`` on every transaction, including those
    after commit/rollback. Pool checkout resets prior session-level residue.

    Args:
        tenant_id: UUID string of the tenant. Must not be empty.
    """
    with tenant_session(SessionLocal, tenant_id) as db:
        yield db


def get_superadmin_db() -> Generator[Session, None, None]:
    """Legacy name retained; a caller-controlled session flag is not admin authority."""
    raise PermissionError("Cross-tenant operations require a separately provisioned operational role")
    yield  # Preserve the dependency's generator interface without opening a session.


# ---------------------------------------------------------------------------
# FastAPI dependency: tenant session derived from auth token
# ---------------------------------------------------------------------------
def _resolve_get_current_tenant():
    """Lazy import to avoid circular dependency between db and security modules."""
    from sg_core.security import get_current_tenant
    return get_current_tenant


def get_tenant_session(
    tenant_id: str = Depends(_resolve_get_current_tenant()),
) -> Generator[Session, None, None]:
    """
    FastAPI dependency that combines authentication with a tenant-scoped DB
    session.  Routes can simply declare::

        def my_endpoint(db: Session = Depends(get_tenant_session)):
            # RLS is automatically active for the authenticated tenant
            ...
    """
    yield from get_tenant_db(tenant_id)
