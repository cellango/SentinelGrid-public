"""Exercise real IAM decisions with synthetic storage and no database/network access."""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# The legacy database module runs extension DDL on import. Block that connection;
# actual database/session qualification has its own disposable-database suite.
with patch("sqlalchemy.engine.Engine.connect", side_effect=RuntimeError("DB disabled in policy tests")):
    from app.api import authorize, policies, iam_portal
    from app.api.request_context import RequestContext, get_current_request_context, get_tenant_session
    from app.models.policies import EvaluationContext as PolicyContext, Policy
    from app.services import evaluation_engine
    from app.services.evaluation_engine import EvaluationContext, EvaluationEngine
    from app.services.policy_service import PolicyService
    from app.services.iam_portal_service import IAMPortalService


TENANT = UUID("11111111-1111-4111-8111-111111111111")
USER = UUID("22222222-2222-4222-8222-222222222222")


def policy(actions=("allow",), *, kind="access", conditions=None, priority=100, **kwargs):
    now = datetime.now(timezone.utc)
    data = {"id": "synthetic-policy", "type": kind, "scope": kwargs.get("scope", "tenant"), "rules": [{
        "id": "synthetic-rule", "conditions": conditions or [],
        "actions": [{"type": action} for action in actions],
    }]}
    return Policy(id=uuid4(), tenant_id=TENANT, name="synthetic", display_name="Synthetic",
                  policy_type=kind, policy_data=data, priority=priority,
                  created_at=now, updated_at=now, **kwargs)


def service_with(items):
    service = object.__new__(PolicyService)
    service.db = Mock()
    service.tenant_id = TENANT
    service.list_policies = Mock(side_effect=lambda policy_type=None: [
        p for p in items if policy_type is None or p.policy_type == policy_type
    ])
    service._log_evaluation = Mock()
    return service


def test_no_policy_is_deny():
    assert service_with([]).evaluate_policy("access", PolicyContext()).result == "deny"


@pytest.mark.parametrize("first,second", [(1, 900), (900, 1)])
def test_deny_wins_across_policies_regardless_of_priority(first, second):
    items = [policy(priority=first), policy(("deny",), priority=second)]
    assert service_with(items).evaluate_policy("access", PolicyContext()).result == "deny"


@pytest.mark.parametrize("actions", [("require_mfa", "deny"), ("require_approval", "deny")])
def test_deny_wins_within_action_list(actions):
    assert service_with([policy(actions)]).evaluate_policy("access", PolicyContext()).result == "deny"


def test_deny_wins_across_rules():
    item = policy(("require_mfa",))
    item.policy_data["rules"].append({"id": "late-denial", "conditions": [], "actions": [{"type": "deny"}]})
    assert service_with([item]).evaluate_policy("access", PolicyContext()).result == "deny"


@pytest.mark.parametrize("actions", [("log",), ("notify",), ("unknown",), ("auto_approve",)])
def test_non_grant_actions_never_create_access(actions):
    assert service_with([policy(actions)]).evaluate_policy("access", PolicyContext()).result == "deny"


@pytest.mark.parametrize("invalid", ["malformed", "unknown_operator", "missing_fact", "invalid_operand", "unknown_action", "mismatched_type"])
def test_invalid_or_unavailable_restriction_cannot_be_hidden_by_allow(invalid):
    restriction = policy(("deny",))
    rule = restriction.policy_data["rules"][0]
    if invalid == "malformed":
        restriction.policy_data = {"rules": "invalid"}
    elif invalid == "unknown_operator":
        rule["conditions"] = [{"type": "role", "op": "typo", "value": "reviewer"}]
    elif invalid == "missing_fact":
        rule["conditions"] = [{"type": "country", "op": "equals", "value": "ZZ"}]
    elif invalid == "invalid_operand":
        rule["conditions"] = [{"type": "role", "op": "in", "value": "not-a-list"}]
    elif invalid == "unknown_action":
        rule["actions"] = [{"type": "denny"}]
    else:
        restriction.policy_data["type"] = "sod"
    assert service_with([policy(priority=1), restriction]).evaluate_policy("access", PolicyContext(roles=[])).result == "deny"


