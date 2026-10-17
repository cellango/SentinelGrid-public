"""Real HTTPX request/response boundary, with synthetic in-memory transport only."""

import asyncio
from uuid import uuid4
import httpx
import pytest
from fastapi import HTTPException
from app.core.config import settings, Settings
from app.services.role_directory_service import RoleDirectoryService


@pytest.fixture
def directory(monkeypatch):
    tenant, user = uuid4(), uuid4()
    calls = []
    monkeypatch.setattr(settings, "IAM_ROLE_SYNC_REALMS", {str(tenant): "tenant-test"})
    monkeypatch.setattr(settings, "KEYCLOAK_URL", "https://identity.example.test")
    monkeypatch.setattr(settings, "KEYCLOAK_VERIFY_TLS", True)
    data = {
        "user": {
            "id": str(user),
            "enabled": True,
            "attributes": {"tenant_id": [str(tenant)]},
        },
        "roles": [{"name": "reader"}],
    }

    def handler(request):
        calls.append(request)
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "synthetic-observation"})
        assert request.headers["Authorization"] == "Bearer synthetic-observation"
        if request.url.path.endswith("/composite"):
            return httpx.Response(200, json=data["roles"])
        if request.url.path.endswith("/users"):
            return httpx.Response(
                200,
                json=[{"id": str(user)}] if request.url.params["first"] == "0" else [],
            )
        return httpx.Response(200, json=data["user"])

    return (
        RoleDirectoryService(transport=httpx.MockTransport(handler)),
        tenant,
        user,
        data,
        calls,
    )


def test_single_snapshot_uses_configured_realm_and_verified_membership(directory):
    client, tenant, user, _, calls = directory
    result = asyncio.run(client.observe(tenant, user))
    assert (
        result[0].tenant_id == tenant
        and result[0].user_id == user
        and result[0].roles == ("reader",)
    )
    assert all(
        "/admin/realms/tenant-test/" in r.url.path for r in calls if r.method == "GET"
    )
    assert [r.method for r in calls] == ["POST", "GET", "GET"]


def test_disabled_user_observation_has_no_roles(directory):
    client, tenant, user, data, _ = directory
    data["user"]["enabled"] = False
    assert asyncio.run(client.observe(tenant, user))[0].roles == ()


@pytest.mark.parametrize(
    "change",
    [
        {"id": str(uuid4())},
        {"enabled": "true"},
        {"attributes": {}},
        {"attributes": {"tenant_id": []}},
        {"attributes": {"tenant_id": ["not-uuid"]}},
        {"attributes": {"tenant_id": [str(uuid4()), str(uuid4())]}},
    ],
)
def test_malformed_user_is_not_membership_proof(directory, change):
    client, tenant, user, data, _ = directory
    data["user"].update(change)
    with pytest.raises(HTTPException) as error:
        asyncio.run(client.observe(tenant, user))
    assert error.value.status_code == 503


def test_foreign_tenant_is_rejected_without_overwrite(directory):
    client, tenant, user, data, _ = directory
    data["user"]["attributes"]["tenant_id"] = [str(uuid4())]
    with pytest.raises(HTTPException) as error:
        asyncio.run(client.observe(tenant, user))
    assert error.value.status_code == 403


@pytest.mark.parametrize(
    "roles",
    [
        None,
        {},
        [{"name": None}],
        [{"name": " "}],
        [{"name": "x" * 101}],
        [{"name": "reader"}] * 101,
    ],
)
def test_invalid_or_excessive_roles_fail_closed(directory, roles):
    client, tenant, user, data, _ = directory
    data["roles"] = roles
    with pytest.raises(HTTPException) as error:
        asyncio.run(client.observe(tenant, user))
    assert error.value.status_code == 503


def test_missing_realm_mapping_performs_no_request(directory, monkeypatch):
    client, tenant, user, _, calls = directory
    monkeypatch.setattr(settings, "IAM_ROLE_SYNC_REALMS", {})
    with pytest.raises(HTTPException) as error:
        asyncio.run(client.observe(tenant, user))
    assert error.value.status_code == 503 and calls == []


@pytest.mark.parametrize(
    "failure", ["redirect", "outage", "timeout", "oversize", "invalid_json"]
)
def test_transport_failure_cannot_become_empty_role_success(directory, failure):
    _, tenant, user, _, _ = directory

    def handler(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("Synthetic timeout")
        if failure == "redirect":
            return httpx.Response(
                302, headers={"location": "https://untrusted.example.test"}
            )
        if failure == "outage":
            return httpx.Response(503)
        if failure == "oversize":
            return httpx.Response(200, content=b" " * 1048577)
        return httpx.Response(200, content=b"not json")

    client = RoleDirectoryService(transport=httpx.MockTransport(handler))
    with pytest.raises(HTTPException) as error:
        asyncio.run(client.observe(tenant, user))
    assert error.value.status_code == 503


def test_bulk_continues_after_short_page_to_empty_page(directory):
    client, tenant, user, _, calls = directory
    result = asyncio.run(client.observe(tenant))
    assert [s.user_id for s in result] == [user]
    pages = [r.url.params["first"] for r in calls if r.url.path.endswith("/users")]
    assert pages == ["0", "1"]


@pytest.mark.parametrize(
    "mapping",
    [
        {"tenant-slug": "realm"},
        {str(uuid4()): "../other"},
        {str(uuid4()): ".."},
        {str(uuid4()): ""},
    ],
)
def test_realm_configuration_requires_uuid_and_path_safe_realm(mapping):
    with pytest.raises(ValueError):
        Settings(_env_file=None, IAM_ROLE_SYNC_REALMS=mapping)
