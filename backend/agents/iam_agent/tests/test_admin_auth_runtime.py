from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.iam_orgs as iam_orgs
import app.api.payment as payment
from app.core.config import KeycloakAdminAuthConfigError
import app.api.realms as realms
import app.services.keycloak_admin_factory as keycloak_admin_factory


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def fetchone(self):
        return self._row


class _PaymentFakeDb:
    def __init__(self, lead):
        self.lead = dict(lead)
        self.customer_insert = None
        self.tenant_insert = None
        self.converted_update = None
        self.commits = 0
        self.closed = False

    def execute(self, statement, params=None):
        sql = str(statement).lower()
        params = params or {}

        if "from leads" in sql:
            return _FakeResult(dict(self.lead))
        if "select id from tenants where slug" in sql:
            return _FakeResult(None)
        if "insert into customers" in sql:
            self.customer_insert = dict(params)
            return _FakeResult(None)
        if "insert into tenants" in sql:
            self.tenant_insert = dict(params)
            return _FakeResult(None)
        if "update leads" in sql and "status = 'converted'" in sql:
            self.converted_update = dict(params)
            self.lead["status"] = "converted"
            return _FakeResult(None)

        return _FakeResult(None)

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


def test_build_keycloak_admin_uses_service_account_when_enabled(monkeypatch):
    with patch("app.services.keycloak_admin_factory.KeycloakAdmin") as mock_admin:
        monkeypatch.setattr(keycloak_admin_factory.settings, "KEYCLOAK_URL", "https://keycloak.internal")
        monkeypatch.setattr(keycloak_admin_factory.settings, "KEYCLOAK_VERIFY_TLS", True)
        monkeypatch.setattr(keycloak_admin_factory.settings, "KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT", True)
        monkeypatch.setattr(keycloak_admin_factory.settings, "KEYCLOAK_ADMIN_CLIENT_ID", "iam-agent")
        monkeypatch.setattr(keycloak_admin_factory.settings, "KEYCLOAK_ADMIN_CLIENT_SECRET", "svc-secret")
        monkeypatch.setattr(keycloak_admin_factory.settings, "KEYCLOAK_ADMIN_TOKEN_REALM", "ops")

        client = keycloak_admin_factory.build_keycloak_admin(realm_name="master")

    assert client is mock_admin.return_value
    kwargs = mock_admin.call_args.kwargs
    assert kwargs["grant_type"] == "client_credentials"
    assert kwargs["client_id"] == "iam-agent"
    assert kwargs["client_secret_key"] == "svc-secret"
    assert kwargs["user_realm_name"] == "ops"
    assert kwargs["realm_name"] == "master"
    assert kwargs["verify"] is True
    assert "username" not in kwargs
    assert "password" not in kwargs


