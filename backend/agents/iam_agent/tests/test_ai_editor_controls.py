"""Synthetic model/gateway and authority adversaries; no live providers or DB."""

import asyncio
import copy
import inspect
import json
from unittest.mock import Mock, AsyncMock
from uuid import uuid4
import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from app.api import ai_editor, policies, protocols, ai_features, ai_chat
from app.api.auth import get_keycloak_client, get_token_validator
from app.api.request_context import (
    RequestContext,
    get_current_request_context,
    get_entitlement_session,
)
from app.core.config import settings, Settings
from app.models.ai_editor import GenerateRequest, ExplainRequest
from app.models.policies import EvaluationContext
from app.services.ai_policy_service import (
    AIPolicyService,
    EditorModelGateway,
    strict_json,
)
from app.services.policy_service import PolicyService
from app.services.protocol_manager import ProtocolManager
from app.services.integration_manager import IntegrationManager


def draft():
    return {
        "id": "draft-policy",
        "type": "access",
        "scope": "tenant",
        "rules": [
            {
                "id": "rule-1",
                "conditions": [{"type": "role", "op": "includes", "value": "reader"}],
                "actions": [{"type": "deny"}],
            }
        ],
    }


def model_result():
    return {
        "policy_dsl": draft(),
        "explanation": "Untrusted draft; requires human review.",
    }


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setattr(settings, "IAM_ENABLE_AI_EDITOR", True)
    context = RequestContext(uuid4(), str(uuid4()), ("TENANT_ADMIN",))
    db = Mock()
    rows = []
    db.add.side_effect = rows.append
    provider = Mock()
    provider.generate = AsyncMock(return_value=json.dumps(model_result()))
    app = FastAPI()
    for router in [
        ai_editor.router,
        policies.router,
        protocols.router,
        ai_features.router,
        ai_chat.router,
    ]:
        app.include_router(router)
    app.dependency_overrides[get_current_request_context] = lambda: context
    app.dependency_overrides[get_entitlement_session] = lambda: db
    service = AIPolicyService(db, provider=provider)
    app.dependency_overrides[ai_editor.get_editor_service] = lambda: service
    return context, db, rows, provider, app, TestClient(app)


def call(setup, operation="generate", request=None, context=None):
    caller, db, _, provider, _, _ = setup
    request = request or GenerateRequest(description="Deny access to readers")
    return asyncio.run(
        AIPolicyService(db, provider=provider).assist(
            operation, request, context or caller
        )
    )


