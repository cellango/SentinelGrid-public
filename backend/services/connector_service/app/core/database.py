"""Database connection and session management."""

from typing import Generator

from fastapi import Depends
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import get_current_tenant

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_tenant_db(tenant_id: str) -> Generator[Session, None, None]:
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
    tenant_id: str = Depends(get_current_tenant),
) -> Generator[Session, None, None]:
    """FastAPI dependency for JWT-derived tenant-scoped DB access."""
    yield from get_tenant_db(tenant_id)