def test_all_policies_enforces_configured_sod_without_hardcoded_role_pairs():
    sod = policy(("deny",), kind="sod", conditions=[
        {"type": "role", "op": "includes", "value": role} for role in ("requester", "approver")
    ])
    service = service_with([policy(), sod])
    assert service.evaluate_all_policies(PolicyContext(roles=["requester", "approver"])).result == "deny"
    assert service.evaluate_all_policies(PolicyContext(roles=["requester"])).result == "allow"
    assert service.evaluate_all_policies(PolicyContext()).result == "deny"


def test_sod_allow_alone_cannot_grant_access():
    assert service_with([policy(kind="sod")]).evaluate_all_policies(PolicyContext()).result == "deny"


@pytest.mark.parametrize("scope", ["app", "entitlement"])
def test_scoped_allow_requires_exact_target(scope):
    target = uuid4()
    service = service_with([policy(scope=scope, scope_id=target)])
    assert service.evaluate_all_policies(PolicyContext(resource=str(uuid4()))).result == "deny"
    kwargs = {"resource_type": "app", "resource": str(target)} if scope == "app" else {"entitlement_ids": [str(target)]}
    assert service.evaluate_all_policies(PolicyContext(**kwargs)).result == "allow"


def test_scoped_deny_cannot_be_bypassed_by_uuid_spelling():
    target = uuid4()
    service = service_with([policy(), policy(("deny",), scope="app", scope_id=target)])
    assert service.evaluate_all_policies(PolicyContext(resource_type="app", resource=str(target).upper())).result == "deny"


def test_missing_fact_after_false_condition_is_not_silently_skipped():
    restriction = policy(("deny",), conditions=[
        {"type": "role", "op": "includes", "value": "absent-role"},
        {"type": "country", "op": "equals", "value": "ZZ"},
    ])
    assert service_with([policy(), restriction]).evaluate_all_policies(PolicyContext(roles=[])).result == "deny"


def context(**kwargs):
    return EvaluationContext(USER, TENANT, "document", "synthetic-doc", "read", **kwargs)


def entitlement(**kwargs):
    values = dict(id=uuid4(), tenant_id=TENANT, granted_to_type="user", granted_to_id=USER,
                  resource_type="document", resource_id="synthetic-doc", action="read", status="active",
                  expires_at=None, metadata_json={}, usage_count_90d=0)
    values.update(kwargs)
    return SimpleNamespace(**values)


def engine_with(monkeypatch, items, policies_):
    engine = EvaluationEngine(Mock())
    engine._find_matching_entitlements = Mock(return_value=items)
    service = service_with(policies_)
    monkeypatch.setattr(evaluation_engine, "PolicyService", Mock(return_value=service), raising=False)
    monkeypatch.setattr(evaluation_engine, "AuditLogger", Mock())
    return engine, service


def decide(engine, ctx=None):
    return asyncio.run(engine.evaluate(ctx or context(), use_cache=True))


def test_entitlement_plus_explicit_policy_allows(monkeypatch):
    engine, _ = engine_with(monkeypatch, [entitlement()], [policy()])
    assert decide(engine).decision == "allow"


@pytest.mark.parametrize("actions", [(), ("deny",), ("require_mfa",), ("require_approval",)])
def test_entitlement_cannot_bypass_policy_or_client_fulfill_requirements(monkeypatch, actions):
    engine, _ = engine_with(monkeypatch, [entitlement()], [policy(actions)] if actions else [])
    ctx = context(additional_context={"roles": ["admin"], "mfa_verified": True, "approved": True})
    assert decide(engine, ctx).decision == "deny"


