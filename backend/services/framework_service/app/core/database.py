"""Database setup for Framework Mapping Service."""

import os
import sys
from typing import Generator, Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import settings

# Add libs to path
libs_path = os.path.join(os.path.dirname(__file__), "../../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

# Use shared ORM Base from sg_core models
from sg_core.models import Base
from sg_core.security import get_current_tenant as get_jwt_current_tenant
from sg_core.service_security import resolve_internal_service_token

security = HTTPBearer(auto_error=False)

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _validate_tenant_header(value: str) -> str:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid X-Tenant-ID header") from exc


def get_current_tenant(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    request: Request = None,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_internal_service_token: Optional[str] = Header(None, alias="X-Internal-Service-Token"),
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token"),
) -> str:
    """Resolve tenant from JWT auth or internal-service auth plus X-Tenant-ID."""
    if x_tenant_id:
        token = resolve_internal_service_token(
            authorization=authorization,
            x_internal_service_token=x_internal_service_token,
            x_internal_token=x_internal_token,
        )
        if token == settings.INTERNAL_SERVICE_TOKEN:
            return _validate_tenant_header(x_tenant_id)

        jwt_tenant = get_jwt_current_tenant(credentials=credentials, request=request)
        if str(jwt_tenant) != str(x_tenant_id):
            raise HTTPException(status_code=403, detail="Cross-tenant access denied")
        return _validate_tenant_header(x_tenant_id)

    return get_jwt_current_tenant(credentials=credentials, request=request)


def get_tenant_session(
    tenant_id: str = Depends(get_current_tenant),
) -> Generator[Session, None, None]:
    """Tenant-scoped session wrapper for framework routes."""
    del tenant_id
    yield from get_db()
