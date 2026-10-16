"""Database session management."""

from typing import Generator
from sqlalchemy import create_engine, text
from fastapi import Depends
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from sg_core.security import get_current_tenant

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.LOG_LEVEL == "DEBUG",
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get database session.
    
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


def get_tenant_session(
    tenant_id: str = Depends(get_current_tenant),
) -> Generator[Session, None, None]:
    """Yield a database session with tenant context when supported by the backend."""
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
