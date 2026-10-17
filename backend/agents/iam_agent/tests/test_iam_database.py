"""Real PostgreSQL tests. Always create a private socket-only synthetic cluster.

Run with SG_TEST_PG_BINDIR pointing to PostgreSQL server tools. No DB_URL or
existing cluster is used; unavailable tools are an error, not a skipped gate.
"""

import asyncio
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

import psycopg2
from psycopg2 import sql
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from sg_core.tenant_session import (
    bind_tenant,
    install_tenant_pool_reset,
    tenant_session,
)
from app.api import entitlements, bulk_operations, request_context, access_requests
from app.api.request_context import RequestContext
from app.models.audit_event import IAMAuditEvent
from app.models.entitlement import Entitlement
from app.models.access_request import AccessRequest, AccessRequestHistory
from app.models.audit_campaign import AuditCampaign
from app.models.certification import Certification
from app.models.certification_history import CertificationHistory
from app.models.audit_schedule import AuditSchedule
from app.models.role_entitlement_pattern import RoleEntitlementPattern
from app.models.role_grant_binding import RoleGrantBinding
from app.services.role_directory_service import RoleSnapshot
from app.services import role_sync_service
from app.api import role_mappings
from app.api import governance
from app.services import governance_service as governance_service
from datetime import datetime, timedelta, timezone
from app.services.audit_logger import AuditLogger
from app.services.evaluation_engine import EvaluationContext, EvaluationEngine

ROOT = Path(__file__).resolve().parents[3]
A = UUID("11111111-1111-4111-8111-111111111111")
B = UUID("22222222-2222-4222-8222-222222222222")
USER = UUID("33333333-3333-4333-8333-333333333333")
GRANT = UUID("44444444-4444-4444-8444-444444444444")


@pytest.fixture(scope="module")
def cluster():
    bindir = os.environ.get("SG_TEST_PG_BINDIR")
    if not bindir:
        config = shutil.which("pg_config")
        bindir = (
            subprocess.check_output([config, "--bindir"], text=True).strip()
            if config
            else ""
        )
    tools = {name: Path(bindir) / name for name in ("postgres", "initdb", "pg_ctl")}
    if any(not path.is_file() for path in tools.values()):
        pytest.fail(
            "Install PostgreSQL server tools and set SG_TEST_PG_BINDIR; an existing DB is never used"
        )
    with TemporaryDirectory(prefix="sg-iam-db-", dir="/tmp") as directory:
        directory = Path(directory)
        directory.chmod(0o700)
        data, socket = directory / "data", directory / "socket"
        socket.mkdir(mode=0o700)
        with (directory / "startup.log").open("w") as log:
            subprocess.run(
                [
                    str(tools["initdb"]),
                    "-D",
                    str(data),
                    "-U",
                    "sg_test_owner",
                    "--auth-local=trust",
                    "--auth-host=reject",
                    "--no-locale",
                    "--encoding=UTF8",
                ],
                check=True,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            subprocess.run(
                [
                    str(tools["pg_ctl"]),
                    "-D",
                    str(data),
                    "-l",
                    str(directory / "postgres.log"),
                    "-o",
                    f"-F -h '' -k {socket} -p 55463",
                    "-w",
                    "start",
                ],
                check=True,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        try:
            params = dict(
                host=str(socket), port=55463, user="sg_test_owner", dbname="postgres"
            )
            connection = psycopg2.connect(**params)
            try:
                connection.autocommit = True
                with connection.cursor() as cursor:
                    cursor.execute(
                        "CREATE ROLE sg_test_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS"
                    )
                    for database in ("iam_test", "catalog_test"):
                        cursor.execute(
                            sql.SQL("CREATE DATABASE {} OWNER sg_test_owner").format(
                                sql.Identifier(database)
                            )
                        )
            finally:
                connection.close()
            yield params
        finally:
            subprocess.run(
                [
                    str(tools["pg_ctl"]),
                    "-D",
                    str(data),
                    "-m",
                    "immediate",
                    "-w",
                    "stop",
                ],
                check=True,
                capture_output=True,
            )


def owner(params, database):
    return psycopg2.connect(**{**params, "dbname": database})


def migration_sql():
    return (
        ROOT / "migrations_consolidated/V014__public_iam_audit_and_tenant_guards.sql"
    ).read_text()


@pytest.fixture(scope="module")
def databases(cluster):
    legacy = ROOT / "agents/iam_agent/migrations"
    with owner(cluster, "iam_test") as connection, connection.cursor() as cursor:
        for path in [
            legacy / name
            for name in (
                "V1__create_entitlements_schema.sql",
                "V2__create_tenant_reference_table.sql",
                "V3__create_access_requests.sql",
            )
        ]:
            cursor.execute(path.read_text())
            connection.commit()
        cursor.execute(
            "INSERT INTO entitlements (id,tenant_id,resource_type,resource_id,action,granted_to_type,granted_to_id,granted_by) VALUES (%s,%s,'document','synthetic-doc','read','user',%s,%s)",
            tuple(map(str, [GRANT, A, USER, USER])),
        )
        cursor.execute(
            "INSERT INTO entitlement_audit_log (entitlement_id,action,performed_by) VALUES (%s,'granted',%s)",
            tuple(map(str, [GRANT, USER])),
        )
        cursor.execute(
            "SELECT row_to_json(e)::text FROM entitlement_audit_log e ORDER BY id"
        )
        before = cursor.fetchall()
        cursor.execute(
            "CREATE POLICY old_flag_bypass ON entitlements USING (current_setting('app.is_superadmin', true) = 'true')"
        )
        cursor.execute(migration_sql())
        cursor.execute(
            "SELECT row_to_json(e)::text FROM entitlement_audit_log e ORDER BY id"
        )
        assert cursor.fetchall() == before
        # Preserve populated legacy rows, including configuration the new adapter
        # deliberately cannot execute. V015 only adds a timestamp/guard.
        legacy_campaign, legacy_cert = uuid4(), uuid4()
        cursor.execute(
            "INSERT INTO audit_campaigns (id,tenant_id,name,campaign_type,scope,review_config,schedule,created_by) VALUES (%s,%s,'Legacy synthetic','continuous','{\"custom_scope\":true}','{\"delegated\":true}','{}',%s)",
            (str(legacy_campaign), str(A), str(USER)),
        )
        cursor.execute(
            "INSERT INTO certifications (id,campaign_id,entitlement_id,certifier_id,certifier_type,deadline) VALUES (%s,%s,%s,%s,'delegated',now())",
            tuple(map(str, [legacy_cert, legacy_campaign, GRANT, USER])),
        )
        cursor.execute(
            "INSERT INTO certification_history (certification_id,entitlement_id,changed_by,new_status) VALUES (%s,%s,%s,'pending')",
            tuple(map(str, [legacy_cert, GRANT, USER])),
        )
        cursor.execute(
            "INSERT INTO audit_schedules (tenant_id,entitlement_pattern,frequency,reviewer_type) VALUES (%s,'document:*:read','monthly','manager')",
            (str(A),),
        )
        preserved = {}
        for table in (
            "audit_campaigns",
            "certifications",
            "certification_history",
            "audit_schedules",
        ):
            cursor.execute(
                sql.SQL("SELECT {} FROM {} t ORDER BY id").format(
                    sql.SQL("to_jsonb(t)-'updated_at'")
                    if table == "audit_campaigns"
                    else sql.SQL("to_jsonb(t)"),
                    sql.Identifier(table),
                )
            )
            preserved[table] = cursor.fetchall()
        cursor.execute(
            (
                ROOT / "migrations_consolidated/V015__public_governance_contract.sql"
            ).read_text()
        )
        for table, rows in preserved.items():
            cursor.execute(
                sql.SQL("SELECT {} FROM {} t ORDER BY id").format(
                    sql.SQL("to_jsonb(t)-'updated_at'")
                    if table == "audit_campaigns"
                    else sql.SQL("to_jsonb(t)"),
                    sql.Identifier(table),
                )
            )
            assert cursor.fetchall() == rows
        cursor.execute(
            "SELECT updated_at IS NOT NULL FROM audit_campaigns WHERE id=%s",
            (str(legacy_campaign),),
        )
        assert cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO role_entitlement_patterns (role_name,tenant_id,entitlement_pattern) VALUES ('legacy',%s,'document:legacy:read'),('global',NULL,'document:global:read')",
            (str(A),),
        )
        cursor.execute(
            "SELECT to_jsonb(r) FROM role_entitlement_patterns r ORDER BY id"
        )
        role_before = cursor.fetchall()
        cursor.execute(
            (
                ROOT / "migrations_consolidated/V016__public_role_grant_provenance.sql"
            ).read_text()
        )
        cursor.execute(
            "SELECT to_jsonb(r)-'auto_grant'-'created_by' FROM role_entitlement_patterns r ORDER BY id"
        )
        assert cursor.fetchall() == role_before
        cursor.execute("SELECT auto_grant,created_by FROM role_entitlement_patterns")
        assert all(value == (False, None) for value in cursor.fetchall())
        cursor.execute("SELECT count(*) FROM iam_role_grants")
        assert cursor.fetchone()[0] == 0
        cursor.execute("SELECT count(*) FROM iam_audit_events")
        assert cursor.fetchone()[0] == 0
        cursor.execute(
            "CREATE TABLE nhi_service_accounts (id uuid PRIMARY KEY, tenant_id uuid, secret_hash varchar(255), metadata jsonb)"
        )
        cursor.execute(
            "INSERT INTO nhi_service_accounts VALUES (%s,%s,'synthetic-legacy-digest','{\"unreviewed\":true}')",
            (str(uuid4()), str(A)),
        )
        cursor.execute("SELECT to_jsonb(n) FROM nhi_service_accounts n")
        legacy_nhi = cursor.fetchall()
        cursor.execute(
            (
                ROOT
                / "migrations_consolidated/V017__public_service_account_registry.sql"
            ).read_text()
        )
        cursor.execute("SELECT to_jsonb(n) FROM nhi_service_accounts n")
        assert cursor.fetchall() == legacy_nhi
        cursor.execute("SELECT count(*) FROM iam_service_accounts")
        assert cursor.fetchone()[0] == 0
    # Exact policy/catalog table declarations from the published dump, not a
    # claim that all V001-V013 extensions, histories and runners are qualified.
    dump = (ROOT / "migrations_consolidated/V001__initial_schema.sql").read_text()
    with owner(cluster, "catalog_test") as connection, connection.cursor() as cursor:
        cursor.execute('CREATE EXTENSION "uuid-ossp"')
        for name in (
            "policies",
            "policy_rules",
            "policy_evaluations",
            "entitlements",
            "policy_templates",
        ):
            declaration = re.search(
                r"CREATE TABLE public\." + name + r" \(.*?\n\);", dump, re.S
            ).group()
            cursor.execute(declaration)
        cursor.execute(
            "CREATE POLICY old_flag_bypass ON policies USING (current_setting('app.is_superadmin', true) = 'true')"
        )
        cursor.execute(migration_sql())
        cursor.execute(
            (
                ROOT / "migrations_consolidated/V015__public_governance_contract.sql"
            ).read_text()
        )
        cursor.execute(
            (
                ROOT / "migrations_consolidated/V016__public_role_grant_provenance.sql"
            ).read_text()
        )
        cursor.execute(
            (
                ROOT
                / "migrations_consolidated/V017__public_service_account_registry.sql"
            ).read_text()
        )
        cursor.execute("SELECT to_regclass('public.iam_service_accounts')")
        assert cursor.fetchone()[0] is None
        cursor.execute("SELECT to_regclass('public.audit_campaigns')")
        assert cursor.fetchone()[0] is None
        cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='entitlements'"
        )
        columns = {row[0] for row in cursor.fetchall()}
        assert "app_id" in columns and "resource_type" not in columns
    engines = []
    for database in ("iam_test", "catalog_test"):
        with owner(cluster, database) as connection, connection.cursor() as cursor:
            cursor.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
            cursor.execute("GRANT USAGE ON SCHEMA public TO sg_test_app")
            cursor.execute(
                "GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO sg_test_app"
            )
            cursor.execute("REVOKE UPDATE,DELETE ON iam_audit_events FROM sg_test_app")
        url = URL.create(
            "postgresql+psycopg2",
            username="sg_test_app",
            database=database,
            query={"host": cluster["host"], "port": str(cluster["port"])},
        )
        engine = create_engine(url, pool_size=1, max_overflow=0, pool_pre_ping=True)
        install_tenant_pool_reset(engine)
        engines.append(engine)
    try:
        yield cluster, engines
    finally:
        for engine in engines:
            engine.dispose()


