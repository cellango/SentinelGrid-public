"""Tenant-owned definition reads; no shared-catalog lookup or execution effects."""

from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from app.database import PlaybookDB
from app.services.playbook_service import PlaybookService


class OwnedPlaybookReader:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _view(row, tenant_id):
        if UUID(str(row.tenant_id)) != tenant_id:
            raise HTTPException(503, "Playbook ownership unavailable")
        # Preserve the logical definition/versions while withholding the installed
        # webhook URL, which can carry a credential. Never mutate the stored row.
        return PlaybookService._to_model(row).model_copy(
            update={"n8n_webhook_url": None}
        )

    def list_owned(self, tenant_id, category=None, is_template=None, skip=0, limit=100):
        statement = select(PlaybookDB).where(PlaybookDB.tenant_id == tenant_id)
        if category is not None:
            statement = statement.where(PlaybookDB.category == category)
        if is_template is not None:
            statement = statement.where(PlaybookDB.is_template == is_template)
        statement = statement.order_by(PlaybookDB.id).offset(skip).limit(limit)
        rows = self.db.execute(statement).scalars().all()
        return [self._view(row, tenant_id) for row in rows]

    def get_owned(self, playbook_id, tenant_id):
        row = self.db.execute(
            select(PlaybookDB).where(
                PlaybookDB.id == playbook_id, PlaybookDB.tenant_id == tenant_id
            )
        ).scalar_one_or_none()
        return self._view(row, tenant_id) if row is not None else None
