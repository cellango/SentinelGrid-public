"""Database configuration."""

import sys
import os
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

# Add libs to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../libs"))

from sg_core.db import get_db, get_tenant_db, get_tenant_session, engine, Base
from sg_core.security import get_current_tenant


def resolve_query_tenant_id(
    tenant_id: UUID = Query(..., description="Tenant ID"),
    current_tenant: str = Depends(get_current_tenant),
) -> str:
    """Validate that the query tenant matches the authenticated tenant."""
    if str(tenant_id) != str(current_tenant):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access denied",
        )
    return str(current_tenant)


def get_query_tenant_session(
    tenant_id: str = Depends(resolve_query_tenant_id),
    db: Session = Depends(get_tenant_session),
) -> Session:
    """Return the authenticated tenant-scoped DB session for query-tenant routes."""
    del tenant_id
    return db


__all__ = [
    "get_db",
    "get_tenant_db",
    "get_tenant_session",
    "get_current_tenant",
    "resolve_query_tenant_id",
    "get_query_tenant_session",
    "engine",
    "Base",
]