def test_cached_allow_cannot_override_revocation(monkeypatch):
    engine, _ = engine_with(monkeypatch, [], [policy()])
    stale = {"decision": "allow", "reason": "stale", "evaluated_at": datetime.now().isoformat()}
    cache_get = Mock(return_value=stale)
    monkeypatch.setattr(evaluation_engine.cache, "get", cache_get)
    assert decide(engine).decision == "deny"
    cache_get.assert_not_called()


def test_policy_change_is_checked_on_each_request(monkeypatch):
    items = [policy()]
    engine, _ = engine_with(monkeypatch, [entitlement()], items)
    assert decide(engine).decision == "allow"
    items.append(policy(("deny",), kind="sod"))
    assert decide(engine).decision == "deny"


def test_missing_ip_and_spoofed_body_ip_fail_restriction(monkeypatch):
    engine, _ = engine_with(monkeypatch, [entitlement(metadata_json={"allowed_ips": ["192.0.2.1"]})], [policy()])
    assert decide(engine, context(additional_context={"client_ip": "192.0.2.1"})).decision == "deny"


def test_caller_clock_does_not_change_allowed_hours(monkeypatch):
    allowed = (datetime.now(timezone.utc).hour + 12) % 24
    engine, _ = engine_with(monkeypatch, [entitlement(metadata_json={"allowed_hours": [allowed]})], [policy()])
    supplied = datetime.now(timezone.utc).replace(hour=allowed)
    assert decide(engine, context(additional_context={"request_time": supplied})).decision == "deny"


def test_expired_timezone_aware_entitlement_denies(monkeypatch):
    engine, _ = engine_with(monkeypatch, [entitlement(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))], [policy()])
    assert decide(engine).decision == "deny"


def test_entitlement_lookup_failure_denies(monkeypatch):
    engine, _ = engine_with(monkeypatch, [], [policy()])
    engine._find_matching_entitlements.side_effect = RuntimeError("synthetic storage failure")
    assert decide(engine).decision == "deny"


def test_policy_lookup_failure_denies(monkeypatch):
    engine, service = engine_with(monkeypatch, [entitlement()], [policy()])
    service.list_policies.side_effect = RuntimeError("synthetic storage failure")
    assert decide(engine).decision == "deny"


def test_commit_failure_never_returns_allow(monkeypatch):
    engine, _ = engine_with(monkeypatch, [entitlement()], [policy()])
    engine.db.commit.side_effect = RuntimeError("synthetic write failure")
    assert decide(engine).decision == "deny"


def test_wildcard_must_match_remaining_suffix():
    engine = EvaluationEngine(Mock())
    assert not engine._matches_pattern("doc:**:read", "doc:123:delete")
    assert engine._matches_pattern("doc:**:read", "doc:123:read")


@pytest.fixture(params=[False, True], ids=["policy-router", "legacy-portal-router"])
def route_client(monkeypatch, request):
    app = FastAPI()
    app.include_router(authorize.router)
    app.include_router(iam_portal.router if request.param else policies.router)
    app.dependency_overrides[get_current_request_context] = lambda: RequestContext(TENANT, str(USER), ("reviewer",))
    app.dependency_overrides[get_tenant_session] = lambda: Mock()
    app.dependency_overrides[policies.get_current_user_info] = lambda: {
        "tenant_id": str(TENANT), "user_id": str(USER), "realm_name": "synthetic", "roles": ["reviewer"]}
    app.dependency_overrides[iam_portal.get_current_user_info] = app.dependency_overrides[policies.get_current_user_info]
    engine = Mock()
    engine.evaluate = Mock(side_effect=lambda ctx, **_: asyncio.sleep(0, result=evaluation_engine.EvaluationResult("deny", "synthetic")))
    monkeypatch.setattr(authorize, "EvaluationEngine", Mock(return_value=engine))
    return TestClient(app), engine


def request_body(**kwargs):
    return dict(user_id=str(USER), tenant_id=str(TENANT), resource_type="document", resource_id="synthetic-doc", action="read", **kwargs)


