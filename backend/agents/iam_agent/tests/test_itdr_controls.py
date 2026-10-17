"""ITDR admission, truthful outcomes, provider errors and legacy bypass negatives."""

import asyncio
from datetime import datetime, timedelta, timezone
import importlib
import inspect
from uuid import uuid4
from unittest.mock import Mock, AsyncMock
import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.api import itdr
from app.api.auth import get_token_validator
from app.api.request_context import (
    RequestContext,
    get_current_request_context,
    get_entitlement_session,
)
from app.core.config import settings
from app.schemas.itdr import ThreatSignal, ThreatSignalBatch
from app.services.itdr_service import ITDRService
from app.services.itdr_response_map import ThreatType, THREAT_RESPONSE_MAP
from app.services.role_directory_service import RoleDirectoryService, RoleSnapshot


@pytest.fixture
def setup(monkeypatch):
    caller = RequestContext(uuid4(), str(uuid4()), ("TENANT_ADMIN",))
    user = uuid4()
    monkeypatch.setattr(
        settings, "IAM_ROLE_SYNC_REALMS", {str(caller.tenant_id): "synthetic"}
    )
    db = Mock()
    rows = []
    db.add.side_effect = rows.append
    directory = Mock()
    directory.observe = AsyncMock(
        side_effect=lambda t, u: [
            RoleSnapshot(t, u, (), datetime.now(timezone.utc), "synthetic")
        ]
    )
    return caller, user, db, directory, rows


def signal(user, **kwargs):
    return ThreatSignal(user_id=user, threat_type="account_takeover", **kwargs)


def propose(setup, signals=None, caller=None):
    context, user, db, directory, _ = setup
    return asyncio.run(
        ITDRService(db, directory=directory).propose(
            signals or [signal(user)], caller or context
        )
    )


@pytest.mark.parametrize("threat", list(ThreatType))
def test_all_categories_are_audited_proposals_without_effect_claims(
    setup, threat, monkeypatch
):
    monkeypatch.setenv("IAM_ENABLE_ITDR_AUTO_RESPONSE", "true")
    caller, user, db, directory, rows = setup
    result = propose(setup, [ThreatSignal(user_id=user, threat_type=threat)])[0]
    assert result.actions_executed == [] and result.auto_response_enabled is False
    assert result.soar_incident_id is None and result.status == "proposal_recorded"
    assert result.actions_recorded == ["log_alert"]
    for action in result.advisory_actions + result.enforcement_actions:
        assert action.status == (
            "recorded" if action.action == "log_alert" else "blocked"
        )
    assert rows[0].event_type == "itdr_proposed"
    assert rows[0].performed_by == __import__("uuid").UUID(caller.user_id)
    assert rows[0].subject_id == user and rows[0].tenant_id == caller.tenant_id
    assert rows[0].decision is None
    db.commit.assert_called_once()


@pytest.mark.parametrize(
    "roles,user",
    [((), "valid"), (("INTERNAL_SERVICE",), None), (("TENANT_ADMIN",), "invalid")],
)
def test_service_requires_actual_admin_user(setup, roles, user):
    caller, _, db, directory, _ = setup
    context = RequestContext(
        caller.tenant_id, caller.user_id if user == "valid" else user, roles
    )
    with pytest.raises(HTTPException) as error:
        propose(setup, caller=context)
    assert error.value.status_code in (401, 403)
    directory.observe.assert_not_called()
    db.add.assert_not_called()


@pytest.mark.parametrize(
    "field,value", [("tenant_id", lambda: str(uuid4())), ("realm", lambda: "foreign")]
)
def test_batch_rejects_every_scope_before_provider_or_audit(setup, field, value):
    _, user, db, directory, _ = setup
    with pytest.raises(HTTPException) as error:
        propose(setup, [signal(user), signal(user, **{field: value()})])
    assert error.value.status_code == 403
    directory.observe.assert_not_called()
    db.add.assert_not_called()


