"""Database session management and utilities.

Provides plain sessions (get_db) and tenant-scoped sessions (get_tenant_db,
get_tenant_session) that set PostgreSQL session variables so Row-Level Security
policies can enforce tenant isolation transparently.
"""

from __future__ import annotations

from typing import Generator
from sqlalchemy import create_engine, event, text
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
# Safety: reset tenant context on every new physical connection
# ---------------------------------------------------------------------------
@event.listens_for(engine, "connect")
def _reset_tenant_on_connect(dbapi_connection, connection_record):
    """Clear tenant session variables when a new connection is created."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SET app.current_tenant_id = ''")
        cursor.execute("SET app.is_superadmin = 'false'")
    finally:
        cursor.close()


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

    Uses ``SET LOCAL`` so the setting is scoped to the current transaction and
    automatically cleared on commit / rollback.

    Args:
        tenant_id: UUID string of the tenant. Must not be empty.
    """
    if not tenant_id:
        raise ValueError("tenant_id must not be empty for get_tenant_db")

    db = SessionLocal()
    try:
        # SET LOCAL is transaction-scoped -- perfect for RLS
        db.execute(text("SET LOCAL app.current_tenant_id = :tid"), {"tid": tenant_id})
        db.execute(text("SET LOCAL app.is_superadmin = 'false'"))
        logger.debug("RLS context set: tenant_id=%s, is_superadmin=false", tenant_id)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        # Belt-and-suspenders: clear even though SET LOCAL auto-resets on
        # transaction end, this guards against connection pool reuse edge cases.
        try:
            db.execute(text("RESET app.current_tenant_id"))
            db.execute(text("RESET app.is_superadmin"))
        except Exception:
            pass
        db.close()


# ---------------------------------------------------------------------------
# Super-admin session (bypasses RLS)
# ---------------------------------------------------------------------------
def get_superadmin_db() -> Generator[Session, None, None]:
    """
    Yield a database session with ``app.is_superadmin = 'true'``.

    Intended for system-level / admin operations that need to read across
    tenants (e.g., migrations, background jobs, platform analytics).
    """
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.is_superadmin = 'true'"))
        db.execute(text("SET LOCAL app.current_tenant_id = ''"))
        logger.debug("RLS context set: superadmin mode")
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        try:
            db.execute(text("RESET app.is_superadmin"))
            db.execute(text("RESET app.current_tenant_id"))
        except Exception:
            pass
        db.close()


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