@pytest.mark.parametrize("path", ["", "/batch", "/user/entitlements"])
def test_user_cannot_evaluate_another_subject(route_client, path):
    client, engine = route_client
    body = request_body()
    body["user_id"] = str(uuid4())
    if path == "/batch":
        body = {"requests": [body]}
    assert client.post("/api/v1/authorize" + path, json=body).status_code == 403
    engine.evaluate.assert_not_called()


def test_authorize_builds_subject_context_from_verified_claims(route_client):
    client, engine = route_client
    response = client.post("/api/v1/authorize", json=request_body(context={"roles": ["admin"], "client_ip": "192.0.2.1"}))
    assert response.status_code == 200
    ctx = engine.evaluate.call_args.args[0]
    assert ctx.subject_roles == ("reviewer",)
    assert ctx.client_ip != "192.0.2.1"


@pytest.mark.parametrize("path,method,body", [
    ("", "post", {}), ("/" + str(USER), "put", {}),
    ("/" + str(USER) + "/approve", "post", None), ("/" + str(USER) + "/reject", "post", None),
    ("/bundles/" + str(USER) + "/clone", "post", None),
    ("/templates/" + str(USER) + "/create?name=synthetic&display_name=Synthetic", "post", None),
    ("/evaluate?policy_type=access", "post", {"roles": ["admin"]}),
])
def test_policy_mutations_and_simulation_require_admin(route_client, path, method, body):
    client, _ = route_client
    assert client.request(method.upper(), "/api/iam-portal/policies" + path, json=body).status_code == 403


def test_delete_policy_requires_admin(route_client):
    client, _ = route_client
    response = client.delete("/api/iam-portal/policies/" + str(USER))
    # The legacy router has no DELETE operation; the policy router must deny it.
    assert response.status_code in {403, 405}


def test_legacy_simulation_delegates_to_shared_evaluator(monkeypatch):
    service = object.__new__(IAMPortalService)
    service.db, service.tenant_id, service.realm_name = Mock(), TENANT, "synthetic"
    shared = service_with([policy(), policy(("deny",))])
    monkeypatch.setattr("app.services.policy_service.PolicyService", Mock(return_value=shared))
    assert service.evaluate_policy("access", {})["result"] == "deny"


def test_delegation_does_not_borrow_administrator_roles():
    caller = RequestContext(TENANT, str(uuid4()), ("TENANT_ADMIN",))
    request = authorize.AuthorizationRequest(**request_body(context={"roles": ["TENANT_ADMIN"]}))
    assert authorize._evaluation_context(request, caller).subject_roles is None


@pytest.mark.parametrize("metadata", [{"allowed_ips": ""}, {"allowed_hours": ""}, {"allowed_days": [False]}, []])
def test_invalid_entitlement_restrictions_fail_closed(monkeypatch, metadata):
    engine, _ = engine_with(monkeypatch, [entitlement(metadata_json=metadata)], [policy()])
    assert decide(engine).decision == "deny"


def test_foreign_entitlement_cannot_be_used_even_if_lookup_returns_it(monkeypatch):
    engine, _ = engine_with(monkeypatch, [entitlement(tenant_id=uuid4())], [policy()])
    assert decide(engine).decision == "deny"


def test_trusted_subject_roles_drive_sod_in_authorization(monkeypatch):
    sod = policy(("deny",), kind="sod", conditions=[
        {"type": "role", "op": "includes", "value": role} for role in ("requester", "approver")])
    engine, _ = engine_with(monkeypatch, [entitlement()], [policy(), sod])
    assert decide(engine, context(subject_roles=("requester",))).decision == "allow"
    assert decide(engine, context(subject_roles=("requester", "approver"))).decision == "deny"


def test_trusted_peer_ip_can_satisfy_restriction(monkeypatch):
    engine, _ = engine_with(monkeypatch, [entitlement(metadata_json={"allowed_ips": ["192.0.2.1"]})], [policy()])
    assert decide(engine, context(trusted_client_ip="192.0.2.1")).decision == "allow"