def test_draft_is_not_published_and_uses_real_actor_audit(setup):
    context, db, rows, provider, _, client = setup
    response = client.post(
        "/api/v1/ai/editor/generate", json={"description": "Deny access to readers"}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["tenant_id"] == str(context.tenant_id)
    assert result["status"] == "draft" and result["review_required"]
    assert result["published"] is False and result["enforced"] is False
    assert result["policy_effects_executed"] == []
    assert response.headers["cache-control"] == "no-store"
    assert [r.event_type for r in rows] == [
        "ai_editor_requested",
        "ai_editor_completed",
    ]
    assert all(
        str(r.performed_by) == context.user_id and r.tenant_id == context.tenant_id
        for r in rows
    )
    assert all(r.changes["request_id"] == result["request_id"] for r in rows)
    assert db.commit.call_count == 2
    db.execute.assert_not_called()
    assert provider.generate.call_args.args[1] == context.tenant_id
    assert "Deny access to readers" not in str([r.changes for r in rows])
    # The owning deterministic evaluator accepts the same DSL without allowing
    # model text to become context/roles. It yields deny for the selected rule.
    dsl = PolicyService._parse_policy_dsl(result["policy_dsl"])
    policy = PolicyService(None, context.tenant_id, "")
    assert policy._evaluate_rule(dsl.rules[0], EvaluationContext(roles=["reader"]))


@pytest.mark.parametrize(
    "roles,user",
    [((), "uuid"), (("INTERNAL_SERVICE",), None), (("TENANT_ADMIN",), "bad")],
)
def test_direct_service_rechecks_identity_before_model_or_audit(setup, roles, user):
    context, db, _, provider, _, _ = setup
    with pytest.raises(HTTPException) as error:
        call(
            setup,
            context=RequestContext(
                context.tenant_id, context.user_id if user == "uuid" else user, roles
            ),
        )
    assert error.value.status_code in (401, 403)
    provider.generate.assert_not_called()
    db.add.assert_not_called()


@pytest.mark.parametrize(
    "body",
    [
        {"tenant_id": str(uuid4())},
        {"approved": True},
        {"roles": ["PLATFORM_ADMIN"]},
        {"context": {"tenant_id": str(uuid4())}},
        {"publish": True},
        {"realm": "master"},
        {"description": "x" * 2001},
        {"description": 123},
    ],
)
def test_authority_and_unbounded_fields_are_rejected(setup, body):
    _, _, _, provider, _, client = setup
    response = client.post(
        "/api/v1/ai/editor/generate",
        json={"description": "Deny access to readers", **body},
    )
    assert response.status_code == 422
    provider.generate.assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [
        {"mode": "playbook"},
        {"scope": "app"},
        {"policy_type": "signon"},
    ],
)
def test_unsupported_generation_never_calls_model(setup, payload):
    _, _, _, provider, _, client = setup
    response = client.post(
        "/api/v1/ai/editor/generate",
        json={"description": "Deny access to readers", **payload},
    )
    assert response.status_code == 501
    provider.generate.assert_not_called()


@pytest.mark.parametrize("endpoint", ["analyze", "suggest", "validate-nl"])
def test_unqualified_operations_have_no_model_dependency(setup, endpoint):
    _, db, _, provider, _, client = setup
    response = client.post("/api/v1/ai/editor/" + endpoint, json={"mode": "policy"})
    assert response.status_code == 501
    provider.generate.assert_not_called()
    db.add.assert_not_called()


@pytest.mark.parametrize(
    "mutation",
    [
        "tenant",
        "approval",
        "extra",
        "empty",
        "duplicates",
        "action",
        "condition",
        "script",
        "scope",
        "many",
    ],
)
def test_model_cannot_expand_supported_draft_contract(setup, mutation):
    result = copy.deepcopy(model_result())
    p = result["policy_dsl"]
    if mutation == "tenant":
        p["tenant_id"] = str(uuid4())
    elif mutation == "approval":
        result["approved"] = True
    elif mutation == "extra":
        result["published"] = True
    elif mutation == "empty":
        p["rules"] = []
    elif mutation == "duplicates":
        p["rules"] *= 2
    elif mutation == "action":
        p["rules"][0]["actions"] = [{"type": "notify"}]
    elif mutation == "condition":
        p["rules"][0]["conditions"][0]["op"] = "not_in"
    elif mutation == "script":
        p["rules"][0]["actions"][0]["params"] = {"code": "execute"}
    elif mutation == "scope":
        p["scope"] = "app"
    elif mutation == "many":
        p["rules"] = [{**p["rules"][0], "id": str(i)} for i in range(21)]
    setup[3].generate.return_value = json.dumps(result)
    with pytest.raises(HTTPException) as error:
        call(setup)
    assert error.value.status_code == 502
    assert [r.event_type for r in setup[2]] == [
        "ai_editor_requested",
        "ai_editor_failed",
    ]
    setup[1].execute.assert_not_called()


@pytest.mark.parametrize(
    "raw",
    ["not JSON", "```json\n{}\n```", '{"x":1,"x":2}', '{"x":NaN}', "[]", "x" * 32769],
)
def test_invalid_model_responses_have_no_fallback_success(setup, raw):
    setup[3].generate.return_value = raw
    with pytest.raises(HTTPException) as error:
        call(setup)
    assert error.value.status_code == 502


