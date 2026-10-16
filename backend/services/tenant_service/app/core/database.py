"""Database connection and session management."""

from typing import Generator
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from app.core.config import settings

Base = declarative_base()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG_MODE,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_tenant(
    x_tenant_id: str = Header(..., alias="X-Tenant-ID", description="Tenant UUID"),
) -> UUID:
    """Extract and validate tenant identity for tenant-bound routes."""
    try:
        return UUID(str(x_tenant_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Tenant-ID header",
        ) from exc


def get_tenant_session(
    tenant_id: UUID = Depends(get_current_tenant),
) -> Generator[Session, None, None]:
    """Return a DB session with best-effort tenant context applied."""
    db = SessionLocal()
    try:
        if db.bind is not None and db.bind.dialect.name == "postgresql":
            db.execute(text("SET LOCAL app.current_tenant_id = :tenant_id"), {"tenant_id": str(tenant_id)})
            db.execute(text("SET LOCAL app.is_superadmin = 'false'"))
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
