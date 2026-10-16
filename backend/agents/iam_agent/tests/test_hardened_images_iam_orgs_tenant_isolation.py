from datetime import date
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import hardened_images, iam_orgs
from app.api.request_context import (
    RequestContext,
    get_current_request_context,
    get_superadmin_db,
    get_tenant_session,
)


class ResultStub:
    def __init__(self, *, rows=None, row=None):
        self._rows = rows or []
        self._row = row

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._row

    def first(self):
        return self._row


class FakeDB:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []
        self.committed = False

    def execute(self, statement, params=None):
        sql = str(statement)
        self.calls.append({"sql": sql, "params": params or {}})
        if self.responses:
            response = self.responses.pop(0)
            if callable(response):
                return response(statement, params or {})
            return response
        return ResultStub()

    def commit(self):
        self.committed = True


def _request_context(*roles: str) -> RequestContext:
    return RequestContext(
        tenant_id=uuid4(),
        user_id=str(uuid4()),
        roles=tuple(roles),
    )


def _override_dependency(app: FastAPI, dependency, value):
    if callable(value):
        app.dependency_overrides[dependency] = value
        return

    app.dependency_overrides[dependency] = lambda: value


def _override_generator_dependency(app: FastAPI, dependency, yielded_value):
    def _override():
        yield yielded_value

    app.dependency_overrides[dependency] = _override


def test_list_hardened_images_requires_authenticated_context():
    app = FastAPI()
    app.include_router(hardened_images.router)
    client = TestClient(app)

    response = client.get("/api/v1/hardened-images")

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing or invalid authorization header"}