def test_gateway_exception_is_generic_and_audited(setup):
    setup[3].generate.side_effect = HTTPException(
        503, "synthetic secret provider error"
    )
    with pytest.raises(HTTPException) as error:
        call(setup)
    assert error.value.status_code == 503
    assert "synthetic secret" not in str(error.value.detail)
    assert "synthetic secret" not in str([r.changes for r in setup[2]])


@pytest.mark.parametrize("failure", ["flush", "commit", "completion_commit"])
def test_audit_failure_withholds_output_and_preflight_prevents_transmission(
    setup, failure
):
    db, provider = setup[1], setup[3]
    if failure == "flush":
        db.flush.side_effect = RuntimeError("audit down")
    elif failure == "commit":
        db.commit.side_effect = RuntimeError("lost ack")
    else:
        db.commit.side_effect = [None, RuntimeError("lost ack")]
    with pytest.raises(HTTPException) as error:
        call(setup)
    assert error.value.status_code == 503 and "audit" in error.value.detail
    assert provider.generate.call_count == (1 if failure == "completion_commit" else 0)
    db.rollback.assert_called_once()


def test_explanation_is_advisory_and_requires_supported_draft(setup):
    setup[3].generate.return_value = json.dumps(
        {"summary": "Advisory only.", "limitations": ["Not a proof of correctness."]}
    )
    result = call(setup, "explain", ExplainRequest(graph_data=draft()))
    assert result["status"] == "advisory" and result["review_required"]
    assert not result["enforced"]


def test_out_of_subset_explanation_does_not_call_model(setup):
    data = draft()
    data["rules"][0]["actions"][0]["type"] = "execute"
    with pytest.raises(HTTPException) as error:
        call(setup, "explain", ExplainRequest(graph_data=data))
    assert error.value.status_code == 422
    setup[3].generate.assert_not_called()


def test_disabled_and_nonadmin_routes_need_no_db_or_model(setup, monkeypatch):
    context, db, _, provider, app, client = setup
    monkeypatch.setattr(settings, "IAM_ENABLE_AI_EDITOR", False)
    assert (
        client.post(
            "/api/v1/ai/editor/generate", json={"description": "Draft a deny rule"}
        ).status_code
        == 501
    )
    app.dependency_overrides[get_current_request_context] = lambda: RequestContext(
        context.tenant_id, context.user_id, ()
    )
    assert (
        client.post(
            "/api/v1/ai/editor/generate", json={"description": "Draft a deny rule"}
        ).status_code
        == 403
    )
    db.add.assert_not_called()
    provider.generate.assert_not_called()


@pytest.mark.parametrize("part", ["nodes", "depth", "size", "nan"])
def test_bounded_input_content(part):
    value = {"nodes": list(range(2001))} if part == "nodes" else {"value": "x" * 32769}
    if part == "depth":
        value = {}
        for _ in range(12):
            value = {"nested": value}
    if part == "nan":
        value = {"value": float("nan")}
    with pytest.raises(ValidationError):
        ExplainRequest(graph_data=value)


def test_authenticated_dependency_cannot_be_replaced_by_body_or_headers(setup):
    _, _, _, provider, app, client = setup
    del app.dependency_overrides[get_current_request_context]
    validator = Mock()
    validator.validate_token.return_value = {"valid": False}
    app.dependency_overrides[get_token_validator] = lambda: validator
    assert (
        client.post(
            "/api/v1/ai/editor/generate",
            headers={"X-Tenant-ID": str(uuid4())},
            json={"description": "Draft a deny rule"},
        ).status_code
        == 401
    )
    provider.generate.assert_not_called()


def envelope(content=None, **choice):
    return {
        "choices": [
            {
                "message": {"content": content or json.dumps(model_result())},
                "finish_reason": "stop",
                **choice,
            }
        ]
    }


