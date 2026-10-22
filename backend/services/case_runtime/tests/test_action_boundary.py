import json
import time
from uuid import uuid4
import pytest
from app.authority.contracts import (
    canonical,
    digest,
    ProposalInput,
    proposal_payload,
    strict_json,
)
from app.config import Settings

C = str(uuid4())
P = str(uuid4())
PATH = "/api/v1/cases/" + C + "/action-proposals"


def proposal():
    return dict(
        tool_id="identity.lock_account",
        tool_version="source-preview-v1",
        targets=[dict(kind="identity.user", resource_id=str(uuid4()))],
        parameters={"reason": "Synthetic containment"},
        expected_effect="Account locked",
        risk="high",
        verification={"check": "authoritative directory state"},
        expires_at=int(time.time()) + 300,
    )


@pytest.mark.parametrize(
    "method,path",
    [("POST", PATH), ("GET", PATH + "/" + P), ("POST", PATH + "/" + P + "/approvals")],
)
def test_missing_credentials_never_reach_database(api, method, path):
    r = api.client.request(method, path, json=proposal())
    assert r.status_code == 401 and not api.calls


@pytest.mark.parametrize(
    "claims",
    [
        {"tenant_id": str(uuid4())},
        {"sg_principal_type": "workload"},
        {"sg_identity_contract": "other"},
        {"act": {}},
        {"azp": "service-client"},
        {"typ": "ID"},
    ],
)
def test_signed_but_unqualified_identity_denied(api, claims):
    r = api.client.post(PATH, headers=api.headers(**claims), json=proposal())
    assert r.status_code == 403, r.text


@pytest.mark.parametrize(
    "name,value",
    [
        ("X-User-ID", str(uuid4())),
        ("X-Roles", "PLATFORM_ADMIN"),
        ("X-Tenant-ID", str(uuid4())),
        ("X-Internal-Token", "synthetic"),
        ("X-Realm", "foreign"),
    ],
)
def test_identity_hints_cannot_override_verified_actor(api, name, value):
    r = api.client.post(PATH, headers={**api.headers(), name: value}, json=proposal())
    assert r.status_code == 403, r.text


@pytest.mark.parametrize(
    "extra",
    [
        {"tenant_id": str(uuid4())},
        {"actor_id": str(uuid4())},
        {"requires_approval": False},
        {"policy_version": "owner"},
        {"approved": True},
    ],
)
def test_request_cannot_supply_authority(api, extra):
    r = api.client.post(
        PATH,
        headers={**api.headers(), "Idempotency-Key": str(uuid4())},
        json={**proposal(), **extra},
    )
    assert r.status_code == 422


def test_disabled_service_never_opens_store(api):
    r = api.client.post(
        PATH,
        headers={**api.headers(), "Idempotency-Key": str(uuid4())},
        json=proposal(),
    )
    assert r.status_code == 503 and api.app.state.action_authority is None
    assert api.client.get("/ready").status_code == 503


def test_cookie_and_ambiguous_authorization_denied(api):
    token = api.sign()
    for headers in [
        [("Cookie", "access_token=" + token)],
        [("Authorization", "Bearer " + token), ("Cookie", "a=b")],
        [("Authorization", "Bearer " + token), ("Authorization", "Bearer " + token)],
    ]:
        assert api.client.post(PATH, headers=headers, json=proposal()).status_code in {
            401,
            403,
        }


@pytest.mark.parametrize(
    "raw",
    [
        b'{"tool_id":"one","tool_id":"two"}',
        b'{"parameters":{"a":1,"a":2}}',
        b'{"v":NaN}',
        b'{"v":Infinity}',
        b"x" * 32769,
    ],
)
def test_noncanonical_raw_json_is_rejected(raw):
    with pytest.raises(ValueError):
        strict_json(raw)


@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), 2**60, "\ud800", {"a": 2**80}]
)
def test_unrepresentable_canonical_values_rejected(value):
    with pytest.raises(ValueError):
        canonical(value)


