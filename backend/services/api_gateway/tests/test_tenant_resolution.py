import uuid
import pytest
from fastapi import HTTPException

from app.utils.tenant_resolution import resolve_tenant_uuid


class DummyTenant:
    def __init__(self, id, slug, realm_name=None):
        self.id = id
        self.slug = slug
        self.realm_name = realm_name


class DummyQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, condition):
        # condition will be a lambda against DummyTenant
        self.rows = [r for r in self.rows if condition(r)]
        return self

    def first(self):
        return self.rows[0] if self.rows else None


class DummySession:
    def __init__(self, tenants):
        self.tenants = tenants

    def query(self, _):
        return DummyQuery(self.tenants.copy())


def test_pass_through_when_no_slug():
    current = str(uuid.uuid4())
    db = DummySession([])
    assert resolve_tenant_uuid(current, db) == current


def test_match_slug_same_tenant():
    tenant_id = str(uuid.uuid4())
    tenants = [DummyTenant(id=tenant_id, slug="demo", realm_name="r1")]
    db = DummySession(tenants)
    assert resolve_tenant_uuid(tenant_id, db, tenant_slug="demo", realm="r1") == tenant_id


def test_forbidden_on_mismatch():
    tenant_id = str(uuid.uuid4())
    tenants = [DummyTenant(id=str(uuid.uuid4()), slug="demo", realm_name="r1")]
    db = DummySession(tenants)
    with pytest.raises(HTTPException) as exc:
        resolve_tenant_uuid(tenant_id, db, tenant_slug="demo", realm="r1")
    assert exc.value.status_code == 403


def test_not_found():
    tenant_id = str(uuid.uuid4())
    db = DummySession([])
    with pytest.raises(HTTPException) as exc:
        resolve_tenant_uuid(tenant_id, db, tenant_slug="missing")
    assert exc.value.status_code == 404