@pytest.fixture
def store(databases, monkeypatch):
    params, (engine, policy_engine) = databases
    with owner(params, "iam_test") as connection, connection.cursor() as cursor:
        cursor.execute(
            "TRUNCATE iam_service_accounts,iam_audit_events,entitlements,access_requests,audit_campaigns,audit_schedules,role_entitlement_patterns CASCADE"
        )
        for tenant in (A, B):
            cursor.execute(
                "INSERT INTO entitlements (id,tenant_id,resource_type,resource_id,action,granted_to_type,granted_to_id,granted_by) VALUES (%s,%s,'document','synthetic-doc','read','user',%s,%s)",
                tuple(
                    map(str, [GRANT if tenant == A else uuid4(), tenant, USER, USER])
                ),
            )
    with owner(params, "catalog_test") as connection, connection.cursor() as cursor:
        cursor.execute(
            "TRUNCATE policies,policy_rules,policy_evaluations,iam_audit_events,policy_templates"
        )
        for tenant in (A, B):
            cursor.execute(
                "INSERT INTO policies (id,tenant_id,name,display_name,policy_type,scope,policy_data) VALUES (%s,%s,'synthetic','Synthetic','access','tenant',%s::jsonb)",
                (
                    str(uuid4()),
                    str(tenant),
                    '{"id":"synthetic","type":"access","rules":[{"id":"grant","conditions":[],"actions":[{"type":"allow"}]}]}',
                ),
            )
    factory, policies = sessionmaker(bind=engine), sessionmaker(bind=policy_engine)
    monkeypatch.setattr(entitlements.cache, "invalidate_entitlement", lambda *_: None)
    monkeypatch.setattr(
        bulk_operations.cache, "invalidate_tenant_entitlements", lambda *_: None
    )
    return params, engine, factory, policies


def visible(session):
    return (
        session.execute(text("SELECT tenant_id FROM public.entitlements"))
        .scalars()
        .all()
    )


def test_migration_and_model_match(databases):
    _, (engine, _) = databases
    catalog = inspect(engine)
    model = IAMAuditEvent.__table__
    columns = {
        row["name"]: row for row in catalog.get_columns(model.name, schema="public")
    }
    assert set(columns) == set(model.columns.keys())
    for field in model.columns:
        assert columns[field.name]["nullable"] == field.nullable
        assert (columns[field.name]["default"] is not None) == (
            field.server_default is not None
        )
        assert (
            str(columns[field.name]["type"].compile(dialect=engine.dialect)).lower()
            == str(field.type.compile(dialect=engine.dialect)).lower()
        )
    assert {
        row["name"]
        for row in catalog.get_check_constraints(model.name, schema="public")
    } == {c.name for c in model.constraints if c.name}
    assert {
        row["name"] for row in catalog.get_indexes(model.name, schema="public")
    } == {i.name for i in model.indexes}
    with engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user"
            )
        ).one() == (False, False, False, False)


def test_commit_rollback_savepoint_and_pool_reuse(store):
    _, engine, factory, _ = store
    with tenant_session(factory, A) as session:
        pid = session.scalar(text("SELECT pg_backend_pid()"))
        assert visible(session) == [A]
        session.commit()
        assert visible(session) == [A]
        session.rollback()
        assert visible(session) == [A]
        with pytest.raises(RuntimeError):
            with session.begin_nested():
                assert visible(session) == [A]
                raise RuntimeError("synthetic savepoint rollback")
        assert visible(session) == [A]
    with tenant_session(factory, B) as session:
        assert session.scalar(text("SELECT pg_backend_pid()")) == pid
        assert visible(session) == [B]
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT pg_backend_pid()")) == pid
        assert (
            connection.execute(text("SELECT tenant_id FROM entitlements")).all() == []
        )


def test_checkout_clears_session_level_residue(store):
    _, engine, _, _ = store
    with engine.connect() as connection:
        connection.execute(
            text(
                "SELECT set_config('app.current_tenant_id', :t, false), set_config('app.is_superadmin','true',false)"
            ),
            {"t": str(B)},
        )
        connection.commit()
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT tenant_id FROM entitlements")).all() == []
        )
        assert (
            connection.scalar(text("SELECT current_setting('app.is_superadmin')"))
            != "true"
        )


@pytest.mark.parametrize("value", [None, "", "tenant-slug", "invalid-uuid"])
def test_missing_or_invalid_context_denies_direct_sql(store, value):
    _, engine, _, _ = store
    with engine.begin() as connection:
        if value is not None:
            connection.execute(
                text("SELECT set_config('app.current_tenant_id',:t,true)"), {"t": value}
            )
        connection.execute(text("SELECT set_config('app.is_superadmin','true',true)"))
        assert (
            connection.execute(text("SELECT tenant_id FROM entitlements")).all() == []
        )


def test_superadmin_flag_cannot_bypass_restrictive_guard(store):
    _, _, factory, _ = store
    with tenant_session(factory, A) as session:
        session.execute(text("SELECT set_config('app.is_superadmin','true',true)"))
        assert visible(session) == [A]
        assert (
            session.execute(
                text("UPDATE entitlements SET status='revoked' WHERE tenant_id=:t"),
                {"t": B},
            ).rowcount
            == 0
        )
        with pytest.raises(DBAPIError):
            with session.begin_nested():
                session.execute(
                    text("UPDATE entitlements SET tenant_id=:t WHERE id=:id"),
                    {"t": B, "id": GRANT},
                )


def test_child_rows_cannot_cross_parent_tenant(store):
    params, _, _, policies = store
    with owner(params, "catalog_test") as connection, connection.cursor() as cursor:
        cursor.execute("SELECT id,tenant_id FROM policies")
        ids = {UUID(str(t)): UUID(str(i)) for i, t in cursor.fetchall()}
        for tenant, target in ids.items():
            cursor.execute(
                "INSERT INTO policy_rules (id,policy_id,rule_id,conditions,actions) VALUES (%s,%s,'synthetic','[]','[]')",
                (str(uuid4()), str(target)),
            )
    with tenant_session(policies, A) as session:
        assert session.scalar(text("SELECT count(*) FROM policy_rules")) == 1
        with pytest.raises(DBAPIError):
            with session.begin_nested():
                session.execute(
                    text(
                        "INSERT INTO policy_rules (id,policy_id,rule_id,conditions,actions) VALUES (:id,:p,'forged','[]','[]')"
                    ),
                    {"id": uuid4(), "p": ids[B]},
                )


def test_allow_and_deny_are_committed_with_actual_actor(store):
    _, _, factory, policies = store
    for subject, expected in [(USER, "allow"), (uuid4(), "deny")]:
        with (
            tenant_session(factory, A) as session,
            tenant_session(policies, A) as policy_session,
        ):
            result = asyncio.run(
                EvaluationEngine(session, policy_db=policy_session).evaluate(
                    EvaluationContext(
                        subject, A, "document", "synthetic-doc", "read", actor_id=USER
                    )
                )
            )
            assert result.decision == expected and result.audit_recorded
    with tenant_session(factory, A) as session:
        rows = session.query(IAMAuditEvent).all()
        assert {r.decision for r in rows} == {"allow", "deny"}
        assert all(r.performed_by == USER for r in rows)
        assert session.get(Entitlement, GRANT).usage_count_90d == 1
    with tenant_session(factory, B) as session:
        assert session.query(IAMAuditEvent).all() == []


def test_audit_failure_prevents_allow_and_usage_update(store):
    params, _, factory, policies = store
    with owner(params, "iam_test") as connection, connection.cursor() as cursor:
        cursor.execute("REVOKE INSERT ON iam_audit_events FROM sg_test_app")
    try:
        with (
            tenant_session(factory, A) as session,
            tenant_session(policies, A) as policy_session,
        ):
            result = asyncio.run(
                EvaluationEngine(session, policy_db=policy_session).evaluate(
                    EvaluationContext(USER, A, "document", "synthetic-doc", "read")
                )
            )
            assert result.decision == "deny" and not result.audit_recorded
        with tenant_session(factory, A) as session:
            assert session.get(Entitlement, GRANT).usage_count_90d == 0
            assert session.query(IAMAuditEvent).count() == 0
    finally:
        with owner(params, "iam_test") as connection, connection.cursor() as cursor:
            cursor.execute("GRANT INSERT ON iam_audit_events TO sg_test_app")


def test_aborted_lookup_transaction_rebinds_and_records_denial(store):
    _, _, factory, policies = store
    with (
        tenant_session(factory, A) as session,
        tenant_session(policies, A) as policy_session,
    ):
        engine = EvaluationEngine(session, policy_db=policy_session)

        def fail_lookup(_context):
            session.execute(text("SELECT 1 / 0"))

        engine._find_matching_entitlements = fail_lookup
        result = asyncio.run(
            engine.evaluate(
                EvaluationContext(USER, A, "document", "synthetic-doc", "read")
            )
        )
        assert result.decision == "deny" and result.audit_recorded
        assert visible(session) == [A]
    with tenant_session(factory, A) as session:
        assert session.query(IAMAuditEvent).one().decision == "deny"


def test_certification_requires_both_parents_in_authenticated_tenant(store):
    params, _, factory, _ = store
    campaigns, grants = {}, {}
    with owner(params, "iam_test") as connection, connection.cursor() as cursor:
        cursor.execute("TRUNCATE audit_campaigns CASCADE")
        cursor.execute("SELECT tenant_id,id FROM entitlements")
        grants = {UUID(str(t)): UUID(str(i)) for t, i in cursor.fetchall()}
        for tenant in (A, B):
            campaigns[tenant] = uuid4()
            cursor.execute(
                "INSERT INTO audit_campaigns (id,tenant_id,name,campaign_type,scope,review_config,schedule,created_by) VALUES (%s,%s,'synthetic','on_demand','{}','{}','{}',%s)",
                tuple(map(str, [campaigns[tenant], tenant, USER])),
            )
            cursor.execute(
                "INSERT INTO certifications (campaign_id,entitlement_id,certifier_id,certifier_type,deadline) VALUES (%s,%s,%s,'admin',now())",
                tuple(map(str, [campaigns[tenant], grants[tenant], USER])),
            )
    with tenant_session(factory, A) as session:
        assert session.scalar(text("SELECT count(*) FROM certifications")) == 1
        with pytest.raises(DBAPIError):
            with session.begin_nested():
                session.execute(
                    text(
                        "INSERT INTO certifications (campaign_id,entitlement_id,certifier_id,certifier_type,deadline) VALUES (:c,:e,:u,'manager',now())"
                    ),
                    {"c": campaigns[A], "e": grants[B], "u": USER},
                )


def test_grant_mutation_rolls_back_when_audit_fails(store):
    params, _, factory, _ = store
    with owner(params, "iam_test") as connection, connection.cursor() as cursor:
        cursor.execute("REVOKE INSERT ON iam_audit_events FROM sg_test_app")
    try:
        with tenant_session(factory, A) as session:
            payload = entitlements.EntitlementCreate(
                tenant_id=A,
                resource_type="document",
                resource_id="new-doc",
                action="read",
                granted_to_type="user",
                granted_to_id=USER,
                granted_by=uuid4(),
            )
            with pytest.raises(Exception) as error:
                asyncio.run(
                    entitlements.create_entitlement(
                        payload,
                        RequestContext(A, str(USER), ("TENANT_ADMIN",)),
                        session,
                    )
                )
            assert error.value.status_code == 503
        with tenant_session(factory, A) as session:
            assert (
                session.query(Entitlement)
                .filter(Entitlement.resource_id == "new-doc")
                .count()
                == 0
            )
    finally:
        with owner(params, "iam_test") as connection, connection.cursor() as cursor:
            cursor.execute("GRANT INSERT ON iam_audit_events TO sg_test_app")


def test_grant_creation_and_bulk_revocation_commit_audit(store):
    _, _, factory, _ = store
    caller = RequestContext(A, str(USER), ("TENANT_ADMIN",))
    with tenant_session(factory, A) as session:
        payload = entitlements.EntitlementCreate(
            tenant_id=A,
            resource_type="document",
            resource_id="new-doc",
            action="read",
            granted_to_type="user",
            granted_to_id=USER,
            granted_by=uuid4(),
        )
        row = asyncio.run(entitlements.create_entitlement(payload, caller, session))
        assert row.granted_by == USER
    with tenant_session(factory, A) as session:
        response = asyncio.run(
            bulk_operations.bulk_delete_entitlements(
                bulk_operations.BulkDeleteRequest(entitlement_ids=[GRANT]),
                caller,
                session,
            )
        )
        assert response.deleted == 1 and response.failed == 0
    with tenant_session(factory, A) as session:
        assert {row.event_type for row in session.query(IAMAuditEvent)} == {
            "created",
            "revoked",
        }
        assert session.get(Entitlement, GRANT).status == "revoked"


