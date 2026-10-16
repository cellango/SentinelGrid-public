from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional


def get_tenant_slug_for_id(db: Session, tenant_id) -> Optional[str]:
    """Resolve tenant_slug from tenant_id."""
    try:
        row = db.execute(
            text("SELECT slug FROM tenants WHERE id = :tid LIMIT 1"),
            {"tid": str(tenant_id)},
        ).fetchone()
        if row:
            return row[0]
    except Exception:
        return None
    return None
