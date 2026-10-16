"""Database configuration and connection."""

from uuid import UUID

from fastapi import Depends
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.core.security import get_current_tenant


# Create engine
engine = create_engine(
    settings.DB_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Get database session."""
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


def get_tenant_session(
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Return an auth-derived tenant-scoped DB session."""
    yield from get_tenant_db(str(tenant_id))
