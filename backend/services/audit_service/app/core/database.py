"""Database configuration for Audit Service."""

from typing import Generator
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_tenant(
    x_tenant_id: str = Header(..., alias="X-Tenant-ID", description="Tenant UUID"),
) -> UUID:
    """Extract and validate the tenant UUID from internal service headers."""
    try:
        return UUID(str(x_tenant_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Tenant-ID header",
        ) from exc


def get_tenant_db(tenant_id: UUID | str) -> Generator[Session, None, None]:
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
    tenant_id: UUID = Depends(get_current_tenant),
) -> Generator[Session, None, None]:
    """FastAPI dependency that returns a tenant-scoped DB session."""
    yield from get_tenant_db(tenant_id)
