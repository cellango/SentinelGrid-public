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

from sg_core.tenant_session import bind_tenant, install_tenant_pool_reset, tenant_session
from app.api import entitlements, bulk_operations, request_context, access_requests
from app.api.request_context import RequestContext
from app.models.audit_event import IAMAuditEvent
from app.models.entitlement import Entitlement
from app.models.access_request import AccessRequest, AccessRequestHistory
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
        bindir = subprocess.check_output([config, "--bindir"], text=True).strip() if config else ""
    tools = {name: Path(bindir) / name for name in ("postgres", "initdb", "pg_ctl")}
    if any(not path.is_file() for path in tools.values()):
        pytest.fail("Install PostgreSQL server tools and set SG_TEST_PG_BINDIR; an existing DB is never used")
    with TemporaryDirectory(prefix="sg-iam-db-", dir="/tmp") as directory:
        directory = Path(directory)
        directory.chmod(0o700)
        data, socket = directory / "data", directory / "socket"
        socket.mkdir(mode=0o700)
        with (directory / "startup.log").open("w") as log:
            subprocess.run([str(tools["initdb"]), "-D", str(data), "-U", "sg_test_owner",
                            "--auth-local=trust", "--auth-host=reject", "--no-locale", "--encoding=UTF8"],
                           check=True, stdout=log, stderr=subprocess.STDOUT)
            subprocess.run([str(tools["pg_ctl"]), "-D", str(data), "-l", str(directory / "postgres.log"),
                            "-o", f"-F -h '' -k {socket} -p 55463", "-w", "start"],
                           check=True, stdout=log, stderr=subprocess.STDOUT)
        try:
            params = dict(host=str(socket), port=55463, user="sg_test_owner", dbname="postgres")
            connection = psycopg2.connect(**params)
            try:
                connection.autocommit = True
                with connection.cursor() as cursor:
                    cursor.execute("CREATE ROLE sg_test_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS")
                    for database in ("iam_test", "catalog_test"):
                        cursor.execute(sql.SQL("CREATE DATABASE {} OWNER sg_test_owner").format(sql.Identifier(database)))
            finally:
                connection.close()
            yield params
        finally:
            subprocess.run([str(tools["pg_ctl"]), "-D", str(data), "-m", "immediate", "-w", "stop"],
                           check=True, capture_output=True)


def owner(params, database):
    return psycopg2.connect(**{**params, "dbname": database})


def migration_sql():
    return (ROOT / "migrations_consolidated/V014__public_iam_audit_and_tenant_guards.sql").read_text()


