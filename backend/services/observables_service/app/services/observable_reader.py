"""Explicit tenant/resource SELECT; no enrichment payload, tracker or provider client."""

from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from app.models import Observable, ObservableResponse

_FIELDS = tuple(
    getattr(Observable, n)
    for n in (
        "id",
        "tenant_id",
        "observable_type",
        "value",
        "source_event_id",
        "first_seen",
        "last_seen",
        "tlp_level",
        "enrichment_status",
        "created_at",
    )
)


class OwnedObservableReader:
    def __init__(self, db):
        self.db = db

    def get_owned(self, observable_id, tenant_id):
        row = (
            self.db.execute(
                select(*_FIELDS).where(
                    Observable.id == UUID(str(observable_id)),
                    Observable.tenant_id == UUID(str(tenant_id)),
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        if UUID(str(row["tenant_id"])) != UUID(str(tenant_id)) or UUID(
            str(row["id"])
        ) != UUID(str(observable_id)):
            raise HTTPException(503, "Observable ownership unavailable")
        if (
            not isinstance(row["value"], str)
            or len(row["value"].encode("utf-8")) > 4096
            or row["observable_type"]
            not in {
                "user_id",
                "ip",
                "domain",
                "url",
                "hash",
                "email",
                "cve",
                "file_path",
                "process_name",
                "registry_key",
            }
            or type(row["tlp_level"]) is not int
            or not 0 <= row["tlp_level"] <= 3
            or row["enrichment_status"]
            not in {"pending", "enriching", "completed", "failed", "skipped"}
        ):
            raise HTTPException(503, "Observable stored metadata unavailable")
        # Preserve the response field, without selecting the arbitrary JSON payload.
        return ObservableResponse(
            **{column.name: row[column.name] for column in _FIELDS},
            enrichment_data=None,
        )
