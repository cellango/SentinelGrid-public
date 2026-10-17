"""Tenant-owned metadata SELECTs never load credentials, sync settings or errors."""

from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from app.models.connector import ConnectorConfig

_FIELDS = (
    ConnectorConfig.id,
    ConnectorConfig.tenant_id,
    ConnectorConfig.type,
    ConnectorConfig.name,
    ConnectorConfig.status,
    ConnectorConfig.last_sync_at,
    ConnectorConfig.created_at,
    ConnectorConfig.updated_at,
)


class OwnedConnectorReader:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _view(row, tenant_id, connector_id=None):
        if UUID(str(row["tenant_id"])) != UUID(str(tenant_id)):
            raise HTTPException(503, "Connector ownership unavailable")
        resource = UUID(str(row["id"]))
        if (
            not resource.int
            or connector_id is not None
            and resource != UUID(str(connector_id))
        ):
            raise HTTPException(503, "Connector target unavailable")
        return dict(
            id=str(row["id"]),
            tenant_id=str(row["tenant_id"]),
            type=row["type"],
            name=row["name"],
            status=row["status"],
            error_message=None,
            last_sync_at=row["last_sync_at"].isoformat()
            if row["last_sync_at"]
            else None,
            created_at=row["created_at"].isoformat(),
            updated_at=row["updated_at"].isoformat(),
        )

    def list_owned(self, tenant_id, skip=0, limit=100):
        rows = (
            self.db.execute(
                select(*_FIELDS)
                .where(ConnectorConfig.tenant_id == UUID(str(tenant_id)))
                .order_by(ConnectorConfig.id)
                .offset(skip)
                .limit(limit)
            )
            .mappings()
            .all()
        )
        return [self._view(row, tenant_id) for row in rows]

    def get_owned(self, connector_id, tenant_id):
        row = (
            self.db.execute(
                select(*_FIELDS).where(
                    ConnectorConfig.id == UUID(str(connector_id)),
                    ConnectorConfig.tenant_id == UUID(str(tenant_id)),
                )
            )
            .mappings()
            .one_or_none()
        )
        return self._view(row, tenant_id, connector_id) if row is not None else None
