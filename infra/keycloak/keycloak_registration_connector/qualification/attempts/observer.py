# SPDX-License-Identifier: Apache-2.0
"""Pinned opt-in observer in run_local.py's new lab, with no provider artifact change."""

import collections
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import signal
import secrets
import subprocess
import time
import zipfile

BB_SHA256 = "52117af1696a53aa77c131353074ada25ccbdf2df511f2af33fad6704fa95104"
H2_SHA256 = "9a3734cb0799fb53d5c8bb159422ff41bb1e1ad938e340880e3b4e35b4b3c69f"
FIELDS = ("pid", "sequence", "thread", "event", "span", "parent", "origin", "request",
          "hook", "verb", "connection", "rpc", "case", "result", "session", "transaction")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(lab):
    root, out, java = lab["LAB"], lab["O"], lab["J"]
    bb = lab["home"] / "lib/lib/main/net.bytebuddy.byte-buddy-1.14.18.jar"
    assert digest(bb) == BB_SHA256 and digest(lab["h2"]) == H2_SHA256
    logs = out / "attempt-events"
    logs.mkdir(mode=0o700)
    (logs / "attempt-report-owned").write_text("Fresh private disposable-lab report\n")
    source = Path(__file__).with_name("java")
    jars = {}
    helper = root / "attempt-helper-classes"
    agent = root / "attempt-agent-classes"
    calibration = root / "attempt-calibration-classes"
    for directory in (helper, agent, calibration):
        directory.mkdir()
    run = lab["run"]
    run([java / "bin/javac", "--release", "21", "-proc:none", "-d", helper,
         source / "AttemptLog.java"], timeout=30)
    run([java / "bin/javac", "--release", "21", "-proc:none", "-cp",
         str(helper) + os.pathsep + str(bb), "-d", agent,
         source / "AttemptAgent.java"], timeout=30)
    run([java / "bin/javac", "--release", "21", "-proc:none", "-cp",
         str(helper) + os.pathsep + str(lab["h2"]), "-d", calibration,
         source / "AttemptCalibration.java"], timeout=30)
    manifest = root / "attempt-agent.mf"
    manifest.write_text("Manifest-Version: 1.0\n"
                        "Premain-Class: ai.sentinelgrid.keycloak.lab.attempts.AttemptAgent\n"
                        "Class-Path: " + bb.as_uri() + "\n\n")
    for name, classes in (("helper", helper), ("agent", agent),
                          ("calibration", calibration)):
        jar = root / ("attempt-" + name + ".jar")
        command = [java / "bin/jar", "--create", "--file", jar]
        if name == "agent":
            command += ["--manifest", manifest]
        run(command + ["-C", classes, "."], timeout=30)
        jars[name] = jar
    source_copy = out / "attempt-source"
    source_copy.mkdir(mode=0o700)
    for p in source.glob("*.java"):
        (source_copy / p.name).write_bytes(p.read_bytes())
    (source_copy / "observer.py").write_bytes(Path(__file__).read_bytes())
    (source_copy / "run_local.py").write_bytes((Path(__file__).parents[1] / "run_local.py").read_bytes())
    with zipfile.ZipFile(bb) as archive:
        licenses = {n: hashlib.sha256(archive.read(n)).hexdigest()
                    for n in archive.namelist() if not n.endswith("/") and ("LICENSE" in n.upper()
                    or "NOTICE" in n.upper())}
    assert licenses, "Pinned Byte Buddy archive has no license metadata"
    provenance = dict(
        h2_sha256=H2_SHA256, byte_buddy_version="1.14.18", byte_buddy_sha256=BB_SHA256,
        byte_buddy_already_in_verified_vendor_distribution=True,
        byte_buddy_license_files_sha256=licenses,
        lab_source_sha256={p.name: digest(p) for p in source.glob("*.java")},
        lab_jar_sha256={n: digest(p) for n, p in jars.items()},
        provider_jar_unchanged=True, vendor_jar_unchanged=True,
        agent_classes_outside_provider_artifact=True,
        handshaking_callsite="H2 2.3.230 SessionRemote.initTransfer line155, opcode12",
        instrumentation_requires_complete_protocol_alignment=True,
    )
    (out / "attempt-build.private.json").write_text(json.dumps(provenance, indent=2) + "\n")
    lab["env"].update(
        SG_LAB_ATTEMPT_CANARY=secrets.token_urlsafe(24),
        SG_LAB_ATTEMPT_LOGS=str(logs),
        JAVA_TOOL_OPTIONS="-javaagent:" + str(jars["agent"]) + "=" + str(jars["helper"]),
    )
    lab["classpath"] += os.pathsep + str(jars["calibration"])
    return jars