@pytest.mark.parametrize(
    "data",
    [
        {"threat_type": "unknown"},
        {"user_id": "../foreign"},
        {"tenant_id": "slug"},
        {"approved": True},
        {"auto_response_enabled": True},
        {"roles": ["PLATFORM_ADMIN"]},
        {"context": {"large": "x" * 2049}},
        {"context": {"nan": float("nan")}},
        {"context": {"nest": [[[[[[[1]]]]]]]}},
    ],
)
def test_untrusted_input_is_typed_and_bounded(data):
    body = dict(user_id=str(uuid4()), threat_type="account_takeover")
    body.update(data)
    with pytest.raises(ValidationError):
        ThreatSignal(**body)


@pytest.mark.parametrize("count", [0, 11])
def test_batch_bounds_are_enforced(count):
    with pytest.raises(ValidationError):
        ThreatSignalBatch(signals=[signal(uuid4()) for _ in range(count)])


@pytest.mark.parametrize(
    "kind",
    [
        "foreign_tenant",
        "foreign_user",
        "stale",
        "future",
        "naive",
        "realm",
        "empty",
        "extra",
    ],
)
def test_unverified_snapshot_never_becomes_a_proposal(setup, kind):
    caller, user, db, directory, rows = setup
    tenant, subject, now, realm = (
        caller.tenant_id,
        user,
        datetime.now(timezone.utc),
        "synthetic",
    )
    if kind == "foreign_tenant":
        tenant = uuid4()
    if kind == "foreign_user":
        subject = uuid4()
    if kind == "stale":
        now -= timedelta(seconds=31)
    if kind == "future":
        now += timedelta(seconds=31)
    if kind == "naive":
        now = now.replace(tzinfo=None)
    if kind == "realm":
        realm = "foreign"
    observations = [RoleSnapshot(tenant, subject, (), now, realm)]
    if kind == "empty":
        observations = []
    if kind == "extra":
        observations *= 2
    directory.observe.side_effect = None
    directory.observe.return_value = observations
    with pytest.raises(HTTPException) as error:
        propose(setup)
    assert error.value.status_code == 503
    assert [r.event_type for r in rows] == ["itdr_rejected"]
    assert rows[0].decision == "deny"
    db.commit.assert_called_once()


@pytest.mark.parametrize(
    "failure",
    [
        HTTPException(403, "private provider details"),
        RuntimeError("private provider details"),
    ],
)
def test_failed_batch_records_rejection_without_partial_proposal(setup, failure):
    caller, user, db, directory, rows = setup
    directory.observe.side_effect = [
        [
            RoleSnapshot(
                caller.tenant_id, user, (), datetime.now(timezone.utc), "synthetic"
            )
        ],
        failure,
    ]
    with pytest.raises(HTTPException) as error:
        propose(setup, [signal(user), signal(uuid4())])
    assert error.value.status_code in (403, 503)
    assert "private provider" not in error.value.detail
    assert [r.event_type for r in rows] == ["itdr_rejected", "itdr_rejected"]
    db.commit.assert_called_once()


@pytest.mark.parametrize("failure", ["flush", "commit"])
def test_audit_outage_prevents_success(setup, failure):
    _, _, db, _, _ = setup
    getattr(db, failure).side_effect = RuntimeError("private database details")
    with pytest.raises(HTTPException) as error:
        propose(setup)
    assert error.value.status_code == 503
    assert "private database" not in error.value.detail
    db.rollback.assert_called_once()


@pytest.mark.parametrize("status", [302, 401, 403, 404, 429, 500])
def test_real_directory_transport_failures_are_audited_and_never_execute(
    setup, monkeypatch, status
):
    caller, user, db, _, rows = setup
    monkeypatch.setattr(settings, "KEYCLOAK_URL", "https://directory.invalid")
    monkeypatch.setattr(
        "app.services.role_directory_service.resolve_keycloak_admin_runtime_auth",
        lambda: Mock(
            user_realm_name="synthetic",
            token_payload={"grant_type": "client_credentials"},
        ),
    )
    calls = []

    def handler(request):
        calls.append((request.method, request.url.path))
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "synthetic-test-token"})
        return httpx.Response(
            status,
            headers={"Location": "https://foreign.invalid"},
            text="private provider detail",
        )

    directory = RoleDirectoryService(transport=httpx.MockTransport(handler))
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            ITDRService(db, directory=directory).propose([signal(user)], caller)
        )
    assert error.value.status_code == 503  # provider HTTP errors are normalized
    assert all(method == "GET" or path.endswith("/token") for method, path in calls)
    assert len(calls) == 2
    assert rows[0].event_type == "itdr_rejected"