def test_audit_cannot_be_modified_or_truncated_by_application(store):
    params, _, factory, _ = store
    with tenant_session(factory, A) as session:
        AuditLogger(session).log_entitlement_event("created", GRANT, A, USER)
    # Even accidental broad UPDATE/DELETE grants cannot overcome restrictive guards.
    with owner(params, "iam_test") as connection, connection.cursor() as cursor:
        cursor.execute("GRANT UPDATE,DELETE ON iam_audit_events TO sg_test_app")
    try:
        with tenant_session(factory, A) as session:
            assert (
                session.execute(
                    text("UPDATE iam_audit_events SET reason='forged'")
                ).rowcount
                == 0
            )
            assert session.execute(text("DELETE FROM iam_audit_events")).rowcount == 0
            with pytest.raises(DBAPIError):
                with session.begin_nested():
                    session.execute(text("TRUNCATE iam_audit_events"))
            with pytest.raises(DBAPIError):
                with session.begin_nested():
                    session.execute(
                        text("ALTER TABLE iam_audit_events DISABLE ROW LEVEL SECURITY")
                    )
    finally:
        with owner(params, "iam_test") as connection, connection.cursor() as cursor:
            cursor.execute("REVOKE UPDATE,DELETE ON iam_audit_events FROM sg_test_app")


def test_bind_rejects_mid_transaction_and_tenant_switch(store):
    _, _, factory, _ = store
    with factory() as session:
        session.execute(text("SELECT 1"))
        with pytest.raises(ValueError):
            bind_tenant(session, A)
    with factory() as session:
        bind_tenant(session, A)
        with pytest.raises(ValueError):
            bind_tenant(session, B)


@pytest.mark.parametrize("table", ["entitlements", "iam_audit_events"])
def test_cross_tenant_insert_is_rejected(store, table):
    _, _, factory, _ = store
    with tenant_session(factory, A) as session:
        with pytest.raises(DBAPIError):
            with session.begin_nested():
                if table == "iam_audit_events":
                    AuditLogger(session).log_entitlement_event("created", None, B, USER)
                else:
                    session.add(
                        Entitlement(
                            tenant_id=B,
                            resource_type="document",
                            resource_id="forged",
                            action="read",
                            granted_to_type="user",
                            granted_to_id=USER,
                            granted_by=USER,
                        )
                    )
                    session.flush()


def test_new_audit_history_survives_live_record_deletion(store):
    params, _, factory, _ = store
    with tenant_session(factory, A) as session:
        AuditLogger(session).log_entitlement_event("created", GRANT, A, USER)
    with owner(params, "iam_test") as connection, connection.cursor() as cursor:
        cursor.execute("DELETE FROM entitlements WHERE id=%s", (str(GRANT),))
    with tenant_session(factory, A) as session:
        assert session.query(IAMAuditEvent).one().entitlement_id == GRANT


def test_iam_dependency_and_shared_helper_rebind_transactions(store, monkeypatch):
    from sg_core import db

    _, _, factory, _ = store
    monkeypatch.setattr(request_context, "IAMSessionLocal", factory)
    dependency = request_context.get_entitlement_session(RequestContext(A, str(USER)))
    session = next(dependency)
    assert visible(session) == [A]
    session.commit()
    assert visible(session) == [A]
    with pytest.raises(StopIteration):
        next(dependency)
    monkeypatch.setattr(db, "SessionLocal", factory)
    dependency = db.get_tenant_db(str(B))
    session = next(dependency)
    assert visible(session) == [B]
    session.rollback()
    assert visible(session) == [B]
    dependency.close()


# Access requests: exact legacy V3 contracts and transactional admission.
@pytest.mark.parametrize("model", [AccessRequest, AccessRequestHistory])
def test_access_request_mapping_matches_existing_v3(databases, model):
    _, (engine, _) = databases
    catalog = inspect(engine)
    table = model.__table__
    columns = {c["name"]: c for c in catalog.get_columns(table.name, schema="public")}
    assert set(columns) == set(table.columns.keys())
    for field in table.columns:
        assert columns[field.name]["nullable"] == field.nullable
        assert (columns[field.name]["default"] is not None) == (
            field.server_default is not None
        )
        assert (
            str(columns[field.name]["type"].compile(dialect=engine.dialect)).lower()
            == str(field.type.compile(dialect=engine.dialect)).lower()
        )
    assert {
        r["name"] for r in catalog.get_check_constraints(table.name, schema="public")
    } == {c.name for c in table.constraints if c.name}
    assert {r["name"] for r in catalog.get_indexes(table.name, schema="public")} == {
        i.name for i in table.indexes
    }


def new_access_request(factory):
    with tenant_session(factory, A) as session:
        body = access_requests.AccessRequestCreate(
            tenant_id=A,
            resource_type="document",
            resource_id="requested-doc",
            action="read",
            justification="Synthetic request only",
        )
        return asyncio.run(
            access_requests.create_access_request(
                body, session, RequestContext(A, str(USER), ())
            )
        )


def request_action(session, row, action):
    caller = RequestContext(
        A, str(USER if action == "cancel" else B), ("TENANT_ADMIN",)
    )
    if action == "cancel":
        return asyncio.run(
            access_requests.cancel_access_request(row.id, session, caller)
        )
    return asyncio.run(
        access_requests.review_access_request(
            row.id,
            access_requests.AccessRequestReview(decision=action),
            session,
            caller,
        )
    )


def test_request_creation_persists_history_jsonb_and_audit(store):
    _, _, factory, _ = store
    row = new_access_request(factory)
    with tenant_session(factory, A) as session:
        history = session.query(AccessRequestHistory).filter_by(request_id=row.id).one()
        assert history.metadata_json == {} and history.performed_by == USER
        audit = session.query(IAMAuditEvent).one()
        assert (
            audit.event_type == "access_request_created" and audit.performed_by == USER
        )
        assert (
            audit.subject_id == USER and audit.changes["resource_id"] == "requested-doc"
        )


@pytest.mark.parametrize(
    "action,expected",
    [("approve", "approved"), ("deny", "denied"), ("cancel", "cancelled")],
)
def test_request_transition_commits_history_and_audit(store, action, expected):
    _, _, factory, _ = store
    row = new_access_request(factory)
    with tenant_session(factory, A) as session:
        result = request_action(session, row, action)
        assert result.status == expected
    with tenant_session(factory, A) as session:
        request = session.get(AccessRequest, row.id)
        assert request.status == expected
        assert (
            session.query(AccessRequestHistory).filter_by(request_id=row.id).count()
            == 2
        )
        event = (
            session.query(IAMAuditEvent)
            .filter_by(event_type="access_request_" + expected)
            .one()
        )
        assert event.performed_by == (USER if action == "cancel" else B)
        assert (
            event.changes["old_status"] == "pending"
            and event.changes["new_status"] == expected
        )
        grants = session.query(Entitlement).filter_by(resource_id="requested-doc").all()
        assert len(grants) == (1 if action == "approve" else 0)
        if grants:
            assert request.entitlement_id == grants[0].id and grants[0].granted_by == B
            assert grants[0].granted_to_id == USER
            assert (
                session.query(IAMAuditEvent)
                .filter_by(entitlement_id=grants[0].id, event_type="created")
                .count()
                == 1
            )


@pytest.mark.parametrize("action", ["create", "approve", "deny", "cancel"])
def test_request_audit_failure_rolls_back_every_effect(store, action):
    params, _, factory, _ = store
    row = new_access_request(factory) if action != "create" else None
    with owner(params, "iam_test") as connection, connection.cursor() as cursor:
        cursor.execute("REVOKE INSERT ON iam_audit_events FROM sg_test_app")
    try:
        with pytest.raises(Exception) as error:
            if row:
                with tenant_session(factory, A) as session:
                    request_action(session, row, action)
            else:
                new_access_request(factory)
        assert error.value.status_code == 503
        with tenant_session(factory, A) as session:
            assert session.query(AccessRequest).count() == (1 if row else 0)
            assert session.query(AccessRequestHistory).count() == (1 if row else 0)
            assert session.query(IAMAuditEvent).count() == (1 if row else 0)
            assert (
                session.query(Entitlement)
                .filter_by(resource_id="requested-doc")
                .count()
                == 0
            )
            if row:
                assert session.get(AccessRequest, row.id).status == "pending"
    finally:
        with owner(params, "iam_test") as connection, connection.cursor() as cursor:
            cursor.execute("GRANT INSERT ON iam_audit_events TO sg_test_app")


def test_request_commit_failure_rolls_back_grant_and_audits(store, monkeypatch):
    _, _, factory, _ = store
    row = new_access_request(factory)
    with tenant_session(factory, A) as session:
        with monkeypatch.context() as patch:

            def unavailable():
                raise RuntimeError("Synthetic commit outage")

            patch.setattr(session, "commit", unavailable)
            with pytest.raises(Exception) as error:
                request_action(session, row, "approve")
            assert error.value.status_code == 503
    with tenant_session(factory, A) as session:
        assert session.get(AccessRequest, row.id).status == "pending"
        assert session.query(AccessRequestHistory).count() == 1
        assert session.query(IAMAuditEvent).count() == 1
        assert (
            session.query(Entitlement).filter_by(resource_id="requested-doc").count()
            == 0
        )


def test_legacy_null_beneficiary_can_be_read_and_reviewed_as_self(store):
    params, _, factory, _ = store
    row = new_access_request(factory)
    with owner(params, "iam_test") as connection, connection.cursor() as cursor:
        cursor.execute(
            "UPDATE access_requests SET requested_for=NULL WHERE id=%s", (str(row.id),)
        )
    with tenant_session(factory, A) as session:
        response = asyncio.run(
            access_requests.get_access_request(
                row.id, session, RequestContext(A, str(USER), ())
            )
        )
        assert response.requested_for == USER
    with tenant_session(factory, A) as session:
        assert request_action(session, row, "approve").requested_for == USER
    with tenant_session(factory, A) as session:
        assert (
            session.query(Entitlement)
            .filter_by(resource_id="requested-doc")
            .one()
            .granted_to_id
            == USER
        )


@pytest.mark.parametrize("second_action", ["approve", "cancel"])
def test_competing_request_transitions_use_row_lock(store, monkeypatch, second_action):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    import time

    params, engine, factory, _ = store
    row = new_access_request(factory)
    # A separate engine permits genuinely concurrent transactions, unlike the
    # normal single-connection pool used to exercise tenant reuse elsewhere.
    concurrent = create_engine(engine.url, pool_size=2, max_overflow=0)
    install_tenant_pool_reset(concurrent)
    sessions = sessionmaker(bind=concurrent)
    staged, release = Event(), Event()
    original = AuditLogger.log_entitlement_event

    def hold(logger, event_type, *args, **kwargs):
        result = original(logger, event_type, *args, **kwargs)
        if event_type == "access_request_approved":
            staged.set()
            assert release.wait(10), "Concurrent test did not release first transition"
        return result

    monkeypatch.setattr(AuditLogger, "log_entitlement_event", hold)

    def invoke(action):
        try:
            with tenant_session(sessions, A) as session:
                return request_action(session, row, action).status
        except Exception as error:
            return error

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(invoke, "approve")
            assert staged.wait(5)
            second = pool.submit(invoke, second_action)
            try:
                deadline = time.monotonic() + 5
                blocked = False
                while time.monotonic() < deadline:
                    with (
                        owner(params, "iam_test") as connection,
                        connection.cursor() as cursor,
                    ):
                        cursor.execute(
                            "SELECT count(*) FROM pg_stat_activity WHERE datname='iam_test' AND usename='sg_test_app' AND wait_event_type='Lock'"
                        )
                        blocked = cursor.fetchone()[0] > 0
                    if blocked:
                        break
                    time.sleep(0.02)
                assert blocked, "Competing transition must wait for the request row"
            finally:
                release.set()
            assert first.result(timeout=5) == "approved"
            assert second.result(timeout=5).status_code == 400
        with tenant_session(factory, A) as session:
            assert (
                session.query(Entitlement)
                .filter_by(resource_id="requested-doc")
                .count()
                == 1
            )
            assert session.query(AccessRequestHistory).count() == 2
            assert session.get(AccessRequest, row.id).status == "approved"
    finally:
        release.set()
        concurrent.dispose()


