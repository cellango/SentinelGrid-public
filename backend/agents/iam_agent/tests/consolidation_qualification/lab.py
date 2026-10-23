"""Owned disposable databases only; existing test role arrangement, no real URLs."""
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
from tempfile import TemporaryDirectory

import psycopg2
from psycopg2 import sql
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sg_core.tenant_session import install_tenant_pool_reset

ROOT = Path(__file__).resolve().parents[5]
FIXTURE = Path(__file__).parent


def run(command, *, env=None):
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    if result.returncode:
        # Do not print subprocess arguments or credentials on failure.
        raise RuntimeError(f"Disposable tool {Path(command[0]).name} failed (exit {result.returncode})")
    return result.stdout


@pytest.fixture(scope="module")
def cluster():
    bindir = Path(os.environ["SG_TEST_PG_BINDIR"])
    for name in ("initdb", "pg_ctl", "pg_dump", "pg_restore"):
        assert (bindir / name).is_file(), f"Missing required tool: {name}"
    with TemporaryDirectory(prefix="sg-iam-consolidation-", dir="/tmp") as directory:
        root = Path(directory)
        root.chmod(0o700)
        sock = root / "socket"
        sock.mkdir(mode=0o700)
        password = secrets.token_urlsafe(32)
        pw = root / "pw"
        pw.write_text(password + "\n")
        pw.chmod(0o600)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        run([str(bindir / "initdb"), "-D", str(root / "data"), "-U", "sg_test_owner",
             "--auth-local=trust", "--auth-host=scram-sha-256", "--pwfile", str(pw), "--no-locale", "--encoding=UTF8"])
        run([str(bindir / "pg_ctl"), "-D", str(root / "data"), "-l", str(root / "postgres.log"),
             "-o", f"-h 127.0.0.1 -k {sock} -p {port}", "-w", "start"])
        params = dict(host=str(sock), port=port, user="sg_test_owner", password=password, dbname="postgres")
        try:
            with psycopg2.connect(**params) as connection:
                connection.autocommit = True
                with connection.cursor() as cursor:
                    cursor.execute("CREATE ROLE sg_test_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS")
            connection = psycopg2.connect(**params)
            connection.autocommit = True
            try:
                with connection.cursor() as cursor:
                    for name in ("iam_test", "catalog_test", "consolidated_test", "restored_test", "fresh_test"):
                        cursor.execute(sql.SQL("CREATE DATABASE {} OWNER sg_test_owner").format(sql.Identifier(name)))
            finally:
                connection.close()
            yield params
        finally:
            run([str(bindir / "pg_ctl"), "-D", str(root / "data"), "-m", "immediate", "-w", "stop"])


def connect(params, database):
    return psycopg2.connect(**{**params, "dbname": database})


def app_engine(params, database):
    engine = create_engine(URL.create("postgresql+psycopg2", username="sg_test_app", database=database,
        query={"host": params["host"], "port": str(params["port"])}), pool_size=1, max_overflow=0)
    install_tenant_pool_reset(engine)
    return engine


def migrate(params, database, *, target=None, command="migrate"):
    import hashlib
    flyway = Path(os.environ["SG_TEST_FLYWAY"])
    assert flyway.is_file(), "Flyway required; no SQL-execution fallback"
    with TemporaryDirectory(prefix="flyway-", dir=Path(params["host"]).parent) as directory:
        directory = Path(directory)
        location = directory / "sql"
        location.mkdir()
        profile = json.loads((ROOT / "publication/iam-database-profile.json").read_text())
        for item in profile["migrations"]:
            path = ROOT / item["path"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
            shutil.copyfile(path, location / path.name)
        fixture = FIXTURE / "V022__public_qualification_effective_policies.sql"
        shutil.copyfile(fixture, location / fixture.name)
        config = directory / "flyway.conf"
        config.write_text(f"flyway.url=jdbc:postgresql://127.0.0.1:{params['port']}/{database}\n"
            f"flyway.user=sg_test_owner\nflyway.password={params['password']}\nflyway.locations=filesystem:{location}\n"
            "flyway.baselineOnMigrate=false\nflyway.validateOnMigrate=true\nflyway.cleanDisabled=true\n"
            "flyway.ignoreMigrationPatterns=\nflyway.validateMigrationNaming=true\n")
        config.chmod(0o600)
        args = [str(flyway), f"-configFiles={config}", "-outputType=json"]
        if target is not None:
            args.append(f"-target={target}")
        return json.loads(run(args + [command]))


def grant_fixture_access(params, database):
    # Same disposable nonowner arrangement as test_iam_database, never deployed.
    with connect(params, database) as connection, connection.cursor() as cursor:
        cursor.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        cursor.execute("GRANT USAGE ON SCHEMA public TO sg_test_app")
        cursor.execute("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO sg_test_app")
        cursor.execute("REVOKE UPDATE,DELETE ON iam_audit_events FROM sg_test_app")


def rows(params, database, table):
    with connect(params, database) as connection, connection.cursor() as cursor:
        cursor.execute(sql.SQL("SELECT to_jsonb(t) FROM public.{} t ORDER BY id").format(sql.Identifier(table)))
        return [row[0] for row in cursor.fetchall()]


def copy_rows(params, source_db, table, cursor):
    # Frozen synthetic inputs only. JSON populate preserves full source columns.
    payload = rows(params, source_db, table)
    if payload:
        cursor.execute(sql.SQL("INSERT INTO public.{} SELECT * FROM jsonb_populate_recordset(NULL::public.{}, %s::jsonb)").format(
            sql.Identifier(table), sql.Identifier(table)), (json.dumps(payload),))
