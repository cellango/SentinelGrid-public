"""Synthetic readback/lifecycle boundaries; no real issuer/provider or custody proof."""

from datetime import datetime, timedelta, timezone
from copy import deepcopy
import json
from types import SimpleNamespace

from fastapi import HTTPException
from pydantic import SecretStr, ValidationError
import pytest

from sg_core.workload_read_client import FixedTicketReadClient
from sg_core.workload_registration import (
    IssuerReadbackSettings,
    IssuerRegistrationReader,
    LocalCredentialLease,
    RegistrationObservation,
)
from test_fixed_ticket_read import (
    boundary,
    keys,
    CLIENT_UUID,
    SUBJECT,
    FOREIGN,
    SECRET,
    ADMIN,
    TENANT,
)

CP = "/clients/" + CLIENT_UUID
UP = "/users/" + SUBJECT


def assert_no_mint_or_data(b):
    assert not any(
        r.url.path.endswith("/token") or r.url.host == "ticket.internal.test"
        for r in b.requests
    )
    assert not b.opened


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", FOREIGN),
        ("clientId", "foreign"),
        ("enabled", False),
        ("enabled", 1),
        ("publicClient", True),
        ("serviceAccountsEnabled", False),
        ("standardFlowEnabled", True),
        ("implicitFlowEnabled", True),
        ("directAccessGrantsEnabled", True),
        ("authorizationServicesEnabled", True),
        ("fullScopeAllowed", True),
        ("redirectUris", ["https://foreign.test"]),
        ("webOrigins", ["*"]),
        ("defaultClientScopes", ["roles"]),
        ("optionalClientScopes", ["offline_access"]),
        ("attributes", {}),
        ("clientAuthenticatorType", "client-jwt"),
        ("protocol", "saml"),
        ("authenticationFlowBindingOverrides", {"browser": FOREIGN}),
        ("authorizationSettings", {"allowRemoteResourceManagement": True}),
    ],
)
def test_client_policy_drift_stops_before_token(boundary, field, value):
    b = boundary
    b.registration[CP][field] = value
    with pytest.raises(HTTPException):
        b.caller.fetch()
    assert_no_mint_or_data(b)


@pytest.mark.parametrize(
    "kind",
    [
        "missing",
        "extra",
        "duplicate",
        "tenant",
        "audience",
        "request",
        "json_type",
        "config",
        "conflicting_embedded",
    ],
)
def test_mapper_drift_or_ambiguity_cannot_mint(boundary, kind):
    b = boundary
    ms = b.registration[CP + "/protocol-mappers/models"]
    if kind == "missing":
        ms.pop()
    elif kind == "extra":
        ms.append(
            dict(
                name="extra",
                protocol="openid-connect",
                protocolMapper="oidc-usermodel-property-mapper",
                config={},
            )
        )
    elif kind == "duplicate":
        ms.append(deepcopy(ms[0]))
    elif kind == "conflicting_embedded":
        b.registration[CP]["protocolMappers"] = []
    else:
        name = {
            "tenant": "tenant_id",
            "request": "sg_request",
            "json_type": "sg_permissions",
        }.get(kind)
        mapper = next((m for m in ms if m["config"].get("claim.name") == name), ms[-1])
        if kind == "audience":
            mapper["config"]["included.custom.audience"] = "account"
        elif kind == "json_type":
            mapper["config"]["jsonType.label"] = "String"
        elif kind == "config":
            mapper["config"]["unknown"] = "true"
        else:
            mapper["config"]["claim.value"] = "foreign"
    with pytest.raises(HTTPException):
        b.caller.fetch()
    assert_no_mint_or_data(b)


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", FOREIGN),
        ("enabled", False),
        ("enabled", 1),
        ("serviceAccountClientId", "foreign"),
        ("serviceAccountClientId", None),
        ("username", "service-account-foreign"),
        ("attributes", {"tenant_id": [FOREIGN]}),
    ],
)
def test_subject_association_cannot_be_inferred_from_name_or_config(
    boundary, field, value
):
    b = boundary
    b.registration[UP][field] = value
    with pytest.raises(HTTPException):
        b.caller.fetch()
    assert_no_mint_or_data(b)


def test_stock24_missing_relationship_is_unavailable_without_auto_creating_GET(
    boundary,
):
    b = boundary
    del b.registration[UP]["serviceAccountClientId"]
    with pytest.raises(HTTPException):
        b.caller.fetch()
    assert_no_mint_or_data(b)
    assert not any("service-account-user" in r.url.path for r in b.requests)