@pytest.fixture(scope="module")
def databases(cluster):
    legacy = ROOT / "agents/iam_agent/migrations"
    with owner(cluster, "iam_test") as connection, connection.cursor() as cursor:
        for path in [legacy / name for name in ("V1__create_entitlements_schema.sql", "V2__create_tenant_reference_table.sql", "V3__create_access_requests.sql")]:
            cursor.execute(path.read_text())
            connection.commit()
        cursor.execute("INSERT INTO entitlements (id,tenant_id,resource_type,resource_id,action,granted_to_type,granted_to_id,granted_by) VALUES (%s,%s,'document','synthetic-doc','read','user',%s,%s)",
                       tuple(map(str, [GRANT,A,USER,USER])))
        cursor.execute("INSERT INTO entitlement_audit_log (entitlement_id,action,performed_by) VALUES (%s,'granted',%s)", tuple(map(str,[GRANT,USER])))
        cursor.execute("SELECT row_to_json(e)::text FROM entitlement_audit_log e ORDER BY id")
        before = cursor.fetchall()
        cursor.execute("CREATE POLICY old_flag_bypass ON entitlements USING (current_setting('app.is_superadmin', true) = 'true')")
        cursor.execute(migration_sql())
        cursor.execute("SELECT row_to_json(e)::text FROM entitlement_audit_log e ORDER BY id")
        assert cursor.fetchall() == before
        cursor.execute("SELECT count(*) FROM iam_audit_events")
        assert cursor.fetchone()[0] == 0
    # Exact policy/catalog table declarations from the published dump, not a
    # claim that all V001-V013 extensions, histories and runners are qualified.
    dump = (ROOT / "migrations_consolidated/V001__initial_schema.sql").read_text()
    with owner(cluster, "catalog_test") as connection, connection.cursor() as cursor:
        cursor.execute('CREATE EXTENSION "uuid-ossp"')
        for name in ("policies", "policy_rules", "policy_evaluations", "entitlements"):
            declaration = re.search(r"CREATE TABLE public\." + name + r" \(.*?\n\);", dump, re.S).group()
            cursor.execute(declaration)
        cursor.execute("CREATE POLICY old_flag_bypass ON policies USING (current_setting('app.is_superadmin', true) = 'true')")
        cursor.execute(migration_sql())
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='entitlements'")
        columns = {row[0] for row in cursor.fetchall()}
        assert "app_id" in columns and "resource_type" not in columns
    engines = []
    for database in ("iam_test", "catalog_test"):
        with owner(cluster, database) as connection, connection.cursor() as cursor:
            cursor.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
            cursor.execute("GRANT USAGE ON SCHEMA public TO sg_test_app")
            cursor.execute("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO sg_test_app")
            cursor.execute("REVOKE UPDATE,DELETE ON iam_audit_events FROM sg_test_app")
        url = URL.create("postgresql+psycopg2", username="sg_test_app", database=database,
                         query={"host": cluster["host"], "port": str(cluster["port"])})
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
        cursor.execute("TRUNCATE iam_audit_events,entitlements,access_requests CASCADE")
        for tenant in (A, B):
            cursor.execute("INSERT INTO entitlements (id,tenant_id,resource_type,resource_id,action,granted_to_type,granted_to_id,granted_by) VALUES (%s,%s,'document','synthetic-doc','read','user',%s,%s)",
                           tuple(map(str,[GRANT if tenant == A else uuid4(), tenant, USER, USER])))
    with owner(params, "catalog_test") as connection, connection.cursor() as cursor:
        cursor.execute("TRUNCATE policies,policy_rules,policy_evaluations,iam_audit_events")
        for tenant in (A, B):
            cursor.execute("INSERT INTO policies (id,tenant_id,name,display_name,policy_type,scope,policy_data) VALUES (%s,%s,'synthetic','Synthetic','access','tenant',%s::jsonb)",
                           (str(uuid4()),str(tenant),'{"id":"synthetic","type":"access","rules":[{"id":"grant","conditions":[],"actions":[{"type":"allow"}]}]}'))
    factory, policies = sessionmaker(bind=engine), sessionmaker(bind=policy_engine)
    monkeypatch.setattr(entitlements.cache, "invalidate_entitlement", lambda *_: None)
    monkeypatch.setattr(bulk_operations.cache, "invalidate_tenant_entitlements", lambda *_: None)
    return params, engine, factory, policies


def visible(session):
    return session.execute(text("SELECT tenant_id FROM public.entitlements")).scalars().all()


def test_migration_and_model_match(databases):
    _, (engine, _) = databases
    catalog = inspect(engine)
    model = IAMAuditEvent.__table__
    columns = {row["name"]:row for row in catalog.get_columns(model.name, schema="public")}
    assert set(columns) == set(model.columns.keys())
    for field in model.columns:
        assert columns[field.name]["nullable"] == field.nullable
        assert (columns[field.name]["default"] is not None) == (field.server_default is not None)
        assert str(columns[field.name]["type"].compile(dialect=engine.dialect)).lower() == str(field.type.compile(dialect=engine.dialect)).lower()
    assert {row["name"] for row in catalog.get_check_constraints(model.name, schema="public")} == {
        c.name for c in model.constraints if c.name}
    assert {row["name"] for row in catalog.get_indexes(model.name, schema="public")} == {i.name for i in model.indexes}
    with engine.connect() as connection:
        assert connection.execute(text("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user")).one() == (False,False,False,False)


