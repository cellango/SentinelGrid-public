"""Tenant isolation coverage for metadata-service incident and tenant routes."""


def test_list_incidents_uses_authenticated_tenant(client):
    response = client.get("/api/v1/metadata/incidents/")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "tenant_id": "tenant-alpha",
    }


def test_get_incident_returns_authenticated_tenant(client):
    response = client.get("/api/v1/metadata/incidents/inc-123")

    assert response.status_code == 200
    assert response.json() == {
        "id": "inc-123",
        "status": "stub",
        "tenant_id": "tenant-alpha",
    }


def test_create_incident_returns_authenticated_tenant(client):
    response = client.post(
        "/api/v1/metadata/incidents/",
        json={"name": "Example incident"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "new-id",
        "status": "created",
        "tenant_id": "tenant-alpha",
    }


def test_list_tenants_is_scoped_to_authenticated_tenant(client):
    response = client.get("/api/v1/metadata/tenants/")

    assert response.status_code == 200
    assert response.json() == {
        "items": [{"id": "tenant-alpha", "status": "stub"}],
        "total": 1,
    }


def test_get_tenant_allows_matching_tenant(client):
    response = client.get("/api/v1/metadata/tenants/tenant-alpha")

    assert response.status_code == 200
    assert response.json() == {
        "id": "tenant-alpha",
        "status": "stub",
    }


def test_get_tenant_blocks_cross_tenant_access(client):
    response = client.get("/api/v1/metadata/tenants/tenant-bravo")

    assert response.status_code == 403
    assert response.json() == {"detail": "Cross-tenant access denied"}


def test_create_tenant_blocks_cross_tenant_payload(client):
    response = client.post(
        "/api/v1/metadata/tenants/",
        json={"tenant_id": "tenant-bravo"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Cross-tenant access denied"}