def test_get_recommended_images_remains_accessible_with_authenticated_context():
    app = FastAPI()
    app.include_router(hardened_images.router)
    _override_dependency(app, get_current_request_context, _request_context("TENANT_ADMIN"))
    fake_db = FakeDB(
        [
            ResultStub(
                rows=[
                    (
                        "img-1",
                        "Ubuntu",
                        "22.04",
                        "aws",
                        "ami-123",
                        "sentinelgrid-ubuntu-22-04",
                        "us-east-1",
                        "CIS Level 1",
                        "1.0.0",
                        "1.2.3",
                        False,
                        date(2026, 3, 1),
                        "active",
                        {"family": "ubuntu"},
                    )
                ]
            )
        ]
    )
    _override_generator_dependency(app, get_tenant_session, fake_db)
    client = TestClient(app)

    response = client.get(
        "/api/v1/hardened-images/recommendations/list?cloud_provider=aws&region=us-east-1",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json()[0]["image_id"] == "ami-123"
    assert fake_db.calls[0]["params"]["cloud_provider"] == "aws"
    assert fake_db.calls[0]["params"]["region"] == "us-east-1"


def test_list_hardened_images_uses_tenant_scoped_session():
    app = FastAPI()
    app.include_router(hardened_images.router)
    _override_dependency(app, get_current_request_context, _request_context("TENANT_ADMIN"))
    fake_db = FakeDB(
        [
            ResultStub(row=(1,)),
            ResultStub(
                rows=[
                    (
                        "img-0",
                        "Ubuntu",
                        "22.04",
                        "aws",
                        "ami-list",
                        "sentinelgrid-ubuntu-list",
                        "us-east-1",
                        "CIS Level 1",
                        "1.0.0",
                        "1.2.3",
                        True,
                        date(2026, 3, 1),
                        "active",
                        {"family": "ubuntu"},
                    )
                ]
            ),
        ]
    )
    _override_generator_dependency(app, get_tenant_session, fake_db)
    client = TestClient(app)

    response = client.get(
        "/api/v1/hardened-images?cloud_provider=aws",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["images"][0]["image_id"] == "ami-list"
    assert fake_db.calls[0]["params"]["cloud_provider"] == "aws"
    assert fake_db.calls[1]["params"]["cloud_provider"] == "aws"


def test_get_hardened_image_uses_authenticated_context():
    app = FastAPI()
    app.include_router(hardened_images.router)
    _override_dependency(app, get_current_request_context, _request_context("TENANT_ADMIN"))
    fake_db = FakeDB(
        [
            ResultStub(
                row=(
                    "img-2",
                    "Amazon Linux 2",
                    "2.0",
                    "aws",
                    "ami-xyz",
                    "sentinelgrid-amzn2",
                    "us-east-1",
                    "CIS Level 1",
                    "2.0.0",
                    "1.2.3",
                    True,
                    date(2026, 3, 2),
                    "active",
                    {"family": "amazon-linux"},
                )
            )
        ]
    )
    _override_generator_dependency(app, get_tenant_session, fake_db)
    client = TestClient(app)

    response = client.get(
        "/api/v1/hardened-images/img-2",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == "img-2"
    assert fake_db.calls[0]["params"]["image_id"] == "img-2"


def test_create_organization_rejects_non_platform_admin(monkeypatch):
    app = FastAPI()
    app.include_router(iam_orgs.router)
    _override_dependency(app, get_current_request_context, _request_context("TENANT_ADMIN"))
    _override_generator_dependency(app, get_superadmin_db, FakeDB())
    monkeypatch.setattr(iam_orgs, "_get_realm_manager", lambda _db: object())
    monkeypatch.setattr(iam_orgs, "_pick_realm", lambda *_args, **_kwargs: "sg-mt-us-1")
    client = TestClient(app)

    response = client.post(
        "/api/iam-portal/organizations",
        headers={"authorization": "Bearer test-token"},
        json={
            "name": "Example Org",
            "display_name": "Example Org",
            "realm_strategy": "shared",
            "region": "us",
            "projected_user_count": 25,
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Missing required role"}


def test_create_organization_allows_platform_admin(monkeypatch):
    app = FastAPI()
    app.include_router(iam_orgs.router)
    _override_dependency(app, get_current_request_context, _request_context("PLATFORM_ADMIN"))
    fake_db = FakeDB(
        [
            ResultStub(row=None),
            ResultStub(row=None),
            ResultStub(),
            ResultStub(),
            ResultStub(),
        ]
    )
    _override_generator_dependency(app, get_superadmin_db, fake_db)
    monkeypatch.setattr(iam_orgs, "_get_realm_manager", lambda _db: object())
    monkeypatch.setattr(iam_orgs, "_pick_realm", lambda *_args, **_kwargs: "sg-mt-us-1")

    async def _fake_create_tenant_internal(**kwargs):
        return iam_orgs.TenantResponse(
            id=str(uuid4()),
            org_id=kwargs["org_id"],
            realm_name=kwargs["realm_name"],
            slug="example-org-main",
            keycloak_org_id="kc-org-1",
            keycloak_group_id="kc-group-1",
            status="active",
        )

    monkeypatch.setattr(iam_orgs, "create_tenant_internal", _fake_create_tenant_internal)
    client = TestClient(app)

    response = client.post(
        "/api/iam-portal/organizations",
        headers={"authorization": "Bearer test-token"},
        json={
            "name": "Example Org",
            "display_name": "Example Org",
            "realm_strategy": "shared",
            "region": "us",
            "projected_user_count": 25,
        },
    )

    assert response.status_code == 201
    assert response.json()["realm_name"] == "sg-mt-us-1"
    assert response.json()["initial_tenant"]["slug"] == "example-org-main"
    assert fake_db.committed is True


def test_create_tenant_requires_platform_admin_and_uses_org_lookup(monkeypatch):
    app = FastAPI()
    app.include_router(iam_orgs.router)
    _override_dependency(app, get_current_request_context, _request_context("PLATFORM_ADMIN"))
    org_id = str(uuid4())
    customer_id = str(uuid4())
    fake_db = FakeDB(
        [
            ResultStub(row=(org_id, customer_id, "sg-mt-us-1")),
        ]
    )
    _override_generator_dependency(app, get_superadmin_db, fake_db)
    monkeypatch.setattr(iam_orgs, "_get_realm_manager", lambda _db: object())

    async def _fake_create_tenant_internal(**kwargs):
        assert kwargs["org_id"] == org_id
        assert kwargs["customer_id"] == customer_id
        assert kwargs["realm_name"] == "sg-mt-us-1"
        return iam_orgs.TenantResponse(
            id=str(uuid4()),
            org_id=org_id,
            realm_name="sg-mt-us-1",
            slug="example-tenant",
            keycloak_org_id="kc-org-2",
            keycloak_group_id="kc-group-2",
            status="active",
        )

    monkeypatch.setattr(iam_orgs, "create_tenant_internal", _fake_create_tenant_internal)
    client = TestClient(app)

    response = client.post(
        f"/api/iam-portal/organizations/{org_id}/tenants",
        headers={"authorization": "Bearer test-token"},
        json={
            "tenant_name": "Example Tenant",
            "tenant_slug": "example-tenant",
            "region": "us",
        },
    )

    assert response.status_code == 201
    assert response.json()["org_id"] == org_id
    assert fake_db.calls[0]["params"]["org_id"] == org_id
    assert fake_db.committed is True


def test_create_organization_uses_superadmin_db(monkeypatch):
    app = FastAPI()
    app.include_router(iam_orgs.router)
    _override_dependency(app, get_current_request_context, _request_context("PLATFORM_ADMIN"))
    fake_db = FakeDB(
        [
            ResultStub(row=None),
            ResultStub(row=None),
            ResultStub(),
            ResultStub(),
            ResultStub(),
        ]
    )
    _override_generator_dependency(app, get_superadmin_db, fake_db)
    monkeypatch.setattr(iam_orgs, "_get_realm_manager", lambda _db: object())
    monkeypatch.setattr(iam_orgs, "_pick_realm", lambda *_args, **_kwargs: "sg-mt-us-1")

    async def _fake_create_tenant_internal(**kwargs):
        return iam_orgs.TenantResponse(
            id=str(uuid4()),
            org_id=kwargs["org_id"],
            realm_name=kwargs["realm_name"],
            slug="example-org-main",
            keycloak_org_id="kc-org-1",
            keycloak_group_id="kc-group-1",
            status="active",
        )

    monkeypatch.setattr(iam_orgs, "create_tenant_internal", _fake_create_tenant_internal)
    client = TestClient(app)

    response = client.post(
        "/api/iam-portal/organizations",
        headers={"authorization": "Bearer test-token"},
        json={
            "name": "Example Org",
            "display_name": "Example Org",
            "realm_strategy": "shared",
            "region": "us",
            "projected_user_count": 25,
        },
    )

    assert response.status_code == 201
    assert fake_db.committed is True
    assert any("INSERT INTO organizations" in call["sql"] for call in fake_db.calls)
