#!/usr/bin/env python3
"""Fail-closed shared-lineage qualification in a new disposable native cluster.

Requires reviewed SG_TEST_PG_BINDIR and SG_TEST_FLYWAY binaries. Accepts no
database URL, credentials or existing data directory. JSON on stdout is evidence,
not deployment approval. Exit 1 means the migration/qualification gate failed.
"""

from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory

import psycopg2

from prepare_iam_flyway import prepare

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "publication/application-database-profile.json"


def successful(returncode, value):
    """Flyway JSON validation failures can have process exit code zero."""
    return (
        returncode == 0
        and isinstance(value, dict)
        and "error" not in value
        and value.get("errorDetails") is None
        and value.get("exception") is None
        and not value.get("invalidMigrations")
        and (value.get("success") is True or value.get("validationSuccessful") is True)
        and value.get("success", True) is not False
        and value.get("validationSuccessful", True) is not False
    )


def qualify():
    bindir = Path(os.environ.get("SG_TEST_PG_BINDIR", "/missing"))
    flyway = Path(os.environ.get("SG_TEST_FLYWAY", "/missing"))
    if (
        not all(
            (bindir / n).is_file()
            for n in ("postgres", "initdb", "pg_ctl", "pg_dump", "pg_restore")
        )
        or not flyway.is_file()
    ):
        raise ValueError("Reviewed native PostgreSQL and Flyway binaries are required")
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("PG", "FLYWAY_"))
        and k
        not in {
            "JAVA_HOME",
            "JAVA_ARGS",
            "JAVA_TOOL_OPTIONS",
            "JDK_JAVA_OPTIONS",
            "_JAVA_OPTIONS",
        }
    }
    report = {
        "profile": "shared_application_lineage",
        "passed": False,
        "D0_fresh_install": False,
        "populated_V013_to_V018": "not_run",
        "scope": "New isolated synthetic native cluster only; privileged lab migrator, not production/application privilege qualification",
        "existing_database_accessed": False,
        "migration_bytes_changed": False,
        "repair_baseline_or_ignore_missing_used": False,
        "flyway_runs": [],
    }
    with TemporaryDirectory(prefix="sg-shared-db-", dir="/private/tmp") as directory:
        lab = Path(directory)
        lab.chmod(0o700)
        data, sock, bundle = lab / "data", lab / "socket", lab / "bundle"
        sock.mkdir(mode=0o700)
        count = prepare(bundle, root=ROOT, profile=PROFILE)
        manifest = json.loads(PROFILE.read_text())
        versions = [
            int(Path(i["path"]).name.split("__")[0][1:]) for i in manifest["migrations"]
        ]
        if count != 18 or versions != list(range(1, 19)):
            raise ValueError("The complete unchanged V001-V018 lineage is required")
        report["migration_sha256"] = manifest["migrations"]
        password = secrets.token_urlsafe(32)
        pwfile = lab / "pw"
        pwfile.write_text(password)
        pwfile.chmod(0o600)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]

        def pg(*args):
            return subprocess.run(
                [str(bindir / args[0]), *args[1:]],
                env=env,
                capture_output=True,
                text=True,
                check=True,
                timeout=90,
            )

        def connect(database="sg_full"):
            return psycopg2.connect(
                host=str(sock), port=port, user="sg_lab_admin", dbname=database
            )

        def query(statement, database="sg_full", parameters=None):
            with (
                closing(connect(database)) as connection,
                connection,
                connection.cursor() as cursor,
            ):
                cursor.execute(statement, parameters)
                return cursor.fetchall() if cursor.description else None

        def migrate(command, database="sg_full", target=None):
            args = [
                str(flyway),
                "-configFiles=" + str(bundle / "flyway.conf"),
                f"-url=jdbc:postgresql://127.0.0.1:{port}/{database}",
                "-user=sg_lab_admin",
                "-reportEnabled=false",
                "-outputType=json",
            ]
            if target is not None:
                args.append("-target=" + str(target))
            process = subprocess.run(
                [*args, command],
                cwd=bundle,
                env={**env, "FLYWAY_PASSWORD": password},
                capture_output=True,
                text=True,
                timeout=180,
            )
            # Generated passwords never enter reports, including driver diagnostics.
            stdout, stderr = (
                s.replace(password, "<redacted>")
                for s in (process.stdout, process.stderr)
            )
            try:
                value = json.loads(stdout)
            except ValueError:
                value = {"error": "Flyway did not return JSON", "stdout": stdout}
            ok = successful(process.returncode, value)
            report["flyway_runs"].append(
                {
                    "command": command,
                    "database": database,
                    "target": target,
                    "exit_code": process.returncode,
                    "passed": ok,
                    "result": value,
                    "stderr": stderr,
                }
            )
            return ok, value

        def catalog(database="sg_full"):
            tables = query(
                "SELECT schemaname, tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY 1,2",
                database,
            )
            history = (
                query(
                    "SELECT version, checksum, success FROM public.flyway_schema_history ORDER BY installed_rank",
                    database,
                )
                if ("public", "flyway_schema_history") in tables
                else []
            )
            return {
                "tables": tables,
                "history": history,
                "extensions": query(
                    "SELECT extname, extversion FROM pg_extension ORDER BY 1", database
                ),
            }

        pg(
            "initdb",
            "-D",
            str(data),
            "-U",
            "sg_lab_admin",
            "--pwfile",
            str(pwfile),
            "--auth-local=trust",
            "--auth-host=scram-sha-256",
            "--no-locale",
            "--encoding=UTF8",
        )
        started = False
        try:
            pg(
                "pg_ctl",
                "-D",
                str(data),
                "-l",
                str(lab / "server.log"),
                "-o",
                f"-h 127.0.0.1 -p {port} -k {sock}",
                "-w",
                "start",
            )
            started = True
            pwfile.unlink()
            with closing(connect("postgres")) as connection:
                connection.autocommit = True
                with connection.cursor() as cursor:
                    cursor.execute("CREATE ROLE sg NOLOGIN NOSUPERUSER NOBYPASSRLS")
                    for database in ("sg_full", "sg_upgrade", "sg_dirty", "sg_restore"):
                        cursor.execute(
                            "CREATE DATABASE " + database + " OWNER sg_lab_admin"
                        )
            report["server_version"] = query("SHOW server_version")[0][0]
            report["migrator_role"] = query(
                "SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user"
            )[0]
            available = dict(
                query(
                    "SELECT name, default_version FROM pg_available_extensions WHERE name IN ('pgcrypto','uuid-ossp','vector')"
                )
            )
            report["available_required_extensions"] = available
            if set(available) != {"pgcrypto", "uuid-ossp", "vector"}:
                report["failure_stage"] = "extension_prerequisites"
                return report
            # A nonempty unversioned database must never be silently baselined.
            query(
                "CREATE TABLE public.synthetic_legacy_witness(id integer PRIMARY KEY)",
                "sg_dirty",
            )
            query(
                "INSERT INTO public.synthetic_legacy_witness VALUES (731)", "sg_dirty"
            )
            dirty_ok, _ = migrate("migrate", "sg_dirty")
            dirty_catalog = catalog("sg_dirty")
            report["unversioned_populated_database_refused"] = (
                not dirty_ok
                and dirty_catalog["tables"] == [("public", "synthetic_legacy_witness")]
                and query("SELECT id FROM public.synthetic_legacy_witness", "sg_dirty")
                == [(731,)]
            )
            ok, result = migrate("migrate")
            report["fresh_catalog"] = catalog()
            if not ok:
                report["failure_stage"] = "D0_fresh_migration"
                before = report["fresh_catalog"]
                again, _ = migrate("migrate")
                report["failure_reproduced_without_history_changes"] = (
                    not again and catalog() == before
                )
                report["no_partial_application_objects"] = (
                    before["tables"] == [("public", "flyway_schema_history")]
                    and before["history"] == []
                    and before["extensions"] == [("plpgsql", "1.0")]
                )
                return report
            report["D0_fresh_install"] = result.get("migrationsExecuted") == 18
            valid, _ = migrate("validate")
            repeated, result = migrate("migrate")
            report["fresh_validation_and_noop"] = (
                valid and repeated and result.get("migrationsExecuted") == 0
            )
            history = report["fresh_catalog"]["history"]
            report["all_18_checksummed_history_entries"] = len(history) == 18 and all(
                h[1] is not None and h[2] for h in history
            )
            # Deliberately corrupt only disposable copies; never repair stored history.
            copied = bundle / "sql" / Path(manifest["migrations"][-1]["path"]).name
            original = copied.read_bytes()
            try:
                copied.write_bytes(original + b"\nSELECT 1;\n")
                report["changed_checksum_refused"] = not migrate("validate")[0]
            finally:
                copied.write_bytes(original)
            hidden = copied.with_suffix(".unavailable")
            try:
                copied.rename(hidden)
                report["missing_applied_version_refused"] = not migrate("validate")[0]
            finally:
                hidden.rename(copied)
            report["history_and_source_restored_without_repair"] = (
                migrate("validate")[0]
                and catalog() == report["fresh_catalog"]
                and all(
                    hashlib.sha256((ROOT / i["path"]).read_bytes()).hexdigest()
                    == i["sha256"]
                    for i in manifest["migrations"]
                )
            )
            ok, _ = migrate("migrate", "sg_upgrade", 13)
            if not ok:
                report["failure_stage"] = "V013_upgrade_baseline"
                return report
            query(
                "INSERT INTO public.tenants(id,name,slug) VALUES ('11111111-1111-4111-8111-111111111111','Synthetic migration witness','synthetic-migration-witness')",
                "sg_upgrade",
            )
            witness_sql = (
                "SELECT row_to_json(t)::text FROM public.tenants t ORDER BY id"
            )
            witness = query(witness_sql, "sg_upgrade")
            ok, _ = migrate("migrate", "sg_upgrade")
            report["populated_V013_to_V018"] = bool(
                ok and query(witness_sql, "sg_upgrade") == witness
            )
            report["upgrade_catalog"] = catalog("sg_upgrade")
            report["synthetic_witness_sha256"] = hashlib.sha256(
                json.dumps(witness).encode()
            ).hexdigest()
            # Immediate stop exercises actual crash recovery, rather than reconnect alone.
            pg("pg_ctl", "-D", str(data), "-m", "immediate", "-w", "stop")
            started = False
            pg(
                "pg_ctl",
                "-D",
                str(data),
                "-l",
                str(lab / "server.log"),
                "-o",
                f"-h 127.0.0.1 -p {port} -k {sock}",
                "-w",
                "start",
            )
            started = True
            report["crash_restart_preserved_history_and_witness"] = (
                catalog() == report["fresh_catalog"]
                and catalog("sg_upgrade") == report["upgrade_catalog"]
                and query(witness_sql, "sg_upgrade") == witness
                and migrate("validate", "sg_upgrade")[0]
            )
            dump = lab / "synthetic.dump"
            pg(
                "pg_dump",
                "-h",
                str(sock),
                "-p",
                str(port),
                "-U",
                "sg_lab_admin",
                "-d",
                "sg_upgrade",
                "-Fc",
                "-f",
                str(dump),
            )
            report["synthetic_backup_sha256"] = hashlib.sha256(
                dump.read_bytes()
            ).hexdigest()
            pg(
                "pg_restore",
                "-h",
                str(sock),
                "-p",
                str(port),
                "-U",
                "sg_lab_admin",
                "-d",
                "sg_restore",
                "--exit-on-error",
                str(dump),
            )
            report["logical_restore_preserved_catalog_history_and_witness"] = (
                catalog("sg_restore") == report["upgrade_catalog"]
                and query(witness_sql, "sg_restore") == witness
                and migrate("validate", "sg_restore")[0]
            )
            report["passed"] = all(
                report.get(k) is True
                for k in (
                    "D0_fresh_install",
                    "unversioned_populated_database_refused",
                    "fresh_validation_and_noop",
                    "all_18_checksummed_history_entries",
                    "populated_V013_to_V018",
                    "changed_checksum_refused",
                    "missing_applied_version_refused",
                    "history_and_source_restored_without_repair",
                    "crash_restart_preserved_history_and_witness",
                    "logical_restore_preserved_catalog_history_and_witness",
                )
            )
            return report
        finally:
            if started:
                pg("pg_ctl", "-D", str(data), "-m", "immediate", "-w", "stop")
                report["owned_cluster_stopped"] = True


def main():
    os.umask(0o077)
    if len(sys.argv) != 1:
        raise SystemExit(
            "No connection arguments accepted; use only the reviewed binary environment variables"
        )
    try:
        report = qualify()
    except Exception as error:
        # Driver/process exceptions may contain credentials or environment details.
        report = {
            "passed": False,
            "failure_stage": "qualification_harness",
            "error_type": type(error).__name__,
            "existing_database_accessed": False,
        }
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
