"""
Periodic lifecycle scheduler for start-date activation and end-date offboarding.
"""

from __future__ import annotations

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
    """Run lifecycle and privileged access expiry across all tenants with due actions."""
    results: Dict[str, Any] = {}
    db = SessionLocal()
    try:
        for row in _get_due_tenants(db):
            tenant_id = UUID(str(row["tenant_id"]))
            realm_name = row["realm_name"] or settings.KEYCLOAK_REALM
            svc = IAMPortalService(db, tenant_id, realm_name)
            try:
                stats = await svc.apply_lifecycle_schedules(actor_id="system")
                results[str(tenant_id)] = {"realm": realm_name, "stats": stats}
            except Exception as e:  # pragma: no cover - defensive
                logger.error("Lifecycle scheduler failed for tenant %s: %s", tenant_id, e, exc_info=True)
                results[str(tenant_id)] = {"realm": realm_name, "error": str(e)}

        # Expire privileged access requests that are past due (no new scheduler needed)
        priv_rows = db.execute(
            text(
                """
                SELECT par.tenant_id,
                       COALESCE(t.slug, :default_realm) AS realm_name
                FROM privileged_access_requests par
                LEFT JOIN tenants t ON par.tenant_id = t.id
                WHERE par.status = 'approved'
                  AND par.expires_at IS NOT NULL
                  AND par.expires_at <= now()
                GROUP BY par.tenant_id, COALESCE(t.slug, :default_realm)
                """
            ),
            {"default_realm": settings.KEYCLOAK_REALM},
        ).mappings().all()

        for row in priv_rows:
            tenant_id = str(row["tenant_id"])
            realm_name = row["realm_name"] or settings.KEYCLOAK_REALM
            svc = PrivilegedAccessService()
            try:
                expired = await svc.expire_and_revoke(tenant_id, realm_name)
                results.setdefault(tenant_id, {}).setdefault("privileged_access", {})["expired"] = expired
            except Exception as e:  # pragma: no cover
                logger.error("Privileged access expiry failed for tenant %s: %s", tenant_id, e, exc_info=True)
                results.setdefault(tenant_id, {}).setdefault("privileged_access", {})["error"] = str(e)
    finally:
        db.close()
    return results


async def _lifecycle_loop():
    interval = max(30, settings.LIFECYCLE_JOB_INTERVAL_SECONDS or 300)
    logger.info("Lifecycle scheduler loop starting (interval=%ss, enabled=%s)", interval, settings.LIFECYCLE_JOB_ENABLED)
    while True:
        try:
            await run_lifecycle_once()
        except Exception as e:  # pragma: no cover - defensive
            logger.error("Lifecycle scheduler loop error: %s", e, exc_info=True)
        await asyncio.sleep(interval)


def start_scheduler():
    """Start the background lifecycle scheduler if enabled."""
    global _scheduler_task
    if not settings.LIFECYCLE_JOB_ENABLED:
        logger.info("Lifecycle scheduler disabled via config; not starting.")
        return
    if _scheduler_task and not _scheduler_task.done():
        return
    _scheduler_task = asyncio.create_task(_lifecycle_loop())


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
