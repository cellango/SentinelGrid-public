"""Privileged access (JIT) persistence and grant/revoke helpers."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from uuid import uuid4

from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.keycloak_admin_client import KeycloakAdminClient

logger = logging.getLogger(__name__)


class PrivilegedAccessService:
    """Service to manage privileged access requests and apply grants."""

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or settings.DB_URL
        if not self.db_url:
            raise RuntimeError("DB_URL not configured")
        self.engine = create_engine(self.db_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._ensure_table()

    def _db(self):
        return self.SessionLocal()

    def _ensure_table(self) -> None:
        """Create table if migrations have not run (best-effort)."""
        ddl = """
        CREATE TABLE IF NOT EXISTS privileged_access_requests (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            requested_by TEXT NOT NULL,
            approver_id TEXT,
            resource_type TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            resource_name TEXT,
            reason TEXT,
            duration_hours INT,
            status TEXT NOT NULL DEFAULT 'pending',
            requested_at TIMESTAMPTZ DEFAULT now(),
            approved_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ,
            revoked_at TIMESTAMPTZ,
            rejection_reason TEXT,
            session_recording BOOLEAN DEFAULT FALSE
        );
        CREATE INDEX IF NOT EXISTS idx_priv_access_tenant ON privileged_access_requests(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_priv_access_status ON privileged_access_requests(status);
        """
        try:
            with self.engine.begin() as conn:
                conn.execute(text(ddl))
                # Backfill new columns when table already existed
                conn.execute(text("ALTER TABLE privileged_access_requests ADD COLUMN IF NOT EXISTS session_recording BOOLEAN DEFAULT FALSE"))
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not ensure privileged_access_requests table: %s", e)

    def create_request(
        self,
        tenant_id: str,
        user_id: str,
        resource_type: str,
        resource_id: str,
        resource_name: Optional[str],
        reason: str,
        duration_hours: int,
        session_recording: bool = False,
    ) -> Dict:
        """Persist a privileged access request."""
        request_id = str(uuid4())
        expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
        db = self._db()
        try:
            db.execute(
                text(
                    """
                    INSERT INTO privileged_access_requests
                        (id, tenant_id, requested_by, resource_type, resource_id, resource_name, reason, duration_hours, status, requested_at, expires_at, session_recording)
                    VALUES
                        (:id, :tenant_id, :requested_by, :resource_type, :resource_id, :resource_name, :reason, :duration_hours, 'pending', now(), :expires_at, :session_recording)
                    """
                ),
                {
                    "id": request_id,
                    "tenant_id": tenant_id,
                    "requested_by": user_id,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "resource_name": resource_name,
                    "reason": reason,
                    "duration_hours": duration_hours,
                    "expires_at": expires_at,
                    "session_recording": session_recording,
                },
            )
            db.commit()
            return {
                "id": request_id,
                "tenant_id": tenant_id,
                "requested_by": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "resource_name": resource_name,
                "reason": reason,
                "duration_hours": duration_hours,
                "status": "pending",
                "requested_at": datetime.utcnow(),
                "expires_at": expires_at,
                "session_recording": session_recording,
            }
        finally:
            db.close()

    def get_request(self, request_id: str, tenant_id: str) -> Optional[Dict]:
        """Get a single request scoped to a tenant."""
        db = self._db()
        try:
            row = db.execute(
                text(
                    """
                    SELECT id, tenant_id, requested_by, approver_id, resource_type, resource_id, resource_name,
                           reason, duration_hours, status, requested_at, approved_at, expires_at, revoked_at, rejection_reason, session_recording
                    FROM privileged_access_requests
                    WHERE id = :id AND tenant_id = :tenant_id
                    """
                ),
                {"id": request_id, "tenant_id": tenant_id},
            ).mappings().first()
            return dict(row) if row else None
        finally:
            db.close()

    def list_requests(
        self,
        tenant_id: str,
        status: Optional[str] = None,
        resource_type: Optional[str] = None,
        requested_by: Optional[str] = None,
    ) -> List[Dict]:
        """List privileged access requests."""
        db = self._db()
        try:
            query = """
                SELECT id, tenant_id, requested_by, resource_type, resource_id, resource_name, reason,
                       duration_hours, status, requested_at, approved_at, expires_at, session_recording
                FROM privileged_access_requests
                WHERE tenant_id = :tenant_id
            """
            params = {"tenant_id": tenant_id}
            if status:
                query += " AND status = :status"
                params["status"] = status
            if resource_type:
                query += " AND resource_type = :resource_type"
                params["resource_type"] = resource_type
            if requested_by:
                query += " AND requested_by = :requested_by"
                params["requested_by"] = requested_by
            rows = db.execute(text(query), params).fetchall()
            return [
                {
                    "id": str(r.id),
                    "tenant_id": str(r.tenant_id),
                    "requested_by": r.requested_by,
                    "resource_type": r.resource_type,
                    "resource_id": r.resource_id,
                    "resource_name": r.resource_name,
                    "reason": r.reason,
                    "duration_hours": r.duration_hours,
                    "status": r.status,
                    "requested_at": r.requested_at,
                    "approved_at": r.approved_at,
                    "expires_at": r.expires_at,
                    "session_recording": getattr(r, "session_recording", False),
                }
                for r in rows
            ]
        finally:
            db.close()

    def update_status(
        self,
        request_id: str,
        status: str,
        approver_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        tenant_id: Optional[str] = None,
        rejection_reason: Optional[str] = None,
        revoked_at: Optional[datetime] = None,
    ) -> None:
        db = self._db()
        try:
            db.execute(
                text(
                    """
                    UPDATE privileged_access_requests
                    SET status = :status,
                        approved_at = CASE WHEN :status = 'approved' THEN now() ELSE approved_at END,
                        approver_id = COALESCE(:approver_id, approver_id),
                        expires_at = COALESCE(:expires_at, expires_at),
                        rejection_reason = COALESCE(:rejection_reason, rejection_reason),
                        revoked_at = COALESCE(:revoked_at, revoked_at)
                    WHERE id = :id AND (:tenant_id IS NULL OR tenant_id = :tenant_id)
                    """
                ),
                {
                    "status": status,
                    "id": request_id,
                    "approver_id": approver_id,
                    "expires_at": expires_at,
                    "tenant_id": tenant_id,
                    "rejection_reason": rejection_reason,
                    "revoked_at": revoked_at,
                },
            )
            db.commit()
        finally:
            db.close()

    async def grant_temporary_role(self, realm: str, user_id: str, role_name: str) -> None:
        """Assign a role in Keycloak."""
        async with KeycloakAdminClient() as kc:
            await kc.assign_realm_role(realm, user_id, role_name)

    async def revoke_role(self, realm: str, user_id: str, role_name: str) -> None:
        async with KeycloakAdminClient() as kc:
            await kc._make_request(
                "DELETE",
                f"/realms/{realm}/users/{user_id}/role-mappings/realm",
                json_data=[{"name": role_name}],
            )

    async def expire_and_revoke(self, tenant_id: str, realm: str) -> int:
        """
        Revoke roles and mark expired approvals for a tenant.

        Returns number of requests expired.
        """
        db = self._db()
        count = 0
        try:
            rows = db.execute(
                text(
                    """
                    SELECT id, requested_by, resource_id
                    FROM privileged_access_requests
                    WHERE tenant_id = :tenant_id
                      AND status = 'approved'
                      AND expires_at IS NOT NULL
                      AND expires_at <= now()
                    """
                ),
                {"tenant_id": tenant_id},
            ).mappings().all()

            for row in rows:
                try:
                    await self.revoke_role(realm, row["requested_by"], row["resource_id"])
                except Exception as revoke_err:  # noqa: BLE001
                    logger.warning("Failed to revoke expired role %s for user %s: %s", row["resource_id"], row["requested_by"], revoke_err)
                self.update_status(
                    request_id=row["id"],
                    status="expired",
                    revoked_at=datetime.utcnow(),
                    tenant_id=tenant_id,
                )
                count += 1
            return count
        finally:
            db.close()

    def expire_due_requests(self) -> int:
        """Mark approved requests as expired when past expires_at."""
        db = self._db()
        try:
            result = db.execute(
                text(
                    """
                    UPDATE privileged_access_requests
                    SET status = 'expired', revoked_at = now()
                    WHERE status = 'approved' AND expires_at IS NOT NULL AND expires_at <= now()
                    """
                )
            )
            db.commit()
            return result.rowcount or 0
        finally:
            db.close()