@pytest.mark.parametrize("action", ["deny", "cancel"])
def test_legacy_delegated_requests_can_be_closed_without_grant(store, action):
    params, _, factory, _ = store
    row = new_access_request(factory)
    with owner(params, "iam_test") as connection, connection.cursor() as cursor:
        cursor.execute(
            "UPDATE access_requests SET requested_for=%s WHERE id=%s",
            (str(uuid4()), str(row.id)),
        )
    with tenant_session(factory, A) as session:
        assert request_action(session, row, action).status in {"denied", "cancelled"}
    with tenant_session(factory, A) as session:
        assert (
            session.query(Entitlement).filter_by(resource_id="requested-doc").count()
            == 0
        )
        assert session.query(AccessRequestHistory).count() == 2
        assert session.query(IAMAuditEvent).count() == 2


def test_request_review_reloads_stale_session_identity(store):
    _, _, factory, _ = store
    row = new_access_request(factory)
    with tenant_session(factory, A) as session:
        session.expire_on_commit = False
        stale = session.get(AccessRequest, row.id)
        session.commit()
        with tenant_session(factory, A) as other:
            request_action(other, row, "deny")
        assert stale.status == "pending"
        with pytest.raises(Exception) as error:
            request_action(session, row, "approve")
        assert error.value.status_code == 400
    with tenant_session(factory, A) as session:
        assert session.get(AccessRequest, row.id).status == "denied"
        assert (
            session.query(Entitlement).filter_by(resource_id="requested-doc").count()
            == 0
        )


def test_foreign_request_id_cannot_be_reviewed_or_read(store):
    _, _, factory, _ = store
    row = new_access_request(factory)
    foreign = RequestContext(B, str(B), ("PLATFORM_ADMIN",))
    for operation in ("read", "review", "cancel", "history"):
        with tenant_session(factory, B) as session:
            with pytest.raises(Exception) as error:
                if operation == "read":
                    asyncio.run(
                        access_requests.get_access_request(row.id, session, foreign)
                    )
                elif operation == "review":
                    asyncio.run(
                        access_requests.review_access_request(
                            row.id,
                            access_requests.AccessRequestReview(decision="approve"),
                            session,
                            foreign,
                        )
                    )
                elif operation == "cancel":
                    asyncio.run(
                        access_requests.cancel_access_request(row.id, session, foreign)
                    )
                else:
                    asyncio.run(
                        access_requests.get_access_request_history(
                            row.id, session, foreign
                        )
                    )
            assert error.value.status_code == 404
    with tenant_session(factory, A) as session:
        assert session.get(AccessRequest, row.id).status == "pending"
        assert session.query(AccessRequestHistory).count() == 1
        assert session.query(IAMAuditEvent).count() == 1


def test_legacy_null_pending_request_blocks_duplicate_creation(store):
    params, _, factory, _ = store
    row = new_access_request(factory)
    with owner(params, "iam_test") as connection, connection.cursor() as cursor:
        cursor.execute(
            "UPDATE access_requests SET requested_for=NULL WHERE id=%s", (str(row.id),)
        )
    with pytest.raises(Exception) as error:
        new_access_request(factory)
    assert error.value.status_code == 409
    with tenant_session(factory, A) as session:
        assert session.query(AccessRequest).count() == 1
        assert session.query(AccessRequestHistory).count() == 1
        assert session.query(IAMAuditEvent).count() == 1


def test_lost_commit_acknowledgement_requires_state_reconciliation(store, monkeypatch):
    _, _, factory, _ = store
    row = new_access_request(factory)
    with tenant_session(factory, A) as session:
        original_commit = session.commit
        with monkeypatch.context() as patch:

            def lost_acknowledgement():
                original_commit()
                raise RuntimeError("Synthetic lost acknowledgement after server commit")

            patch.setattr(session, "commit", lost_acknowledgement)
            with pytest.raises(Exception) as error:
                request_action(session, row, "approve")
            assert error.value.status_code == 503
    # A 503 is not proof of no effect. The durable row tells the caller what
    # happened; a retry must not create another grant or another transition.
    with tenant_session(factory, A) as session:
        assert session.get(AccessRequest, row.id).status == "approved"
        assert (
            session.query(Entitlement).filter_by(resource_id="requested-doc").count()
            == 1
        )
        assert session.query(AccessRequestHistory).count() == 2
        assert session.query(IAMAuditEvent).count() == 3
        with pytest.raises(Exception) as error:
            request_action(session, row, "approve")
        assert error.value.status_code == 400


# Governance uses exact legacy V1 data, an explicit DTO contract, and additive V015.
ADMIN = RequestContext(A, str(B), ("TENANT_ADMIN",))
REVIEWER = RequestContext(A, str(USER), ())


def campaign_create(factory, **changes):
    now = datetime.now(timezone.utc)
    data = dict(
        tenant_id=A,
        name="Synthetic governance",
        start_date=now - timedelta(minutes=1),
        end_date=now + timedelta(hours=1),
        reviewer_type="self",
        auto_revoke_days=0,
        entitlement_patterns=["document:*:read"],
    )
    data.update(changes)
    with tenant_session(factory, A) as session:
        return governance_service.create_campaign(
            session, ADMIN, governance.CampaignCreate(**data)
        )


def campaign_start(factory, **changes):
    row = campaign_create(factory, **changes)
    with tenant_session(factory, A) as session:
        governance_service.start_campaign(session, ADMIN, row.id)
    return row


def certification_ids(factory, campaign):
    with tenant_session(factory, A) as session:
        return [
            c.id
            for c in session.query(Certification)
            .filter_by(campaign_id=campaign.id)
            .order_by(Certification.id)
        ]


def extra_grant(
    factory, *, resource="second-doc", beneficiary=USER, granted_to_type="user"
):
    identity = uuid4()
    with tenant_session(factory, A) as session:
        session.add(
            Entitlement(
                id=identity,
                tenant_id=A,
                resource_type="document",
                resource_id=resource,
                action="read",
                granted_to_type=granted_to_type,
                granted_to_id=beneficiary,
                status="active",
                granted_by=B,
            )
        )
    return identity


@pytest.mark.parametrize(
    "model", [AuditCampaign, Certification, CertificationHistory, AuditSchedule]
)
def test_governance_models_match_reviewed_sql(databases, model):
    _, (engine, _) = databases
    catalog = inspect(engine)
    table = model.__table__
    columns = {c["name"]: c for c in catalog.get_columns(table.name, schema="public")}
    assert set(columns) == set(table.columns.keys())
    for field in table.columns:
        assert columns[field.name]["nullable"] == field.nullable
        assert (columns[field.name]["default"] is not None) == (
            field.server_default is not None
        )
        assert (
            str(columns[field.name]["type"].compile(dialect=engine.dialect)).lower()
            == str(field.type.compile(dialect=engine.dialect)).lower()
        )
    assert {
        r["name"] for r in catalog.get_check_constraints(table.name, schema="public")
    } == {
        c.name for c in table.constraints if c.__class__.__name__ == "CheckConstraint"
    }
    assert {
        r["name"]
        for r in catalog.get_indexes(table.name, schema="public")
        if not r.get("duplicates_constraint")
    } == {i.name for i in table.indexes}
    assert {
        r["name"] for r in catalog.get_unique_constraints(table.name, schema="public")
    } == {
        c.name for c in table.constraints if c.__class__.__name__ == "UniqueConstraint"
    }
    assert {
        r["name"] for r in catalog.get_foreign_keys(table.name, schema="public")
    } == {
        c.name
        for c in table.constraints
        if c.__class__.__name__ == "ForeignKeyConstraint"
    }


@pytest.mark.parametrize("decision", ["approved", "retained", "revoked"])
def test_governance_roundtrip_records_decision_history_and_actual_actor(
    store, decision
):
    _, _, factory, _ = store
    row = campaign_start(factory)
    ids = certification_ids(factory, row)
    assert len(ids) == 1
    with tenant_session(factory, A) as session:
        result = governance_service.certify(
            session, REVIEWER, ids, decision, "Synthetic decision"
        )
        assert (
            result.review_status == decision
            and result.user_id == USER
            and result.reviewer_id == USER
        )
    with tenant_session(factory, A) as session:
        cert = session.get(Certification, ids[0])
        history = session.query(CertificationHistory).one()
        assert cert.status == ("revoked" if decision == "revoked" else "approved")
        assert cert.decision == ("revoke" if decision == "revoked" else "approve")
        assert history.changed_by == USER and history.previous_status == "pending"
        assert session.get(Entitlement, GRANT).status == (
            "revoked" if decision == "revoked" else "active"
        )
        event = session.query(IAMAuditEvent).filter_by(event_type="certified").one()
        assert (
            event.performed_by == USER
            and event.subject_id == USER
            and event.certification_id == ids[0]
        )
    with tenant_session(factory, A) as session:
        assert (
            governance_service.complete_campaign(session, ADMIN, row.id, False).status
            == "completed"
        )


def test_governance_scope_is_persisted_and_honored(store):
    _, _, factory, _ = store
    extra_grant(factory)
    extra_grant(factory, resource="role-doc", granted_to_type="role")
    row = campaign_start(factory, entitlement_patterns=["document:synthetic-doc:read"])
    with tenant_session(factory, A) as session:
        campaign = session.get(AuditCampaign, row.id)
        assert campaign.scope["entitlement_patterns"] == ["document:synthetic-doc:read"]
        assert campaign.status == "active" and campaign.started_at is not None
        assert [c.entitlement_id for c in session.query(Certification)] == [GRANT]
        with pytest.raises(Exception) as error:
            governance_service.start_campaign(session, ADMIN, row.id)
        assert error.value.status_code == 400


def test_manager_assignment_is_blocked_without_fabricated_reviewer(store):
    _, _, factory, _ = store
    row = campaign_create(factory, reviewer_type="manager")
    with tenant_session(factory, A) as session:
        with pytest.raises(Exception) as error:
            governance_service.start_campaign(session, ADMIN, row.id)
        assert error.value.status_code == 409
    with tenant_session(factory, A) as session:
        assert session.get(AuditCampaign, row.id).status == "draft"
        assert session.query(Certification).count() == 0
        assert session.query(IAMAuditEvent).count() == 1


def test_admin_assignment_requires_current_role_and_independence(store):
    _, _, factory, _ = store
    row = campaign_start(factory, reviewer_type="admin")
    ids = certification_ids(factory, row)
    for caller in [RequestContext(A, str(B), ()), REVIEWER]:
        with tenant_session(factory, A) as session:
            with pytest.raises(Exception) as error:
                governance_service.certify(session, caller, ids, "approved", None)
            assert error.value.status_code == 403
    with tenant_session(factory, A) as session:
        response = governance_service.certify(session, ADMIN, ids, "approved", None)
        assert response.reviewer_id == B
    own = campaign_create(factory, reviewer_type="admin")
    extra_grant(factory, resource="admin-doc", beneficiary=B)
    with tenant_session(factory, A) as session:
        with pytest.raises(Exception) as error:
            governance_service.start_campaign(session, ADMIN, own.id)
        assert error.value.status_code == 409


def test_started_campaign_configuration_is_immutable_and_cancel_closes_decisions(store):
    _, _, factory, _ = store
    row = campaign_start(factory)
    ids = certification_ids(factory, row)
    with tenant_session(factory, A) as session:
        with pytest.raises(Exception) as error:
            governance_service.update_campaign(
                session,
                ADMIN,
                row.id,
                governance.CampaignUpdate(
                    end_date=datetime.now(timezone.utc) + timedelta(days=2)
                ),
            )
        assert error.value.status_code == 409
        response = governance_service.update_campaign(
            session, ADMIN, row.id, governance.CampaignUpdate(status="cancelled")
        )
        assert response.status == "cancelled"
    with tenant_session(factory, A) as session:
        with pytest.raises(Exception) as error:
            governance_service.certify(session, REVIEWER, ids, "approved", None)
        assert error.value.status_code == 409
        assert session.get(Entitlement, GRANT).status == "active"


def test_legacy_configuration_is_preserved_but_not_implicitly_executed(store):
    params, _, factory, _ = store
    identity = uuid4()
    with owner(params, "iam_test") as connection, connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO audit_campaigns (id,tenant_id,name,campaign_type,scope,review_config,schedule,created_by) VALUES (%s,%s,'Legacy','continuous','{}','{}','{}',%s)",
            tuple(map(str, [identity, A, USER])),
        )
    with tenant_session(factory, A) as session:
        with pytest.raises(Exception) as error:
            governance_service.start_campaign(session, ADMIN, identity)
        assert error.value.status_code == 409
        row = session.get(AuditCampaign, identity)
        assert (
            row.campaign_type == "continuous"
            and row.scope == {}
            and row.status == "draft"
        )