@pytest.mark.parametrize(
    "path,value",
    [
        (CP + "/default-client-scopes", [{"name": "roles"}]),
        (CP + "/optional-client-scopes", [{"name": "offline_access"}]),
        (UP + "/groups", [{"id": FOREIGN}]),
        (UP + "/role-mappings/realm/composite", [{"name": "admin"}]),
        (CP + "/scope-mappings", {"realmMappings": [{"name": "admin"}]}),
        (UP + "/role-mappings", {"clientMappings": {"realm-management": {}}}),
        (UP + "/role-mappings", {"unknown": []}),
        (UP + "/groups", {}),
    ],
)
def test_direct_or_inherited_grants_and_incompatible_shapes_deny(boundary, path, value):
    b = boundary
    b.registration[path] = value
    with pytest.raises(HTTPException):
        b.caller.fetch()
    assert_no_mint_or_data(b)


@pytest.mark.parametrize("status", [301, 302, 307, 401, 403, 404, 429, 500])
def test_management_failures_no_retry_fallback_or_empty_success(boundary, status):
    b = boundary
    b.admin_status = status
    with pytest.raises(HTTPException) as exc:
        b.caller.fetch()
    assert exc.value.status_code == 503 and SECRET not in str(exc.value)
    assert sum(str(r.url).startswith(ADMIN) for r in b.requests) == 1
    assert_no_mint_or_data(b)


@pytest.mark.parametrize(
    "body", [b'{"id":"a","id":"b"}', b'{"x":NaN}', b'{"x":1e999}', b"x" * 131073, b"[]"]
)
def test_bounded_strict_management_JSON(boundary, body):
    b = boundary
    b.admin_content = body
    with pytest.raises(HTTPException):
        b.caller.fetch()
    assert_no_mint_or_data(b)


@pytest.mark.parametrize(
    "change",
    [
        {"sub": FOREIGN},
        {"azp": "ticket-reader"},
        {"tenant_id": FOREIGN},
        {"sg_principal_type": "user"},
        {"sg_identity_contract": "keycloak-user-v1"},
        {"sg_permissions": ["iam.manage_workload_registration"]},
        {"sg_registration_target": {}},
        {"aud": ["review-client"]},
        {"aud": ["review-client", "realm-management", "account"]},
        {"act": {"sub": SUBJECT}},
        {"resource_access": {"realm-management": {"roles": ["realm-admin"]}}},
        {"scope": "offline_access"},
        {"jti": "ambiguous"},
        {"exp": 1},
        {"realm_access": {"roles": ["admin"]}},
    ],
)
def test_wrong_management_authority_never_contacts_issuer(boundary, change):
    b = boundary
    b.management_claims.update(change)
    b.configure_management()
    with pytest.raises(HTTPException):
        b.caller.fetch()
    assert_no_mint_or_data(b)
    assert not any(str(r.url).startswith(ADMIN) for r in b.requests)


def test_management_forgery_denied_by_current_IAM(boundary):
    b = boundary
    b.configure_management(forged=True)
    with pytest.raises(HTTPException):
        b.caller.fetch()
    assert_no_mint_or_data(b)
    assert len(b.requests) == 1


def test_default_disabled_readback_no_transport(boundary):
    b = boundary
    values = b.readback_config.model_dump()
    values.pop("enabled")
    reader = IssuerRegistrationReader(
        IssuerReadbackSettings(**values), SecretStr(b.management_token), b.verifier
    )
    with pytest.raises(HTTPException):
        reader.inspect(b.config, b.verifier)
    assert not b.requests


def test_disabled_registration_observable_but_never_dispatchable(boundary):
    b = boundary
    b.registration[CP]["enabled"] = False
    b.readback_config = b.readback_config.model_copy(
        update={"expected_client_enabled": False}
    )
    b.configure_management()
    observation = b.reader.inspect(b.config, b.verifier)
    assert observation.enabled is False and observation.subject_id == SUBJECT
    assert len(observation.policy_sha256) == 64 and SECRET not in repr(observation)
    with pytest.raises(HTTPException):
        b.caller.fetch()
    assert_no_mint_or_data(b)


def test_no_reader_or_constructed_observation_is_an_admission_channel(boundary):
    b = boundary
    for reader in [
        None,
        RegistrationObservation(CLIENT_UUID, SUBJECT, True, 0, "invented"),
        SimpleNamespace(inspect=lambda *a: True),
    ]:
        caller = FixedTicketReadClient(
            b.config, b.lease, b.verifier, registration=reader
        )
        with pytest.raises(HTTPException):
            caller.fetch()
    with pytest.raises(ValueError):
        FixedTicketReadClient(
            b.config, SecretStr(SECRET), b.verifier, registration=b.reader
        )
    assert not b.requests