def test_build_keycloak_admin_rejects_password_grant_in_production(monkeypatch):
    monkeypatch.setattr(keycloak_admin_factory.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(keycloak_admin_factory.settings, "KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT", False)

    with pytest.raises(KeycloakAdminAuthConfigError, match="disabled in production"):
        keycloak_admin_factory.build_keycloak_admin(realm_name="master")


def test_realms_get_keycloak_admin_uses_shared_factory(monkeypatch):
    previous_admin = realms._keycloak_admin
    sentinel_admin = object()
    realms._keycloak_admin = None
    factory_mock = Mock(return_value=sentinel_admin)

    try:
        monkeypatch.setattr(realms, "build_keycloak_admin", factory_mock)
        result = realms.get_keycloak_admin()
    finally:
        realms._keycloak_admin = previous_admin

    assert result is sentinel_admin
    factory_mock.assert_called_once_with(realm_name="master")


def test_iam_orgs_get_realm_manager_uses_shared_factory(monkeypatch):
    sentinel_admin = object()
    factory_mock = Mock(return_value=sentinel_admin)
    db = object()

    with patch("app.api.iam_orgs.MultiTenantRealmManager") as mock_manager:
        monkeypatch.setattr(iam_orgs, "build_keycloak_admin", factory_mock)
        result = iam_orgs._get_realm_manager(db)

    assert result is mock_manager.return_value
    factory_mock.assert_called_once_with(realm_name="master")
    mock_manager.assert_called_once_with(sentinel_admin, db)


def test_payment_success_uses_keycloak_admin_client_for_dedicated_realm(monkeypatch):
    lead = {
        "id": "lead-123",
        "email": "buyer@example.com",
        "company_name": "Acme",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "password_hash": "hash",
        "user_count": 25,
        "user_band": "1-25",
        "compliance_required": True,
        "package_name": "protect_defend_comply",
        "estimated_price_cents": 149900,
        "status": "payment_started",
        "stripe_session_id": "dev_session_lead-123",
        "metadata": {
            "provisioning_token": "opaque-provisioning-token",
            "plan_tier": "protect_defend_comply",
            "services_selected": {"socManaged": False},
            "tenant_slug": "acme",
        },
        "expires_at": datetime.utcnow() + timedelta(days=7),
    }
    fake_db = _PaymentFakeDb(lead)

    def fake_sessionmaker(*args, **kwargs):
        return lambda: fake_db

    class FakeRealmManager:
        instances = []

        def __init__(self, admin):
            self.admin = admin
            self.created = []
            FakeRealmManager.instances.append(self)

        def _generate_realm_name(self, _company_name):
            return "sg-ent-acme"

        async def create_dedicated_realm(self, realm_name, customer_data):
            self.created.append((realm_name, customer_data))
            return True

    class FakeKeycloakAdminClient:
        instances = []

        def __init__(self):
            self.calls = []
            FakeKeycloakAdminClient.instances.append(self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def create_user(self, **kwargs):
            self.calls.append(("create_user", kwargs))
            return "kc-user-1"

        async def set_user_password(self, realm, user_id, password, temporary=False):
            self.calls.append(
                (
                    "set_user_password",
                    {
                        "realm": realm,
                        "user_id": user_id,
                        "password": password,
                        "temporary": temporary,
                    },
                )
            )

        async def assign_realm_role(self, realm, user_id, role_name):
            self.calls.append(
                (
                    "assign_realm_role",
                    {"realm": realm, "user_id": user_id, "role_name": role_name},
                )
            )

        async def get_user_by_username(self, realm, username, exact=True):
            self.calls.append(
                (
                    "get_user_by_username",
                    {"realm": realm, "username": username, "exact": exact},
                )
            )
            return {
                "id": "kc-user-1",
                "requiredActions": ["UPDATE_PASSWORD"],
            }

    build_admin_mock = Mock(return_value=object())

    monkeypatch.setattr(payment, "create_engine", lambda *args, **kwargs: object())
    monkeypatch.setattr(payment, "sessionmaker", fake_sessionmaker)
    monkeypatch.setattr(payment.settings, "DB_URL", "postgresql://test")
    monkeypatch.setattr(payment.settings, "PAYMENT_DEV_MODE", True)
    monkeypatch.setattr(payment.settings, "STRIPE_SECRET_KEY", None)
    monkeypatch.setattr(payment, "RealmManager", FakeRealmManager)
    monkeypatch.setattr(payment, "KeycloakAdminClient", FakeKeycloakAdminClient)
    monkeypatch.setattr(payment, "build_keycloak_admin", build_admin_mock)

    app = FastAPI()
    app.include_router(payment.router)
    client = TestClient(app)

    response = client.post(
        "/api/v1/payment/success",
        json={
            "session_id": "dev_session_lead-123",
            "lead_id": "lead-123",
            "provisioning_token": "opaque-provisioning-token",
        },
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["password_reset_required"] is True
    assert response.json()["user_verified"] is True
    assert response.json()["dev_mode"] is True
    assert fake_db.commits == 1
    assert fake_db.closed is True
    assert fake_db.customer_insert["has_dedicated_realm"] is True
    assert fake_db.customer_insert["package_name"] == "protect_defend_comply"
    assert fake_db.customer_insert["plan_tier"] == "protect_defend_comply"
    assert fake_db.tenant_insert["slug"] == "acme"
    assert fake_db.tenant_insert["package_name"] == "protect_defend_comply"
    assert fake_db.tenant_insert["plan_tier"] == "protect_defend_comply"
    build_admin_mock.assert_called_once_with(realm_name="master")
    assert FakeRealmManager.instances[0].created == [
        (
            "sg-ent-acme",
            {
                "name": "Acme",
                "package_name": "protect_defend_comply",
                "compliance_required": True,
            },
        )
    ]
    assert FakeKeycloakAdminClient.instances[0].calls == [
        (
            "create_user",
            {
                "realm": "sg-ent-acme",
                "username": "buyer@example.com",
                "email": "buyer@example.com",
                "first_name": "Ada",
                "last_name": "Lovelace",
                "enabled": True,
                "email_verified": False,
                "attributes": {
                    "tenant_id": [fake_db.converted_update["tenant_id"]],
                    "customer_id": [fake_db.converted_update["customer_id"]],
                },
                "required_actions": ["UPDATE_PASSWORD"],
            },
        ),
        (
            "set_user_password",
            {
                "realm": "sg-ent-acme",
                "user_id": "kc-user-1",
                "password": "TempPassword123!",
                "temporary": True,
            },
        ),
        (
            "assign_realm_role",
            {"realm": "sg-ent-acme", "user_id": "kc-user-1", "role_name": "TENANT_ADMIN"},
        ),
        (
            "get_user_by_username",
            {"realm": "sg-ent-acme", "username": "buyer@example.com", "exact": True},
        ),
    ]