def test_commit_rollback_savepoint_and_pool_reuse(store):
    _, engine, factory, _ = store
    with tenant_session(factory,A) as session:
        pid = session.scalar(text("SELECT pg_backend_pid()"))
        assert visible(session)==[A]
        session.commit()
        assert visible(session)==[A]
        session.rollback()
        assert visible(session)==[A]
        with pytest.raises(RuntimeError):
            with session.begin_nested():
                assert visible(session)==[A]
                raise RuntimeError("synthetic savepoint rollback")
        assert visible(session)==[A]
    with tenant_session(factory,B) as session:
        assert session.scalar(text("SELECT pg_backend_pid()"))==pid
        assert visible(session)==[B]
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT pg_backend_pid()"))==pid
        assert connection.execute(text("SELECT tenant_id FROM entitlements")).all()==[]


def test_checkout_clears_session_level_residue(store):
    _, engine, _, _ = store
    with engine.connect() as connection:
        connection.execute(text("SELECT set_config('app.current_tenant_id', :t, false), set_config('app.is_superadmin','true',false)"),{"t":str(B)})
        connection.commit()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT tenant_id FROM entitlements")).all()==[]
        assert connection.scalar(text("SELECT current_setting('app.is_superadmin')")) != "true"


@pytest.mark.parametrize("value", [None,"","tenant-slug","invalid-uuid"])
def test_missing_or_invalid_context_denies_direct_sql(store,value):
    _, engine, _, _ = store
    with engine.begin() as connection:
        if value is not None:
            connection.execute(text("SELECT set_config('app.current_tenant_id',:t,true)"),{"t":value})
        connection.execute(text("SELECT set_config('app.is_superadmin','true',true)"))
        assert connection.execute(text("SELECT tenant_id FROM entitlements")).all()==[]


def test_superadmin_flag_cannot_bypass_restrictive_guard(store):
    _, _, factory, _ = store
    with tenant_session(factory,A) as session:
        session.execute(text("SELECT set_config('app.is_superadmin','true',true)"))
        assert visible(session)==[A]
        assert session.execute(text("UPDATE entitlements SET status='revoked' WHERE tenant_id=:t"),{"t":B}).rowcount==0
        with pytest.raises(DBAPIError):
            with session.begin_nested():
                session.execute(text("UPDATE entitlements SET tenant_id=:t WHERE id=:id"),{"t":B,"id":GRANT})


def test_child_rows_cannot_cross_parent_tenant(store):
    params, _, _, policies = store
    with owner(params,"catalog_test") as connection, connection.cursor() as cursor:
        cursor.execute("SELECT id,tenant_id FROM policies")
        ids={UUID(str(t)):UUID(str(i)) for i,t in cursor.fetchall()}
        for tenant,target in ids.items():
            cursor.execute("INSERT INTO policy_rules (id,policy_id,rule_id,conditions,actions) VALUES (%s,%s,'synthetic','[]','[]')",(str(uuid4()),str(target)))
    with tenant_session(policies,A) as session:
        assert session.scalar(text("SELECT count(*) FROM policy_rules"))==1
        with pytest.raises(DBAPIError):
            with session.begin_nested():
                session.execute(text("INSERT INTO policy_rules (id,policy_id,rule_id,conditions,actions) VALUES (:id,:p,'forged','[]','[]')"),{"id":uuid4(),"p":ids[B]})


def test_allow_and_deny_are_committed_with_actual_actor(store):
    _, _, factory, policies = store
    for subject, expected in [(USER,"allow"),(uuid4(),"deny")]:
        with tenant_session(factory,A) as session, tenant_session(policies,A) as policy_session:
            result=asyncio.run(EvaluationEngine(session,policy_db=policy_session).evaluate(
                EvaluationContext(subject,A,"document","synthetic-doc","read",actor_id=USER)))
            assert result.decision==expected and result.audit_recorded
    with tenant_session(factory,A) as session:
        rows=session.query(IAMAuditEvent).all()
        assert {r.decision for r in rows}=={"allow","deny"}
        assert all(r.performed_by==USER for r in rows)
        assert session.get(Entitlement,GRANT).usage_count_90d==1
    with tenant_session(factory,B) as session:
        assert session.query(IAMAuditEvent).all()==[]