def test_governance_rejects_cross_tenant_ids_even_for_platform_role(store):
    _, _, factory, _ = store
    row = campaign_start(factory)
    ids = certification_ids(factory, row)
    foreign = RequestContext(B, str(B), ("PLATFORM_ADMIN",))
    with tenant_session(factory, B) as session:
        with pytest.raises(Exception) as error:
            governance_service.complete_campaign(session, foreign, row.id, True)
        assert error.value.status_code == 404
        with pytest.raises(Exception) as error:
            governance_service.certify(session, foreign, ids, "revoked", None)
        assert error.value.status_code == 404
    with tenant_session(factory, A) as session:
        assert session.get(Entitlement, GRANT).status == "active"
        assert session.query(CertificationHistory).count() == 0


def test_governance_participant_visibility_is_not_tenant_wide(store):
    _, _, factory, _ = store
    extra_grant(factory, beneficiary=uuid4())
    row = campaign_start(factory)
    with tenant_session(factory, A) as session:
        visible = asyncio.run(
            governance.list_certifications(
                campaign_id=None,
                user_id=None,
                review_status=None,
                limit=100,
                offset=0,
                request_context=REVIEWER,
                db=session,
            )
        )
        assert len(visible) == 1 and visible[0].user_id == USER
        with pytest.raises(Exception) as error:
            asyncio.run(
                governance.get_pending_certifications(
                    user_id=B,
                    campaign_id=None,
                    limit=100,
                    offset=0,
                    request_context=REVIEWER,
                    db=session,
                )
            )
        assert error.value.status_code == 403


@pytest.mark.parametrize("mutation", ["target", "inactive"])
def test_changed_or_inactive_grant_cannot_be_attested(store, mutation):
    _, _, factory, _ = store
    row = campaign_start(factory)
    ids = certification_ids(factory, row)
    with tenant_session(factory, A) as session:
        grant = session.get(Entitlement, GRANT)
        if mutation == "target":
            grant.resource_id = "changed-after-assignment"
        else:
            grant.status = "suspended"
    with tenant_session(factory, A) as session:
        with pytest.raises(Exception) as error:
            governance_service.certify(session, REVIEWER, ids, "retained", None)
        assert error.value.status_code == 409
    with tenant_session(factory, A) as session:
        assert session.query(CertificationHistory).count() == 0


@pytest.mark.parametrize("auto_revoke,days", [(True, 0), (False, 0), (True, None)])
def test_completion_cannot_skip_pending_or_revocation_grace(store, auto_revoke, days):
    _, _, factory, _ = store
    row = campaign_start(factory, auto_revoke_days=days)
    with tenant_session(factory, A) as session:
        with pytest.raises(Exception) as error:
            governance_service.complete_campaign(session, ADMIN, row.id, auto_revoke)
        assert error.value.status_code == 409
    with tenant_session(factory, A) as session:
        assert session.get(AuditCampaign, row.id).status == "active"
        assert session.get(Entitlement, GRANT).status == "active"


def test_manual_completion_after_grace_audits_each_revocation(store, monkeypatch):
    _, _, factory, _ = store
    row = campaign_start(factory)

    class Later(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(timezone.utc) + timedelta(hours=2)

    monkeypatch.setattr(governance_service, "datetime", Later)
    with tenant_session(factory, A) as session:
        assert (
            governance_service.complete_campaign(session, ADMIN, row.id, True).status
            == "completed"
        )
    with tenant_session(factory, A) as session:
        assert session.get(Entitlement, GRANT).status == "revoked"
        assert session.query(CertificationHistory).one().changed_by == B
        for event in session.query(IAMAuditEvent).filter(
            IAMAuditEvent.event_type.in_(["certified", "revoked", "campaign_completed"])
        ):
            assert event.performed_by == B


@pytest.mark.parametrize(
    "operation", ["create", "update", "start", "complete", "certify", "bulk"]
)
def test_governance_audit_unavailable_rolls_back_all_state(store, operation):
    params, _, factory, _ = store
    row = None if operation == "create" else campaign_create(factory)
    if operation in {"complete", "certify", "bulk"}:
        with tenant_session(factory, A) as session:
            governance_service.start_campaign(session, ADMIN, row.id)
    ids = certification_ids(factory, row) if row else []
    if operation == "complete":
        with tenant_session(factory, A) as session:
            governance_service.certify(session, REVIEWER, ids, "approved", None)
    with tenant_session(factory, A) as session:
        before = (
            session.query(IAMAuditEvent).count(),
            session.query(CertificationHistory).count(),
        )
    with owner(params, "iam_test") as connection, connection.cursor() as cursor:
        cursor.execute("REVOKE INSERT ON iam_audit_events FROM sg_test_app")
    try:
        with pytest.raises(Exception) as error:
            if operation == "create":
                campaign_create(factory)
            else:
                with tenant_session(factory, A) as session:
                    if operation == "update":
                        governance_service.update_campaign(
                            session,
                            ADMIN,
                            row.id,
                            governance.CampaignUpdate(name="Changed"),
                        )
                    elif operation == "start":
                        governance_service.start_campaign(session, ADMIN, row.id)
                    elif operation == "complete":
                        governance_service.complete_campaign(
                            session, ADMIN, row.id, False
                        )
                    else:
                        governance_service.certify(
                            session,
                            REVIEWER,
                            ids,
                            "revoked",
                            None,
                            bulk=operation == "bulk",
                        )
        assert error.value.status_code == 503
        with tenant_session(factory, A) as session:
            assert (
                session.query(IAMAuditEvent).count(),
                session.query(CertificationHistory).count(),
            ) == before
            assert session.get(Entitlement, GRANT).status == "active"
            if row:
                current = session.get(AuditCampaign, row.id)
                assert current.name == "Synthetic governance"
                assert current.status == (
                    "active"
                    if operation in {"complete", "certify", "bulk"}
                    else "draft"
                )
            else:
                assert session.query(AuditCampaign).count() == 0
    finally:
        with owner(params, "iam_test") as connection, connection.cursor() as cursor:
            cursor.execute("GRANT INSERT ON iam_audit_events TO sg_test_app")


def test_bulk_validation_does_not_commit_valid_subset(store):
    _, _, factory, _ = store
    second = extra_grant(factory)
    row = campaign_start(factory)
    ids = certification_ids(factory, row)
    with tenant_session(factory, A) as session:
        session.get(Entitlement, second).resource_id = "changed-target"
    with tenant_session(factory, A) as session:
        with pytest.raises(Exception) as error:
            governance_service.certify(
                session, REVIEWER, ids, "revoked", None, bulk=True
            )
        assert error.value.status_code == 409
    with tenant_session(factory, A) as session:
        assert {c.status for c in session.query(Certification)} == {"pending"}
        assert {g.status for g in session.query(Entitlement)} == {"active"}
        assert session.query(CertificationHistory).count() == 0


def test_certification_history_failure_prevents_grant_revocation(store):
    params, _, factory, _ = store
    row = campaign_start(factory)
    ids = certification_ids(factory, row)
    with owner(params, "iam_test") as connection, connection.cursor() as cursor:
        cursor.execute("REVOKE INSERT ON certification_history FROM sg_test_app")
    try:
        with tenant_session(factory, A) as session:
            with pytest.raises(Exception) as error:
                governance_service.certify(session, REVIEWER, ids, "revoked", None)
            assert error.value.status_code == 503
        with tenant_session(factory, A) as session:
            assert session.get(Entitlement, GRANT).status == "active"
            assert session.query(CertificationHistory).count() == 0
            assert (
                session.query(IAMAuditEvent).filter_by(event_type="certified").count()
                == 0
            )
    finally:
        with owner(params, "iam_test") as connection, connection.cursor() as cursor:
            cursor.execute("GRANT INSERT ON certification_history TO sg_test_app")


def test_history_cannot_name_different_same_tenant_grant(store):
    _, _, factory, _ = store
    other = extra_grant(factory)
    row = campaign_start(factory)
    ids = certification_ids(factory, row)
    with tenant_session(factory, A) as session:
        cert = session.get(Certification, ids[0])
        wrong = other if cert.entitlement_id != other else GRANT
        session.execute(text("SELECT set_config('app.is_superadmin','true',true)"))
        with pytest.raises(DBAPIError):
            with session.begin_nested():
                session.add(
                    CertificationHistory(
                        certification_id=cert.id,
                        entitlement_id=wrong,
                        changed_by=USER,
                        new_status="revoked",
                    )
                )
                session.flush()


def test_campaign_size_bound_rolls_back_start(store, monkeypatch):
    _, _, factory, _ = store
    extra_grant(factory)
    row = campaign_create(factory)
    monkeypatch.setattr(governance_service, "MAX_CERTIFICATIONS", 1)
    with tenant_session(factory, A) as session:
        with pytest.raises(Exception) as error:
            governance_service.start_campaign(session, ADMIN, row.id)
        assert error.value.status_code == 409
    with tenant_session(factory, A) as session:
        assert session.query(Certification).count() == 0


def test_governance_commit_failure_and_lost_acknowledgement(store, monkeypatch):
    _, _, factory, _ = store
    row = campaign_start(factory)
    ids = certification_ids(factory, row)
    with tenant_session(factory, A) as session:
        with monkeypatch.context() as patch:
            patch.setattr(
                session,
                "commit",
                lambda: (_ for _ in ()).throw(
                    RuntimeError("Synthetic before-commit outage")
                ),
            )
            with pytest.raises(Exception) as error:
                governance_service.certify(session, REVIEWER, ids, "revoked", None)
            assert error.value.status_code == 503
    with tenant_session(factory, A) as session:
        assert session.get(Entitlement, GRANT).status == "active"
        assert session.query(CertificationHistory).count() == 0
        original = session.commit

        def lost_ack():
            original()
            raise RuntimeError("Synthetic lost commit acknowledgement")

        with monkeypatch.context() as patch:
            patch.setattr(session, "commit", lost_ack)
            with pytest.raises(Exception) as error:
                governance_service.certify(session, REVIEWER, ids, "revoked", None)
            assert error.value.status_code == 503
    with tenant_session(factory, A) as session:
        assert session.get(Entitlement, GRANT).status == "revoked"
        assert session.query(CertificationHistory).count() == 1
        with pytest.raises(Exception) as error:
            governance_service.certify(session, REVIEWER, ids, "revoked", None)
        assert error.value.status_code == 409


def test_completion_serializes_with_reviewer_decision(store, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    import time

    params, engine, factory, _ = store
    row = campaign_start(factory)
    ids = certification_ids(factory, row)
    concurrent = create_engine(engine.url, pool_size=2, max_overflow=0)
    install_tenant_pool_reset(concurrent)
    sessions = sessionmaker(bind=concurrent)
    staged, release = Event(), Event()
    original = AuditLogger.log_entitlement_event

    def hold(logger, event_type, *args, **kwargs):
        event = original(logger, event_type, *args, **kwargs)
        if event_type == "certified":
            staged.set()
            assert release.wait(10)
        return event

    monkeypatch.setattr(AuditLogger, "log_entitlement_event", hold)

    def review():
        with tenant_session(sessions, A) as session:
            return governance_service.certify(session, REVIEWER, ids, "approved", None)

    def complete():
        with tenant_session(sessions, A) as session:
            return governance_service.complete_campaign(session, ADMIN, row.id, True)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(review)
            assert staged.wait(5)
            second = pool.submit(complete)
            try:
                deadline = time.monotonic() + 5
                blocked = False
                while time.monotonic() < deadline:
                    with (
                        owner(params, "iam_test") as connection,
                        connection.cursor() as cursor,
                    ):
                        cursor.execute(
                            "SELECT count(*) FROM pg_stat_activity WHERE datname='iam_test' AND usename='sg_test_app' AND wait_event_type='Lock'"
                        )
                        blocked = cursor.fetchone()[0] > 0
                    if blocked:
                        break
                    time.sleep(0.02)
                assert blocked
            finally:
                release.set()
            assert first.result(timeout=5).review_status == "approved"
            assert second.result(timeout=5).status == "completed"
        with tenant_session(factory, A) as session:
            assert session.get(Entitlement, GRANT).status == "active"
            assert session.query(CertificationHistory).count() == 1
            assert (
                session.query(IAMAuditEvent).filter_by(event_type="revoked").count()
                == 0
            )
    finally:
        release.set()
        concurrent.dispose()


@pytest.mark.parametrize("mutation", ["missing", "questioned"])
def test_completion_rejects_missing_or_unresolved_certification_set(store, mutation):
    _, _, factory, _ = store
    row = campaign_start(factory)
    ids = certification_ids(factory, row)
    with tenant_session(factory, A) as session:
        cert = session.get(Certification, ids[0])
        if mutation == "missing":
            session.delete(cert)
        else:
            cert.status = "questioned"
    with tenant_session(factory, A) as session:
        with pytest.raises(Exception) as error:
            governance_service.complete_campaign(session, ADMIN, row.id, True)
        assert error.value.status_code == 409
    with tenant_session(factory, A) as session:
        assert session.get(AuditCampaign, row.id).status == "active"
        assert session.get(Entitlement, GRANT).status == "active"


@pytest.mark.parametrize("ids,decision", [([], "approved"), ([GRANT], "unsupported")])
def test_domain_entrypoint_rejects_invalid_decisions_or_empty_work(
    store, ids, decision
):
    _, _, factory, _ = store
    with tenant_session(factory, A) as session:
        with pytest.raises(Exception) as error:
            governance_service.certify(
                session, REVIEWER, ids, decision, None, bulk=True
            )
        assert error.value.status_code == 422
        assert session.query(CertificationHistory).count() == 0


def test_governance_revocation_invalidates_read_cache_after_durable_commit(
    store, monkeypatch
):
    _, _, factory, _ = store
    row = campaign_start(factory)
    ids = certification_ids(factory, row)
    calls = []

    def invalidate(identity, tenant):
        with tenant_session(factory, A) as other:
            assert other.get(Entitlement, UUID(identity)).status == "revoked"
            assert (
                other.query(IAMAuditEvent).filter_by(event_type="revoked").count() == 1
            )
        calls.append((identity, tenant))

    monkeypatch.setattr(governance_service.cache, "invalidate_entitlement", invalidate)
    with tenant_session(factory, A) as session:
        governance_service.certify(session, REVIEWER, ids, "revoked", None)
    assert calls == [(str(GRANT), str(A))]


# Role synchronization owns grants through a separate table, never body metadata.
class SyntheticRoleDirectory:
    def __init__(self, roles=("reader",), *, user=USER, tenant=A, age=0):
        self.snapshots = [
            RoleSnapshot(
                tenant,
                user,
                tuple(roles),
                datetime.now(timezone.utc) - timedelta(seconds=age),
                "synthetic-test",
            )
        ]

    async def observe(self, tenant, identity=None):
        return self.snapshots


def role_pattern(factory, role="reader", target="document:role-doc:read"):
    with tenant_session(factory, A) as session:
        return role_sync_service.pattern_change(
            session,
            ADMIN,
            role_mappings.RolePatternCreate(
                role_name=role, tenant_id=A, entitlement_pattern=target, created_by=USER
            ),
        )


def role_sync(factory, directory):
    with tenant_session(factory, A) as session:
        return asyncio.run(
            role_sync_service.RoleSyncService(
                session, directory=directory
            ).sync_user_roles_to_entitlements(USER, A, USER, request_context=ADMIN)
        )


@pytest.mark.parametrize("model", [RoleEntitlementPattern, RoleGrantBinding])
def test_role_models_match_reviewed_sql(databases, model):
    test_governance_models_match_reviewed_sql(databases, model)


def test_role_pattern_actor_crud_and_audit_are_compatible(store):
    _, _, factory, _ = store
    row = role_pattern(factory)
    assert row.created_by == B and row.auto_grant and row.enabled
    with pytest.raises(Exception) as error:
        role_pattern(factory)
    assert error.value.status_code == 409
    with tenant_session(factory, A) as session:
        changed = role_sync_service.pattern_change(
            session,
            ADMIN,
            role_mappings.RolePatternUpdate(auto_grant=False),
            identity=row.id,
        )
        assert not changed.auto_grant
        role_sync_service.pattern_change(session, ADMIN, identity=row.id, delete=True)
    with tenant_session(factory, A) as session:
        assert session.get(RoleEntitlementPattern, row.id) is None
        assert {e.event_type for e in session.query(IAMAuditEvent)} == {
            "role_pattern_created",
            "role_pattern_updated",
            "role_pattern_deleted",
        }
        assert {e.performed_by for e in session.query(IAMAuditEvent)} == {B}


def test_role_sync_creates_owned_grant_with_verified_actor_and_retries_idempotently(
    store,
):
    _, _, factory, _ = store
    pattern = role_pattern(factory)
    result = role_sync(factory, SyntheticRoleDirectory())
    assert result["entitlements_created"] == 1 and result["errors"] == []
    result = role_sync(factory, SyntheticRoleDirectory())
    assert result["entitlements_created"] == 0 and result["entitlements_existing"] == 1
    with tenant_session(factory, A) as session:
        binding = session.query(RoleGrantBinding).one()
        grant = session.get(Entitlement, binding.entitlement_id)
        assert grant.granted_by == binding.created_by == B
        assert (
            binding.tenant_id == A
            and binding.subject_id == USER
            and binding.roles == ["reader"]
        )
        assert binding.pattern_ids == [str(pattern.id)]
        assert session.query(IAMAuditEvent).filter_by(event_type="created").count() == 1
        assert (
            session.query(IAMAuditEvent)
            .filter_by(event_type="role_grant_bound")
            .one()
            .performed_by
            == B
        )


def test_overlapping_roles_do_not_revoke_remaining_authority(store):
    _, _, factory, _ = store
    role_pattern(factory)
    role_pattern(factory, "editor")
    role_sync(factory, SyntheticRoleDirectory(("reader", "editor")))
    result = role_sync(factory, SyntheticRoleDirectory(("reader",)))
    assert result["entitlements_revoked"] == 0
    with tenant_session(factory, A) as session:
        binding = session.query(RoleGrantBinding).one()
        assert (
            binding.roles == ["reader"]
            and session.get(Entitlement, binding.entitlement_id).status == "active"
        )
    result = role_sync(factory, SyntheticRoleDirectory(()))
    assert result["entitlements_revoked"] == 1
    result = role_sync(factory, SyntheticRoleDirectory(("reader",)))
    assert result["entitlements_created"] == 0 and result["entitlements_blocked"] == 1
    with tenant_session(factory, A) as session:
        assert (
            session.get(
                Entitlement, session.query(RoleGrantBinding).one().entitlement_id
            ).status
            == "revoked"
        )


def test_manual_or_legacy_metadata_never_creates_sync_ownership(store):
    _, _, factory, _ = store
    role_pattern(factory, target="document:synthetic-doc:read")
    with tenant_session(factory, A) as session:
        session.get(Entitlement, GRANT).metadata_json = {
            "source": "role_sync",
            "role": "reader",
            "contract": "iam_role_sync_v1",
        }
    assert role_sync(factory, SyntheticRoleDirectory())["entitlements_existing"] == 1
    role_sync(factory, SyntheticRoleDirectory(()))
    with tenant_session(factory, A) as session:
        assert session.get(Entitlement, GRANT).status == "active"
        assert session.query(RoleGrantBinding).count() == 0


@pytest.mark.parametrize(
    "directory", [SyntheticRoleDirectory(tenant=B), SyntheticRoleDirectory(age=60)]
)
def test_unverified_or_stale_observation_cannot_grant(store, directory):
    _, _, factory, _ = store
    role_pattern(factory)
    with pytest.raises(Exception) as error:
        role_sync(factory, directory)
    assert error.value.status_code == 503
    with tenant_session(factory, A) as session:
        assert session.query(RoleGrantBinding).count() == 0


def test_directory_outage_does_not_mean_role_removal(store):
    _, _, factory, _ = store
    role_pattern(factory)
    role_sync(factory, SyntheticRoleDirectory())

    class Unavailable:
        async def observe(self, *args):
            raise HTTPException(status_code=503, detail="Synthetic directory outage")

    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        role_sync(factory, Unavailable())
    with tenant_session(factory, A) as session:
        assert (
            session.get(
                Entitlement, session.query(RoleGrantBinding).one().entitlement_id
            ).status
            == "active"
        )


@pytest.mark.parametrize("table", ["iam_audit_events", "iam_role_grants"])
def test_role_sync_write_failure_cannot_commit_grant_or_ownership(store, table):
    params, _, factory, _ = store
    role_pattern(factory)
    with owner(params, "iam_test") as connection, connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("REVOKE INSERT ON {} FROM sg_test_app").format(
                sql.Identifier(table)
            )
        )
    try:
        with pytest.raises(Exception) as error:
            role_sync(factory, SyntheticRoleDirectory())
        assert error.value.status_code == 503
        with tenant_session(factory, A) as session:
            assert session.query(RoleGrantBinding).count() == 0
            assert (
                session.query(Entitlement).filter_by(resource_id="role-doc").count()
                == 0
            )
            assert (
                session.query(IAMAuditEvent).count() == 1
            )  # The earlier definition creation only.
    finally:
        with owner(params, "iam_test") as connection, connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("GRANT INSERT ON {} TO sg_test_app").format(
                    sql.Identifier(table)
                )
            )