def gateway(monkeypatch, handler, url="https://gateway.example.test"):
    monkeypatch.setattr(settings, "IAM_AI_EDITOR_GATEWAY_URL", url)
    monkeypatch.setattr(
        settings,
        "IAM_AI_EDITOR_GATEWAY_TOKEN",
        SecretStr("synthetic-runtime-credential-" + "x" * 24),
    )
    return EditorModelGateway(transport=httpx.MockTransport(handler))


def test_gateway_uses_server_tenant_and_no_tools_or_fallback(monkeypatch):
    tenant = uuid4()
    calls = []

    def handle(request):
        calls.append(request)
        assert request.headers["X-Tenant-ID"] == str(tenant)
        assert request.headers["cache-control"] == "no-store"
        assert "tools" not in json.loads(request.content)
        return httpx.Response(200, json=envelope())

    provider = gateway(monkeypatch, handle)
    result = asyncio.run(provider.generate("synthetic user content", tenant))
    assert strict_json(result) == model_result() and len(calls) == 1


@pytest.mark.parametrize(
    "case",
    [
        "redirect",
        "http_error",
        "timeout",
        "not_json",
        "tool",
        "truncated",
        "multiple",
        "oversize",
        "duplicate",
    ],
)
def test_gateway_failure_is_bounded_generic_no_retry(monkeypatch, case):
    calls = []

    def handle(request):
        calls.append(request)
        if case == "redirect":
            return httpx.Response(
                307, headers={"location": "https://foreign.example.test"}
            )
        if case == "http_error":
            return httpx.Response(500, text="synthetic provider error")
        if case == "timeout":
            raise httpx.ReadTimeout("synthetic provider error")
        if case == "not_json":
            return httpx.Response(200, text="not json")
        if case == "oversize":
            return httpx.Response(200, content=b"x" * 65537)
        if case == "duplicate":
            return httpx.Response(200, text='{"choices":[],"choices":[]}')
        data = envelope()
        if case == "tool":
            data["choices"][0]["message"]["tool_calls"] = [{"name": "publish"}]
        if case == "truncated":
            data["choices"][0]["finish_reason"] = "length"
        if case == "multiple":
            data["choices"] *= 2
        return httpx.Response(200, json=data)

    with pytest.raises(HTTPException) as error:
        asyncio.run(gateway(monkeypatch, handle).generate("test", uuid4()))
    assert error.value.status_code == 503 and len(calls) == 1
    assert "synthetic provider" not in error.value.detail


@pytest.mark.parametrize(
    "url",
    [
        None,
        "http://gateway.example.test",
        "https://user:pass@gateway.example.test",
        "https://gateway.example.test?token=x",
        "https://gateway.example.test#frag",
        "https://[",
        "https://gateway.example.test:invalid",
    ],
)
def test_gateway_requires_explicit_secure_config(monkeypatch, url):
    calls = []
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            gateway(monkeypatch, lambda r: calls.append(r), url=url).generate(
                "test", uuid4()
            )
        )
    assert error.value.status_code == 503 and calls == []


def test_editor_default_off_and_secret_excluded():
    value = Settings(_env_file=None)
    assert value.IAM_ENABLE_AI_EDITOR is False
    assert value.IAM_AI_EDITOR_GATEWAY_URL is None
    assert "IAM_AI_EDITOR_GATEWAY_TOKEN" not in value.model_dump()
    assert (
        Settings.model_config["env_file"] == ".env"
        and Settings.model_config["case_sensitive"] is True
    )


@pytest.mark.parametrize("manager", [ProtocolManager, IntegrationManager])
def test_every_manager_operation_fails_before_provider_call(manager):
    provider = Mock()
    service = manager(provider)
    for name, method in inspect.getmembers(service, inspect.ismethod):
        if name == "__init__":
            continue
        kwargs = {
            n: None
            for n, p in inspect.signature(method).parameters.items()
            if p.default is inspect.Parameter.empty
        }
        with pytest.raises(HTTPException) as error:
            method(**kwargs)
        assert error.value.status_code == 501
    assert provider.mock_calls == []


