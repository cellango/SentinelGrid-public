from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import protocols
from app.api.request_context import RequestContext, get_current_request_context


class ProtocolManagerSpy:
    def __init__(self):
        self.saml_calls = []
        self.oauth_calls = []
        self.scim_calls = []
        self.ldap_calls = []
        self.list_calls = []
        self.test_calls = []

    def configure_saml_identity_provider(self, **kwargs):
        self.saml_calls.append(kwargs)
        return {
            "alias": kwargs["alias"],
            "protocol": "saml2",
            "status": "configured",
            "entity_id": kwargs["entity_id"],
            "sso_url": kwargs["sso_url"],
            "tenant_id": kwargs["tenant_id"],
            "configured_at": datetime.now(timezone.utc),
        }

    def configure_oauth2_client(self, **kwargs):
        self.oauth_calls.append(kwargs)
        return {
            "client_id": kwargs["client_id"],
            "protocol": "oauth2",
            "status": "configured",
            "redirect_uris": kwargs["redirect_uris"],
            "tenant_id": kwargs["tenant_id"],
            "configured_at": datetime.now(timezone.utc),
        }

    def configure_scim_client(self, **kwargs):
        self.scim_calls.append(kwargs)
        return {
            "scim_endpoint": kwargs["scim_endpoint"],
            "protocol": "scim2",
            "status": "configured",
            "tenant_id": kwargs["tenant_id"],
            "configured_at": datetime.now(timezone.utc),
        }

    def configure_ldap_federation(self, **kwargs):
        self.ldap_calls.append(kwargs)
        return {
            "provider_name": kwargs["provider_name"],
            "protocol": "ldap",
            "status": "configured",
            "connection_url": kwargs["connection_url"],
            "users_dn": kwargs["users_dn"],
            "tenant_id": kwargs["tenant_id"],
            "configured_at": datetime.now(timezone.utc),
        }

    def list_protocol_configurations(self, protocol_type=None, tenant_id=None):
        self.list_calls.append((protocol_type, tenant_id))
        return [{"id": "cfg-1", "tenant_id": tenant_id}]

    def test_protocol_connection(self, config_id, protocol_type, tenant_id=None):
        self.test_calls.append((config_id, protocol_type, tenant_id))
        return {"config_id": config_id, "status": "ok", "tenant_id": tenant_id}


class IntegrationManagerSpy:
    def __init__(self):
        self.ad_calls = []
        self.azure_calls = []
        self.okta_calls = []
        self.list_calls = []
        self.sync_calls = []
        self.test_calls = []

    def create_active_directory_integration(self, **kwargs):
        self.ad_calls.append(kwargs)
        return {
            "integration_id": "ad-1",
            "name": kwargs["name"],
            "type": "active_directory",
            "status": "active",
            "tenant_id": kwargs["tenant_id"],
            "created_at": datetime.now(timezone.utc),
        }

    def create_azure_ad_integration(self, **kwargs):
        self.azure_calls.append(kwargs)
        return {
            "integration_id": "az-1",
            "name": kwargs["name"],
            "type": "azure_ad",
            "status": "active",
            "tenant_id": kwargs["tenant_id"],
            "created_at": datetime.now(timezone.utc),
        }

    def create_okta_integration(self, **kwargs):
        self.okta_calls.append(kwargs)
        return {
            "integration_id": "okta-1",
            "name": kwargs["name"],
            "type": "okta",
            "status": "active",
            "tenant_id": kwargs["tenant_id"],
            "created_at": datetime.now(timezone.utc),
        }

    def list_integrations(self, integration_type=None, tenant_id=None):
        self.list_calls.append((integration_type, tenant_id))
        return [{"integration_id": "int-1", "tenant_id": tenant_id}]

    def sync_integration(self, integration_id, sync_type="full", tenant_id=None):
        self.sync_calls.append((integration_id, sync_type, tenant_id))
        return {
            "integration_id": integration_id,
            "sync_type": sync_type,
            "status": "queued",
            "synced_at": datetime.now(timezone.utc),
            "result": {},
        }

    def test_integration_connection(self, integration_id, tenant_id=None):
        self.test_calls.append((integration_id, tenant_id))
        return {"integration_id": integration_id, "status": "ok", "tenant_id": tenant_id}