def test_role_removal_audit_failure_keeps_grant_and_sources(store):
    params, _, factory, _ = store
    role_pattern(factory)
    role_sync(factory, SyntheticRoleDirectory())
    with owner(params, "iam_test") as connection, connection.cursor() as cursor:
        cursor.execute("REVOKE INSERT ON iam_audit_events FROM sg_test_app")
    try:
        with pytest.raises(Exception) as error:
            role_sync(factory, SyntheticRoleDirectory(()))
        assert error.value.status_code == 503
        with tenant_session(factory, A) as session:
            binding = session.query(RoleGrantBinding).one()
            assert (
                binding.roles == ["reader"]
                and session.get(Entitlement, binding.entitlement_id).status == "active"
            )
    finally:
        with owner(params, "iam_test") as connection, connection.cursor() as cursor:
            cursor.execute("GRANT INSERT ON iam_audit_events TO sg_test_app")


def test_revoke_requires_verified_role_absence(store):
    _, _, factory, _ = store
    role_pattern(factory)
    role_sync(factory, SyntheticRoleDirectory())
    with tenant_session(factory, A) as session:
        service = role_sync_service.RoleSyncService(
            session, directory=SyntheticRoleDirectory()
        )
        with pytest.raises(Exception) as error:
            asyncio.run(
                service.revoke_user_entitlements_for_role(
                    USER, "reader", A, request_context=ADMIN
                )
            )
        assert error.value.status_code == 409
    with tenant_session(factory, A) as session:
        service = role_sync_service.RoleSyncService(
            session, directory=SyntheticRoleDirectory(())
        )
        assert (
            asyncio.run(
                service.revoke_user_entitlements_for_role(
                    USER, "reader", A, request_context=ADMIN
                )
            )["entitlements_revoked"]
            == 1
        )


def test_pattern_deletion_does_not_orphan_managed_grants(store):
    _, _, factory, _ = store
    pattern = role_pattern(factory)
    role_sync(factory, SyntheticRoleDirectory())
    with tenant_session(factory, A) as session:
        role_sync_service.pattern_change(
            session, ADMIN, identity=pattern.id, delete=True
        )
    assert role_sync(factory, SyntheticRoleDirectory())["entitlements_revoked"] == 1


def test_bulk_roles_are_atomic_and_reconcile_former_members(store):
    _, _, factory, _ = store
    role_pattern(factory)
    role_sync(factory, SyntheticRoleDirectory())
    directory = SyntheticRoleDirectory(())
    directory.snapshots.append(
        RoleSnapshot(
            A, uuid4(), ("reader",), datetime.now(timezone.utc), "synthetic-test"
        )
    )
    with tenant_session(factory, A) as session:
        result = asyncio.run(
            role_sync_service.RoleSyncService(
                session, directory=directory
            ).sync_role_to_all_users("reader", A, request_context=ADMIN)
        )
        assert (
            result["users_processed"] == 2
            and result["entitlements_created"] == 1
            and result["entitlements_revoked"] == 1
        )
    directory.snapshots.append(
        RoleSnapshot(
            A,
            uuid4(),
            ("reader",),
            datetime.now(timezone.utc) - timedelta(seconds=60),
            "synthetic-test",
        )
    )
    with tenant_session(factory, A) as session:
        before = session.query(RoleGrantBinding).count()
        session.commit()
        with pytest.raises(Exception) as error:
            asyncio.run(
                role_sync_service.RoleSyncService(
                    session, directory=directory
                ).sync_role_to_all_users("reader", A, request_context=ADMIN)
            )
        assert error.value.status_code == 503
        assert session.query(RoleGrantBinding).count() == before


def test_global_definitions_remain_invisible_and_cannot_grant(store):
    params, _, factory, _ = store
    identity = uuid4()
    with owner(params, "iam_test") as connection, connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO role_entitlement_patterns (id,role_name,tenant_id,entitlement_pattern,auto_grant) VALUES (%s,'reader',NULL,'document:global:read',true)",
            (str(identity),),
        )
    role_sync(factory, SyntheticRoleDirectory())
    with tenant_session(factory, A) as session:
        session.execute(text("SELECT set_config('app.is_superadmin','true',true)"))
        assert session.get(RoleEntitlementPattern, identity) is None
        assert session.query(RoleGrantBinding).count() == 0


