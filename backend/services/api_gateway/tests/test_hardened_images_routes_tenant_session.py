from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes_hardened_images
from sg_core.db import get_tenant_session
from sg_core.security import get_current_tenant


def test_hardened_image_recommendations_route_uses_tenant_scoped_dependency():
    app = FastAPI()
    app.include_router(routes_hardened_images.router, prefix="/hardened-images")
    tenant_id = str(uuid4())

    def _get_tenant():
        return tenant_id

    def _get_db():
        yield object()

    app.dependency_overrides[get_current_tenant] = _get_tenant
    app.dependency_overrides[get_tenant_session] = _get_db

    with TestClient(app) as client:
        response = client.get("/hardened-images/recommendations/list?cloud_provider=aws")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "cloud_provider": "aws",
    }
