from typing import Generator
"""Database connection and session management."""

from fastapi import Depends
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import get_current_tenant

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False  # Set to True for SQL query logging
)

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
    """Yield a tenant-scoped session when PostgreSQL RLS variables are available."""
    db = SessionLocal()
    is_postgres = getattr(getattr(db.bind, "dialect", None), "name", "") == "postgresql"

    try:
        if is_postgres:
            db.execute(text("SET LOCAL app.current_tenant_id = :tenant_id"), {"tenant_id": str(tenant_id)})
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
    tenant_id = Depends(get_current_tenant),
) -> Generator[Session, None, None]:
    """Tenant-scoped session wrapper for route-level isolation enforcement."""
    yield from get_tenant_db(tenant_id)


def init_db():
    """Initialize database (create tables)."""
    Base.metadata.create_all(bind=engine)