@pytest.mark.parametrize("foreign", [True, False])
def test_binding_cannot_cross_tenant_or_subject_even_with_admin_flag(store, foreign):
    _, _, factory, _ = store
    with tenant_session(factory, A) as session:
        session.execute(text("SELECT set_config('app.is_superadmin','true',true)"))
        with pytest.raises(DBAPIError):
            with session.begin_nested():
                session.add(
                    RoleGrantBinding(
                        tenant_id=B if foreign else A,
                        subject_id=USER if foreign else B,
                        entitlement_id=GRANT,
                        target={},
                        roles=[],
                        pattern_ids=[],
                        created_by=B,
                    )
                )
                session.flush()


def test_managed_grant_target_cannot_be_repurposed_by_generic_writer(store):
    _, _, factory, _ = store
    role_pattern(factory)
    role_sync(factory, SyntheticRoleDirectory())
    with tenant_session(factory, A) as session:
        identity = session.query(RoleGrantBinding).one().entitlement_id
        with pytest.raises(DBAPIError):
            with session.begin_nested():
                grant = session.get(Entitlement, identity)
                grant.resource_id = "replacement-target"
                session.flush()
        assert session.get(Entitlement, identity).resource_id == "role-doc"


def test_role_sync_commit_failure_and_lost_ack_are_reconciled(store, monkeypatch):
    _, _, factory, _ = store
    role_pattern(factory)
    with tenant_session(factory, A) as session:
        with monkeypatch.context() as patch:

            def unavailable():
                raise RuntimeError("Synthetic pre-commit outage")

            patch.setattr(session, "commit", unavailable)
            with pytest.raises(Exception) as error:
                asyncio.run(
                    role_sync_service.RoleSyncService(
                        session, directory=SyntheticRoleDirectory()
                    ).sync_user_roles_to_entitlements(USER, A, request_context=ADMIN)
                )
            assert error.value.status_code == 503
    with tenant_session(factory, A) as session:
        assert session.query(RoleGrantBinding).count() == 0
        session.commit()
        original = session.commit
        with monkeypatch.context() as patch:

            def lost_ack():
                original()
                raise RuntimeError("Synthetic acknowledgement loss")

            patch.setattr(session, "commit", lost_ack)
            with pytest.raises(Exception) as error:
                asyncio.run(
                    role_sync_service.RoleSyncService(
                        session, directory=SyntheticRoleDirectory()
                    ).sync_user_roles_to_entitlements(USER, A, request_context=ADMIN)
                )
            assert error.value.status_code == 503
    assert role_sync(factory, SyntheticRoleDirectory())["entitlements_created"] == 0
    with tenant_session(factory, A) as session:
        assert session.query(RoleGrantBinding).count() == 1


