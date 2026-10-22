"""Synthetic native PostgreSQL/Flyway qualification; never opens an existing DB.

Set SG_TEST_PG_BINDIR and SG_TEST_FLYWAY to reviewed local tools. Missing tools
fail this separate gate. No SQLite, create_all, baseline, repair or skipped gate.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json, os, secrets, shutil, socket, subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4
import psycopg2
from psycopg2 import sql
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from starlette.requests import Request
from app.authority.models import (
    Base,
    Case,
    CaseAccessGrant,
)
from app.authority.store import ActionAuthority
from test_action_boundary import proposal

ROOT = Path(__file__).resolve().parents[3]
TENANT = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"


@pytest.fixture(scope="module")
def lab():
    bindir = Path(os.environ.get("SG_TEST_PG_BINDIR", "/missing"))
    flyway = Path(os.environ.get("SG_TEST_FLYWAY", "/missing"))
    assert (
        all((bindir / n).is_file() for n in ("postgres", "initdb", "pg_ctl"))
        and flyway.is_file()
    ), "Reviewed PostgreSQL/Flyway server tools are required"
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("FLYWAY_", "PG"))
        and k
        not in {
            "JAVA_HOME",
            "JAVA_ARGS",
            "JAVA_TOOL_OPTIONS",
            "JDK_JAVA_OPTIONS",
            "_JAVA_OPTIONS",
        }
    }
    with TemporaryDirectory(prefix="sg-action-lab-", dir="/private/tmp") as tmp:
        root = Path(tmp)
        root.chmod(0o700)
        data = root / "data"
        sock = root / "socket"
        sock.mkdir(mode=0o700)
        password = secrets.token_urlsafe(32)
        pw = root / "pw"
        pw.write_text(password)
        pw.chmod(0o600)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        subprocess.run(
            [
                str(bindir / "initdb"),
                "-D",
                str(data),
                "-U",
                "sg_owner",
                "--pwfile",
                str(pw),
                "--auth-local=trust",
                "--auth-host=scram-sha-256",
                "--no-locale",
                "--encoding=UTF8",
            ],
            env=env,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                str(bindir / "pg_ctl"),
                "-D",
                str(data),
                "-l",
                str(root / "server.log"),
                "-o",
                f"-h 127.0.0.1 -p {port} -k {sock}",
                "-w",
                "start",
            ],
            env=env,
            check=True,
            capture_output=True,
        )
        pw.unlink()

        def connect(database="sg_case_lab", user="sg_owner"):
            return psycopg2.connect(
                host=str(sock), port=port, dbname=database, user=user
            )

        try:
            c = connect("postgres")
            c.autocommit = True
            with c.cursor() as q:
                q.execute(
                    sql.SQL(
                        "CREATE ROLE sg_migrator LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
                    ).format(sql.Literal(password))
                )
                q.execute(
                    "CREATE ROLE sg_action_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
                )
                q.execute("CREATE DATABASE sg_case_lab OWNER sg_migrator")
                q.execute("CREATE DATABASE sg_case_dirty OWNER sg_migrator")
            c.close()
            bundle = root / "bundle"
            bundle.mkdir()
            (bundle / "sql").mkdir()
            migration = (
                ROOT / "migrations_consolidated/V018__case_runtime_action_authority.sql"
            )
            copied = bundle / "sql" / migration.name
            shutil.copyfile(migration, copied)
            (bundle / "flyway.conf").write_text(
                "flyway.locations=filesystem:sql\nflyway.table=flyway_schema_history\nflyway.defaultSchema=public\nflyway.schemas=public\nflyway.createSchemas=false\nflyway.validateOnMigrate=true\nflyway.validateMigrationNaming=true\nflyway.baselineOnMigrate=false\nflyway.cleanDisabled=true\n"
            )
            reports = []

            def migrate(command, database="sg_case_lab"):
                r = subprocess.run(
                    [
                        str(flyway),
                        "-configFiles=" + str(bundle / "flyway.conf"),
                        "-url=" + f"jdbc:postgresql://127.0.0.1:{port}/{database}",
                        "-user=sg_migrator",
                        "-reportEnabled=false",
                        "-outputType=json",
                        command,
                    ],
                    cwd=bundle,
                    env={**env, "FLYWAY_PASSWORD": password},
                    text=True,
                    capture_output=True,
                    timeout=90,
                )
                try:
                    value = json.loads(r.stdout)
                except ValueError:
                    raise AssertionError(
                        (r.stdout + r.stderr).replace(password, "<redacted>")
                    ) from None
                passed = (
                    r.returncode == 0
                    and "error" not in value
                    and value.get("validationSuccessful", True) is not False
                    and value.get("success", True) is not False
                )
                reports.append(
                    {
                        "command": command,
                        "database": database,
                        "passed": passed,
                        "result": value,
                    }
                )
                return passed, value

            ok, result = migrate("migrate")
            assert ok and result["migrationsExecuted"] == 1, result
            assert migrate("validate")[0]
            ok, result = migrate("migrate")
            assert ok and result["migrationsExecuted"] == 0, result
            original = copied.read_bytes()
            copied.write_bytes(original + b"\nSELECT 1;\n")
            assert not migrate("validate")[0]
            copied.write_bytes(original)
            assert migrate("validate")[0]
            c = connect("sg_case_dirty", "sg_migrator")
            with c, c.cursor() as q:
                q.execute("CREATE TABLE synthetic_legacy(id integer PRIMARY KEY)")
                q.execute("INSERT INTO synthetic_legacy VALUES (731)")
            c.close()
            assert not migrate("migrate", "sg_case_dirty")[0]
            c = connect("sg_case_dirty")
            with c, c.cursor() as q:
                q.execute("SELECT to_regclass('public.flyway_schema_history')")
                assert q.fetchone()[0] is None
                q.execute("SELECT id FROM synthetic_legacy")
                assert q.fetchall() == [(731,)]
            c.close()
            c = connect()
            with c, c.cursor() as q:
                q.execute("GRANT USAGE ON SCHEMA case_runtime TO sg_action_app")
                q.execute(
                    "GRANT SELECT ON ALL TABLES IN SCHEMA case_runtime TO sg_action_app"
                )
                q.execute(
                    "GRANT SELECT ON public.flyway_schema_history TO sg_action_app"
                )
                q.execute(
                    "GRANT UPDATE(id) ON case_runtime.cases,case_runtime.case_access_grants TO sg_action_app"
                )
                q.execute(
                    "GRANT INSERT ON case_runtime.action_proposals,case_runtime.approval_requests,case_runtime.approval_decisions,case_runtime.policy_decisions,case_runtime.action_claims,case_runtime.resource_fences,case_runtime.action_attempts,case_runtime.outbox_events TO sg_action_app"
                )
                q.execute(
                    "GRANT UPDATE(generation) ON case_runtime.resource_fences TO sg_action_app"
                )
            c.close()
            engine = create_engine(
                URL.create(
                    "postgresql+psycopg2",
                    username="sg_action_app",
                    database="sg_case_lab",
                    query={"host": str(sock), "port": str(port)},
                ),
                pool_size=4,
                max_overflow=0,
                pool_timeout=2,
                connect_args={
                    "options": "-c statement_timeout=3000 -c lock_timeout=1500"
                },
            )
            owner = create_engine(
                URL.create(
                    "postgresql+psycopg2",
                    username="sg_owner",
                    database="sg_case_lab",
                    query={"host": str(sock), "port": str(port)},
                )
            )

            def restart():
                engine.dispose()
                owner.dispose()
                subprocess.run(
                    [
                        str(bindir / "pg_ctl"),
                        "-D",
                        str(data),
                        "-m",
                        "immediate",
                        "-w",
                        "stop",
                    ],
                    env=env,
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    [
                        str(bindir / "pg_ctl"),
                        "-D",
                        str(data),
                        "-l",
                        str(root / "server.log"),
                        "-o",
                        f"-h 127.0.0.1 -p {port} -k {sock}",
                        "-w",
                        "start",
                    ],
                    env=env,
                    check=True,
                    capture_output=True,
                )

            yield dict(
                restart=restart,
                engine=engine,
                owner=owner,
                connect=connect,
                reports=reports,
                migrate=migrate,
            )
            engine.dispose()
            owner.dispose()
            report = os.environ.get("SG_ACTION_LAB_REPORT")
            if report:
                Path(report).write_text(
                    json.dumps(
                        {
                            "passed": True,
                            "scope": "fresh isolated V018 only; no full shared baseline, existing data, provider or deployment qualification",
                            "flyway": reports,
                        },
                        indent=2,
                    )
                    + "\n"
                )
        finally:
            subprocess.run(
                [
                    str(bindir / "pg_ctl"),
                    "-D",
                    str(data),
                    "-m",
                    "immediate",
                    "-w",
                    "stop",
                ],
                env=env,
                check=True,
                capture_output=True,
            )


@pytest.fixture
def flow(api, lab):
    case_id = str(uuid4())
    users = [str(uuid4()) for _ in range(4)]
    with Session(lab["owner"]) as s, s.begin():
        s.add(
            Case(
                id=UUID(case_id),
                tenant_id=UUID(TENANT),
                policy_version="action-policy-v1",
            )
        )
        s.flush()
        for user in users[:3]:
            for permission in ["propose", "approve", "execute", "read"]:
                s.add(
                    CaseAccessGrant(
                        id=uuid4(),
                        tenant_id=UUID(TENANT),
                        case_id=UUID(case_id),
                        subject_id=UUID(user),
                        permission=permission,
                        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                    )
                )
    api.config.ACTION_AUTHORITY_ENABLED = True
    api.app.state.action_authority = ActionAuthority(lab["engine"], enabled=True)
    path = "/api/v1/cases/" + case_id + "/action-proposals"

    def submit(body=None, key=None, user=0):
        return api.client.post(
            path,
            headers={
                **api.headers(users[user]),
                "Idempotency-Key": key or str(uuid4()),
            },
            json=body or proposal(),
        )

    def decide(p, decision="approve", user=1, hash=None):
        return api.client.post(
            path + "/" + p["proposal_id"] + "/approvals",
            headers=api.headers(users[user]),
            json=dict(
                proposal_hash=hash or p["proposal_hash"],
                decision=decision,
                reason="Synthetic review",
            ),
        )

    def reserve(p, user=2):
        headers = api.headers(users[user])
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/internal-test",
                "headers": [
                    (k.lower().encode(), v.encode()) for k, v in headers.items()
                ],
                "app": api.app,
                "query_string": b"",
            }
        )
        return api.app.state.action_authority.reserve(request, p["proposal_id"])

    return dict(
        api=api,
        lab=lab,
        case_id=case_id,
        users=users,
        path=path,
        submit=submit,
        decide=decide,
        reserve=reserve,
    )


def test_paired_orm_rls_and_immutable_records(lab):
    with lab["owner"].connect() as c:
        inspector = inspect(c)
        assert set(inspector.get_table_names(schema="case_runtime")) == {
            t.name for t in Base.metadata.sorted_tables
        }
        for table in Base.metadata.sorted_tables:
            columns = {
                x["name"]
                for x in inspector.get_columns(table.name, schema="case_runtime")
            }
            assert columns == set(table.columns.keys())
        rows = c.execute(
            text(
                "SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class JOIN pg_namespace n ON n.oid=relnamespace WHERE n.nspname='case_runtime' AND relkind='r'"
            )
        ).all()
        assert len(rows) == 12 and all(r[1] and r[2] for r in rows)
    with lab["engine"].connect() as c:
        assert c.execute(text("SELECT count(*) FROM case_runtime.cases")).scalar() == 0
        with pytest.raises(DBAPIError) as failure:
            c.execute(
                text(
                    "INSERT INTO case_runtime.cases(id,tenant_id,policy_version) VALUES (gen_random_uuid(),gen_random_uuid(),'action-policy-v1')"
                )
            )


def test_propose_approve_reserve_is_not_execution(flow):
    p = flow["submit"]().json()
    assert p["status"] == "pending_approval" and not p["execution_available"]
    approved = flow["decide"](p)
    assert approved.status_code == 201 and approved.json()["status"] == "approved"
    repeated = flow["decide"](p)
    assert repeated.json()["decision_id"] == approved.json()["decision_id"]
    read = flow["api"].client.get(
        flow["path"] + "/" + p["proposal_id"],
        headers=flow["api"].headers(flow["users"][0]),
    )
    assert read.json()["status"] == "approved"
    claim = flow["reserve"](p)
    assert claim["status"] == "reserved" and not claim["execution_available"]
    with pytest.raises(HTTPException) as e:
        flow["reserve"](p)
    assert e.value.status_code == 409
    assert flow["decide"](p, "revoke").status_code == 409
    with flow["lab"]["owner"].connect() as c:
        assert (
            c.execute(
                text("SELECT count(*) FROM case_runtime.action_receipts")
            ).scalar()
            == 0
        )
        assert (
            c.execute(
                text("SELECT count(*) FROM case_runtime.action_verifications")
            ).scalar()
            == 0
        )


def test_retries_bind_exact_content_and_survive_new_store(flow):
    body = proposal()
    key = str(uuid4())
    first = flow["submit"](body, key)
    assert first.status_code == 201, first.text
    p = first.json()
    assert flow["submit"](body, key).json() == p
    flow["api"].app.state.action_authority = ActionAuthority(
        flow["lab"]["engine"], enabled=True
    )
    assert flow["submit"](body, key).json() == p
    changed = {**body, "parameters": {"reason": "Changed exact intent"}}
    assert flow["submit"](changed, key).status_code == 409
    with flow["lab"]["owner"].connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM case_runtime.action_proposals WHERE case_id=:id"
                ),
                {"id": flow["case_id"]},
            ).scalar()
            == 1
        )
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM case_runtime.outbox_events WHERE aggregate_id=:id"
                ),
                {"id": p["proposal_id"]},
            ).scalar()
            == 1
        )


def test_concurrent_idempotent_submission_and_single_reservation(flow):
    body = proposal()
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: flow["submit"](body, key), range(4)))
    assert {r.status_code for r in responses} == {201}, [
        (r.status_code, r.text) for r in responses
    ]
    assert len({r.json()["proposal_id"] for r in responses}) == 1
    p = responses[0].json()
    assert flow["decide"](p).status_code == 201

    def reserve(_):
        try:
            return flow["reserve"](p)["status"]
        except HTTPException as e:
            return e.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, range(2)))
    assert sorted(map(str, results)) == ["409", "reserved"]


def test_case_acl_separation_exact_hash_and_revocation(flow):
    assert flow["submit"](user=3).status_code == 403
    p = flow["submit"]().json()
    assert flow["decide"](p, user=0).status_code == 403
    assert flow["decide"](p, hash="0" * 64).status_code == 409
    with pytest.raises(HTTPException) as e:
        flow["reserve"](p)
    assert e.value.status_code == 403
    assert flow["decide"](p).status_code == 201
    with pytest.raises(HTTPException) as e:
        flow["reserve"](p, user=1)
    assert e.value.status_code == 403
    assert flow["decide"](p, "revoke").status_code == 201
    assert flow["decide"](p).status_code == 409
    with pytest.raises(HTTPException) as e:
        flow["reserve"](p)
    assert e.value.status_code == 403


def test_revoked_current_approver_grant_blocks_and_reports_truthfully(flow):
    p = flow["submit"]().json()
    assert flow["decide"](p).status_code == 201
    with flow["lab"]["owner"].begin() as c:
        c.execute(
            text(
                "DELETE FROM case_runtime.case_access_grants WHERE case_id=:case AND subject_id=:subject AND permission='approve'"
            ),
            {"case": flow["case_id"], "subject": flow["users"][1]},
        )
    read = flow["api"].client.get(
        flow["path"] + "/" + p["proposal_id"],
        headers=flow["api"].headers(flow["users"][0]),
    )
    assert read.json()["status"] == "approval_authority_revoked"
    with pytest.raises(HTTPException) as e:
        flow["reserve"](p)
    assert e.value.status_code == 403


def test_stale_case_revision_and_cross_case_path_denied(flow):
    p = flow["submit"]().json()
    wrong = flow["api"].client.get(
        "/api/v1/cases/" + str(uuid4()) + "/action-proposals/" + p["proposal_id"],
        headers=flow["api"].headers(flow["users"][0]),
    )
    assert wrong.status_code == 404
    with flow["lab"]["owner"].begin() as c:
        c.execute(
            text("UPDATE case_runtime.cases SET revision=revision+1 WHERE id=:id"),
            {"id": flow["case_id"]},
        )
    assert flow["decide"](p).status_code == 409


def test_foreign_tenant_rows_hidden_and_history_role_unsafe(flow):
    with flow["lab"]["engine"].begin() as c:
        c.execute(
            text("SELECT set_config('app.current_tenant_id',:tenant,true)"),
            {"tenant": OTHER},
        )
        assert (
            c.execute(
                text("SELECT count(*) FROM case_runtime.cases WHERE id=:id"),
                {"id": flow["case_id"]},
            ).scalar()
            == 0
        )
    flow["api"].app.state.action_authority = ActionAuthority(
        flow["lab"]["owner"], enabled=True
    )
    assert flow["submit"]().status_code == 503


def test_unsupported_or_expired_proposals_never_create_approval(flow):
    for body, code in [
        ({**proposal(), "tool_id": "endpoint.isolate"}, 503),
        ({**proposal(), "expires_at": 1}, 422),
        ({**proposal(), "parameters": {"requires_approval": False}}, 422),
    ]:
        r = flow["submit"](body)
        assert r.status_code == code, r.text
    with flow["lab"]["owner"].connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM case_runtime.action_proposals WHERE case_id=:id"
                ),
                {"id": flow["case_id"]},
            ).scalar()
            == 0
        )


def test_outbox_failure_rolls_back_proposal_and_approval_request(flow):
    with flow["lab"]["owner"].begin() as c:
        c.execute(
            text("REVOKE INSERT ON case_runtime.outbox_events FROM sg_action_app")
        )
    try:
        r = flow["submit"]()
        assert r.status_code == 503, r.text
        with flow["lab"]["owner"].connect() as c:
            assert (
                c.execute(
                    text(
                        "SELECT count(*) FROM case_runtime.action_proposals WHERE case_id=:id"
                    ),
                    {"id": flow["case_id"]},
                ).scalar()
                == 0
            )
    finally:
        with flow["lab"]["owner"].begin() as c:
            c.execute(
                text("GRANT INSERT ON case_runtime.outbox_events TO sg_action_app")
            )
    assert flow["submit"]().status_code == 201


def test_immutable_evidence_and_foreign_hash_binding(flow):
    p = flow["submit"]().json()
    with flow["lab"]["owner"].begin() as c:
        with pytest.raises(DBAPIError) as immutable_update:
            with c.begin_nested():
                c.execute(
                    text(
                        "UPDATE case_runtime.action_proposals SET canonical_payload='{}' WHERE id=:id"
                    ),
                    {"id": p["proposal_id"]},
                )
        assert immutable_update.value.orig.pgcode == "23514"
        with pytest.raises(DBAPIError) as immutable_delete:
            with c.begin_nested():
                c.execute(
                    text("DELETE FROM case_runtime.action_proposals WHERE id=:id"),
                    {"id": p["proposal_id"]},
                )
        assert immutable_delete.value.orig.pgcode == "23514"
        with pytest.raises(DBAPIError) as foreign_binding:
            with c.begin_nested():
                c.execute(
                    text(
                        "INSERT INTO case_runtime.approval_requests(id,tenant_id,proposal_id,proposal_hash) VALUES (:id,:tenant,:proposal,:hash)"
                    ),
                    {
                        "id": str(uuid4()),
                        "tenant": OTHER,
                        "proposal": p["proposal_id"],
                        "hash": p["proposal_hash"],
                    },
                )

        assert foreign_binding.value.orig.pgcode == "23503"


def test_expired_proposal_cannot_be_approved_and_replay_reports_expired(flow):
    import time

    body = {**proposal(), "expires_at": int(time.time()) + 2}
    key = str(uuid4())
    r = flow["submit"](body, key)
    assert r.status_code == 201, r.text
    time.sleep(2.1)
    assert flow["decide"](r.json()).status_code == 410
    replay = flow["submit"](body, key)
    assert replay.status_code == 201 and replay.json()["status"] == "expired"


def test_new_target_action_is_blocked_after_uncertain_prior_reservation(flow):
    body = proposal()
    p = flow["submit"](body).json()
    assert flow["decide"](p).status_code == 201
    first = flow["reserve"](p)
    assert first["status"] == "reserved"
    second = flow["submit"](body).json()
    assert flow["decide"](second).status_code == 201
    with pytest.raises(HTTPException) as e:
        flow["reserve"](second)
    assert e.value.status_code == 409


def test_committed_approval_and_idempotency_survive_actual_database_crash_restart(flow):
    body = proposal()
    key = str(uuid4())
    p = flow["submit"](body, key).json()
    approved = flow["decide"](p)
    assert approved.status_code == 201
    flow["lab"]["restart"]()
    flow["api"].app.state.action_authority = ActionAuthority(
        flow["lab"]["engine"], enabled=True
    )
    replay = flow["submit"](body, key)
    assert replay.status_code == 201, replay.text
    assert (
        replay.json()["proposal_id"] == p["proposal_id"]
        and replay.json()["status"] == "approved"
    )
    repeated = flow["decide"](p)
    assert (
        repeated.status_code == 201
        and repeated.json()["decision_id"] == approved.json()["decision_id"]
    )
    c = flow["lab"]["connect"](user="sg_migrator")
    with c, c.cursor() as q:
        q.execute(
            "SELECT count(*) FROM case_runtime.cases WHERE id=%s", (flow["case_id"],)
        )
        assert q.fetchone()[0] == 0
        q.execute("SELECT set_config('app.current_tenant_id',%s,true)", (TENANT,))
        q.execute(
            "SELECT count(*) FROM case_runtime.cases WHERE id=%s", (flow["case_id"],)
        )
        assert q.fetchone()[0] == 1
    c.close()
