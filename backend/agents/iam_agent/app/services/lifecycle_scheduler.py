"""
Periodic lifecycle scheduler for start-date activation and end-date offboarding.
"""

from __future__ import annotations
from fastapi import HTTPException

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from uuid import UUID

from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.iam_portal_service import IAMPortalService
from app.services.privileged_access_service import PrivilegedAccessService

logger = logging.getLogger(__name__)

_scheduler_task: asyncio.Task | None = None


def _get_due_tenants(db) -> list[dict]:
    """
    Return tenant_id + realm_name pairs that have due lifecycle actions.
    Realm resolution priority:
    - user_tenants.realm_name (per-user binding)
    - tenants.slug as a fallback realm hint
    - settings.KEYCLOAK_REALM as last resort
    """
    now = datetime.now(timezone.utc)
    rows = db.execute(
        text(
            """
            SELECT ul.tenant_id,
                   COALESCE(ut.realm_name, t.slug, :default_realm) AS realm_name
            FROM user_lifecycle_schedule ul
            LEFT JOIN user_tenants ut
              ON ul.tenant_id = ut.tenant_id AND ul.user_id = ut.user_id
            LEFT JOIN tenants t ON ul.tenant_id = t.id
            WHERE (ul.activate_at IS NOT NULL AND ul.activate_at <= :now)
               OR (ul.deactivate_at IS NOT NULL AND ul.deactivate_at <= :now)
            GROUP BY ul.tenant_id, COALESCE(ut.realm_name, t.slug, :default_realm)
            """
        ),
        {"now": now, "default_realm": settings.KEYCLOAK_REALM},
    ).fetchall()

    return [{"tenant_id": row.tenant_id, "realm_name": row.realm_name} for row in rows]


async def run_lifecycle_once() -> Dict[str, Any]:
    raise HTTPException(status_code=501, detail="Legacy lifecycle scheduling is unavailable pending action and tenant qualification")


async def _lifecycle_loop():
    raise HTTPException(status_code=501, detail="Legacy lifecycle scheduling is unavailable pending action and tenant qualification")


def start_scheduler():
    logger.warning("Legacy lifecycle scheduler is unavailable; no background task started")
    return


async def stop_scheduler():
    """Stop the background lifecycle scheduler."""
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
    _scheduler_task = None