def test_audit_failure_prevents_allow_and_usage_update(store):
    params, _, factory, policies = store
    with owner(params,"iam_test") as connection, connection.cursor() as cursor:
        cursor.execute("REVOKE INSERT ON iam_audit_events FROM sg_test_app")
    try:
        with tenant_session(factory,A) as session, tenant_session(policies,A) as policy_session:
            result=asyncio.run(EvaluationEngine(session,policy_db=policy_session).evaluate(EvaluationContext(USER,A,"document","synthetic-doc","read")))
            assert result.decision=="deny" and not result.audit_recorded
        with tenant_session(factory,A) as session:
            assert session.get(Entitlement,GRANT).usage_count_90d==0
            assert session.query(IAMAuditEvent).count()==0
    finally:
        with owner(params,"iam_test") as connection, connection.cursor() as cursor:
            cursor.execute("GRANT INSERT ON iam_audit_events TO sg_test_app")


def test_aborted_lookup_transaction_rebinds_and_records_denial(store):
    _, _, factory, policies = store
    with tenant_session(factory,A) as session, tenant_session(policies,A) as policy_session:
        engine=EvaluationEngine(session,policy_db=policy_session)
        def fail_lookup(_context):
            session.execute(text("SELECT 1 / 0"))
        engine._find_matching_entitlements=fail_lookup
        result=asyncio.run(engine.evaluate(EvaluationContext(USER,A,"document","synthetic-doc","read")))
        assert result.decision=="deny" and result.audit_recorded
        assert visible(session)==[A]
    with tenant_session(factory,A) as session:
        assert session.query(IAMAuditEvent).one().decision=="deny"


def test_certification_requires_both_parents_in_authenticated_tenant(store):
    params, _, factory, _ = store
    campaigns, grants={},{}
    with owner(params,"iam_test") as connection, connection.cursor() as cursor:
        cursor.execute("TRUNCATE audit_campaigns CASCADE")
        cursor.execute("SELECT tenant_id,id FROM entitlements")
        grants={UUID(str(t)):UUID(str(i)) for t,i in cursor.fetchall()}
        for tenant in (A,B):
            campaigns[tenant]=uuid4()
            cursor.execute("INSERT INTO audit_campaigns (id,tenant_id,name,campaign_type,scope,review_config,schedule,created_by) VALUES (%s,%s,'synthetic','on_demand','{}','{}','{}',%s)",
                           tuple(map(str,[campaigns[tenant],tenant,USER])))
            cursor.execute("INSERT INTO certifications (campaign_id,entitlement_id,certifier_id,certifier_type,deadline) VALUES (%s,%s,%s,'admin',now())",
                           tuple(map(str,[campaigns[tenant],grants[tenant],USER])))
    with tenant_session(factory,A) as session:
        assert session.scalar(text("SELECT count(*) FROM certifications"))==1
        with pytest.raises(DBAPIError):
            with session.begin_nested():
                session.execute(text("INSERT INTO certifications (campaign_id,entitlement_id,certifier_id,certifier_type,deadline) VALUES (:c,:e,:u,'manager',now())"),
                                {"c":campaigns[A],"e":grants[B],"u":USER})


def test_grant_mutation_rolls_back_when_audit_fails(store):
    params, _, factory, _ = store
    with owner(params,"iam_test") as connection, connection.cursor() as cursor:
        cursor.execute("REVOKE INSERT ON iam_audit_events FROM sg_test_app")
    try:
        with tenant_session(factory,A) as session:
            payload=entitlements.EntitlementCreate(tenant_id=A,resource_type="document",resource_id="new-doc",action="read",granted_to_type="user",granted_to_id=USER,granted_by=uuid4())
            with pytest.raises(Exception) as error:
                asyncio.run(entitlements.create_entitlement(payload,RequestContext(A,str(USER),("TENANT_ADMIN",)),session))
            assert error.value.status_code==503
        with tenant_session(factory,A) as session:
            assert session.query(Entitlement).filter(Entitlement.resource_id=="new-doc").count()==0
    finally:
        with owner(params,"iam_test") as connection, connection.cursor() as cursor:
            cursor.execute("GRANT INSERT ON iam_audit_events TO sg_test_app")


