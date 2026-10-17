"""Stored inventory from the existing V001 table, with explicit columns and tenancy.

No ORM/schema creation, unqualified table name, manager client or live status claim.
"""

from datetime import datetime
import re
from ipaddress import ip_address
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import text
from app.models.agent import AgentListItem

_SQL = text("""SELECT id, tenant_id, wazuh_agent_id, agent_name, ip_address,
    os_platform, os_version, status, last_keepalive, registration_date, agent_version
    FROM public.endpoint_agents
    WHERE tenant_id = :tenant_id
    ORDER BY registration_date DESC, id
    LIMIT :limit OFFSET :skip""")


def _time(value, required=False):
    if value is None and not required:
        return None
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise HTTPException(503, "Stored sensor timestamp unavailable")
    return value.isoformat()


def _string(value, maximum, optional=False):
    if value is None and optional:
        return None
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= maximum
        or any(ord(c) < 32 or ord(c) == 127 for c in value)
    ):
        raise HTTPException(503, "Stored sensor metadata unavailable")
    return value


class OwnedEndpointInventory:
    def __init__(self, db):
        self.db = db

    def list_owned(self, tenant_id, skip=0, limit=100):
        if (
            type(skip) is not int
            or not 0 <= skip <= 10000
            or type(limit) is not int
            or not 1 <= limit <= 100
        ):
            raise HTTPException(503, "Stored inventory bounds unavailable")
        rows = (
            self.db.execute(
                _SQL, {"tenant_id": UUID(str(tenant_id)), "skip": skip, "limit": limit}
            )
            .mappings()
            .all()
        )
        if len(rows) > limit:
            raise HTTPException(503, "Stored inventory exceeds read bounds")
        result = []
        for row in rows:
            resource = UUID(str(row["id"]))
            if not resource.int or UUID(str(row["tenant_id"])) != UUID(str(tenant_id)):
                raise HTTPException(503, "Stored sensor ownership unavailable")
            vendor = _string(row["wazuh_agent_id"], 10)
            if not re.fullmatch(r"[0-9]{3,10}", vendor) or not int(vendor):
                raise HTTPException(503, "Stored sensor identifier unavailable")
            if row["status"] not in {"pending", "active", "disconnected", "removed"}:
                raise HTTPException(503, "Stored sensor status unavailable")
            platform = _string(row["os_platform"], 100, optional=True)
            version = _string(row["os_version"], 100, optional=True)
            result.append(
                AgentListItem(
                    id=str(resource),
                    wazuh_agent_id=vendor,
                    name=_string(row["agent_name"], 255),
                    ip=str(ip_address(row["ip_address"]))
                    if row["ip_address"] is not None
                    else None,
                    os=" ".join(v for v in (platform, version) if v) or None,
                    status=row["status"],
                    last_seen=_time(row["last_keepalive"]),
                    registered=_time(row["registration_date"], True),
                    version=_string(row["agent_version"], 50, optional=True),
                )
            )
        return result
