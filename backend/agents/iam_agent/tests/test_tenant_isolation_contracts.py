import pytest
from fastapi import HTTPException

from app.core.tenant_isolation import TenantIsolationValidator


def test_enforce_tenant_isolation_accepts_matching_tenant_ids(tenant_pair):
    tenant_id, _ = tenant_pair

    TenantIsolationValidator.enforce_tenant_isolation(tenant_id, tenant_id)


def test_enforce_tenant_isolation_rejects_mismatched_tenant_ids(foreign_tenant_pair):
    with pytest.raises(HTTPException) as exc:
        TenantIsolationValidator.enforce_tenant_isolation(
            foreign_tenant_pair["authenticated"],
            foreign_tenant_pair["foreign"],
        )

    assert exc.value.status_code == 403


def test_get_tenant_id_for_query_uses_provided_tenant_scope(tenant_pair):
    tenant_id, _ = tenant_pair

    resolved = TenantIsolationValidator.get_tenant_id_for_query(
        tenant_id=tenant_id,
        current_user_id=tenant_id,
    )

    assert resolved == tenant_id


def test_foreign_tenant_identifier_is_not_echoed_in_error_paths(foreign_tenant_pair):
    with pytest.raises(HTTPException) as exc:
        TenantIsolationValidator.enforce_tenant_isolation(
            foreign_tenant_pair["authenticated"],
            foreign_tenant_pair["foreign"],
        )

    assert exc.value.detail == "Access denied"