def test_grant_creation_and_bulk_revocation_commit_audit(store):
    _, _, factory, _ = store
    caller=RequestContext(A,str(USER),("TENANT_ADMIN",))
    with tenant_session(factory,A) as session:
        payload=entitlements.EntitlementCreate(tenant_id=A,resource_type="document",resource_id="new-doc",action="read",granted_to_type="user",granted_to_id=USER,granted_by=uuid4())
        row=asyncio.run(entitlements.create_entitlement(payload,caller,session))
        assert row.granted_by==USER
    with tenant_session(factory,A) as session:
        response=asyncio.run(bulk_operations.bulk_delete_entitlements(bulk_operations.BulkDeleteRequest(entitlement_ids=[GRANT]),caller,session))
        assert response.deleted==1 and response.failed==0
    with tenant_session(factory,A) as session:
        assert {row.event_type for row in session.query(IAMAuditEvent)}=={"created","revoked"}
        assert session.get(Entitlement,GRANT).status=="revoked"


def test_audit_cannot_be_modified_or_truncated_by_application(store):
    params, _, factory, _ = store
    with tenant_session(factory,A) as session:
        AuditLogger(session).log_entitlement_event("created",GRANT,A,USER)
    # Even accidental broad UPDATE/DELETE grants cannot overcome restrictive guards.
    with owner(params,"iam_test") as connection, connection.cursor() as cursor:
        cursor.execute("GRANT UPDATE,DELETE ON iam_audit_events TO sg_test_app")
    try:
        with tenant_session(factory,A) as session:
            assert session.execute(text("UPDATE iam_audit_events SET reason='forged'")).rowcount==0
            assert session.execute(text("DELETE FROM iam_audit_events")).rowcount==0
            with pytest.raises(DBAPIError):
                with session.begin_nested():session.execute(text("TRUNCATE iam_audit_events"))
            with pytest.raises(DBAPIError):
                with session.begin_nested():session.execute(text("ALTER TABLE iam_audit_events DISABLE ROW LEVEL SECURITY"))
    finally:
        with owner(params,"iam_test") as connection, connection.cursor() as cursor:
            cursor.execute("REVOKE UPDATE,DELETE ON iam_audit_events FROM sg_test_app")


def test_bind_rejects_mid_transaction_and_tenant_switch(store):
    _, _, factory, _ = store
    with factory() as session:
        session.execute(text("SELECT 1"))
        with pytest.raises(ValueError):bind_tenant(session,A)
    with factory() as session:
        bind_tenant(session,A)
        with pytest.raises(ValueError):bind_tenant(session,B)


@pytest.mark.parametrize("table", ["entitlements", "iam_audit_events"])
def test_cross_tenant_insert_is_rejected(store, table):
    _, _, factory, _ = store
    with tenant_session(factory,A) as session:
        with pytest.raises(DBAPIError):
            with session.begin_nested():
                if table == "iam_audit_events":
                    AuditLogger(session).log_entitlement_event("created",None,B,USER)
                else:
                    session.add(Entitlement(tenant_id=B,resource_type="document",resource_id="forged",action="read",
                                granted_to_type="user",granted_to_id=USER,granted_by=USER))
                    session.flush()


def test_new_audit_history_survives_live_record_deletion(store):
    params, _, factory, _ = store
    with tenant_session(factory,A) as session:
        AuditLogger(session).log_entitlement_event("created",GRANT,A,USER)
    with owner(params,"iam_test") as connection, connection.cursor() as cursor:
        cursor.execute("DELETE FROM entitlements WHERE id=%s",(str(GRANT),))
    with tenant_session(factory,A) as session:
        assert session.query(IAMAuditEvent).one().entitlement_id==GRANT


def test_iam_dependency_and_shared_helper_rebind_transactions(store,monkeypatch):
    from sg_core import db
    _, _, factory, _ = store
    monkeypatch.setattr(request_context,"IAMSessionLocal",factory)
    dependency=request_context.get_entitlement_session(RequestContext(A,str(USER)))
    session=next(dependency)
    assert visible(session)==[A]
    session.commit()
    assert visible(session)==[A]
    with pytest.raises(StopIteration):next(dependency)
    monkeypatch.setattr(db,"SessionLocal",factory)
    dependency=db.get_tenant_db(str(B))
    session=next(dependency)
    assert visible(session)==[B]
    session.rollback()
    assert visible(session)==[B]
    dependency.close()