def test_route_authentication_and_internal_token_cannot_submit(setup, monkeypatch):
    _, user, db, directory, _ = setup
    app = FastAPI()
    app.include_router(itdr.router)
    validator = Mock()
    validator.validate_token.return_value = {"valid": False}
    app.dependency_overrides[get_token_validator] = lambda: validator
    app.dependency_overrides[get_entitlement_session] = lambda: db
    with TestClient(app) as client:
        assert (
            client.post(
                "/internal/iam/itdr/enforce", json=signal(user).model_dump(mode="json")
            ).status_code
            == 401
        )
        monkeypatch.setattr(settings, "INTERNAL_SERVICE_TOKEN", "synthetic-internal")
        assert (
            client.post(
                "/internal/iam/itdr/enforce",
                headers={
                    "Authorization": "Bearer synthetic-internal",
                    "X-Tenant-ID": str(uuid4()),
                },
                json=signal(user).model_dump(mode="json"),
            ).status_code
            == 401
        )
    db.add.assert_not_called()


def test_routes_use_committed_receipts_and_batch_contract(setup, monkeypatch):
    caller, user, db, directory, _ = setup
    app = FastAPI()
    app.include_router(itdr.router)
    app.dependency_overrides[get_current_request_context] = lambda: caller
    app.dependency_overrides[get_entitlement_session] = lambda: db
    monkeypatch.setattr(
        "app.services.itdr_service.RoleDirectoryService", lambda: directory
    )
    with TestClient(app) as client:
        for path, payload in [
            ("/enforce", signal(user).model_dump(mode="json")),
            ("/enforce/batch", {"signals": [signal(user).model_dump(mode="json")]}),
        ]:
            result = client.post("/internal/iam/itdr" + path, json=payload)
            assert result.status_code == 200, result.text
            row = result.json().get("results", [result.json()])[0]
            assert row["actions_executed"] == [] and row["proposal_id"]
    assert db.commit.call_count == 2


LEGACY = {
    "automated_response": [
        "respond_to_anomaly",
        "_execute_response",
        "_lock_account",
        "_force_mfa",
        "_send_alert",
        "_revoke_sessions",
    ],
    "automated_responses": [
        "process_risk_response",
        "auto_revoke_suspicious_access",
        "_execute_action",
    ],
    "auto_remediation": [
        "remediate_policy_violations",
        "cleanup_stale_access",
        "remediate_compliance_issues",
        "_remediate_over_privileged_user",
        "_remediate_policy_violation",
        "_remediate_expired_entitlement",
        "_remediate_unused_entitlement",
        "_remediate_missing_mfa",
        "_remediate_weak_password_policy",
        "_remediate_excessive_privileges",
        "_remediate_missing_access_review",
    ],
    "workflow_integration": [
        "trigger_soar_playbook",
        "create_automated_approval_workflow",
        "execute_remediation_workflow",
        "get_workflow_status",
        "create_risk_response_playbook",
        "integrate_with_access_review_workflow",
    ],
}


@pytest.mark.parametrize(
    "module,method", [(m, n) for m, names in LEGACY.items() for n in names]
)
def test_legacy_response_entrypoints_and_helpers_cannot_bypass_action_boundary(
    module, method
):
    mod = importlib.import_module("app.services." + module)
    name = {
        "auto_remediation": "AutoRemediationService",
        "workflow_integration": "WorkflowIntegrationService",
    }.get(module, "AutomatedResponseService")
    service = getattr(mod, name).__new__(getattr(mod, name))
    service.keycloak_client = Mock(side_effect=AssertionError("No provider permitted"))
    call = getattr(service, method)
    args = {
        p: None
        for p, v in inspect.signature(call).parameters.items()
        if v.default is inspect.Parameter.empty
    }
    with pytest.raises(HTTPException) as error:
        if inspect.iscoroutinefunction(call):
            asyncio.run(call(**args))
        else:
            call(**args)
    assert error.value.status_code == 503
    service.keycloak_client.assert_not_called()


