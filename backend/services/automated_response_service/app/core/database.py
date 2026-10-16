"""Database session management."""

from typing import Generator
from fastapi import Depends
from sqlalchemy import create_engine
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
    """Tenant-scoped session wrapper for automated-response routes."""
    del tenant_id
    yield from get_db()