# Access requests: exact legacy V3 contracts and transactional admission.
@pytest.mark.parametrize("model", [AccessRequest, AccessRequestHistory])
def test_access_request_mapping_matches_existing_v3(databases, model):
    _, (engine, _)=databases
    catalog=inspect(engine); table=model.__table__
    columns={c["name"]:c for c in catalog.get_columns(table.name,schema="public")}
    assert set(columns)==set(table.columns.keys())
    for field in table.columns:
        assert columns[field.name]["nullable"]==field.nullable
        assert (columns[field.name]["default"] is not None)==(field.server_default is not None)
        assert str(columns[field.name]["type"].compile(dialect=engine.dialect)).lower()==str(field.type.compile(dialect=engine.dialect)).lower()
    assert {r["name"] for r in catalog.get_check_constraints(table.name,schema="public")}=={c.name for c in table.constraints if c.name}
    assert {r["name"] for r in catalog.get_indexes(table.name,schema="public")}=={i.name for i in table.indexes}


def new_access_request(factory):
    with tenant_session(factory,A) as session:
        body=access_requests.AccessRequestCreate(tenant_id=A,resource_type="document",resource_id="requested-doc",action="read",justification="Synthetic request only")
        return asyncio.run(access_requests.create_access_request(body,session,RequestContext(A,str(USER),())))


def request_action(session, row, action):
    caller=RequestContext(A,str(USER if action=="cancel" else B),("TENANT_ADMIN",))
    if action=="cancel":return asyncio.run(access_requests.cancel_access_request(row.id,session,caller))
    return asyncio.run(access_requests.review_access_request(row.id,access_requests.AccessRequestReview(decision=action),session,caller))


def test_request_creation_persists_history_jsonb_and_audit(store):
    _, _, factory, _=store
    row=new_access_request(factory)
    with tenant_session(factory,A) as session:
        history=session.query(AccessRequestHistory).filter_by(request_id=row.id).one()
        assert history.metadata_json=={} and history.performed_by==USER
        audit=session.query(IAMAuditEvent).one()
        assert audit.event_type=="access_request_created" and audit.performed_by==USER
        assert audit.subject_id==USER and audit.changes["resource_id"]=="requested-doc"


@pytest.mark.parametrize("action,expected", [("approve","approved"),("deny","denied"),("cancel","cancelled")])
def test_request_transition_commits_history_and_audit(store, action, expected):
    _, _, factory, _=store
    row=new_access_request(factory)
    with tenant_session(factory,A) as session:
        result=request_action(session,row,action)
        assert result.status==expected
    with tenant_session(factory,A) as session:
        request=session.get(AccessRequest,row.id)
        assert request.status==expected
        assert session.query(AccessRequestHistory).filter_by(request_id=row.id).count()==2
        event=session.query(IAMAuditEvent).filter_by(event_type="access_request_"+expected).one()
        assert event.performed_by==(USER if action=="cancel" else B)
        assert event.changes["old_status"]=="pending" and event.changes["new_status"]==expected
        grants=session.query(Entitlement).filter_by(resource_id="requested-doc").all()
        assert len(grants)==(1 if action=="approve" else 0)
        if grants:
            assert request.entitlement_id==grants[0].id and grants[0].granted_by==B
            assert grants[0].granted_to_id==USER
            assert session.query(IAMAuditEvent).filter_by(entitlement_id=grants[0].id,event_type="created").count()==1


@pytest.mark.parametrize("action", ["create","approve","deny","cancel"])
def test_request_audit_failure_rolls_back_every_effect(store, action):
    params, _, factory, _=store
    row=new_access_request(factory) if action!="create" else None
    with owner(params,"iam_test") as connection, connection.cursor() as cursor:
        cursor.execute("REVOKE INSERT ON iam_audit_events FROM sg_test_app")
    try:
        with pytest.raises(Exception) as error:
            if row:
                with tenant_session(factory,A) as session:request_action(session,row,action)
            else:new_access_request(factory)
        assert error.value.status_code==503
        with tenant_session(factory,A) as session:
            assert session.query(AccessRequest).count()==(1 if row else 0)
            assert session.query(AccessRequestHistory).count()==(1 if row else 0)
            assert session.query(IAMAuditEvent).count()==(1 if row else 0)
            assert session.query(Entitlement).filter_by(resource_id="requested-doc").count()==0
            if row:assert session.get(AccessRequest,row.id).status=="pending"
    finally:
        with owner(params,"iam_test") as connection, connection.cursor() as cursor:
            cursor.execute("GRANT INSERT ON iam_audit_events TO sg_test_app")