def test_anomaly_detection_returns_no_effect_claims(monkeypatch):
    from app.api import anomalies

    service = Mock()
    service.detect_anomalies = AsyncMock(
        return_value=[{"risk_score": 99, "anomaly_type": "impossible_travel"}]
    )
    monkeypatch.setattr(anomalies, "AnomalyDetectionService", lambda: service)
    result = asyncio.run(
        anomalies.trigger_anomaly_detection(
            request_context=RequestContext(uuid4(), str(uuid4()), ("TENANT_ADMIN",))
        )
    )
    assert result["actions_taken"] == [] and result["response_status"] == "blocked"


def test_catalog_is_immutable_and_has_exactly_reviewed_categories():
    assert len(THREAT_RESPONSE_MAP) == 10
    with pytest.raises(TypeError):
        THREAT_RESPONSE_MAP[ThreatType.ACCOUNT_TAKEOVER] = None


def test_authority_claims_nested_in_evidence_never_enable_effects(setup):
    _, user, _, _, rows = setup
    result = propose(
        setup,
        [
            signal(
                user,
                context={
                    "approved": True,
                    "auto_response_enabled": True,
                    "roles": ["PLATFORM_ADMIN"],
                },
            )
        ],
    )[0]
    assert result.actions_executed == [] and result.auto_response_enabled is False
    assert rows[0].metadata_json["signal_trust"] == "caller_assertion"


def test_missing_server_realm_map_fails_before_http_and_audits_rejection(
    setup, monkeypatch
):
    caller, user, db, _, rows = setup
    monkeypatch.setattr(settings, "IAM_ROLE_SYNC_REALMS", {})
    transport = httpx.MockTransport(
        lambda request: pytest.fail("No HTTP without realm mapping")
    )
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            ITDRService(
                db, directory=RoleDirectoryService(transport=transport)
            ).propose([signal(user)], caller)
        )
    assert error.value.status_code == 503 and rows[0].event_type == "itdr_rejected"


def test_read_only_provider_observations_can_produce_a_receipt(setup, monkeypatch):
    caller, user, db, _, rows = setup
    monkeypatch.setattr(settings, "KEYCLOAK_URL", "https://directory.invalid")
    monkeypatch.setattr(
        "app.services.role_directory_service.resolve_keycloak_admin_runtime_auth",
        lambda: Mock(
            user_realm_name="synthetic",
            token_payload={"grant_type": "client_credentials"},
        ),
    )
    calls = []

    def handler(request):
        calls.append((request.method, request.url.path))
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "synthetic-test-token"})
        if request.url.path.endswith("/role-mappings/realm/composite"):
            return httpx.Response(200, json=[])
        assert request.url.path == "/admin/realms/synthetic/users/" + str(user)
        return httpx.Response(
            200,
            json={
                "id": str(user),
                "enabled": True,
                "attributes": {"tenant_id": [str(caller.tenant_id)]},
            },
        )

    result = asyncio.run(
        ITDRService(
            db, directory=RoleDirectoryService(transport=httpx.MockTransport(handler))
        ).propose([signal(user)], caller)
    )[0]
    assert result.status == "proposal_recorded" and result.actions_executed == []
    assert len(calls) == 3 and sum(method == "GET" for method, _ in calls) == 2
    assert rows[0].event_type == "itdr_proposed"


def test_rejection_audit_failure_does_not_claim_durable_rejection(setup):
    _, _, db, directory, _ = setup
    directory.observe.side_effect = RuntimeError("Synthetic provider failure")
    db.flush.side_effect = RuntimeError("Synthetic audit failure")
    db.rollback.side_effect = RuntimeError("Synthetic connection failure")
    with pytest.raises(HTTPException) as error:
        propose(setup)
    assert (
        error.value.status_code == 503
        and "audit could not be confirmed" in error.value.detail
    )
    db.commit.assert_not_called()