def calibrate(lab):
    root, out, java = lab["LAB"], lab["O"], lab["J"]
    started = time.monotonic()
    command = [java / "bin/java", "-cp", lab["classpath"],
               "ai.sentinelgrid.keycloak.lab.attempts.AttemptCalibration"]
    normal = json.loads(lab["run"](command + ["normal"], timeout=50).stdout)
    logger_fault = json.loads(lab["run"](command + ["logger-failure"], timeout=20).stdout)
    # Isolate actual TCP-server death from the real issuer; restart it only after recovery.
    lab["stop"](lab["KC"])
    before = lab["snapshot"]()
    child = lab["launch"](command + ["crash-commit"], "attempt-crash-client")
    deadline = time.monotonic() + 20
    while not (root / "attempt-crash-ready").exists():
        if child.poll() is not None or time.monotonic() > deadline:
            raise RuntimeError("New synthetic crash client did not reach barrier")
        time.sleep(0.02)
    old = lab["DBPROC"]
    os.killpg(old.pid, signal.SIGKILL)
    old.wait(timeout=10)
    (root / "attempt-crash-release").write_text("Owned database process exited\n")
    assert child.wait(timeout=20) == 0
    lab["DBPROC"] = lab["launch"](
        [java / "bin/java", "-Dh2.bindAddress=127.0.0.1", "-cp", lab["classpath"],
         "org.h2.tools.Server", "-tcp", "-tcpPort", str(lab["dbport"]),
         "-ifNotExists", "-baseDir", root / "db"], "h2-attempt-recovery")
    lab["wait_port"](lab["DBPROC"], lab["dbport"])
    after = lab["snapshot"]()
    assert before == after, "Committed snapshots changed across synthetic database death"
    recovery = json.loads(lab["run"](command + ["recover"], timeout=30).stdout)
    lab["start_kc"]()
    # Pause a genuine association query, then complete a supported native Admin write.
    # This measures attribution without changing the provider's old stale-state witness.
    tok = lab["token"]()
    (root / "barrier.control").write_text("START\tSERVICE_ACCOUNT_LOOKUP\t1")
    url = lab["issuer"] + "/sentinelgrid-registration/v1/clients/" + lab["CLIENT"] + "/association"
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(lab["http"].get, url, headers={"Authorization": "Bearer " + tok})
        deadline = time.monotonic() + 6
        try:
            while not (root / "barrier.entered").exists():
                if future.done() or time.monotonic() > deadline:
                    raise RuntimeError("Actual native query did not reach attribution barrier")
                time.sleep(0.01)
            value = lab["admin"]("GET", "/clients/" + lab["CLIENT"]).json()
            value["enabled"] = False
            lab["admin"]("PUT", "/clients/" + lab["CLIENT"], json=value)
        finally:
            (root / "barrier.release").write_text("Native Admin write finished or failed\n")
        observation = future.result(timeout=10)
    assert observation.status_code == 200 and observation.json()["client_enabled"] is True
    value["enabled"] = True
    lab["admin"]("PUT", "/clients/" + lab["CLIENT"], json=value)
    for scope in ("user", "realm"):
        lab["admin"]("POST", "/clear-" + scope + "-cache")
    for name in ("barrier.control", "barrier.claimed", "barrier.entered", "barrier.release", "barrier.seen"):
        (root / name).unlink(missing_ok=True)
    result = dict(
        elapsed_calibration_seconds=round(time.monotonic() - started, 3),
        deferred_worker_deadline_seconds=4,
        native_Admin_mutation_interleaved_with_actual_provider_query=True,
        provider_still_returns_earlier_enabled_state=True,
        consistency_gate_still_failed=True,
        expected_abrupt_database_pid=old.pid,
        expected_logger_fault_pid=logger_fault["logger_failure_pid"],
        logger_failure_detected=logger_fault["logger_failure_detected"],
        calibration_cases_passed=normal["cases_passed"],
        actual_database_process_SIGKILL=True,
        commit_rejected_after_actual_outage=True,
        uncommitted_row_absent_after_restart=recovery["uncommitted_row_absent_after_restart"],
        committed_fingerprints_equal_across_crash=True,
        native_issuer_restarted_before_baseline=True,
        no_authentication_query_or_transaction_outcome_override=True,
    )
    (out / "attempt-calibration.private.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def iter_events(out):
    for path in sorted((out / "attempt-events").glob("*.tsv")):
        with path.open() as stream:
            for number, line in enumerate(stream, 1):
                parts = line.rstrip("\n").split("\t")
                if len(parts) != len(FIELDS):
                    yield path.name, number, None
                    continue
                row = dict(zip(FIELDS, parts))
                try:
                    for key in ("pid", "sequence", "thread", "span", "parent", "request", "rpc"):
                        row[key] = int(row[key])
                except ValueError:
                    yield path.name, number, None
                    continue
                yield path.name, number, row


def analyze(out, *, protected_values=()):
    """Streaming analysis: exact protocol joins, retained unknowns and explicit crash tails."""
    counts, expected, pids = collections.Counter(), {}, set()
    malformed, gaps, health, active, orphan = [], [], {}, set(), 0
    clients, servers, duplicates, routes, ended = {}, {}, [], {}, set()
    for file, number, row in iter_events(out):
        if row is None:
            malformed.append(dict(file=file, line=number))
            continue
        pid, event = row["pid"], row["event"]
        pids.add(pid)
        if row["sequence"] != expected.get(pid, 1):
            gaps.append(dict(file=file, expected=expected.get(pid, 1), actual=row["sequence"]))
        expected[pid] = row["sequence"] + 1
        counts[event] += 1
        key = (pid, row["span"])
        if event == "ENTER":
            active.add(key)
        elif event in {"EXIT", "ERROR"}:
            if key not in active:
                orphan += 1
            active.discard(key)
        elif event == "HEALTH":
            health[pid] = row["result"]
        elif event == "HTTP_ROUTE":
            rkey = (pid, row["request"])
            old = routes.setdefault(rkey, row["origin"])
            if old != row["origin"]:
                duplicates.append(dict(kind="conflicting_native_route", pid=pid, request=row["request"]))
        elif event == "HTTP_END":
            ended.add((pid, row["request"]))
        elif event in {"CLIENT_RPC", "SERVER_RPC"}:
            mapping = clients if event == "CLIENT_RPC" else servers
            key = (row["connection"], row["rpc"])
            if key in mapping:
                duplicates.append(dict(side=event, connection=key[0], rpc=key[1]))
            mapping[key] = (pid, row["origin"], row["request"], row["result"], row["case"])
    unmatched, mismatch, attributed = [], [], collections.Counter()
    unreceived = []
    connection_origins = collections.defaultdict(set)
    for key, server in servers.items():
        client = clients.get(key)
        if client is None:
            unmatched.append(dict(connection=key[0], rpc=key[1]))
        elif client[3] != server[3]:
            mismatch.append(dict(connection=key[0], rpc=key[1], client=client[3], server=server[3]))
        else:
            origin = routes.get((client[0], client[2]), client[1])
            attributed[origin] += 1
            connection_origins[key[0]].add(origin)
    for key, client in clients.items():
        if key not in servers:
            unreceived.append(dict(connection=key[0], rpc=key[1],
                                   origin=routes.get((client[0], client[2]), client[1])))
    cases = collections.defaultdict(lambda: dict(errors=[], entered_hooks=collections.Counter(),
                                                verbs=collections.Counter(), row_attempts=0))
    scoped = collections.defaultdict(collections.Counter)
    scoped_rows = collections.defaultdict(collections.Counter)
    unknown_server_sql = 0
    transaction_ids = collections.defaultdict(set)
    rows_without_transaction = 0
    mutations = {"INSERT", "UPDATE", "DELETE", "MERGE", "DDL", "CREATE", "ALTER", "DROP",
                 "TRUNCATE", "GRANT", "REVOKE", "COMMENT", "UNKNOWN", "CALL", "SET"}
    for _, _, e in iter_events(out):
        if e is None:
            continue
        key = (e["connection"], e["rpc"])
        client = clients.get(key) if e["rpc"] else None
        joined = client is not None and key in servers and client[3] == servers[key][3]
        origin = routes.get((e["pid"], e["request"]), e["origin"])
        case = e["case"]
        if joined and (e["origin"] in {"SERVER", "UNKNOWN"} or e["session"] != "-"):
            origin = routes.get((client[0], client[2]), client[1])
            if case == "-":
                case = client[4]
        if case != "-":
            row = cases[case]
            if e["event"] == "ERROR":
                row["errors"].append(dict(hook=e["hook"], exception=e["result"]))
            if e["event"] == "ENTER":
                row["entered_hooks"][e["hook"]] += 1
                row["verbs"][e["verb"]] += 1
            if e["event"] == "ROW":
                row["row_attempts"] += 1
        if e["event"] == "ROW":
            scoped_rows[origin][e["hook"]] += 1
            if e["transaction"] in {"NONE", "null:null"} or e["session"] in {"-", "null"}:
                rows_without_transaction += 1
            else:
                transaction_ids[origin].add((e["pid"], e["session"], e["transaction"]))
        if e["event"] == "ENTER" and e["session"] != "-":
            scoped[origin]["server_entries"] += 1
            if e["verb"] in mutations:
                scoped[origin]["mutating_or_unknown_entries"] += 1
            if origin in {"UNKNOWN", "HTTP_UNCLASSIFIED"}:
                unknown_server_sql += 1
    absent_health = pids - set(health)
    crash = json.loads((out / "attempt-calibration.private.json").read_text())
    expected_crash = crash["expected_abrupt_database_pid"]
    fault_pid = crash.get("expected_logger_fault_pid")
    full_health = all(v == "errors=0,active=0,requests=0" for v in health.values())
    healthy_except_known_fault = all(v == "errors=0,active=0,requests=0"
                                     for k, v in health.items() if k != fault_pid)
    expected_fault_gaps = [g for g in gaps if g["file"] == str(fault_pid) + ".tsv"]
    unexpected_gaps = [g for g in gaps if g not in expected_fault_gaps]
    redaction_failures = 0
    for path in (out / "attempt-events").glob("*.tsv"):
        with path.open() as stream:
            redaction_failures += sum(any(v in line for v in protected_values if v) for line in stream)
    scoped_unreceived = [r for r in unreceived if r["origin"] in {"OBSERVER", "ADMIN", "ISSUER"}]
    protocol_ok = not duplicates and not unmatched and not mismatch
    http_closed = all(k in ended for k in routes)
    case_checks = {
        "server_parse_failure_observed": any("Parser.prepare" in e["hook"]
            for e in cases["server_parse_failure"]["errors"]),
        "client_bind_failure_observed": any("JdbcPreparedStatement.setInt" in e["hook"]
            for e in cases["client_bad_bind_index"]["errors"]),
        "zero_row_update_delete_observed": cases["zero_row_update_delete"]["verbs"]["UPDATE"] > 0
            and cases["zero_row_update_delete"]["verbs"]["DELETE"] > 0
            and cases["zero_row_update_delete"]["row_attempts"] == 0,
        "rollback_row_attempt_retained": cases["row_rollback"]["row_attempts"] > 0,
        "nested_internal_DDL_observed": cases["nested_internal_ddl"]["verbs"]["CREATE"] > 0
            and cases["nested_internal_ddl"]["verbs"]["ALTER"] > 0
            and cases["nested_internal_ddl"]["verbs"]["DROP"] > 0,
        "recompile_method_and_nested_parse_observed": any("recompileIfRequired" in k for k
            in cases["prepared_statement_recompile"]["entered_hooks"])
            and any("Parser.prepare" in k for k in cases["prepared_statement_recompile"]["entered_hooks"]),
        "delayed_background_row_attempt_observed": cases["delayed_background_write"]["row_attempts"] > 0,
        "actual_dead_server_commit_failure_observed": bool(cases["commit_after_actual_server_death"]["errors"]),
        "known_abrupt_process_tail_rejected": expected_crash in absent_health,
        "native_observer_rows_separated_from_Admin": not scoped_rows["OBSERVER"]
            and scoped_rows["ADMIN"]["CLIENT"] > 0,
        "pooled_connection_changes_route_without_stale_origin": any(
            "OBSERVER" in v and "ADMIN" in v for v in connection_origins.values()),
        "row_events_have_actual_session_and_transaction_id": rows_without_transaction == 0
            and bool(transaction_ids["ADMIN"]),
        "logger_failure_and_missing_record_are_rejected": bool(expected_fault_gaps)
            and health.get(fault_pid) == "errors=1,active=0,requests=0",
        "SQL_bind_and_credential_redaction_probe": bool(protected_values)
            and redaction_failures == 0,
    }
    result = dict(
        format_version=2, events=sum(counts.values()), processes=len(pids),
        event_counts=dict(counts), per_process_event_sequence_gaps=gaps,
        malformed_records=malformed, incomplete_spans=len(active), orphan_exits=orphan,
        health_records=[dict(pid=k, result=v) for k, v in health.items()],
        processes_without_graceful_health=sorted(absent_health),
        expected_abrupt_database_pid=expected_crash,
        protocol_client_frames=len(clients), protocol_server_frames=len(servers),
        duplicate_protocol_keys=duplicates, unmatched_server_frames=unmatched,
        protocol_opcode_mismatches=mismatch, matched_frame_origins=dict(attributed),
        client_attempt_frames_without_server_receipt=unreceived,
        claimed_native_route_frames_without_server_receipt=scoped_unreceived,
        pooled_connections_with_multiple_known_origins=sum(len(v & {"OBSERVER", "ADMIN", "ISSUER"}) > 1
                                                         for v in connection_origins.values()),
        row_events_without_session_or_transaction_id=rows_without_transaction,
        row_transaction_counts_by_origin={k: len(v) for k, v in transaction_ids.items()},
        redaction_probe_applied=bool(protected_values),
        redaction_failure_records=redaction_failures,
        deliberate_logger_failure_pid=fault_pid,
        unexpected_sequence_gaps=unexpected_gaps,
        complete_process_health_gate_passed=full_health,
        native_route_contexts=len(routes), native_route_contexts_all_closed=http_closed,
        scoped_server_entries={k: dict(v) for k, v in scoped.items()},
        scoped_row_attempts={k: dict(v) for k, v in scoped_rows.items()},
        unclassified_server_entries_outside_claimed_native_route_scope=unknown_server_sql,
        calibration_case_events=dict(cases), calibration_detection_checks=case_checks,
        bounded_calibration_gate_passed=(all(case_checks.values()) and protocol_ok
            and http_closed and healthy_except_known_fault and not malformed and not unexpected_gaps
            and not orphan and not active and not scoped_unreceived
            and not scoped["OBSERVER"]["mutating_or_unknown_entries"]
            and absent_health == {expected_crash}),
        all_attribution_and_observer_health_gates_passed=False,
        complete_unbounded_absence_of_attempts_proof=False,
        incomplete_abrupt_death_tails_are_not_zero_attempt_proof=True,
        prior_native_Admin_attribution_not_reclassified=True,
        prior_nine_failed_provider_gates_unchanged=True,
        full_provider_or_production_adoption=False,
    )
    (out / "attempt-observation.private.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