def test_request_commit_failure_rolls_back_grant_and_audits(store, monkeypatch):
    _, _, factory, _=store
    row=new_access_request(factory)
    with tenant_session(factory,A) as session:
        with monkeypatch.context() as patch:
            def unavailable():raise RuntimeError("Synthetic commit outage")
            patch.setattr(session,"commit",unavailable)
            with pytest.raises(Exception) as error:request_action(session,row,"approve")
            assert error.value.status_code==503
    with tenant_session(factory,A) as session:
        assert session.get(AccessRequest,row.id).status=="pending"
        assert session.query(AccessRequestHistory).count()==1
        assert session.query(IAMAuditEvent).count()==1
        assert session.query(Entitlement).filter_by(resource_id="requested-doc").count()==0


def test_legacy_null_beneficiary_can_be_read_and_reviewed_as_self(store):
    params, _, factory, _=store
    row=new_access_request(factory)
    with owner(params,"iam_test") as connection, connection.cursor() as cursor:
        cursor.execute("UPDATE access_requests SET requested_for=NULL WHERE id=%s",(str(row.id),))
    with tenant_session(factory,A) as session:
        response=asyncio.run(access_requests.get_access_request(row.id,session,RequestContext(A,str(USER),())))
        assert response.requested_for==USER
    with tenant_session(factory,A) as session:
        assert request_action(session,row,"approve").requested_for==USER
    with tenant_session(factory,A) as session:
        assert session.query(Entitlement).filter_by(resource_id="requested-doc").one().granted_to_id==USER


@pytest.mark.parametrize("second_action", ["approve","cancel"])
def test_competing_request_transitions_use_row_lock(store, monkeypatch, second_action):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    import time
    params, engine, factory, _=store
    row=new_access_request(factory)
    # A separate engine permits genuinely concurrent transactions, unlike the
    # normal single-connection pool used to exercise tenant reuse elsewhere.
    concurrent=create_engine(engine.url,pool_size=2,max_overflow=0)
    install_tenant_pool_reset(concurrent)
    sessions=sessionmaker(bind=concurrent)
    staged,release=Event(),Event()
    original=AuditLogger.log_entitlement_event
    def hold(logger,event_type,*args,**kwargs):
        result=original(logger,event_type,*args,**kwargs)
        if event_type=="access_request_approved":
            staged.set()
            assert release.wait(10), "Concurrent test did not release first transition"
        return result
    monkeypatch.setattr(AuditLogger,"log_entitlement_event",hold)
    def invoke(action):
        try:
            with tenant_session(sessions,A) as session:return request_action(session,row,action).status
        except Exception as error:return error
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(invoke,"approve")
            assert staged.wait(5)
            second=pool.submit(invoke,second_action)
            try:
                deadline=time.monotonic()+5;blocked=False
                while time.monotonic()<deadline:
                    with owner(params,"iam_test") as connection, connection.cursor() as cursor:
                        cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE datname='iam_test' AND usename='sg_test_app' AND wait_event_type='Lock'")
                        blocked=cursor.fetchone()[0]>0
                    if blocked:break
                    time.sleep(0.02)
                assert blocked, "Competing transition must wait for the request row"
            finally:release.set()
            assert first.result(timeout=5)=="approved"
            assert second.result(timeout=5).status_code==400
        with tenant_session(factory,A) as session:
            assert session.query(Entitlement).filter_by(resource_id="requested-doc").count()==1
            assert session.query(AccessRequestHistory).count()==2
            assert session.get(AccessRequest,row.id).status=="approved"
    finally:
        release.set();concurrent.dispose()