def test_rfc8785_primitive_and_utf16_vectors():
    # RFC8785 section3.2.2; independent fixed bytes, not generated expectations.
    value = {
        "numbers": [333333333.33333329, 1e30, 4.50, 2e-3, 1e-27],
        "string": '\u20ac$\x0f\nA\'B"\\"/',
        "literals": [None, True, False],
    }
    expected = b'{"literals":[null,true,false],"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],"string":"\xe2\x82\xac$\\u000f\\nA\'B\\"\\\\\\"/"}'
    assert canonical(value) == expected
    assert (
        canonical({"\U0001f600": 1, "\ue000": 2, "a": 3})
        == '{"a":3,"\U0001f600":1,"\ue000":2}'.encode()
    )
    assert (
        canonical({"z": -0.0, "b": 1e-7, "a": 1e-6}) == b'{"a":0.000001,"b":1e-7,"z":0}'
    )


def test_bound_payload_hash_changes_with_every_authority_dimension():
    body = ProposalInput.model_validate(proposal())
    args = dict(
        tenant_id=str(uuid4()),
        case_id=C,
        case_revision=1,
        plan_revision=1,
        policy_version="action-policy-v1",
        action_id=str(uuid4()),
        proposal_id=P,
        actor_id=str(uuid4()),
    )
    original = digest(proposal_payload(body, **args))
    for field in args:
        changed = {
            **args,
            field: 2
            if isinstance(args[field], int)
            else "action-policy-v2"
            if field == "policy_version"
            else str(uuid4()),
        }
        assert digest(proposal_payload(body, **changed)) != original
    assert (
        digest({"b": 2, "a": 1})
        == "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
    )


def test_nondev_configuration_requires_owned_tls_and_budget():
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            ACTION_AUTHORITY_ENABLED=True,
            ACTION_AUTHORITY_DATABASE_URL="postgresql+psycopg2://user@localhost/db",
        )


@pytest.mark.parametrize("value", [2**60, "\ud800", {"x": [0] * 257}])
def test_noncanonical_user_payload_returns_validation_error_before_store(api, value):
    body = proposal()
    body["verification"] = {"check": value}
    r = api.client.post(
        PATH,
        headers={**api.headers(), "Idempotency-Key": str(uuid4())},
        content=json.dumps(body).encode(),
    )
    assert r.status_code == 422, r.text


def test_owned_production_settings_allow_only_tls_and_fail_closed_budget():
    from sg_core.http_rate_limit import RateLimitPolicy

    config = Settings(
        _env_file=None,
        ENVIRONMENT="production",
        IAM_AGENT_URL="https://iam.internal.test",
        ACTION_AUTHORITY_ENABLED=True,
        ACTION_AUTHORITY_DATABASE_URL="postgresql+psycopg2://runtime@database.internal.test/app?sslmode=verify-full",
        ACTION_RATE_POLICY=RateLimitPolicy(
            enabled=True,
            fail_closed=True,
            redis_url="rediss://budget.internal.test:6379/0",
        ),
    )
    assert config.ACTION_AUTHORITY_ENABLED


@pytest.mark.parametrize(
    "change",
    [
        {"ACTION_RATE_POLICY": {"enabled": False}},
        {
            "ACTION_RATE_POLICY": {
                "enabled": True,
                "fail_closed": False,
                "redis_url": "rediss://budget.internal.test:6379/0",
            }
        },
        {
            "ACTION_RATE_POLICY": {
                "enabled": True,
                "redis_url": "redis://budget.internal.test:6379/0",
            }
        },
        {
            "ACTION_AUTHORITY_DATABASE_URL": "postgresql+psycopg2://runtime@database.internal.test/app?sslmode=require"
        },
        {
            "ACTION_AUTHORITY_DATABASE_URL": "postgresql+psycopg2://runtime@database.internal.test/app?sslmode=verify-full&sslmode=disable"
        },
    ],
)
def test_production_settings_cannot_weaken_owned_tls_or_budget(change):
    from sg_core.http_rate_limit import RateLimitPolicy

    values = dict(
        ENVIRONMENT="production",
        IAM_AGENT_URL="https://iam.internal.test",
        ACTION_AUTHORITY_ENABLED=True,
        ACTION_AUTHORITY_DATABASE_URL="postgresql+psycopg2://runtime@database.internal.test/app?sslmode=verify-full",
        ACTION_RATE_POLICY=RateLimitPolicy(
            enabled=True,
            fail_closed=True,
            redis_url="rediss://budget.internal.test:6379/0",
        ),
    )
    values.update(change)
    with pytest.raises(ValueError):
        Settings(_env_file=None, **values)
