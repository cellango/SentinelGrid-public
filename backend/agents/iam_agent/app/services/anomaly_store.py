"""
Lightweight persistence and event loading for anomaly detection.

This module intentionally keeps a minimal schema (created on first use) to avoid
relying on the Flyway pipeline while it is being cleaned up. If the database is
unavailable, callers should degrade gracefully and return empty results.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import engine, SessionLocal

logger = logging.getLogger(__name__)


class AnomalyStore:
    """Thin wrapper around the anomalies table and auth event loading."""

    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
        self._tables_ready = False

    @property
    def available(self) -> bool:
        """Whether we can talk to the database."""
        return self.engine is not None

    def ensure_tables(self) -> bool:
        """Create anomalies table/indexes if they do not exist."""
        if not self.available:
            return False
        if self._tables_ready:
            return True
        ddl = """
        CREATE TABLE IF NOT EXISTS anomalies (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            user_id TEXT,
            anomaly_type VARCHAR(100) NOT NULL,
            severity VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            risk_score FLOAT DEFAULT 0.0,
            metadata JSONB,
            status VARCHAR(50) DEFAULT 'open',
            acknowledged_at TIMESTAMPTZ,
            acknowledged_by TEXT,
            resolved_at TIMESTAMPTZ,
            resolved_by TEXT,
            resolution_notes TEXT,
            detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_anomalies_tenant ON anomalies(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_anomalies_user ON anomalies(user_id);
        CREATE INDEX IF NOT EXISTS idx_anomalies_type ON anomalies(anomaly_type);
        CREATE INDEX IF NOT EXISTS idx_anomalies_severity ON anomalies(severity);
        CREATE INDEX IF NOT EXISTS idx_anomalies_status ON anomalies(status);
        CREATE INDEX IF NOT EXISTS idx_anomalies_detected_at ON anomalies(detected_at);
        """
        try:
            with self.engine.begin() as conn:
                conn.execute(text(ddl))
            self._tables_ready = True
            return True
        except SQLAlchemyError as exc:
            logger.error("Failed to ensure anomalies table: %s", exc, exc_info=True)
            return False

    # ------------------------------------------------------------------ #
    # Event loading
    # ------------------------------------------------------------------ #

    def fetch_auth_events(
        self,
        tenant_id: str,
        since: datetime,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Load recent authentication-related events for a tenant.

        Prefers platform_audit_logs (with tenant_id); falls back to realm_audit_log
        joined via user_tenants when needed. Returns normalized rows as dicts.
        """
        if not self.available:
            return []

        events: List[Dict[str, Any]] = []
        tenant_filter = {"tenant_id": tenant_id, "since": since}

        try:
            with self.engine.connect() as conn:
                # Primary source: platform_audit_logs
                platform_sql = """
                    SELECT
                        actor_user_id AS user_id,
                        ip_address::text AS ip_address,
                        user_agent,
                        metadata,
                        action,
                        success,
                        timestamp AS occurred_at
                    FROM platform_audit_logs
                    WHERE tenant_id = :tenant_id
                      AND timestamp >= :since
                      AND (
                        action_category = 'auth'
                        OR action ILIKE '%%login%%'
                        OR action IN ('token_refresh', 'mfa_challenge', 'mfa_verify', 'mfa_challenge_sent')
                      )
                    ORDER BY timestamp ASC
                """
                if user_id:
                    platform_sql = platform_sql.replace(
                        "ORDER BY",
                        "AND actor_user_id = :user_id ORDER BY",
                    )
                    tenant_filter["user_id"] = user_id

                result = conn.execute(text(platform_sql), tenant_filter).mappings().all()
                events.extend(result)

                # Fallback: realm_audit_log (may not carry tenant_id directly)
                if not events:
                    realm_sql = """
                        SELECT
                            r.actor_user_id AS user_id,
                            r.ip_address::text AS ip_address,
                            r.user_agent,
                            r.details AS metadata,
                            r.action,
                            NULL::boolean AS success,
                            r.created_at AS occurred_at
                        FROM realm_audit_log r
                        JOIN user_tenants ut ON ut.user_id = r.actor_user_id
                        WHERE ut.tenant_id = :tenant_id
                          AND r.created_at >= :since
                          AND r.action ILIKE '%%login%%'
                    """
                    if user_id:
                        realm_sql += " AND r.actor_user_id = :user_id"
                    realm_sql += " ORDER BY r.created_at ASC"
                    realm_rows = conn.execute(text(realm_sql), tenant_filter).mappings().all()
                    events.extend(realm_rows)

        except SQLAlchemyError as exc:
            logger.error("Failed to load auth events for tenant %s: %s", tenant_id, exc, exc_info=True)
            return []

        return [dict(row) for row in events]

    # ------------------------------------------------------------------ #
    # Anomaly persistence helpers
    # ------------------------------------------------------------------ #

    def upsert_anomalies(
        self,
        anomalies: List[Dict[str, Any]],
        window_start: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Insert or refresh anomalies, avoiding duplicates within the window.

        Returns the stored anomaly payloads (including id and timestamps).
        """
        if not anomalies or not self.ensure_tables():
            return []

        stored: List[Dict[str, Any]] = []
        with self.SessionLocal() as session:
            try:
                for anomaly in anomalies:
                    tenant_id = anomaly["tenant_id"]
                    anomaly_type = anomaly["anomaly_type"]
                    user_id = anomaly.get("user_id")

                    existing_sql = """
                        SELECT *
                        FROM anomalies
                        WHERE tenant_id = :tenant_id
                          AND anomaly_type = :anomaly_type
                          AND (user_id = :user_id OR (:user_id IS NULL AND user_id IS NULL))
                          AND detected_at >= :window_start
                        ORDER BY detected_at DESC
                        LIMIT 1
                    """
                    existing = session.execute(
                        text(existing_sql),
                        {
                            "tenant_id": tenant_id,
                            "anomaly_type": anomaly_type,
                            "user_id": user_id,
                            "window_start": window_start,
                        },
                    ).mappings().first()

                    now = datetime.utcnow()
                    incoming_meta = anomaly.get("metadata") or {}
                    if isinstance(incoming_meta, str):
                        try:
                            import json
                            incoming_meta = json.loads(incoming_meta)
                        except Exception:
                            incoming_meta = {}
                    if existing:
                        existing_meta = existing.get("metadata") or {}
                        if isinstance(existing_meta, str):
                            try:
                                import json
                                existing_meta = json.loads(existing_meta)
                            except Exception:
                                existing_meta = {}
                        # Preserve prior responses unless caller explicitly overwrote them
                        if "responses" in existing_meta and "responses" not in incoming_meta:
                            incoming_meta["responses"] = existing_meta.get("responses")

                        update_sql = """
                            UPDATE anomalies
                            SET risk_score = :risk_score,
                                severity = :severity,
                                description = :description,
                                metadata = :metadata,
                                status = :status,
                                updated_at = :updated_at
                            WHERE id = :id
                            RETURNING *
                        """
                        updated = session.execute(
                            text(update_sql),
                            {
                                "id": existing["id"],
                                "risk_score": anomaly.get("risk_score", existing.get("risk_score", 0)),
                                "severity": anomaly.get("severity", existing.get("severity", "medium")),
                                "description": anomaly.get("description"),
                                "metadata": incoming_meta,
                                "status": anomaly.get("status", existing.get("status", "open")),
                                "updated_at": now,
                            },
                        ).mappings().first()
                        stored.append(dict(updated))
                    else:
                        insert_sql = """
                            INSERT INTO anomalies (
                                id, tenant_id, user_id, anomaly_type, severity,
                                title, description, risk_score, metadata, status,
                                detected_at, created_at, updated_at
                            ) VALUES (
                                :id, :tenant_id, :user_id, :anomaly_type, :severity,
                                :title, :description, :risk_score, :metadata, :status,
                                :detected_at, :created_at, :updated_at
                            )
                            RETURNING *
                        """
                        anomaly_id = anomaly.get("id") or uuid.uuid4()
                        inserted = session.execute(
                            text(insert_sql),
                            {
                                "id": anomaly_id,
                                "tenant_id": tenant_id,
                                "user_id": user_id,
                                "anomaly_type": anomaly_type,
                                "severity": anomaly.get("severity", "medium"),
                                "title": anomaly.get("title", ""),
                                "description": anomaly.get("description"),
                                "risk_score": anomaly.get("risk_score", 0),
                                "metadata": incoming_meta,
                                "status": anomaly.get("status", "open"),
                                "detected_at": anomaly.get("detected_at", now),
                                "created_at": now,
                                "updated_at": now,
                            },
                        ).mappings().first()
                        stored.append(dict(inserted))

                session.commit()
            except SQLAlchemyError as exc:
                session.rollback()
                logger.error("Failed to upsert anomalies: %s", exc, exc_info=True)
                return []

        return stored

    def list_anomalies(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        anomaly_type: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List anomalies with basic filtering and pagination."""
        if not self.ensure_tables():
            return {"items": [], "total": 0}

        params: Dict[str, Any] = {"tenant_id": tenant_id}
        filters = ["tenant_id = :tenant_id"]

        if user_id:
            filters.append("user_id = :user_id")
            params["user_id"] = user_id
        if anomaly_type:
            filters.append("anomaly_type = :anomaly_type")
            params["anomaly_type"] = anomaly_type
        if severity:
            filters.append("severity = :severity")
            params["severity"] = severity
        if status:
            filters.append("status = :status")
            params["status"] = status

        where_clause = " AND ".join(filters)
        offset = (page - 1) * limit
        params.update({"limit": limit, "offset": offset})

        query = f"""
            SELECT * FROM anomalies
            WHERE {where_clause}
            ORDER BY detected_at DESC
            LIMIT :limit OFFSET :offset
        """
        count_sql = f"SELECT COUNT(*) FROM anomalies WHERE {where_clause}"

        with self.SessionLocal() as session:
            rows = session.execute(text(query), params).mappings().all()
            total = session.execute(text(count_sql), params).scalar() or 0

        items = [self._row_to_dict(r) for r in rows]
        return {"items": items, "total": total}

    def acknowledge(self, tenant_id: str, anomaly_id: str, actor: Optional[str]) -> bool:
        """Mark an anomaly as acknowledged."""
        if not self.ensure_tables():
            return False
        with self.SessionLocal() as session:
            try:
                result = session.execute(
                    text(
                        """
                        UPDATE anomalies
                        SET status = 'acknowledged',
                            acknowledged_at = :ts,
                            acknowledged_by = :actor,
                            updated_at = :ts
                        WHERE id = :id AND tenant_id = :tenant_id
                        """
                    ),
                    {"id": anomaly_id, "tenant_id": tenant_id, "actor": actor, "ts": datetime.utcnow()},
                )
                session.commit()
                return result.rowcount > 0
            except SQLAlchemyError as exc:
                session.rollback()
                logger.error("Failed to acknowledge anomaly %s: %s", anomaly_id, exc, exc_info=True)
                return False

    def append_responses(self, tenant_id: str, anomaly_id: str, actions: List[Dict]) -> bool:
        """Attach automated response actions to anomaly metadata."""
        if not actions or not self.ensure_tables():
            return False
        with self.SessionLocal() as session:
            try:
                row = session.execute(
                    text("SELECT metadata FROM anomalies WHERE id = :id AND tenant_id = :tenant_id"),
                    {"id": anomaly_id, "tenant_id": tenant_id},
                ).mappings().first()
                if not row:
                    return False
                import json

                meta = row.get("metadata") or {}
                if isinstance(meta, str):
                    try:
                        meta = json.loads(meta)
                    except Exception:
                        meta = {}
                existing = meta.get("responses") or []
                if not isinstance(existing, list):
                    existing = [existing]
                existing.extend(actions)
                meta["responses"] = existing

                session.execute(
                    text(
                        """
                        UPDATE anomalies
                        SET metadata = :metadata, updated_at = :ts
                        WHERE id = :id AND tenant_id = :tenant_id
                        """
                    ),
                    {"metadata": meta, "ts": datetime.utcnow(), "id": anomaly_id, "tenant_id": tenant_id},
                )
                session.commit()
                return True
            except SQLAlchemyError as exc:
                session.rollback()
                logger.error("Failed to append responses to anomaly %s: %s", anomaly_id, exc, exc_info=True)
                return False

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        """Convert SQLAlchemy mapping row to plain dict with parsed metadata."""
        data = dict(row)
        metadata = data.get("metadata")
        if metadata and isinstance(metadata, str):
            try:
                data["metadata"] = json.loads(metadata)
            except json.JSONDecodeError:
                pass
        return data
