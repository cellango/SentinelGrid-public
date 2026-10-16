"""Focused tenant-isolation tests for tenant-scoped provisioning routes."""

from uuid import uuid4

from sqlalchemy import text


def _create_tenant(db, tenant_id: str, slug: str = "tenant-a") -> None:
    db.execute(
        text(
            """
            INSERT INTO tenants (id, name, slug, status, created_at, updated_at)
            VALUES (:id, :name, :slug, :status, datetime('now'), datetime('now'))
            """
        ),
        {
            "id": tenant_id,
            "name": "Test Tenant",
            "slug": slug,
            "status": "active",
        },
    )
    db.commit()


def test_integration_status_rejects_cross_tenant_header(client, test_db):
    tenant_id = str(uuid4())
    _create_tenant(test_db, tenant_id)

    response = client.get(
        f"/api/v1/tenants/{tenant_id}/integration-status",
        headers={"X-Tenant-ID": str(uuid4())},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-tenant access denied"


def test_set_alert_preferences_rejects_cross_tenant_header(client, test_db):
    tenant_id = str(uuid4())
    _create_tenant(test_db, tenant_id)

    response = client.post(
        f"/api/v1/tenants/{tenant_id}/alert-preferences",
        headers={"X-Tenant-ID": str(uuid4())},
        json={
            "email_notifications": {"critical": True},
            "notification_email": "security@test.com",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-tenant access denied"


def test_get_feature_flags_rejects_cross_tenant_header(client, test_db):
    tenant_id = str(uuid4())
    _create_tenant(test_db, tenant_id)

    response = client.get(
        f"/api/v1/tenants/{tenant_id}/feature-flags",
        headers={"X-Tenant-ID": str(uuid4())},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-tenant access denied"


def test_set_feature_flags_rejects_cross_tenant_header(client, test_db):
    tenant_id = str(uuid4())
    _create_tenant(test_db, tenant_id)

    response = client.post(
        f"/api/v1/tenants/{tenant_id}/feature-flags",
        headers={"X-Tenant-ID": str(uuid4())},
        json={
            "edr_openedr_enabled": True,
            "edr_velociraptor_enabled": False,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-tenant access denied"


def test_invite_users_rejects_cross_tenant_header(client, test_db, mock_keycloak_client):
    tenant_id = str(uuid4())
    _create_tenant(test_db, tenant_id)

    response = client.post(
        f"/api/v1/tenants/{tenant_id}/invitations",
        headers={"X-Tenant-ID": str(uuid4())},
        json={
            "emails": ["user@test.com"],
            "role": "soc_analyst",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-tenant access denied"
