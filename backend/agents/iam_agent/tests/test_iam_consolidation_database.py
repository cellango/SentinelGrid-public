"""Actual evaluator on a disposable Flyway target. No runtime wiring change."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from .test_iam_database import databases, store, A, B, USER, GRANT
from .consolidation_qualification.lab import (
    cluster, connect, app_engine, migrate, grant_fixture_access, rows, copy_rows, run,
)
from .consolidation_qualification.models import Base
from app.services.evaluation_engine import EvaluationContext, EvaluationEngine
from app.services.policy_service import PolicyService
from app.models.policies import EvaluationContext as PolicyContext
from sg_core.tenant_session import tenant_session


@pytest.fixture(scope="module")
def target(databases):
    params, _ = databases
    assert migrate(params, "consolidated_test")["migrationsExecuted"] == 9
    assert migrate(params, "consolidated_test", command="validate")["validationSuccessful"]
    grant_fixture_access(params, "consolidated_test")
    engine = app_engine(params, "consolidated_test")
    try:
        yield params, engine
    finally:
        engine.dispose()


@pytest.fixture
def consolidated(store, target):
    params, engine = target
    with connect(params, "consolidated_test") as connection, connection.cursor() as cursor:
        cursor.execute("TRUNCATE policies,policy_rules,entitlements,iam_audit_events CASCADE")
        copy_rows(params, "catalog_test", "policies", cursor)
        copy_rows(params, "catalog_test", "policy_rules", cursor)
        copy_rows(params, "iam_test", "entitlements", cursor)
    return params, sessionmaker(bind=engine), store[2], store[3]


def evaluate(factory, policies=None, tenant=A, user=USER):
    with tenant_session(factory, tenant) as session:
        context = EvaluationContext(user, tenant, "document", "synthetic-doc", "read", actor_id=USER)
        if policies is None:
            return asyncio.run(EvaluationEngine(session, policy_db=session).evaluate(context))
        with tenant_session(policies, tenant) as policy_session:
            return asyncio.run(EvaluationEngine(session, policy_db=policy_session).evaluate(context))


def set_action(params, database, action, *, tenant=A):
    payload = {"id": "synthetic", "type": "access", "rules": [{"id": "rule", "conditions": [], "actions": [{"type": action}]}]}
    with connect(params, database) as connection, connection.cursor() as cursor:
        cursor.execute("UPDATE policies SET policy_data=%s::jsonb WHERE tenant_id=%s", (json.dumps(payload), str(tenant)))


@pytest.mark.parametrize("action,expected", [("allow", "allow"), ("deny", "deny"), ("require_mfa", "deny"), ("require_approval", "deny"), ("unknown", "deny")])
def test_actual_evaluator_parity(consolidated, action, expected):
    params, local, grants, policies = consolidated
    for database in ("catalog_test", "consolidated_test"):
        set_action(params, database, action)
    before, after = evaluate(grants, policies), evaluate(local)
    assert before.decision == after.decision == expected
    assert before.audit_recorded and after.audit_recorded
    assert before.reason == after.reason


def test_policy_challenge_parity_before_final_boundary(consolidated):
    params, local, _, policies = consolidated
    for database in ("catalog_test", "consolidated_test"):
        set_action(params, database, "require_mfa")
    for factory in (policies, local):
        with tenant_session(factory, A) as session:
            result = PolicyService(session, A, "", load_seed_tenant=False).evaluate_all_policies(PolicyContext(user_id=str(USER)))
            assert result.result == "step_up"


@pytest.mark.parametrize("change", ["revoked", "expired", "missing_subject"])
def test_grant_restriction_parity(consolidated, change):
    params, local, grants, policies = consolidated
    user = uuid4() if change == "missing_subject" else USER
    for database in ("iam_test", "consolidated_test"):
        with connect(params, database) as connection, connection.cursor() as cursor:
            if change == "revoked":
                cursor.execute("UPDATE entitlements SET status='revoked' WHERE tenant_id=%s", (str(A),))
            elif change == "expired":
                cursor.execute("UPDATE entitlements SET expires_at=%s WHERE tenant_id=%s", (datetime.now(timezone.utc)-timedelta(seconds=30), str(A)))
    before, after = evaluate(grants, policies, user=user), evaluate(local, user=user)
    assert before.decision == after.decision == "deny"
    assert before.audit_recorded and after.audit_recorded


def test_new_deny_policy_overrides_existing_allow(consolidated):
    _, local, _, _ = consolidated
    assert evaluate(local).decision == "allow"
    with tenant_session(local, A) as session:
        payload = {"id": "new-deny", "type": "authorization", "rules": [{"id": "deny", "conditions": [], "actions": [{"type": "deny"}]}]}
        session.execute(text("INSERT INTO policies (id,tenant_id,name,display_name,policy_type,policy_data) VALUES (:id,:t,'new','New','authorization',:p)"),
                        {"id": uuid4(), "t": A, "p": json.dumps(payload)})
    assert evaluate(local).decision == "deny"
    assert evaluate(local, tenant=B).decision == "allow"


def test_nonowner_tenant_isolation_and_missing_scope(consolidated):
    _, local, _, _ = consolidated
    with local() as session:
        assert session.execute(text("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user")).one() == (False, False, False, False)
        assert session.scalar(text("SELECT count(*) FROM policies")) == 0
        assert session.scalar(text("SELECT count(*) FROM entitlements")) == 0
    for tenant in (A, B):
        with tenant_session(local, tenant) as session:
            assert set(session.scalars(text("SELECT tenant_id FROM policies"))) == {tenant}
            assert set(session.scalars(text("SELECT tenant_id FROM entitlements"))) == {tenant}
            with pytest.raises(DBAPIError):
                with session.begin_nested():
                    session.execute(text("UPDATE policies SET tenant_id=:other"), {"other": B if tenant == A else A})


def test_parent_tenant_blocks_forged_child(consolidated):
    params, local, _, _ = consolidated
    foreign = next(row["id"] for row in rows(params, "consolidated_test", "policies") if row["tenant_id"] == str(B))
    with tenant_session(local, A) as session:
        with pytest.raises(DBAPIError):
            with session.begin_nested():
                session.execute(text("INSERT INTO policy_rules (id,policy_id,rule_id,conditions,actions) VALUES (:id,:p,'forged','[]','[]')"), {"id": uuid4(), "p": foreign})


def test_atomic_policy_grant_rollback(consolidated):
    _, local, _, _ = consolidated
    with pytest.raises(RuntimeError, match="injected"):
        with tenant_session(local, A) as session:
            session.execute(text("UPDATE policies SET is_active=false"))
            session.execute(text("UPDATE entitlements SET status='revoked'"))
            raise RuntimeError("injected before commit")
    assert evaluate(local).decision == "allow"
    with tenant_session(local, A) as session:
        session.execute(text("UPDATE policies SET is_active=false"))
        session.execute(text("UPDATE entitlements SET status='revoked'"))
    assert evaluate(local).decision == "deny"


def test_copy_preserves_exact_rows_and_does_not_copy_templates(consolidated):
    params, _, _, _ = consolidated
    for source, table in (("catalog_test", "policies"), ("catalog_test", "policy_rules"), ("iam_test", "entitlements")):
        assert rows(params, source, table) == rows(params, "consolidated_test", table)
    with connect(params, "consolidated_test") as connection, connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.policy_templates')")
        assert cursor.fetchone()[0] is None


def test_duplicate_copy_rolls_back_prior_changes(consolidated):
    params, local, _, _ = consolidated
    from psycopg2.errors import UniqueViolation
    with pytest.raises(UniqueViolation):
        with connect(params, "consolidated_test") as connection, connection.cursor() as cursor:
            cursor.execute("UPDATE policies SET is_active=false")
            copy_rows(params, "iam_test", "entitlements", cursor)
    assert evaluate(local).decision == "allow"


def test_models_match_native_migration(target):
    _, engine = target
    inspector = inspect(engine)
    for table in Base.metadata.sorted_tables:
        actual = {c["name"]: c for c in inspector.get_columns(table.name, schema="public")}
        assert set(actual) == set(table.columns.keys())
        for column in table.columns:
            assert actual[column.name]["nullable"] == column.nullable
            assert (actual[column.name]["default"] is not None) == (column.server_default is not None)
            assert str(actual[column.name]["type"].compile(dialect=engine.dialect)).lower() == str(column.type.compile(dialect=engine.dialect)).lower()
        assert inspector.get_pk_constraint(table.name, schema="public")["constrained_columns"] == ["id"]
    assert inspector.get_foreign_keys("policy_rules", schema="public")[0]["referred_table"] == "policies"


def test_recognized_upgrade_preserves_existing_grant_and_flyway_retry(target):
    params, _ = target
    assert migrate(params, "fresh_test", target="17")["migrationsExecuted"] == 8
    with connect(params, "fresh_test") as connection, connection.cursor() as cursor:
        cursor.execute("INSERT INTO entitlements (id,tenant_id,resource_type,resource_id,action,granted_to_type,granted_to_id,granted_by) VALUES (%s,%s,'document','synthetic-doc','read','user',%s,%s)", tuple(map(str, (GRANT, A, USER, USER))))
    before = rows(params, "fresh_test", "entitlements")
    assert migrate(params, "fresh_test")["migrationsExecuted"] == 1
    assert rows(params, "fresh_test", "entitlements") == before
    assert migrate(params, "fresh_test")["migrationsExecuted"] == 0
    assert migrate(params, "fresh_test", command="validate")["validationSuccessful"]


def test_dump_restore_preserves_decisions_audit_and_rows(consolidated):
    params, local, _, _ = consolidated
    assert evaluate(local).decision == "allow"
    set_action(params, "consolidated_test", "deny")
    assert evaluate(local).decision == "deny"
    before = {table: rows(params, "consolidated_test", table) for table in ("policies", "policy_rules", "entitlements", "iam_audit_events")}
    bindir = Path(os.environ["SG_TEST_PG_BINDIR"])
    dump = Path(params["host"]).parent / "consolidated.dump"
    args = ["-h", params["host"], "-p", str(params["port"]), "-U", params["user"]]
    run([str(bindir / "pg_dump"), *args, "-Fc", "-f", str(dump), "consolidated_test"])
    run([str(bindir / "pg_restore"), *args, "--exit-on-error", "-d", "restored_test", str(dump)])
    for table, expected in before.items():
        assert rows(params, "restored_test", table) == expected
    assert migrate(params, "restored_test", command="validate")["validationSuccessful"]
    engine = app_engine(params, "restored_test")
    try:
        assert evaluate(sessionmaker(bind=engine)).decision == "deny"
    finally:
        engine.dispose()

# Atomic runtime mutation qualification uses both current and consolidated stores.
@pytest.fixture(params=["split", "consolidated"])
def mutation_store(consolidated, request):
    params, local, _, policies = consolidated
    if request.param == "split":
        return params, policies, "catalog_test"
    return params, local, "consolidated_test"


def mutation_payload(marker="first", action="allow"):
    return {"id": marker, "type": "access", "rules": [{"id": marker, "conditions": [], "actions": [{"type": action}]}]}


def create_request(marker="first"):
    from app.models.policies import PolicyCreate
    return PolicyCreate(name=marker, display_name=marker, policy_type="access", policy_data=mutation_payload(marker))


def policy_snapshot(params, database):
    return {name: rows(params, database, name) for name in ("policies", "policy_rules")}


def test_atomic_create_update_success(mutation_store):
    from app.models.policies import PolicyUpdate
    params, factory, database = mutation_store
    with tenant_session(factory, A) as session:
        service = PolicyService(session, A, "", load_seed_tenant=False)
        created = service.create_policy(create_request(), str(USER))
        assert created is not None
        assert service.update_policy(created.id, PolicyUpdate(policy_data=mutation_payload("second", "deny")))
    data = policy_snapshot(params, database)
    parent = next(p for p in data["policies"] if p["id"] == str(created.id))
    children = [r for r in data["policy_rules"] if r["policy_id"] == str(created.id)]
    assert parent["policy_data"]["rules"][0]["id"] == "second"
    assert [r["rule_id"] for r in children] == ["second"]
    assert children[0]["actions"][0]["type"] == "deny"


@pytest.mark.parametrize("stage", ["before_rules", "after_rule_delete", "after_rule_insert"])
def test_failed_create_rolls_back_parent_and_rules(mutation_store, monkeypatch, stage):
    params, factory, database = mutation_store
    before = policy_snapshot(params, database)
    with tenant_session(factory, A) as session:
        service = PolicyService(session, A, "", load_seed_tenant=False)
        execute = session.execute
        def failing(statement, *args, **kwargs):
            sql = str(statement)
            if stage == "before_rules" and "DELETE FROM policy_rules" in sql:
                raise RuntimeError("synthetic extraction failure")
            result = execute(statement, *args, **kwargs)
            if (stage == "after_rule_delete" and "DELETE FROM policy_rules" in sql) or (stage == "after_rule_insert" and "INSERT INTO policy_rules" in sql):
                raise RuntimeError("synthetic extraction failure")
            return result
        monkeypatch.setattr(session, "execute", failing)
        assert service.create_policy(create_request(), str(USER)) is None
    assert policy_snapshot(params, database) == before


@pytest.mark.parametrize("stage", ["after_rule_delete", "after_parent_update"])
def test_failed_update_restores_previous_policy_and_rules(mutation_store, monkeypatch, stage):
    from app.models.policies import PolicyUpdate
    params, factory, database = mutation_store
    with tenant_session(factory, A) as session:
        created = PolicyService(session, A, "", load_seed_tenant=False).create_policy(create_request(), str(USER))
        assert created
    before = policy_snapshot(params, database)
    with tenant_session(factory, A) as session:
        service = PolicyService(session, A, "", load_seed_tenant=False)
        execute = session.execute
        def failing(statement, *args, **kwargs):
            result = execute(statement, *args, **kwargs)
            sql = str(statement)
            if (stage == "after_rule_delete" and "DELETE FROM policy_rules" in sql) or (stage == "after_parent_update" and "UPDATE policies" in sql):
                raise RuntimeError("synthetic update failure")
            return result
        monkeypatch.setattr(session, "execute", failing)
        assert not service.update_policy(created.id, PolicyUpdate(policy_data=mutation_payload("replacement")))
    assert policy_snapshot(params, database) == before


def test_invalid_dsl_and_missing_or_foreign_ids_do_not_write(mutation_store):
    from app.models.policies import PolicyCreate, PolicyUpdate
    params, factory, database = mutation_store
    before = policy_snapshot(params, database)
    foreign = next(p["id"] for p in before["policies"] if p["tenant_id"] == str(B))
    own = next(p["id"] for p in before["policies"] if p["tenant_id"] == str(A))
    with tenant_session(factory, A) as session:
        service = PolicyService(session, A, "", load_seed_tenant=False)
        invalid = {"id": "bad", "type": "access", "rules": []}
        assert service.create_policy(PolicyCreate(name="bad", display_name="bad", policy_type="access", policy_data=invalid), str(USER)) is None
        assert not service.update_policy(own, PolicyUpdate(policy_data=invalid))
        for identifier in (foreign, uuid4()):
            assert not service.update_policy(identifier, PolicyUpdate(policy_data=mutation_payload()))
            assert not service.update_policy(identifier, PolicyUpdate())
            with pytest.raises(ValueError, match="not available"):
                service._extract_and_store_rules(identifier, mutation_payload())
    assert policy_snapshot(params, database) == before


def test_template_clone_inherits_atomic_create(mutation_store, monkeypatch):
    from types import SimpleNamespace
    params, factory, database = mutation_store
    template_id = uuid4()
    template = SimpleNamespace(id=template_id, description="Synthetic catalog template", policy_type="access", template_data=mutation_payload("clone"))
    with tenant_session(factory, A) as session:
        service = PolicyService(session, A, "", load_seed_tenant=False)
        # Publication/visibility is not under test; existing tenant-template suite covers it.
        monkeypatch.setattr(service, "list_templates", lambda: [template])
        cloned = service.create_policy_from_template(template_id, "clone", "Clone", str(USER))
        assert cloned
        assert service.create_policy_from_template(uuid4(), "absent", "Absent", str(USER)) is None
    before = policy_snapshot(params, database)
    with tenant_session(factory, A) as session:
        service = PolicyService(session, A, "", load_seed_tenant=False)
        monkeypatch.setattr(service, "list_templates", lambda: [template])
        extract = service._extract_and_store_rules
        def fail_after_rules(*args):
            extract(*args)
            raise RuntimeError("synthetic clone failure")
        monkeypatch.setattr(service, "_extract_and_store_rules", fail_after_rules)
        assert service.create_policy_from_template(template_id, "failed", "Failed", str(USER)) is None
    assert policy_snapshot(params, database) == before


def test_api_failure_envelopes_and_success(mutation_store):
    from app.api import policies as api
    from app.models.policies import PolicyUpdate
    from fastapi import HTTPException
    _, factory, _ = mutation_store
    with tenant_session(factory, A) as session:
        service = PolicyService(session, A, "", load_seed_tenant=False)
        created = asyncio.run(api.create_policy(create_request("api"), service, str(USER)))
        updated = asyncio.run(api.update_policy(created.id, PolicyUpdate(display_name="Updated"), service))
        assert updated.display_name == "Updated"
        with pytest.raises(HTTPException) as error:
            asyncio.run(api.update_policy(uuid4(), PolicyUpdate(), service))
        assert error.value.status_code == 400


@pytest.mark.parametrize("portal_second", [False, True])
def test_concurrent_updates_serialize_policy_and_rules(mutation_store, monkeypatch, portal_second):
    from concurrent.futures import ThreadPoolExecutor
    from queue import Queue
    from threading import Event
    import time
    from app.models.policies import PolicyUpdate
    params, factory, database = mutation_store
    with tenant_session(factory, A) as session:
        created = PolicyService(session, A, "", load_seed_tenant=False).create_policy(create_request(), str(USER))
        assert created
    entered, release = Event(), Event()
    second_pid = Queue()
    second_engine = app_engine(params, database)  # independent pool: prove DB locking, not pool queuing
    second_factory = sessionmaker(bind=second_engine)
    def first():
        with tenant_session(factory, A) as session:
            service = PolicyService(session, A, "", load_seed_tenant=False)
            extract = service._extract_and_store_rules
            def pause(*args):
                entered.set()
                assert release.wait(8), "test coordinator timeout"
                return extract(*args)
            service._extract_and_store_rules = pause
            return service.update_policy(created.id, PolicyUpdate(policy_data=mutation_payload("one")))
    def second():
        with tenant_session(second_factory, A) as session:
            second_pid.put(session.scalar(text("SELECT pg_backend_pid()")))
            session.execute(text("SET LOCAL lock_timeout='8s'"))
            if portal_second:
                from app.models.iam_portal import PolicyUpdate as PortalUpdate
                return make_portal(session, A, monkeypatch).update_policy(created.id, PortalUpdate(policy_data=mutation_payload("two")))
            return PolicyService(session, A, "", load_seed_tenant=False).update_policy(created.id, PolicyUpdate(policy_data=mutation_payload("two")))
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            one = pool.submit(first)
            try:
                assert entered.wait(5)
                two = pool.submit(second)
                pid = second_pid.get(timeout=5)
                deadline = time.monotonic() + 5
                blocked = False
                while time.monotonic() < deadline:
                    with connect(params, database) as connection, connection.cursor() as cursor:
                        cursor.execute("SELECT cardinality(pg_blocking_pids(%s)) > 0", (pid,))
                        blocked = cursor.fetchone()[0]
                    if blocked:
                        break
                    time.sleep(0.02)
                assert blocked, "second writer did not wait on the PostgreSQL row lock"
            finally:
                release.set()
            assert one.result(timeout=5) and two.result(timeout=5)
    finally:
        release.set()
        second_engine.dispose()
    snapshot = policy_snapshot(params, database)
    parent = next(p for p in snapshot["policies"] if p["id"] == str(created.id))
    children = [r for r in snapshot["policy_rules"] if r["policy_id"] == str(created.id)]
    assert parent["policy_data"]["rules"][0]["id"] == "two"
    assert [r["rule_id"] for r in children] == ["two"]


def test_rule_helper_does_not_commit_callers_transaction(mutation_store):
    params, factory, database = mutation_store
    with tenant_session(factory, A) as session:
        created = PolicyService(session, A, "", load_seed_tenant=False).create_policy(create_request(), str(USER))
        assert created
    before = policy_snapshot(params, database)
    with pytest.raises(RuntimeError, match="caller aborted"):
        with tenant_session(factory, A) as session:
            PolicyService(session, A, "", load_seed_tenant=False)._extract_and_store_rules(created.id, mutation_payload("uncommitted"))
            raise RuntimeError("caller aborted")
    assert policy_snapshot(params, database) == before


def test_failure_before_commit_rolls_back_complete_create(mutation_store, monkeypatch):
    params, factory, database = mutation_store
    before = policy_snapshot(params, database)
    with tenant_session(factory, A) as session:
        service = PolicyService(session, A, "", load_seed_tenant=False)
        def fail_commit():
            raise RuntimeError("synthetic failure before commit")
        with monkeypatch.context() as scoped:
            scoped.setattr(session, "commit", fail_commit)
            assert service.create_policy(create_request("commit-failure"), str(USER)) is None
    assert policy_snapshot(params, database) == before


def make_portal(session, tenant, monkeypatch):
    from types import SimpleNamespace
    from app.services import iam_portal_service as portal
    # Provider boundary unused in this storage test; never initialize real admin credentials.
    monkeypatch.setattr(portal, "KeycloakRoleClient", lambda: SimpleNamespace(realm="synthetic"))
    return portal.IAMPortalService(session, tenant, "synthetic")


def portal_request(marker="portal"):
    from app.models.iam_portal import PolicyCreate
    return PolicyCreate(name=marker, display_name=marker, policy_type="access",
                        policy_data=mutation_payload(marker), approval_required=True)


def test_portal_create_and_expanded_update_preserve_fields(mutation_store, monkeypatch):
    from app.models.iam_portal import PolicyUpdate
    params, factory, database = mutation_store
    scope_id = uuid4()
    with tenant_session(factory, A) as session:
        service = make_portal(session, A, monkeypatch)
        created = service.create_policy(portal_request(), str(USER))
        assert created and created.approval_required and created.approval_status == "approved"
        data = mutation_payload("expanded")
        data.update(type="authorization", scope="app", scope_id=str(scope_id))
        updated = service.update_policy(created.id, PolicyUpdate(name="renamed", display_name="Renamed", description="Description",
            policy_type="authorization", scope="app", scope_id=scope_id, policy_data=data,
            priority=7, is_active=False, approval_required=True, approval_status="pending"))
        assert updated
        assert (updated.name, updated.display_name, updated.description) == ("renamed", "Renamed", "Description")
        assert (updated.policy_type, updated.scope, updated.scope_id) == ("authorization", "app", scope_id)
        assert (updated.priority, updated.is_active, updated.approval_required, updated.approval_status) == (7, False, True, "pending")
    before_rules = rows(params, database, "policy_rules")
    with tenant_session(factory, A) as session:
        service = make_portal(session, A, monkeypatch)
        approved = service.update_policy(created.id, PolicyUpdate(approval_required=False, approval_status="approved"))
        assert approved and not approved.approval_required and approved.approval_status == "approved"
        # None retains existing values, matching historical COALESCE behavior.
        unchanged = service.update_policy(created.id, PolicyUpdate(description=None, scope_id=None))
        assert unchanged and unchanged.description == "Description" and unchanged.scope_id == scope_id
    assert rows(params, database, "policy_rules") == before_rules
    own_rules = [r for r in before_rules if r["policy_id"] == str(created.id)]
    assert [r["rule_id"] for r in own_rules] == ["expanded"]


@pytest.mark.parametrize("operation", ["create", "update", "clone"])
def test_portal_rule_failure_rolls_back_whole_operation(mutation_store, monkeypatch, operation):
    from app.models.iam_portal import PolicyUpdate
    params, factory, database = mutation_store
    with tenant_session(factory, A) as session:
        original = make_portal(session, A, monkeypatch).create_policy(portal_request("original"), str(USER))
        assert original
        session.execute(text("UPDATE policies SET is_template=true WHERE id=:id"), {"id": original.id})
    before = policy_snapshot(params, database)
    with tenant_session(factory, A) as session:
        service = make_portal(session, A, monkeypatch)
        execute = session.execute
        def failing(statement, *args, **kwargs):
            result = execute(statement, *args, **kwargs)
            if "INSERT INTO policy_rules" in str(statement):
                raise RuntimeError("synthetic portal child failure")
            return result
        monkeypatch.setattr(session, "execute", failing)
        if operation == "create":
            assert service.create_policy(portal_request("failed"), str(USER)) is None
        elif operation == "update":
            assert service.update_policy(original.id, PolicyUpdate(name="failed", policy_data=mutation_payload("failed"))) is None
        else:
            assert service.create_policy_from_template(original.id, "failed", "Failed", str(USER)) is None
    assert policy_snapshot(params, database) == before


def test_portal_clone_uses_real_tenant_template_row(mutation_store, monkeypatch):
    params, factory, database = mutation_store
    with tenant_session(factory, A) as session:
        service = make_portal(session, A, monkeypatch)
        template = service.create_policy(portal_request("template"), str(USER))
        assert template
        session.execute(text("UPDATE policies SET is_template=true WHERE id=:id"), {"id": template.id})
    with tenant_session(factory, A) as session:
        cloned = make_portal(session, A, monkeypatch).create_policy_from_template(template.id, "clone", "Clone", str(USER))
        assert cloned and cloned.id != template.id and not cloned.is_template
        assert not cloned.approval_required and cloned.approval_status == "approved"
    children = [r for r in rows(params, database, "policy_rules") if r["policy_id"] == str(cloned.id)]
    assert [r["rule_id"] for r in children] == ["template"]
    before = policy_snapshot(params, database)
    with tenant_session(factory, B) as session:
        assert make_portal(session, B, monkeypatch).create_policy_from_template(template.id, "foreign", "Foreign", str(USER)) is None
    assert policy_snapshot(params, database) == before


def test_portal_invalid_dsl_missing_foreign_and_restricted_fields(mutation_store, monkeypatch):
    from app.models.iam_portal import PolicyUpdate
    params, factory, database = mutation_store
    before = policy_snapshot(params, database)
    own = next(p["id"] for p in before["policies"] if p["tenant_id"] == str(A))
    foreign = next(p["id"] for p in before["policies"] if p["tenant_id"] == str(B))
    with tenant_session(factory, A) as session:
        service = make_portal(session, A, monkeypatch)
        bad = portal_request("bad").model_copy(update={"policy_data": {"id":"bad", "type":"access", "rules":[]}})
        assert service.create_policy(bad, str(USER)) is None
        assert service.update_policy(own, PolicyUpdate(policy_data=bad.policy_data)) is None
        for identifier in (foreign, uuid4()):
            assert service.update_policy(identifier, PolicyUpdate(policy_data=mutation_payload())) is None
            assert service.update_policy(identifier, PolicyUpdate()) is None
        writer = PolicyService(session, A, "", load_seed_tenant=False)
        assert not writer._update_policy_fields(own, {"tenant_id": B})
        assert not writer._update_policy_fields(own, {"is_template": True})
    assert policy_snapshot(params, database) == before


@pytest.mark.parametrize("operation", ["create", "update"])
def test_portal_response_failure_rolls_back(mutation_store, monkeypatch, operation):
    from app.models.iam_portal import PolicyUpdate
    params, factory, database = mutation_store
    before = policy_snapshot(params, database)
    own = next(p["id"] for p in before["policies"] if p["tenant_id"] == str(A))
    with tenant_session(factory, A) as session:
        service = make_portal(session, A, monkeypatch)
        monkeypatch.setattr(service, "get_policy", lambda *_: None)
        if operation == "create":
            assert service.create_policy(portal_request(), str(USER)) is None
        else:
            assert service.update_policy(own, PolicyUpdate(policy_data=mutation_payload("failed"))) is None
    assert policy_snapshot(params, database) == before


def test_portal_parent_constraint_failure_restores_rules(mutation_store, monkeypatch):
    from app.models.iam_portal import PolicyUpdate
    params, factory, database = mutation_store
    before = policy_snapshot(params, database)
    own = next(p["id"] for p in before["policies"] if p["tenant_id"] == str(A))
    with tenant_session(factory, A) as session:
        assert make_portal(session, A, monkeypatch).update_policy(own, PolicyUpdate(
            policy_data=mutation_payload("must-rollback"), approval_status="invalid-status")) is None
    assert policy_snapshot(params, database) == before


def test_portal_api_preserves_failure_status_mapping(mutation_store, monkeypatch):
    from app.api import iam_portal as api
    from app.models.iam_portal import PolicyUpdate
    from fastapi import HTTPException
    params, factory, database = mutation_store
    with tenant_session(factory, A) as session:
        service = make_portal(session, A, monkeypatch)
        created = asyncio.run(api.create_policy(portal_request("api"), service, str(USER)))
        assert created.approval_required
        updated = asyncio.run(api.update_policy(created.id, PolicyUpdate(display_name="API"), service))
        assert updated.display_name == "API"
        bad = portal_request("bad").model_copy(update={"policy_data": {"id":"bad", "type":"access", "rules":[]}})
        with pytest.raises(HTTPException) as failure:
            asyncio.run(api.create_policy(bad, service, str(USER)))
        assert failure.value.status_code == 400
        foreign = next(p["id"] for p in rows(params, database, "policies") if p["tenant_id"] == str(B))
        for identifier in (uuid4(), foreign):
            with pytest.raises(HTTPException) as failure:
                asyncio.run(api.update_policy(identifier, PolicyUpdate(), service))
            assert failure.value.status_code == 404
            with pytest.raises(HTTPException) as failure:
                asyncio.run(api.create_policy_from_template(identifier, "clone", "Clone", service, str(USER)))
            assert failure.value.status_code == 404
