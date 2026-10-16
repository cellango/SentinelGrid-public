"""Database configuration and session management."""

from typing import Generator

from fastapi import Depends
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.core.security import get_tenant_id

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


@event.listens_for(engine, "connect")
def _reset_tenant_on_connect(dbapi_connection, connection_record):
    """Clear tenant RLS state when a new physical connection is created."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SET app.current_tenant_id = ''")
        cursor.execute("SET app.is_superadmin = 'false'")
    finally:
        cursor.close()


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_tenant_db(tenant_id) -> Generator[Session, None, None]:
    """Yield a DB session with tenant-scoped RLS context applied."""
    resolved_tenant = str(tenant_id)
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.current_tenant_id = :tid"), {"tid": resolved_tenant})
        db.execute(text("SET LOCAL app.is_superadmin = 'false'"))
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        try:
            db.execute(text("RESET app.current_tenant_id"))
            db.execute(text("RESET app.is_superadmin"))
        except Exception:
            pass
        db.close()


def get_tenant_session(
    tenant_id = Depends(get_tenant_id),
) -> Generator[Session, None, None]:
    """FastAPI dependency that returns a tenant-scoped DB session."""
    yield from get_tenant_db(tenant_id)
