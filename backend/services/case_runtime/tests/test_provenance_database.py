"""Inactive storage qualification in an owned native cluster, never real authority.

Owner inserts are test setup, not a production provisioning identity. The separate
RLS probe role exists only inside this disposable cluster.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

import pytest
from fastapi import HTTPException
from psycopg2 import sql
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.authority.database_role import require_safe_database_role
from app.authority.models import Case
from app.provenance.models import (
    Base,
    EvidenceReference,
    CaseEvidenceLink,
    RunManifest,
    RunEvidenceLink,
)
from test_action_database import lab as lab, flow as flow, ROOT, TENANT, OTHER

TABLES = tuple(t.name for t in Base.metadata.sorted_tables)


def case(engine, tenant=TENANT):
    ident = uuid4()
    with engine.begin() as c:
        c.execute(
            Case.__table__.insert().values(
                id=ident, tenant_id=tenant, policy_version="synthetic-v1"
            )
        )
    return ident


def evidence(tenant=TENANT, **changes):
    now = datetime.now(timezone.utc)
    result = dict(
        id=uuid4(),
        tenant_id=tenant,
        source_type="synthetic",
        source_locator="synthetic://fixture/alert",
        source_version="fixture-v1",
        content_sha256="a" * 64,
        digest_unavailable_reason=None,
        observed_at=now,
        collected_at=now,
        retain_until=now + timedelta(days=30),
        access_class="synthetic-internal",
        custody_reference="synthetic://custody/v1",
    )
    return {**result, **changes}


def manifest(case_id, ids=(), **changes):
    payload = json.dumps({"evidence_ids": [str(i) for i in ids], "synthetic": True})
    result = dict(
        id=uuid4(),
        tenant_id=TENANT,
        case_id=case_id,
        request_key=uuid4(),
        initiated_by=uuid4(),
        mode="synthetic",
        schema_version="run-manifest-v1",
        trigger_reference="synthetic://trigger/v1",
        source_content_reference="synthetic://content/v1",
        payload=payload,
        payload_sha256=hashlib.sha256(payload.encode()).hexdigest(),
    )
    for key in (
        "playbook",
        "selection",
        "skill",
        "model",
        "prompt",
        "toolset",
        "policy",
        "runtime",
    ):
        result[key + "_version"] = "synthetic-immutable-v1"
    return {**result, **changes}


def insert_graph(engine):
    cid = case(engine)
    ev = evidence()
    run = manifest(cid, [ev["id"]])
    with engine.begin() as c:
        c.execute(EvidenceReference.__table__.insert().values(**ev))
        c.execute(
            CaseEvidenceLink.__table__.insert().values(
                tenant_id=TENANT, case_id=cid, evidence_id=ev["id"]
            )
        )
        c.execute(RunManifest.__table__.insert().values(**run))
        c.execute(
            RunEvidenceLink.__table__.insert().values(
                tenant_id=TENANT, case_id=cid, run_id=run["id"], evidence_id=ev["id"]
            )
        )
    return cid, ev, run


@pytest.fixture(scope="module")
def provenance(lab):
    assert os.environ.get("SG_ACTION_DB_PROFILE") == "shared_application"
    profile = json.loads(
        (ROOT.parent / "publication/case-provenance-profile.json").read_text()
    )
    baseline = json.loads(
        (ROOT.parent / "publication/application-database-profile.json").read_text()
    )
    assert profile["migrations"][:-1] == baseline["migrations"]
    witness = case(lab["owner"])
    with lab["owner"].connect() as c:
        before = c.execute(
            text("SELECT * FROM public.flyway_schema_history ORDER BY installed_rank")
        ).all()
        grants = c.execute(
            text(
                "SELECT relname,relacl::text FROM pg_class WHERE relnamespace='case_runtime'::regnamespace ORDER BY relname"
            )
        ).all()
    entry = profile["migrations"][-1]
    source = ROOT.parent / entry["path"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == entry["sha256"]
    copied = lab["bundle"] / "sql" / source.name
    shutil.copyfile(source, copied)
    ok, report = lab["migrate"]("migrate")
    assert ok and report["migrationsExecuted"] == 1, report
    assert lab["migrate"]("validate")[0]
    ok, report = lab["migrate"]("migrate")
    assert ok and report["migrationsExecuted"] == 0
    with lab["owner"].connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT * FROM public.flyway_schema_history WHERE installed_rank<=18 ORDER BY installed_rank"
                )
            ).all()
            == before
        )
        assert (
            c.execute(
                text("SELECT id FROM case_runtime.cases WHERE id=:id"), {"id": witness}
            ).scalar()
            == witness
        )
        for name, acl in grants:
            assert (
                c.execute(
                    text(
                        "SELECT relacl::text FROM pg_class WHERE relnamespace='case_runtime'::regnamespace AND relname=:name"
                    ),
                    {"name": name},
                ).scalar()
                == acl
            )
    original = copied.read_bytes()
    try:
        copied.write_bytes(original + b"\nSELECT 1;\n")
        assert not lab["migrate"]("validate")[0]
    finally:
        copied.write_bytes(original)
    assert lab["migrate"]("validate")[0]
    yield lab


def test_models_physical_schema_and_no_application_privileges(provenance):
    inspector = inspect(provenance["owner"])
    with provenance["owner"].connect() as c:
        for table in Base.metadata.sorted_tables:
            actual = {
                x["name"]: x
                for x in inspector.get_columns(table.name, schema="case_runtime")
            }
            assert set(actual) == set(table.columns.keys())
            for column in table.columns:
                assert actual[column.name]["nullable"] == column.nullable
                assert actual[column.name]["type"].compile(
                    dialect=provenance["owner"].dialect
                ) == column.type.compile(dialect=provenance["owner"].dialect)
            assert set(
                inspector.get_pk_constraint(table.name, schema="case_runtime")[
                    "constrained_columns"
                ]
            ) == set(table.primary_key.columns.keys())
            assert {
                (
                    tuple(f["constrained_columns"]),
                    f["referred_schema"],
                    f["referred_table"],
                    tuple(f["referred_columns"]),
                )
                for f in inspector.get_foreign_keys(table.name, schema="case_runtime")
            } == {
                (
                    tuple(f.column_keys),
                    f.referred_table.schema,
                    f.referred_table.name,
                    tuple(e.column.name for e in f.elements),
                )
                for f in table.foreign_key_constraints
            }
            assert {
                tuple(u["column_names"])
                for u in inspector.get_unique_constraints(
                    table.name, schema="case_runtime"
                )
            } == {
                tuple(u.columns.keys())
                for u in table.constraints
                if u.__class__.__name__ == "UniqueConstraint"
            }
            assert {
                x["name"]
                for x in inspector.get_check_constraints(
                    table.name, schema="case_runtime"
                )
            } == {
                x.name
                for x in table.constraints
                if x.__class__.__name__ == "CheckConstraint"
            }
            assert c.execute(
                text(
                    "SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid=to_regclass(:name)"
                ),
                {"name": "case_runtime." + table.name},
            ).one() == (True, True)
            for privilege in (
                "SELECT",
                "INSERT",
                "UPDATE",
                "DELETE",
                "TRUNCATE",
                "REFERENCES",
                "TRIGGER",
            ):
                assert not c.execute(
                    text(
                        "SELECT has_table_privilege('sg_action_app',:name,:privilege)"
                    ),
                    {"name": "case_runtime." + table.name, "privilege": privilege},
                ).scalar()
    with Session(provenance["engine"]) as session:
        require_safe_database_role(session)


@pytest.mark.parametrize(
    "changes",
    [
        {"content_sha256": None},
        {"content_sha256": "invalid"},
        {"digest_unavailable_reason": "also supplied"},
        {"content_sha256": None, "digest_unavailable_reason": ""},
        {"source_version": ""},
        {"source_locator": "x" * 2049},
        {"access_class": ""},
        {"custody_reference": ""},
        {"retain_until": datetime(2000, 1, 1, tzinfo=timezone.utc)},
        {"tenant_id": "00000000-0000-0000-0000-000000000000"},
    ],
)
def test_invalid_evidence_rejected(provenance, changes):
    with pytest.raises(DBAPIError), provenance["owner"].begin() as c:
        c.execute(EvidenceReference.__table__.insert().values(**evidence(**changes)))


def test_unavailable_digest_is_explicit_not_fabricated(provenance):
    with provenance["owner"].begin() as c:
        c.execute(
            EvidenceReference.__table__.insert().values(
                **evidence(
                    content_sha256=None,
                    digest_unavailable_reason="upstream content unavailable; synthetic test",
                )
            )
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"payload_sha256": "b" * 64},
        {"payload": "[]"},
        {"payload": "not JSON"},
        {"mode": "executed"},
        {"schema_version": "unknown"},
        {"skill_version": ""},
        {"runtime_version": None},
        {"source_content_reference": ""},
        {"initiated_by": "00000000-0000-0000-0000-000000000000"},
    ],
)
def test_invalid_manifest_rejected(provenance, changes):
    with pytest.raises(DBAPIError), provenance["owner"].begin() as c:
        c.execute(
            RunManifest.__table__.insert().values(
                **manifest(case(provenance["owner"]), **changes)
            )
        )


@pytest.mark.parametrize(
    "ids", [[], ["missing"], ["duplicate", "duplicate"], [None], [123]]
)
def test_declared_evidence_set_must_match_atomically(provenance, ids):
    cid = case(provenance["owner"])
    ev = evidence()
    declared = [ev["id"] if x in ("missing", "duplicate") else x for x in ids]
    run = manifest(cid, declared)
    # Empty declaration with a link is extra evidence; other declarations have no links.
    with pytest.raises(DBAPIError), provenance["owner"].begin() as c:
        c.execute(EvidenceReference.__table__.insert().values(**ev))
        c.execute(
            CaseEvidenceLink.__table__.insert().values(
                tenant_id=TENANT, case_id=cid, evidence_id=ev["id"]
            )
        )
        c.execute(RunManifest.__table__.insert().values(**run))
        if not ids:
            c.execute(
                RunEvidenceLink.__table__.insert().values(
                    tenant_id=TENANT,
                    case_id=cid,
                    run_id=run["id"],
                    evidence_id=ev["id"],
                )
            )
    with provenance["owner"].connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM case_runtime.evidence_references WHERE id=:id"
                ),
                {"id": ev["id"]},
            ).scalar()
            == 0
        )
        assert (
            c.execute(
                text("SELECT count(*) FROM case_runtime.run_manifests WHERE id=:id"),
                {"id": run["id"]},
            ).scalar()
            == 0
        )


def test_case_and_tenant_edges_and_request_deduplication(provenance):
    cid, ev, run = insert_graph(provenance["owner"])
    for tenant, wrong_case in (
        (OTHER, cid),
        (TENANT, case(provenance["owner"], OTHER)),
    ):
        with pytest.raises(DBAPIError), provenance["owner"].begin() as c:
            c.execute(
                CaseEvidenceLink.__table__.insert().values(
                    tenant_id=tenant, case_id=wrong_case, evidence_id=ev["id"]
                )
            )
    with pytest.raises(DBAPIError), provenance["owner"].begin() as c:
        c.execute(
            RunManifest.__table__.insert().values(
                **manifest(cid, request_key=run["request_key"])
            )
        )
    # Same tenant, different case cannot attach this run or evidence linkage.
    with pytest.raises(DBAPIError), provenance["owner"].begin() as c:
        c.execute(
            RunEvidenceLink.__table__.insert().values(
                tenant_id=TENANT,
                case_id=case(provenance["owner"]),
                run_id=run["id"],
                evidence_id=ev["id"],
            )
        )


@pytest.mark.parametrize("table", TABLES)
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_immutable_even_for_fixture_owner(provenance, table, operation):
    insert_graph(provenance["owner"])
    statement = (
        f"UPDATE case_runtime.{table} SET tenant_id=tenant_id"
        if operation == "UPDATE"
        else f"DELETE FROM case_runtime.{table}"
    )
    with pytest.raises(DBAPIError), provenance["owner"].begin() as c:
        c.execute(text(statement))


def test_forced_rls_separate_probe_and_app_grant_rejection(provenance):
    cid, ev, run = insert_graph(provenance["owner"])
    c = provenance["connect"]()
    try:
        with c, c.cursor() as q:
            q.execute("CREATE ROLE sg_provenance_probe NOLOGIN NOSUPERUSER NOBYPASSRLS")
            q.execute("GRANT USAGE ON SCHEMA case_runtime TO sg_provenance_probe")
            q.execute(
                "GRANT SELECT, INSERT ON case_runtime.evidence_references,case_runtime.case_evidence_links,case_runtime.run_manifests,case_runtime.run_evidence_links TO sg_provenance_probe"
            )
        for tenant, expected in ((TENANT, 1), (OTHER, 0), ("", 0)):
            with c, c.cursor() as q:
                q.execute("SET LOCAL ROLE sg_provenance_probe")
                q.execute(
                    "SELECT set_config('app.current_tenant_id',%s,true)", (tenant,)
                )
                q.execute(
                    "SELECT count(*) FROM case_runtime.run_manifests WHERE id=%s",
                    (str(run["id"]),),
                )
                assert q.fetchone()[0] == expected
        with pytest.raises(Exception) as caught:
            with c, c.cursor() as q:
                q.execute("SET LOCAL ROLE sg_provenance_probe")
                q.execute(
                    "SELECT set_config('app.current_tenant_id',%s,true)", (OTHER,)
                )
                q.execute(
                    "INSERT INTO case_runtime.case_evidence_links VALUES (%s,%s,%s,now())",
                    (TENANT, str(cid), str(ev["id"])),
                )
        assert caught.value.pgcode == "42501"
        with c, c.cursor() as q:
            q.execute("GRANT SELECT ON case_runtime.run_manifests TO sg_action_app")
        try:
            with pytest.raises(HTTPException), Session(provenance["engine"]) as session:
                require_safe_database_role(session)
        finally:
            with c, c.cursor() as q:
                q.execute(
                    "REVOKE SELECT ON case_runtime.run_manifests FROM sg_action_app"
                )
        with Session(provenance["engine"]) as session:
            require_safe_database_role(session)
    finally:
        c.close()


def test_crash_restart_and_dump_restore(provenance):
    _, ev, run = insert_graph(provenance["owner"])
    provenance["restart"]()
    with provenance["owner"].connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT payload_sha256 FROM case_runtime.run_manifests WHERE id=:id"
                ),
                {"id": run["id"]},
            ).scalar()
            == run["payload_sha256"]
        )
    c = provenance["connect"]("postgres")
    params = c.get_dsn_parameters()
    c.autocommit = True
    with c.cursor() as q:
        q.execute("CREATE DATABASE sg_provenance_restore OWNER sg_migrator")
    c.close()
    bindir = Path(os.environ["SG_TEST_PG_BINDIR"])
    dump = provenance["bundle"] / "recovery.dump"
    env = {k: v for k, v in os.environ.items() if not k.startswith("PG")}
    common = ["-h", params["host"], "-p", params["port"], "-U", "sg_owner"]
    subprocess.run(
        [str(bindir / "pg_dump"), *common, "-Fc", "-f", str(dump), "sg_case_lab"],
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            str(bindir / "pg_restore"),
            *common,
            "--exit-on-error",
            "-d",
            "sg_provenance_restore",
            str(dump),
        ],
        env=env,
        check=True,
        capture_output=True,
    )
    c = provenance["connect"]("sg_provenance_restore")
    try:
        with c, c.cursor() as q:
            q.execute(
                "SELECT payload,payload_sha256 FROM case_runtime.run_manifests WHERE id=%s",
                (str(run["id"]),),
            )
            assert q.fetchone() == (run["payload"], run["payload_sha256"])
            q.execute(
                "SELECT count(*) FROM case_runtime.run_evidence_links WHERE run_id=%s AND evidence_id=%s",
                (str(run["id"]), str(ev["id"])),
            )
            assert q.fetchone()[0] == 1
    finally:
        c.close()
    assert provenance["migrate"]("validate", "sg_provenance_restore")[0]


def test_fresh_full_lineage_install(provenance):
    # Temporary elevation is only the established migration fixture bootstrap;
    # it is revoked in finally, and never granted to the application role.
    c = provenance["connect"]("postgres")
    c.autocommit = True
    with c.cursor() as q:
        q.execute("CREATE DATABASE sg_provenance_fresh OWNER sg_migrator")
    c.close()
    c = provenance["connect"]("sg_provenance_fresh")
    try:
        with c, c.cursor() as q:
            q.execute("ALTER ROLE sg SUPERUSER")
            q.execute("SET ROLE sg")
            for extension in ("pgcrypto", "uuid-ossp", "vector"):
                q.execute(
                    sql.SQL("CREATE EXTENSION {} WITH SCHEMA public").format(
                        sql.Identifier(extension)
                    )
                )
            q.execute("RESET ROLE")
            q.execute("ALTER ROLE sg NOSUPERUSER NOBYPASSRLS")
            q.execute("GRANT USAGE, CREATE ON SCHEMA public TO sg")
            q.execute("ALTER ROLE sg_migrator BYPASSRLS")
        ok, report = provenance["migrate"]("migrate", "sg_provenance_fresh")
        assert ok and report["migrationsExecuted"] == 19, report
        assert provenance["migrate"]("validate", "sg_provenance_fresh")[0]
        ok, report = provenance["migrate"]("migrate", "sg_provenance_fresh")
        assert ok and report["migrationsExecuted"] == 0, report
        with c, c.cursor() as q:
            q.execute("SELECT count(*) FROM pg_tables WHERE schemaname='case_runtime'")
            assert q.fetchone()[0] == 16
    finally:
        with c, c.cursor() as q:
            q.execute("ALTER ROLE sg NOSUPERUSER NOBYPASSRLS")
            q.execute("ALTER ROLE sg_migrator NOBYPASSRLS")
        c.close()


@pytest.mark.parametrize("table", TABLES)
@pytest.mark.parametrize("operation", ["SELECT", "INSERT", "TRUNCATE"])
def test_application_has_no_reachable_storage_access(provenance, table, operation):
    statement = {
        "SELECT": f"SELECT * FROM case_runtime.{table}",
        "INSERT": f"INSERT INTO case_runtime.{table} DEFAULT VALUES",
        "TRUNCATE": f"TRUNCATE case_runtime.{table} CASCADE",
    }[operation]
    with pytest.raises(DBAPIError) as caught, provenance["engine"].begin() as c:
        c.execute(text(statement))
    assert caught.value.orig.pgcode == "42501"


def test_committed_manifest_cannot_gain_evidence_later(provenance):
    cid, _, run = insert_graph(provenance["owner"])
    ev = evidence()
    with provenance["owner"].begin() as c:
        c.execute(EvidenceReference.__table__.insert().values(**ev))
        c.execute(
            CaseEvidenceLink.__table__.insert().values(
                tenant_id=TENANT, case_id=cid, evidence_id=ev["id"]
            )
        )
    with pytest.raises(DBAPIError), provenance["owner"].begin() as c:
        c.execute(
            RunEvidenceLink.__table__.insert().values(
                tenant_id=TENANT, case_id=cid, run_id=run["id"], evidence_id=ev["id"]
            )
        )


@pytest.mark.parametrize(
    "payload",
    [
        "{}",
        '{"evidence_ids":null}',
        '{"evidence_ids":{}}',
        json.dumps({"evidence_ids": [str(uuid4())] * 257}),
        json.dumps({"evidence_ids": [], "oversized": "x" * 262144}),
    ],
)
def test_manifest_structure_and_size_rejected(provenance, payload):
    run = manifest(
        case(provenance["owner"]),
        payload=payload,
        payload_sha256=hashlib.sha256(payload.encode()).hexdigest(),
    )
    with pytest.raises(DBAPIError), provenance["owner"].begin() as c:
        c.execute(RunManifest.__table__.insert().values(**run))


def test_existing_action_path_after_upgrade_is_still_effect_disabled(provenance, flow):
    response = flow["submit"]()
    assert response.status_code == 201, response.text
    proposal = response.json()
    assert flow["decide"](proposal).status_code == 201
    reserved = flow["reserve"](proposal)
    assert reserved["status"] == "reserved"
    assert reserved["execution_available"] is False