@pytest.mark.parametrize(
    "change",
    [
        {"client_uuid": "alias"},
        {"management_subject_id": SUBJECT},
        {"management_client_id": "ticket-reader"},
        {"management_issuer": "https://foreign.test/realms/synthetic"},
        {"timeout_seconds": 11.0},
        {"ca_bundle": ""},
        {"extra": "unowned"},
    ],
)
def test_owned_settings_are_exact_and_management_identity_separate(boundary, change):
    with pytest.raises(ValidationError):
        IssuerReadbackSettings(**{**boundary.readback_config.model_dump(), **change})


@pytest.mark.parametrize("kind", ["expired", "revoked", "foreign_binding"])
def test_local_credential_unavailability_prevents_any_transport(boundary, kind):
    b = boundary
    if kind == "expired":
        b.lease._expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    elif kind == "revoked":
        b.lease.revoke_locally(expected_version=1)
    else:
        b.lease._binding = b.binding.model_copy(update={"tenant_id": FOREIGN})
    with pytest.raises(HTTPException):
        b.caller.fetch()
    assert not b.requests


def test_revocation_during_readback_stops_before_token(boundary):
    b = boundary

    def revoke(path):
        if path == UP + "/role-mappings":
            b.lease.revoke_locally(expected_version=1)

    b.admin_hook = revoke
    with pytest.raises(HTTPException):
        b.caller.fetch()
    assert_no_mint_or_data(b)


def test_version_change_during_token_request_stops_data(boundary):
    b = boundary
    b.token_hook = lambda: b.lease.replace_locally(
        SecretStr("SYNTHETIC_REPLACEMENT_ONLY"),
        expected_version=1,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
    )
    with pytest.raises(HTTPException):
        b.caller.fetch()
    assert sum(r.url.path.endswith("/token") for r in b.requests) == 1
    assert (
        not any(r.url.host == "ticket.internal.test" for r in b.requests)
        and not b.opened
    )


def test_local_CAS_replacement_and_terminal_revocation_are_not_provider_rotation(
    boundary,
):
    b = boundary
    until = datetime.now(timezone.utc) + timedelta(minutes=1)
    assert (
        b.lease.replace_locally(
            SecretStr("SYNTHETIC_REPLACEMENT_ONLY"),
            expected_version=1,
            expires_at=until,
        )
        == 2
    )
    with pytest.raises(HTTPException):
        b.lease.require_current(b.binding, 1)
    with pytest.raises(HTTPException):
        b.lease.replace_locally(
            SecretStr("OTHER_SYNTHETIC"), expected_version=1, expires_at=until
        )
    assert b.lease.revoke_locally(expected_version=2) == 3
    with pytest.raises(HTTPException):
        b.lease.replace_locally(
            SecretStr("OTHER_SYNTHETIC"), expected_version=3, expires_at=until
        )
    with pytest.raises(HTTPException):
        b.lease.snapshot(b.binding)
    assert not b.requests


@pytest.mark.parametrize(
    "version,secret,expiry",
    [
        (
            True,
            SecretStr("synthetic"),
            datetime.now(timezone.utc) + timedelta(minutes=1),
        ),
        (0, SecretStr("synthetic"), datetime.now(timezone.utc) + timedelta(minutes=1)),
        (1, "raw", datetime.now(timezone.utc) + timedelta(minutes=1)),
        (1, SecretStr(""), datetime.now(timezone.utc) + timedelta(minutes=1)),
        (1, SecretStr("x" * 4097), datetime.now(timezone.utc) + timedelta(minutes=1)),
        (
            1,
            SecretStr("line\nbreak"),
            datetime.now(timezone.utc) + timedelta(minutes=1),
        ),
        (1, SecretStr("nonasciié"), datetime.now(timezone.utc) + timedelta(minutes=1)),
        (1, SecretStr("synthetic"), datetime.now()),
    ],
)
def test_local_lease_requires_protected_secret_version_and_aware_future_expiry(
    boundary, version, secret, expiry
):
    with pytest.raises(ValueError):
        LocalCredentialLease(
            boundary.binding, secret, version=version, expires_at=expiry
        )


def test_every_fetch_observes_drift_again_and_metadata_cookie_does_not_escape(boundary):
    b = boundary
    assert b.caller.fetch()[0]["tenant_id"] == TENANT
    before = len(b.requests)
    b.registration[CP]["fullScopeAllowed"] = True
    with pytest.raises(HTTPException):
        b.caller.fetch()
    assert not any(r.url.path.endswith("/token") for r in b.requests[before:])
    assert len(b.opened) == 1
