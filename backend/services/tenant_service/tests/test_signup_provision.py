"""Signup/provisioning safeguards."""
from types import SimpleNamespace
from sqlalchemy import text

from app.services.enhanced_provisioning_service import EnhancedProvisioningService


class DummyKeycloak:
    """Minimal stub to satisfy EnhancedProvisioningService without network calls."""

    def __init__(self):
        self.realm_name = "master"

    # The provision flow monkeypatches _create_admin_user/_assign_roles, so no-op here.
    def __getattr__(self, name):  # pragma: no cover - guard for unexpected calls
        raise AssertionError(f"Unexpected Keycloak call: {name}")


def _ensure_schema(db):
    """Create a minimal schema with FK constraints to catch provisioning logging issues."""
    db.execute(text("PRAGMA foreign_keys=ON"))
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                pricing_tier TEXT,
                plan_tier TEXT NOT NULL DEFAULT 'protect',
                region TEXT,
                compliance_required BOOLEAN,
                employee_count INTEGER,
                industry TEXT,
                has_dedicated_realm BOOLEAN,
                user_count INTEGER DEFAULT 0,
                org_count INTEGER DEFAULT 0,
                status TEXT,
                realm_name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS tenants (
                id TEXT PRIMARY KEY,
                customer_id TEXT REFERENCES customers(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                realm_name TEXT,
                region TEXT,
                pricing_tier TEXT,
                plan_tier TEXT NOT NULL DEFAULT 'protect',
                realm_strategy TEXT,
                incident_management_mode TEXT,
                ticketing_provider TEXT,
                ticketing_project TEXT,
                services_selected TEXT,
                keycloak_org_id TEXT,
                keycloak_group_id TEXT,
                status TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS tenant_provisioning_log (
                id TEXT PRIMARY KEY,
                tenant_id TEXT REFERENCES tenants(id) ON DELETE CASCADE,
                customer_id TEXT REFERENCES customers(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                realm_name TEXT,
                details TEXT,
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    )
    db.commit()


def test_provision_logs_and_persists_with_fk_constraints(test_db, monkeypatch):
    """End-to-end provisioning should not poison the transaction when logging events with FKs."""
    _ensure_schema(test_db)

    service = EnhancedProvisioningService(test_db, DummyKeycloak())

    # Force deterministic realm selection without hitting Keycloak
    monkeypatch.setattr(service, "_determine_pricing_tier", lambda *_args, **_kw: "starter")
    service.mt_realm_manager = SimpleNamespace(
        get_available_shared_realm=lambda region: "sg-mt-us-1",
        assign_tenant_to_shared_realm=lambda **_kw: {
            "keycloak_org_id": "org-1",
            "keycloak_group_id": "group-1",
        },
    )
    # Avoid real Keycloak user/role creation
    monkeypatch.setattr(service, "_create_admin_user", lambda *a, **k: "user-123")
    monkeypatch.setattr(service, "_assign_roles", lambda *a, **k: None)

    result = service.provision_tenant(
        company_name="Tenant B",
        admin_email="admin+tenantb@sentinelgrid.ai",
        admin_password="StrongPass1!",
        admin_first_name="Tenant",
        admin_last_name="B",
        employee_count=10,
        region="us",
        compliance_required=False,
        services_selected={"socManaged": False},
    )

    assert result["success"] is True
    tenant_id = result["tenant_id"]
    customer_id = result["customer_id"]

    # Verify rows persisted
    customer_row = test_db.execute(
        text("SELECT id, slug, realm_name FROM customers WHERE id=:id"),
        {"id": customer_id},
    ).fetchone()
    tenant_row = test_db.execute(
        text("SELECT id, keycloak_org_id, keycloak_group_id FROM tenants WHERE id=:id"),
        {"id": tenant_id},
    ).fetchone()
    assert customer_row is not None
    assert tenant_row is not None
    assert tenant_row[1] == "org-1"
    assert tenant_row[2] == "group-1"

    # Provisioning log should include start, realm assignment, and success
    events = {
        row[0]
        for row in test_db.execute(
            text("SELECT event_type FROM tenant_provisioning_log")
        ).fetchall()
    }
    assert {"provision_start", "realm_assigned", "provision_success"}.issubset(events)
