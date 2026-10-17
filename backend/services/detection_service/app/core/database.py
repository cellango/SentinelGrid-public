"""Database connection and session management."""

from typing import Generator

from fastapi import Depends, HTTPException
from sqlalchemy import create_engine
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


def get_db():
    """Unscoped legacy sessions do not establish detection operation authority."""
    raise HTTPException(503, "Owned detection storage contract required")
    yield


def get_tenant_db(tenant_id: str) -> Generator[Session, None, None]:
    raise HTTPException(503, "Owned detection tenant and storage contract required")
    yield


def get_tenant_session(tenant_id: str = Depends(get_current_tenant)) -> Generator[Session, None, None]:
    """Stored rule adoption remains unavailable pending model/Flyway reconciliation."""
    raise HTTPException(503, "Owned detection rule storage contract required")
    yield