@pytest.mark.parametrize("action", ["deny", "cancel"])
def test_legacy_delegated_requests_can_be_closed_without_grant(store, action):
    params, _, factory, _=store
    row=new_access_request(factory)
    with owner(params,"iam_test") as connection, connection.cursor() as cursor:
        cursor.execute("UPDATE access_requests SET requested_for=%s WHERE id=%s",(str(uuid4()),str(row.id)))
    with tenant_session(factory,A) as session:
        assert request_action(session,row,action).status in {"denied","cancelled"}
    with tenant_session(factory,A) as session:
        assert session.query(Entitlement).filter_by(resource_id="requested-doc").count()==0
        assert session.query(AccessRequestHistory).count()==2
        assert session.query(IAMAuditEvent).count()==2


def test_request_review_reloads_stale_session_identity(store):
    _, _, factory, _=store
    row=new_access_request(factory)
    with tenant_session(factory,A) as session:
        session.expire_on_commit=False
        stale=session.get(AccessRequest,row.id)
        session.commit()
        with tenant_session(factory,A) as other:request_action(other,row,"deny")
        assert stale.status=="pending"
        with pytest.raises(Exception) as error:request_action(session,row,"approve")
        assert error.value.status_code==400
    with tenant_session(factory,A) as session:
        assert session.get(AccessRequest,row.id).status=="denied"
        assert session.query(Entitlement).filter_by(resource_id="requested-doc").count()==0


def test_foreign_request_id_cannot_be_reviewed_or_read(store):
    _, _, factory, _=store
    row=new_access_request(factory)
    foreign=RequestContext(B,str(B),("PLATFORM_ADMIN",))
    for operation in ("read","review","cancel","history"):
        with tenant_session(factory,B) as session:
            with pytest.raises(Exception) as error:
                if operation=="read":asyncio.run(access_requests.get_access_request(row.id,session,foreign))
                elif operation=="review":asyncio.run(access_requests.review_access_request(row.id,access_requests.AccessRequestReview(decision="approve"),session,foreign))
                elif operation=="cancel":asyncio.run(access_requests.cancel_access_request(row.id,session,foreign))
                else:asyncio.run(access_requests.get_access_request_history(row.id,session,foreign))
            assert error.value.status_code==404
    with tenant_session(factory,A) as session:
        assert session.get(AccessRequest,row.id).status=="pending"
        assert session.query(AccessRequestHistory).count()==1
        assert session.query(IAMAuditEvent).count()==1


def test_legacy_null_pending_request_blocks_duplicate_creation(store):
    params, _, factory, _=store
    row=new_access_request(factory)
    with owner(params,"iam_test") as connection, connection.cursor() as cursor:
        cursor.execute("UPDATE access_requests SET requested_for=NULL WHERE id=%s",(str(row.id),))
    with pytest.raises(Exception) as error:new_access_request(factory)
    assert error.value.status_code==409
    with tenant_session(factory,A) as session:
        assert session.query(AccessRequest).count()==1
        assert session.query(AccessRequestHistory).count()==1
        assert session.query(IAMAuditEvent).count()==1


def test_lost_commit_acknowledgement_requires_state_reconciliation(store, monkeypatch):
    _, _, factory, _=store
    row=new_access_request(factory)
    with tenant_session(factory,A) as session:
        original_commit=session.commit
        with monkeypatch.context() as patch:
            def lost_acknowledgement():
                original_commit()
                raise RuntimeError("Synthetic lost acknowledgement after server commit")
            patch.setattr(session,"commit",lost_acknowledgement)
            with pytest.raises(Exception) as error:request_action(session,row,"approve")
            assert error.value.status_code==503
    # A 503 is not proof of no effect. The durable row tells the caller what
    # happened; a retry must not create another grant or another transition.
    with tenant_session(factory,A) as session:
        assert session.get(AccessRequest,row.id).status=="approved"
        assert session.query(Entitlement).filter_by(resource_id="requested-doc").count()==1
        assert session.query(AccessRequestHistory).count()==2
        assert session.query(IAMAuditEvent).count()==3
        with pytest.raises(Exception) as error:request_action(session,row,"approve")
        assert error.value.status_code==400
