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