@pytest.fixture
def request_context():
    return RequestContext(
        tenant_id=uuid4(),
        user_id=str(uuid4()),
        roles=("TENANT_ADMIN",),
    )


@pytest.fixture
def protocols_test_app(request_context):
    app = FastAPI()
    app.include_router(protocols.router)
    app.dependency_overrides[get_current_request_context] = lambda: request_context
    return app


@pytest.fixture
def protocols_client(protocols_test_app):
    return TestClient(protocols_test_app)


def _override_dependency(app, dependency, value):
    app.dependency_overrides[dependency] = lambda: value


def test_configure_saml_rejects_foreign_body_tenant(protocols_test_app, protocols_client):
    manager = ProtocolManagerSpy()
    _override_dependency(protocols_test_app, protocols.get_protocol_manager, manager)

    response = protocols_client.post(
        "/internal/iam/protocols/saml",
        headers={"authorization": "Bearer test-token"},
        json={
            "alias": "corp-saml",
            "entity_id": "entity",
            "sso_url": "https://idp.example.com/sso",
            "certificate": "cert",
            "tenant_id": str(uuid4()),
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert manager.saml_calls == []


def test_configure_oauth2_rejects_foreign_body_tenant(protocols_test_app, protocols_client):
    manager = ProtocolManagerSpy()
    _override_dependency(protocols_test_app, protocols.get_protocol_manager, manager)

    response = protocols_client.post(
        "/internal/iam/protocols/oauth2",
        headers={"authorization": "Bearer test-token"},
        json={
            "client_id": "client-1",
            "redirect_uris": ["https://app.example.com/callback"],
            "tenant_id": str(uuid4()),
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert manager.oauth_calls == []


def test_list_protocol_configurations_defaults_to_authenticated_tenant(
    protocols_test_app,
    protocols_client,
    request_context,
):
    manager = ProtocolManagerSpy()
    _override_dependency(protocols_test_app, protocols.get_protocol_manager, manager)

    response = protocols_client.get(
        "/internal/iam/protocols/configurations",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 501
    assert manager.list_calls == []


def test_test_protocol_connection_rejects_foreign_query_tenant(
    protocols_test_app,
    protocols_client,
):
    manager = ProtocolManagerSpy()
    _override_dependency(protocols_test_app, protocols.get_protocol_manager, manager)

    response = protocols_client.post(
        f"/internal/iam/protocols/test/cfg-1?protocol_type=saml2&tenant_id={uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert manager.test_calls == []


def test_create_active_directory_integration_rejects_foreign_body_tenant(
    protocols_test_app,
    protocols_client,
):
    manager = IntegrationManagerSpy()
    _override_dependency(protocols_test_app, protocols.get_integration_manager, manager)

    response = protocols_client.post(
        "/internal/iam/protocols/integrations/active-directory",
        headers={"authorization": "Bearer test-token"},
        json={
            "name": "corp-ad",
            "domain": "corp.example.com",
            "ldap_url": "ldaps://corp.example.com",
            "bind_dn": "cn=admin,dc=corp,dc=example,dc=com",
            "bind_password": "secret",
            "users_dn": "ou=users,dc=corp,dc=example,dc=com",
            "tenant_id": str(uuid4()),
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert manager.ad_calls == []


def test_list_integrations_rejects_foreign_query_tenant(
    protocols_test_app,
    protocols_client,
):
    manager = IntegrationManagerSpy()
    _override_dependency(protocols_test_app, protocols.get_integration_manager, manager)

    response = protocols_client.get(
        f"/internal/iam/protocols/integrations?tenant_id={uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert manager.list_calls == []


def test_sync_integration_rejects_foreign_query_tenant(
    protocols_test_app,
    protocols_client,
):
    manager = IntegrationManagerSpy()
    _override_dependency(protocols_test_app, protocols.get_integration_manager, manager)

    response = protocols_client.post(
        f"/internal/iam/protocols/integrations/int-1/sync?tenant_id={uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert manager.sync_calls == []


def test_test_integration_rejects_foreign_query_tenant(
    protocols_test_app,
    protocols_client,
):
    manager = IntegrationManagerSpy()
    _override_dependency(protocols_test_app, protocols.get_integration_manager, manager)

    response = protocols_client.post(
        f"/internal/iam/protocols/integrations/int-1/test?tenant_id={uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert manager.test_calls == []