def test_competing_role_syncs_serialize_and_create_one_grant(store, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    import time

    params, engine, factory, _ = store
    role_pattern(factory)
    concurrent = create_engine(engine.url, pool_size=2, max_overflow=0)
    install_tenant_pool_reset(concurrent)
    sessions = sessionmaker(bind=concurrent)
    staged, release = Event(), Event()
    original = AuditLogger.log_entitlement_event

    def hold(logger, event_type, *args, **kwargs):
        event = original(logger, event_type, *args, **kwargs)
        if event_type == "role_grant_bound":
            staged.set()
            assert release.wait(10)
        return event

    monkeypatch.setattr(AuditLogger, "log_entitlement_event", hold)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(role_sync, sessions, SyntheticRoleDirectory())
            assert staged.wait(5)
            second = pool.submit(role_sync, sessions, SyntheticRoleDirectory())
            try:
                deadline = time.monotonic() + 5
                blocked = False
                while time.monotonic() < deadline:
                    with (
                        owner(params, "iam_test") as connection,
                        connection.cursor() as cursor,
                    ):
                        cursor.execute(
                            "SELECT count(*) FROM pg_stat_activity WHERE datname='iam_test' AND usename='sg_test_app' AND wait_event_type='Lock'"
                        )
                        blocked = cursor.fetchone()[0] > 0
                    if blocked:
                        break
                    time.sleep(0.02)
                assert blocked
            finally:
                release.set()
            assert first.result(timeout=5)["entitlements_created"] == 1
            assert second.result(timeout=5)["entitlements_created"] == 0
        with tenant_session(factory, A) as session:
            assert session.query(RoleGrantBinding).count() == 1
    finally:
        release.set()
        concurrent.dispose()


def test_policy_templates_are_tenant_local_and_seeds_fail_explicitly(store):
    from app.services.policy_service import PolicyService
    from app.services.iam_portal_service import IAMPortalService
    from fastapi import HTTPException

    params, _, _, policies = store
    with owner(params, "catalog_test") as connection, connection.cursor() as cursor:
        for tenant, name in [(A, "own"), (B, "foreign"), (None, "global")]:
            cursor.execute(
                "INSERT INTO policy_templates (id,name,display_name,policy_type,template_data,tenant_id) VALUES (%s,%s,'Synthetic','access','{}',%s)",
                (str(uuid4()), name, str(tenant) if tenant else None),
            )
    with tenant_session(policies, A) as session:
        service = PolicyService(session, A, "synthetic")
        assert [template.name for template in service.list_templates()] == ["own"]
        for method in [
            service.list_seed_policies,
            lambda: service.clone_seed_policy(uuid4(), str(B)),
        ]:
            with pytest.raises(HTTPException) as error:
                method()
            assert error.value.status_code == 503
        portal = IAMPortalService.__new__(IAMPortalService)
        portal.db = session
        portal.tenant_id = A
        with pytest.raises(HTTPException) as error:
            portal.list_policy_bundles()
        assert error.value.status_code == 503


# ITDR proposals reuse append-only IAM audit storage; no new runtime DDL.
from app.schemas.itdr import ThreatSignal
from app.services.itdr_service import ITDRService
from fastapi import HTTPException


class SyntheticITDRDirectory:
    async def observe(self, tenant, user):
        return [
            RoleSnapshot(tenant, user, (), datetime.now(timezone.utc), "synthetic-itdr")
        ]


def itdr_setup(monkeypatch):
    monkeypatch.setattr(
        "app.core.config.settings.IAM_ROLE_SYNC_REALMS",
        {str(A): "synthetic-itdr", str(B): "synthetic-itdr"},
    )
    return ThreatSignal(
        user_id=USER,
        threat_type="account_takeover",
        context={
            "password": "synthetic-only",
            "nested": {"authorization": "synthetic-only"},
            "source_ip": "192.0.2.1",
        },
    )


def test_itdr_durable_receipt_actor_redaction_and_tenant_visibility(store, monkeypatch):
    _, _, factory, _ = store
    signal = itdr_setup(monkeypatch)
    with tenant_session(factory, A) as session:
        result = asyncio.run(
            ITDRService(session, directory=SyntheticITDRDirectory()).propose(
                [signal], ADMIN
            )
        )[0]
    with tenant_session(factory, A) as session:
        row = session.get(IAMAuditEvent, result.proposal_id)
        assert (
            row.event_type == "itdr_proposed"
            and row.performed_by == B
            and row.subject_id == USER
        )
        assert row.decision is None and row.changes["effects_executed"] == []
        assert row.metadata_json["context"]["password"] == "[REDACTED]"
        assert row.metadata_json["context"]["nested"]["authorization"] == "[REDACTED]"
        assert row.metadata_json["signal_trust"] == "caller_assertion"
        assert session.query(Entitlement).count() == 1
        assert session.get(Entitlement, GRANT).status == "active"
    with tenant_session(factory, B) as session:
        assert session.get(IAMAuditEvent, result.proposal_id) is None
    assert result.actions_executed == [] and result.soar_incident_id is None


def test_itdr_second_audit_failure_rolls_back_entire_batch(store, monkeypatch):
    _, _, factory, _ = store
    signal = itdr_setup(monkeypatch)
    original = AuditLogger.log_entitlement_event
    calls = 0

    def fail_second(logger, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("Synthetic audit outage")
        return original(logger, *args, **kwargs)

    monkeypatch.setattr(AuditLogger, "log_entitlement_event", fail_second)
    with tenant_session(factory, A) as session:
        with pytest.raises(HTTPException) as error:
            asyncio.run(
                ITDRService(session, directory=SyntheticITDRDirectory()).propose(
                    [signal, signal], ADMIN
                )
            )
        assert error.value.status_code == 503
    with tenant_session(factory, A) as session:
        assert session.query(IAMAuditEvent).count() == 0


def test_itdr_failed_directory_batch_commits_only_rejections(store, monkeypatch):
    _, _, factory, _ = store
    signal = itdr_setup(monkeypatch)

    class Failure(SyntheticITDRDirectory):
        async def observe(self, *args):
            raise RuntimeError("Synthetic provider outage")

    with tenant_session(factory, A) as session:
        with pytest.raises(HTTPException) as error:
            asyncio.run(
                ITDRService(session, directory=Failure()).propose(
                    [signal, signal], ADMIN
                )
            )
        assert error.value.status_code == 503
    with tenant_session(factory, A) as session:
        rows = session.query(IAMAuditEvent).all()
        assert len(rows) == 2 and all(
            row.event_type == "itdr_rejected" and row.decision == "deny" for row in rows
        )
        assert all(row.changes["effects_executed"] == [] for row in rows)


@pytest.mark.parametrize("lost_ack", [False, True])
def test_itdr_commit_failure_never_returns_success_and_can_be_reconciled(
    store, monkeypatch, lost_ack
):
    _, _, factory, _ = store
    signal = itdr_setup(monkeypatch)
    with tenant_session(factory, A) as session:
        original = session.commit

        def fail():
            if lost_ack:
                original()
            raise RuntimeError("Synthetic acknowledgement failure")

        with monkeypatch.context() as patch:
            patch.setattr(session, "commit", fail)
            with pytest.raises(HTTPException) as error:
                asyncio.run(
                    ITDRService(session, directory=SyntheticITDRDirectory()).propose(
                        [signal], ADMIN
                    )
                )
            assert (
                error.value.status_code == 503
                and "inspect audit state" in error.value.detail
            )
    with tenant_session(factory, A) as session:
        assert session.query(IAMAuditEvent).count() == (1 if lost_ack else 0)


def test_itdr_forced_rls_blocks_misbound_session_audit(store, monkeypatch):
    _, _, factory, _ = store
    signal = itdr_setup(monkeypatch)
    with tenant_session(factory, B) as session:
        with pytest.raises(HTTPException) as error:
            asyncio.run(
                ITDRService(session, directory=SyntheticITDRDirectory()).propose(
                    [signal], ADMIN
                )
            )
        assert error.value.status_code == 503
    with tenant_session(factory, A) as session:
        assert session.query(IAMAuditEvent).count() == 0


def test_itdr_audit_permission_outage_blocks_proposal(store, monkeypatch):
    params, _, factory, _ = store
    signal = itdr_setup(monkeypatch)
    with owner(params, "iam_test") as connection, connection.cursor() as cursor:
        cursor.execute("REVOKE INSERT ON iam_audit_events FROM sg_test_app")
    try:
        with tenant_session(factory, A) as session:
            with pytest.raises(HTTPException) as error:
                asyncio.run(
                    ITDRService(session, directory=SyntheticITDRDirectory()).propose(
                        [signal], ADMIN
                    )
                )
            assert error.value.status_code == 503
    finally:
        with owner(params, "iam_test") as connection, connection.cursor() as cursor:
            cursor.execute("GRANT INSERT ON iam_audit_events TO sg_test_app")
    with tenant_session(factory, A) as session:
        assert session.query(IAMAuditEvent).count() == 0


# IAM-local NHI lifecycle: no provider or machine-authentication integration.
from app.models.service_account import ServiceAccount
from app.services.nhi_service import NHIService
from app.services import nhi_service as nhi_service_module


@pytest.fixture
def nhi_enabled(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.IAM_ENABLE_SERVICE_ACCOUNTS", True)


def nhi_create(factory, caller=ADMIN, **changes):
    with tenant_session(factory, caller.tenant_id) as session:
        return NHIService(session, caller).create_service_account(
            {"name": "synthetic-nhi", **changes}
        )


def nhi_change(factory, account, operation, version, caller=ADMIN):
    with tenant_session(factory, caller.tenant_id) as session:
        return NHIService(session, caller).transition(
            account, operation, {"expected_version": version}
        )


def nhi_check(factory, account, secret, caller=ADMIN):
    with tenant_session(factory, caller.tenant_id) as session:
        return NHIService(session, caller).check_credentials(account.client_id, secret)


def test_nhi_model_matches_reviewed_sql(databases):
    test_governance_models_match_reviewed_sql(databases, ServiceAccount)


def test_nhi_creation_is_local_tenant_owned_and_audited_without_secrets(
    store, nhi_enabled
):
    import hashlib

    _, _, factory, _ = store
    issued = nhi_create(factory)
    with tenant_session(factory, A) as session:
        row = session.get(ServiceAccount, issued.id)
        assert row.owner_user_id == B == row.created_by
        assert (
            row.secret_hash == hashlib.sha256(issued.client_secret.encode()).hexdigest()
        )
        assert row.secret_hash != issued.client_secret
        events = session.query(IAMAuditEvent).all()
        assert len(events) == 1 and events[0].event_type == "nhi_created"
        assert events[0].performed_by == B and events[0].subject_id == row.id
        assert issued.client_secret not in str(
            events[0].changes
        ) and row.secret_hash not in str(events[0].changes)
        assert (
            session.query(Entitlement).count() == 1
        )  # no credential-to-permission shortcut
    assert (
        issued.provider_status == "not_integrated"
        and issued.credential_scope == "local_registry_only"
    )
    assert nhi_check(factory, issued, issued.client_secret) is True
    assert nhi_check(factory, issued, "synthetic-wrong-secret") is False


def test_nhi_rotation_replaces_secret_and_stale_retry_cannot_rotate_again(
    store, nhi_enabled
):
    _, _, factory, _ = store
    first = nhi_create(factory)
    rotated = nhi_change(factory, first.id, "rotate", 1)
    assert (
        rotated.credential_version == 2 and rotated.client_secret != first.client_secret
    )
    assert nhi_check(factory, first, first.client_secret) is False
    assert nhi_check(factory, rotated, rotated.client_secret) is True
    with pytest.raises(HTTPException) as error:
        nhi_change(factory, first.id, "rotate", 1)
    assert error.value.status_code == 409
    with tenant_session(factory, A) as session:
        assert session.get(ServiceAccount, first.id).credential_version == 2
        assert (
            session.query(IAMAuditEvent).filter_by(event_type="nhi_rotate").count() == 1
        )


def test_nhi_deactivation_clears_credentials_and_activation_issues_fresh_secret(
    store, nhi_enabled
):
    _, _, factory, _ = store
    first = nhi_create(factory)
    inactive = nhi_change(factory, first.id, "deactivate", 1)
    assert inactive.status == "inactive" and inactive.credential_expires_at is None
    assert nhi_check(factory, first, first.client_secret) is False
    with tenant_session(factory, A) as session:
        assert session.get(ServiceAccount, first.id).secret_hash is None
    renewed = nhi_change(factory, first.id, "activate", 2)
    assert (
        renewed.credential_version == 3 and renewed.client_secret != first.client_secret
    )
    assert nhi_check(factory, first, first.client_secret) is False
    assert nhi_check(factory, renewed, renewed.client_secret) is True


@pytest.mark.parametrize("status", ["active", "inactive"])
def test_nhi_soft_delete_is_terminal_and_never_reactivates_a_credential(
    store, nhi_enabled, status
):
    _, _, factory, _ = store
    issued = nhi_create(factory)
    version = 1
    if status == "inactive":
        nhi_change(factory, issued.id, "deactivate", version)
        version += 1
    deleted = nhi_change(factory, issued.id, "delete", version)
    assert deleted.status == "deleted" and deleted.credential_expires_at is None
    for operation in ["activate", "rotate", "deactivate", "delete"]:
        with pytest.raises(HTTPException) as error:
            nhi_change(factory, issued.id, operation, version + 1)
        assert error.value.status_code == 409
    assert nhi_check(factory, issued, issued.client_secret) is False
    with pytest.raises(HTTPException) as error:
        nhi_create(factory)
    assert error.value.status_code == 409  # deletion does not free a historical name


def test_nhi_expiry_uses_aware_time_and_expiring_list_includes_expired_records(
    store, nhi_enabled, monkeypatch
):
    _, _, factory, _ = store

    class Past(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(timezone.utc) - timedelta(days=400)

    with monkeypatch.context() as patch:
        patch.setattr(nhi_service_module, "datetime", Past)
        issued = nhi_create(factory, rotation_days=1)
    assert nhi_check(factory, issued, issued.client_secret) is False
    with tenant_session(factory, A) as session:
        service = NHIService(session, ADMIN)
        assert service.get_service_account(issued.id).credential_expired is True
        assert [r.id for r in service.list_service_accounts(within_days=0)] == [
            issued.id
        ]


def test_nhi_other_tenant_cannot_read_rotate_or_check_same_client(store, nhi_enabled):
    _, _, factory, _ = store
    issued = nhi_create(factory)
    foreign = RequestContext(B, str(USER), ("PLATFORM_ADMIN",))
    with tenant_session(factory, B) as session:
        service = NHIService(session, foreign)
        assert service.list_service_accounts() == []
        with pytest.raises(HTTPException) as error:
            service.get_service_account(issued.id)
        assert error.value.status_code == 404
    with pytest.raises(HTTPException) as error:
        nhi_change(factory, issued.id, "rotate", 1, foreign)
    assert error.value.status_code == 404
    assert nhi_check(factory, issued, issued.client_secret, foreign) is False
    assert nhi_check(factory, issued, issued.client_secret) is True


def test_nhi_same_names_in_different_tenants_are_distinct(store, nhi_enabled):
    _, _, factory, _ = store
    first = nhi_create(factory)
    second = nhi_create(factory, RequestContext(B, str(USER), ("TENANT_ADMIN",)))
    assert first.id != second.id and first.client_id != second.client_id


@pytest.mark.parametrize(
    "operation", ["create", "rotate", "deactivate", "activate", "delete"]
)
def test_nhi_audit_outage_rolls_back_entire_lifecycle_change(
    store, nhi_enabled, monkeypatch, operation
):
    _, _, factory, _ = store
    issued = None
    if operation != "create":
        issued = nhi_create(factory)
    if operation == "activate":
        nhi_change(factory, issued.id, "deactivate", 1)
    version = 2 if operation == "activate" else 1
    original = AuditLogger.log_entitlement_event

    def fail(logger, event, *args, **kwargs):
        if event == "nhi_" + ("created" if operation == "create" else operation):
            raise RuntimeError("Synthetic audit outage")
        return original(logger, event, *args, **kwargs)

    monkeypatch.setattr(AuditLogger, "log_entitlement_event", fail)
    with pytest.raises(HTTPException) as error:
        if operation == "create":
            nhi_create(factory)
        else:
            nhi_change(factory, issued.id, operation, version)
    assert error.value.status_code == 503
    with tenant_session(factory, A) as session:
        if operation == "create":
            assert session.query(ServiceAccount).count() == 0
        else:
            row = session.get(ServiceAccount, issued.id)
            assert row.credential_version == version
            assert row.status == ("inactive" if operation == "activate" else "active")
    if operation not in {"create", "activate"}:
        assert nhi_check(factory, issued, issued.client_secret) is True


@pytest.mark.parametrize("lost_ack", [False, True])
def test_nhi_uncertain_rotation_requires_inspection_and_new_explicit_version(
    store, nhi_enabled, monkeypatch, lost_ack
):
    _, _, factory, _ = store
    issued = nhi_create(factory)
    with tenant_session(factory, A) as session:
        commit = session.commit

        def fail():
            if lost_ack:
                commit()
            raise RuntimeError("Synthetic acknowledgement failure")

        with monkeypatch.context() as patch:
            patch.setattr(session, "commit", fail)
            with pytest.raises(HTTPException) as error:
                NHIService(session, ADMIN).transition(
                    issued.id, "rotate", {"expected_version": 1}
                )
            assert error.value.status_code == 503
    with tenant_session(factory, A) as session:
        version = session.get(ServiceAccount, issued.id).credential_version
    assert version == (2 if lost_ack else 1)
    assert nhi_check(factory, issued, issued.client_secret) is (not lost_ack)
    repaired = nhi_change(factory, issued.id, "rotate", version)
    assert nhi_check(factory, repaired, repaired.client_secret) is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("tenant_id", B),
        ("owner_user_id", USER),
        ("client_id", "sa-forged"),
        ("credential_version", 99),
    ],
)
def test_nhi_database_guards_ownership_and_version_even_with_admin_flag(
    store, nhi_enabled, field, value
):
    _, _, factory, _ = store
    issued = nhi_create(factory)
    with tenant_session(factory, A) as session:
        session.execute(text("SELECT set_config('app.is_superadmin','true',true)"))
        row = session.get(ServiceAccount, issued.id)
        setattr(row, field, value)
        with pytest.raises(DBAPIError):
            session.flush()
        session.rollback()
    with tenant_session(factory, A) as session:
        assert session.get(ServiceAccount, issued.id).credential_version == 1


def test_nhi_rls_cannot_be_widened_by_permissive_policy_and_rows_cannot_be_hard_deleted(
    store, nhi_enabled
):
    params, _, factory, _ = store
    issued = nhi_create(factory)
    with owner(params, "iam_test") as connection, connection.cursor() as cursor:
        cursor.execute(
            "CREATE POLICY synthetic_unsafe_all ON iam_service_accounts USING(true) WITH CHECK(true)"
        )
    try:
        with tenant_session(factory, B) as session:
            assert session.query(ServiceAccount).count() == 0
            assert (
                session.execute(
                    text("UPDATE iam_service_accounts SET status=status")
                ).rowcount
                == 0
            )
        with tenant_session(factory, A) as session:
            assert (
                session.execute(text("DELETE FROM iam_service_accounts")).rowcount == 0
            )
            with pytest.raises(DBAPIError):
                session.execute(text("TRUNCATE iam_service_accounts"))
            session.rollback()
    finally:
        with owner(params, "iam_test") as connection, connection.cursor() as cursor:
            cursor.execute("DROP POLICY synthetic_unsafe_all ON iam_service_accounts")


def test_nhi_concurrent_rotations_accept_one_version_only(store, nhi_enabled):
    from concurrent.futures import ThreadPoolExecutor

    _, engine, factory, _ = store
    issued = nhi_create(factory)
    concurrent = create_engine(engine.url, pool_size=2, max_overflow=0)
    install_tenant_pool_reset(concurrent)
    sessions = sessionmaker(bind=concurrent)

    def attempt():
        try:
            return nhi_change(sessions, issued.id, "rotate", 1)
        except HTTPException as error:
            return error.status_code

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt(), range(2)))
        assert sum(isinstance(r, int) and r == 409 for r in results) == 1
        success = next(r for r in results if not isinstance(r, int))
        assert (
            success.credential_version == 2
            and nhi_check(factory, success, success.client_secret) is True
        )
        with tenant_session(factory, A) as session:
            assert (
                session.query(IAMAuditEvent).filter_by(event_type="nhi_rotate").count()
                == 1
            )
    finally:
        concurrent.dispose()


def test_nhi_proof_audit_outage_does_not_return_credential_success(
    store, nhi_enabled, monkeypatch
):
    _, _, factory, _ = store
    issued = nhi_create(factory)
    monkeypatch.setattr(
        AuditLogger,
        "log_entitlement_event",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("Synthetic audit outage")
        ),
    )
    with pytest.raises(HTTPException) as error:
        nhi_check(factory, issued, issued.client_secret)
    assert error.value.status_code == 503


def test_nhi_misbound_session_cannot_create_another_tenant_account(store, nhi_enabled):
    _, _, factory, _ = store
    with tenant_session(factory, B) as session:
        with pytest.raises(HTTPException) as error:
            NHIService(session, ADMIN).create_service_account(
                {"name": "synthetic-misbound"}
            )
        assert error.value.status_code == 503
    with tenant_session(factory, A) as session:
        assert session.query(ServiceAccount).count() == 0
        assert session.query(IAMAuditEvent).count() == 0


def test_nhi_inventory_limit_never_silently_truncates(store, nhi_enabled):
    params, _, factory, _ = store
    with owner(params, "iam_test") as connection, connection.cursor() as cursor:
        rows = []
        for index in range(101):
            identity = uuid4()
            rows.append(
                (
                    str(identity),
                    str(A),
                    "Synthetic " + str(index),
                    "sa-" + str(identity),
                    str(USER),
                    str(USER),
                )
            )
        cursor.executemany(
            "INSERT INTO iam_service_accounts (id,tenant_id,name,client_id,owner_user_id,created_by,status) VALUES (%s,%s,%s,%s,%s,%s,'inactive')",
            rows,
        )
    with tenant_session(factory, A) as session:
        with pytest.raises(HTTPException) as error:
            NHIService(session, ADMIN).list_service_accounts()
        assert error.value.status_code == 409