@pytest.mark.parametrize(
    "method,path,body",
    [
        (
            "post",
            "/internal/iam/protocols/saml",
            {
                "alias": "idp",
                "entity_id": "entity",
                "sso_url": "https://idp.example.test",
                "certificate": "synthetic",
            },
        ),
        (
            "post",
            "/internal/iam/protocols/oauth2",
            {"client_id": "synthetic", "redirect_uris": ["https://app.example.test"]},
        ),
        (
            "post",
            "/internal/iam/protocols/ldap",
            {
                "provider_name": "synthetic",
                "connection_url": "ldaps://directory.example.test",
                "bind_dn": "cn=read",
                "bind_credential": "synthetic",
                "users_dn": "ou=users",
            },
        ),
        ("get", "/internal/iam/protocols/configurations", None),
        ("post", "/internal/iam/protocols/test/id?protocol_type=ldap", None),
        ("get", "/internal/iam/protocols/integrations", None),
        ("post", "/internal/iam/protocols/integrations/id/sync", None),
        ("post", "/internal/iam/protocols/integrations/id/test", None),
        (
            "post",
            "/internal/iam/chat",
            {
                "query": "Connect this application",
                "context": {"onboarding_state": {"approved": True}},
            },
        ),
        (
            "post",
            "/internal/iam/ai/recommendations",
            {"type": "ai", "query": "Publish a policy"},
        ),
        ("get", "/internal/iam/ai/risk/users", None),
        (
            "post",
            "/api/iam-portal/policies/generate",
            {"description": "Draft a deny policy", "policy_type": "access"},
        ),
        ("post", "/api/iam-portal/policies/" + str(uuid4()) + "/explain", None),
        ("get", "/api/iam-portal/policies/" + str(uuid4()) + "/analyze", None),
    ],
)
def test_legacy_paths_never_initialize_provider_or_claim_success(
    setup, method, path, body
):
    _, _, _, provider, app, client = setup

    def forbidden():
        raise AssertionError("provider dependency was constructed")

    app.dependency_overrides[get_keycloak_client] = forbidden
    response = client.request(
        method, path, **({"json": body} if body is not None else {})
    )
    assert response.status_code == 501, response.text
    provider.generate.assert_not_called()


def test_gateway_transport_disables_redirects_proxies_and_requires_tls(monkeypatch):
    original = httpx.AsyncClient
    observed = []

    def client(**kwargs):
        observed.append(kwargs)
        return original(**kwargs)

    provider = gateway(
        monkeypatch, lambda request: httpx.Response(200, json=envelope())
    )
    monkeypatch.setattr(httpx, "AsyncClient", client)
    asyncio.run(provider.generate("synthetic", uuid4()))
    assert observed[0]["verify"] is True
    assert (
        observed[0]["trust_env"] is False and observed[0]["follow_redirects"] is False
    )
    assert observed[0]["timeout"] == 15.0


def test_editor_middleware_defers_to_durable_audit_without_provider_construction(
    setup, monkeypatch
):
    from app.middleware.admin_audit import AdminAuditMiddleware
    from app.services import keycloak_client

    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected realm client")

    monkeypatch.setattr(keycloak_client, "KeycloakClient", forbidden)
    setup[4].add_middleware(AdminAuditMiddleware)
    with TestClient(setup[4]) as client:
        response = client.post(
            "/api/v1/ai/editor/generate", json={"description": "Draft a deny rule"}
        )
        assert response.status_code == 200
        assert len(setup[2]) == 2
        invalid = client.post(
            "/api/v1/ai/editor/generate",
            json={"description": "secret", "credential": "synthetic"},
        )
        assert invalid.status_code == 422 and "synthetic" not in invalid.text
        assert invalid.headers["cache-control"] == "no-store"
