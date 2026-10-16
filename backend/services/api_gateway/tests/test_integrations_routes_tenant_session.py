from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes_integrations
from sg_core.db import get_tenant_session
from sg_core.security import get_current_tenant


@pytest.fixture
def integrations_client():
    app = FastAPI()
    app.include_router(routes_integrations.router, prefix="/integrations")
    tenant_id = str(uuid4())

    def _get_tenant():
        return tenant_id

    def _get_db():
        yield object()

    app.dependency_overrides[get_current_tenant] = _get_tenant
    app.dependency_overrides[get_tenant_session] = _get_db

    with TestClient(app) as client:
        yield client, tenant_id

    app.dependency_overrides.clear()


def test_list_integrations_accepts_tenant_scoped_db_dependency(integrations_client):
    client, _tenant_id = integrations_client

    response = client.get("/integrations/")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_create_integration_accepts_tenant_scoped_db_dependency(integrations_client):
    client, _tenant_id = integrations_client

    response = client.post(
        "/integrations/",
        json={"name": "Test Integration", "type": "siem", "config": {}},
    )

    assert response.status_code == 200
    assert response.json() == {"id": "int-1", "status": "created"}
