# SPDX-License-Identifier: Apache-2.0
"""Controlled experiments in run_local.py's fresh owned lab; never an application API."""

import collections
import concurrent.futures
import json
import os
import signal
import subprocess
import time


def run(lab):
    root, out = lab["LAB"], lab["O"]
    db, snapshot, token = lab["db"], lab["snapshot"], lab["token"]
    http, admin = lab["http"], lab["admin"]
    subject, client, foreign = lab["SUBJECT"], lab["CLIENT"], lab["FOREIGN"]
    url = (
        lab["issuer"]
        + "/sentinelgrid-registration/v1/clients/"
        + client
        + "/association"
    )
    records = []
    mutation_verbs = {
        "INSERT",
        "UPDATE",
        "DELETE",
        "MERGE",
        "TRUNCATE",
        "CREATE",
        "ALTER",
        "DROP",
        "GRANT",
        "REVOKE",
        "COMMENT",
        "SET",
        "OTHER",
    }

    def save():
        value = dict(
            format_version=1,
            experiments=records,
            experiment_count=len(records),
            experiments_completed=all(r["experiment_completed"] for r in records),
            adoption_gate_passed=bool(records)
            and all(r["gate_passed"] for r in records),
            failed_gates=[r["case"] for r in records if not r["gate_passed"]],
            existing_application_and_Python_guard_unchanged=True,
            no_authentication_or_query_result_override=True,
            statement_listener_limits="Pinned H2 prepared-command callbacks; parse/recompile and abrupt-process-death gaps remain. No general SQL engine or cluster clearance.",
        )
        (out / "controlled-failures.private.json").write_text(
            json.dumps(value, indent=2) + "\n"
        )
        return value

    def add(record):
        records.append(record)
        save()
        print(
            json.dumps(
                {k: record[k] for k in ["case", "experiment_completed", "gate_passed"]}
            ),
            flush=True,
        )

    def sql(statement):
        path = root / "controlled-fixture.sql"
        path.write_text(statement)
        try:
            db("sql", str(path))
        finally:
            path.unlink(missing_ok=True)

    def clear():
        for scope in ["user", "realm"]:
            admin("POST", "/clear-" + scope + "-cache")

    def statements():
        path = root / "statements.tsv"
        if not path.exists():
            return []
        result = []
        for line in path.read_text().splitlines():
            epoch, n, event, verb, channel, shape = line.split("\t")
            result.append(
                dict(
                    epoch=int(epoch),
                    sequence=int(n),
                    event=event,
                    verb=verb,
                    channel=channel,
                    shape=shape,
                )
            )
        return result

    def rows():
        path = root / "writes.tsv"
        if not path.exists():
            return []
        return [
            dict(zip(["table", "operation", "channel"], line.split("\t")))
            for line in path.read_text().splitlines()
        ]

    def health():
        n, errors = db("observer-health").strip().split(":")
        assert int(errors) == 0, "Statement observer I/O failure"
        groups = collections.defaultdict(list)
        for event in statements():
            groups[event["epoch"]].append(event["sequence"])
        assert all(
            values == list(range(1, len(values) + 1)) for values in groups.values()
        ), "Statement observation gap"
        return dict(
            errors=0,
            epochs=len(groups),
            events=sum(len(v) for v in groups.values()),
            current_process_events_at_call=int(n),
        )

    def window(start_statement, start_row):
        events = statements()[start_statement:]
        writes = rows()[start_row:]
        unmarked = [
            e
            for e in events
            if e["event"] == "START"
            and e["channel"] == "UNMARKED"
            and e["verb"] in mutation_verbs
        ]
        protected = [
            r
            for r in writes
            if r["channel"] == "UNMARKED" and r["table"] not in lab["BOOKKEEP"]
        ]
        return dict(
            statement_starts=dict(
                collections.Counter(e["verb"] for e in events if e["event"] == "START")
            ),
            unmarked_write_or_unknown_statement_starts=len(unmarked),
            unmarked_protected_row_attempts=len(protected),
            fixture_statement_starts=dict(
                collections.Counter(
                    e["verb"]
                    for e in events
                    if e["event"] == "START" and e["channel"] == "FIXTURE"
                )
            ),
            fixture_protected_row_attempts=sum(
                r["channel"] == "FIXTURE" and r["table"] not in lab["BOOKKEEP"]
                for r in writes
            ),
            service_account_query_starts=sum(
                e["event"] == "START"
                and e["shape"] == "SERVICE_ACCOUNT_LOOKUP"
                and e["channel"] == "UNMARKED"
                for e in events
            ),
        )

    def result(response):
        if response.status_code == 503:
            assert response.json() == {"detail": "Association observation unavailable"}
            assert response.headers.get("cache-control") == "no-store"
            return dict(status=503)
        assert response.status_code == 200, "Unexpected routed response"
        value = response.json()
        assert set(value) == {
            "contract",
            "issuer",
            "realm_id",
            "client_uuid",
            "client_id",
            "subject_id",
            "tenant_id",
            "client_enabled",
            "subject_enabled",
            "observed_at",
        }
        assert response.headers.get("cache-control") == "no-store"
        return dict(
            status=200,
            client_enabled=value["client_enabled"],
            subject_enabled=value["subject_enabled"],
            observed_at=value["observed_at"],
        )

    def get(tok):
        return http.get(url, headers={"Authorization": "Bearer " + tok})

    def unchanged(before, after):
        return [
            t
            for t in set(before) | set(after)
            if t not in lab["BOOKKEEP"] and before.get(t) != after.get(t)
        ]

    def observe(name, expected=None, allow_unavailable=False):
        tok = token()
        before = snapshot()
        mark = len(statements())
        rowmark = len(rows())
        response = get(tok)
        time.sleep(0.1)
        evidence = window(mark, rowmark)
        after = snapshot()
        value = result(response)
        changed = unchanged(before, after)
        truth = (value["status"] == 503 and allow_unavailable) or (
            value["status"] == 200
            and all(value.get(k) == v for k, v in (expected or {}).items())
        )
        passed = (
            truth
            and not changed
            and not evidence["unmarked_write_or_unknown_statement_starts"]
            and not evidence["unmarked_protected_row_attempts"]
        )
        health()
        record = dict(
            case=name,
            experiment_completed=True,
            gate_passed=passed,
            response=value,
            required_observed_state=expected,
            protected_persistent_changes_during_observation=changed,
            **evidence,
        )
        add(record)
        return record

    # Separate intentional fixture calibration from all observation measurements.
    before = snapshot()
    mark = len(statements())
    rowmark = len(rows())
    sql(
        "CREATE TABLE SG_OBSERVER_CALIBRATION(ID INT); ALTER TABLE SG_OBSERVER_CALIBRATION ADD NOTE INT; UPDATE USER_ENTITY SET ENABLED=FALSE WHERE ID='"
        + foreign
        + "'; BEGIN; UPDATE USER_ENTITY SET ENABLED=FALSE WHERE ID='"
        + subject
        + "'; ROLLBACK; DROP TABLE SG_OBSERVER_CALIBRATION;"
    )
    starts = collections.Counter(
        e["verb"]
        for e in statements()[mark:]
        if e["event"] == "START" and e["channel"] == "FIXTURE"
    )
    attempts = [
        r
        for r in rows()[rowmark:]
        if r["table"] == "USER_ENTITY" and r["channel"] == "FIXTURE"
    ]
    assert (
        starts["CREATE"]
        and starts["ALTER"]
        and starts["DROP"]
        and starts["UPDATE"] == 2
        and starts["TRANSACTION"] >= 2
    )
    assert len(attempts) == 1 and snapshot() == before
    error_mark = len(statements())
    failed = False
    try:
        sql("UPDATE USER_ENTITY SET SG_NONEXISTENT_CALIBRATION_COLUMN=1")
    except subprocess.CalledProcessError:
        failed = True
    assert failed
    error_callback_visible = any(
        e["event"] == "ERROR" for e in statements()[error_mark:]
    )
    add(
        dict(
            case="statement_and_row_observer_calibration",
            experiment_completed=True,
            gate_passed=error_callback_visible,
            zero_row_update_statement_detected=True,
            rolled_back_update_row_detected=True,
            DDL_create_alter_drop_detected=True,
            parse_failure_rejected_by_JDBC=True,
            parse_failure_database_callback_visible=error_callback_visible,
            executed_statement_and_row_paths_calibrated=True,
            fixture_write_statements=dict(starts),
            persistent_snapshot_unchanged=True,
            health=health(),
        )
    )

    clear()
    observe("cold_read_sql_profile", dict(client_enabled=True, subject_enabled=True))
    observe("warm_read_sql_profile", dict(client_enabled=True, subject_enabled=True))
    # Cache-bypass writes are an adversarial lab stale-cache witness, not a supported external writer.
    sql("UPDATE CLIENT SET ENABLED=FALSE WHERE ID='" + client + "'")
    try:
        observe(
            "committed_client_disable_before_warm_read",
            dict(client_enabled=False, subject_enabled=True),
            True,
        )
    finally:
        sql("UPDATE CLIENT SET ENABLED=TRUE WHERE ID='" + client + "'")
        clear()
    sql("UPDATE USER_ENTITY SET ENABLED=FALSE WHERE ID='" + subject + "'")
    try:
        observe(
            "committed_subject_disable_before_read",
            dict(client_enabled=True, subject_enabled=False),
            True,
        )
    finally:
        sql("UPDATE USER_ENTITY SET ENABLED=TRUE WHERE ID='" + subject + "'")
        clear()

    def reset_barrier():
        for name in ["control", "claimed", "entered", "release", "timeout", "seen"]:
            (root / ("barrier." + name)).unlink(missing_ok=True)

    def wait_barrier(future):
        deadline = time.monotonic() + 6
        while not (root / "barrier.entered").exists():
            if future.done():
                raise AssertionError(
                    "Read completed without reaching controlled SQL barrier"
                )
            if time.monotonic() > deadline:
                raise AssertionError("Controlled SQL barrier was not reached")
            time.sleep(0.01)

    def race(
        name,
        mutate,
        restore,
        expected=None,
        phase="START",
        ordinal=1,
        native_admin_writer=False,
    ):
        clear()
        get(token())  # Warm verified provider/cache before the controlled request.
        tok = token()
        before = snapshot()
        mark = len(statements())
        rowmark = len(rows())
        reset_barrier()
        (root / "barrier.control").write_text(
            phase + "\tSERVICE_ACCOUNT_LOOKUP\t" + str(ordinal)
        )
        changed = False
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(get, tok)
                wait_barrier(future)
                mutate()
                changed = True
                (root / "barrier.release").write_text("release")
                response = future.result(timeout=10)
            assert not (root / "barrier.timeout").exists(), "Controlled pause timed out"
            evidence = window(mark, rowmark)
            after = snapshot()
            value = result(response)
            # Unavailable is safe; success must match the committed state before resuming the read.
            truth = (
                value["status"] == 503
                or expected is not None
                and value["status"] == 200
                and all(value.get(k) == v for k, v in expected.items())
            )
            passed = truth and (
                bool(unchanged(before, after))
                if native_admin_writer
                else evidence["fixture_protected_row_attempts"] > 0
                and not evidence["unmarked_write_or_unknown_statement_starts"]
                and not evidence["unmarked_protected_row_attempts"]
            )
            health()
            add(
                dict(
                    case=name,
                    experiment_completed=True,
                    gate_passed=passed,
                    response=value,
                    required_observed_state=expected,
                    pause=(root / "barrier.entered").read_text(),
                    committed_fixture_changes=unchanged(before, after),
                    fixture_committed_before_read_resumed=True,
                    mutation_path="supported_native_Admin_REST"
                    if native_admin_writer
                    else "tagged_lab_JDBC",
                    observation_write_attribution_complete=not native_admin_writer,
                    write_attribution_limit="Admin REST SQL shares the unmarked channel; this case measures freshness only"
                    if native_admin_writer
                    else None,
                    **evidence,
                )
            )
        finally:
            (root / "barrier.release").write_text("release")
            if changed:
                restore()
            reset_barrier()
            clear()

    def native_client_enabled(enabled):
        value = admin("GET", "/clients/" + client).json()
        value["enabled"] = enabled
        admin("PUT", "/clients/" + client, json=value)

    race(
        "supported_admin_client_disable_during_query",
        lambda: native_client_enabled(False),
        lambda: native_client_enabled(True),
        dict(client_enabled=False, subject_enabled=True),
        native_admin_writer=True,
    )

    race(
        "client_disable_during_first_association_query",
        lambda: sql("UPDATE CLIENT SET ENABLED=FALSE WHERE ID='" + client + "'"),
        lambda: sql("UPDATE CLIENT SET ENABLED=TRUE WHERE ID='" + client + "'"),
        dict(client_enabled=False, subject_enabled=True),
    )
    race(
        "subject_disable_during_first_association_query",
        lambda: sql("UPDATE USER_ENTITY SET ENABLED=FALSE WHERE ID='" + subject + "'"),
        lambda: sql("UPDATE USER_ENTITY SET ENABLED=TRUE WHERE ID='" + subject + "'"),
        dict(client_enabled=True, subject_enabled=False),
    )
    race(
        "client_rename_during_first_association_query",
        lambda: sql(
            "UPDATE CLIENT SET CLIENT_ID='ticket-reader-replaced' WHERE ID='"
            + client
            + "'"
        ),
        lambda: sql(
            "UPDATE CLIENT SET CLIENT_ID='ticket-reader' WHERE ID='" + client + "'"
        ),
    )
    for phase, ordinal in [("START", 1), ("END", 2)]:
        race(
            "subject_rebind_" + phase.lower() + "_" + str(ordinal),
            lambda: sql(
                "UPDATE USER_ENTITY SET SERVICE_ACCOUNT_CLIENT_LINK='"
                + foreign
                + "' WHERE ID='"
                + subject
                + "'"
            ),
            lambda: sql(
                "UPDATE USER_ENTITY SET SERVICE_ACCOUNT_CLIENT_LINK='"
                + client
                + "' WHERE ID='"
                + subject
                + "'"
            ),
            phase=phase,
            ordinal=ordinal,
        )

    # Only the fresh fixed synthetic subject and its direct FK rows are backed up privately for fixture restoration.
    db("backup-subject")

    def restore_subject():
        sql(
            "DELETE FROM USER_ENTITY WHERE ID='"
            + foreign
            + "';\n"
            + (root / "subject-fixture-backup.sql").read_text()
        )

    def replace_subject():
        db("delete-subject")
        sql(
            "INSERT INTO USER_ENTITY(ID,REALM_ID,USERNAME,EMAIL_CONSTRAINT,ENABLED,SERVICE_ACCOUNT_CLIENT_LINK,CREATED_TIMESTAMP,NOT_BEFORE) VALUES('"
            + foreign
            + "','"
            + lab["realmId"]
            + "','service-account-ticket-reader','"
            + foreign
            + "',TRUE,'"
            + client
            + "',0,0)"
        )

    for phase, ordinal in [("START", 1), ("END", 2)]:
        race(
            "subject_delete_" + phase.lower() + "_" + str(ordinal),
            lambda: db("delete-subject"),
            restore_subject,
            phase=phase,
            ordinal=ordinal,
        )
        race(
            "same_name_recreation_" + phase.lower() + "_" + str(ordinal),
            replace_subject,
            restore_subject,
            phase=phase,
            ordinal=ordinal,
        )
    (root / "subject-fixture-backup.sql").unlink()

    # Uncommitted rollback is a fixture transaction, not a provider-side write or recovery guarantee.
    race(
        "concurrent_fixture_rollback",
        lambda: sql(
            "BEGIN; UPDATE USER_ENTITY SET ENABLED=FALSE WHERE ID='"
            + subject
            + "'; ROLLBACK;"
        ),
        lambda: None,
        dict(client_enabled=True, subject_enabled=True),
    )

    # Actual database process death while the native JPA query is paused; no fake return/exception injection.
    clear()
    get(token())
    tok = token()
    before = snapshot()
    mark = len(statements())
    rowmark = len(rows())
    prior_health = health()
    reset_barrier()
    (root / "barrier.control").write_text("START\tSERVICE_ACCOUNT_LOOKUP\t1")
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(get, tok)
        wait_barrier(future)
        process = lab["DBPROC"]
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)
        (root / "barrier.release").write_text("release")
        response = future.result(timeout=10)
    value = result(response)
    evidence = window(mark, rowmark)
    assert value["status"] == 503
    lab["stop"](lab["KC"])
    reset_barrier()
    (root / "fixture-connection-initialized").unlink(missing_ok=True)
    lab["DBPROC"] = lab["launch"](process.args, "h2-recovery")
    lab["wait_port"](lab["DBPROC"], lab["dbport"])
    recovered = snapshot()
    changes = unchanged(before, recovered)
    lab["start_kc"]()
    health()
    add(
        dict(
            case="persistent_database_loss_and_recovery",
            experiment_completed=True,
            gate_passed=not changes
            and not evidence["unmarked_protected_row_attempts"]
            and not evidence["unmarked_write_or_unknown_statement_starts"],
            response=value,
            protected_persistent_changes_after_recovery=changes,
            health_before_failure=prior_health,
            abrupt_death_statement_END_and_exception_callbacks_unavailable=True,
            **evidence,
        )
    )
    observe(
        "post_recovery_native_retry", dict(client_enabled=True, subject_enabled=True)
    )
    value = save()
    value["final_observer_health"] = health()
    (out / "controlled-failures.private.json").write_text(
        json.dumps(value, indent=2) + "\n"
    )
    return value
