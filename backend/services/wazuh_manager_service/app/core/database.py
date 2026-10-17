"""Database connection and session management."""

from typing import Generator

from fastapi import HTTPException, Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import get_current_tenant
from sg_core.tenant_session import tenant_session, install_tenant_pool_reset

engine = create_engine(
    settings.DB_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

install_tenant_pool_reset(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Legacy unscoped helper cannot establish Wazuh operation authority."""
    raise HTTPException(503, "Owned Wazuh operation context required")
    yield


def get_tenant_db(tenant_id: str) -> Generator[Session, None, None]:
    """A raw UUID or queue argument is not a verified operation context."""
    raise HTTPException(503, "Owned Wazuh workload or action contract required")
    yield


def get_tenant_session(request: Request) -> Generator[Session, None, None]:
    """Resolve the actual owned request; direct raw UUID calls cannot open storage."""
    if not isinstance(request, Request):
        raise HTTPException(503, "Owned Wazuh request context required")
    tenant_id = get_current_tenant(request)
    try:
        with tenant_session(SessionLocal, tenant_id) as db:
            yield db
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "Owned Wazuh store unavailable") from None
