# Disposable SQL attempt observer

**Experimental lab tooling, with bounded calibration evidence.** This extends
the [existing disposable runtime lab](../../README.md). It installs nothing into
an existing issuer and changes no provider artifact, application caller, grant,
schema, deployment or default. The JVM instrumentation agent here is a Java
tracing mechanism, not an AI reasoning agent. [ADR 0003](../../../../../docs/architecture/decisions/0003-association-consistency-and-issuance.md)
remains proposed; all nine earlier provider gates remain failed.

## Run and inspect

Use `qualification/run_local.py` with its existing reviewed Java21,
distribution-archive, provider-JAR and new private report-directory arguments,
adding `--attempt-calibration --disposable-local-only`. This mode and
`--controlled-failures` are mutually exclusive. The runner creates all realms,
accounts, clients, credentials, database state and processes from scratch on
loopback, and removes the lab in its cleanup path. It deliberately kills its
own new database process, exercises fixture writes and damages one fixture
process's log sink to test detection. Never redirect it to existing state.

Run the offline evidence controls separately:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover \
  -s infra/keycloak/keycloak_registration_connector/qualification/attempts \
  -p test_evidence.py -v
```

These log-validator tests make no issuer or database calls. They do not replace
the native runtime scenarios.

The private report separates `bounded_calibration_gate_passed` from
`all_attribution_and_observer_health_gates_passed`. The deliberately lost record
and killed process must fail whole-log health/absence-of-attempts evidence; the
calibration succeeds when those faults are detected and all scoped controls
pass. Exit 2 retains that unmet global evidence gate. Exit 1 indicates an
unexpected harness/runtime failure. Inspect the report fields and cleanup,
rather than treating process completion as runtime adoption.

## What the observer records

The lab compiles original recorder/advice/calibration classes and uses the
Byte Buddy 1.14.18 archive already present in the hash-verified vendor
distribution. H2 remains 2.3.230 and Keycloak 26.0.6. These are historical
compatibility pins, not maintained production selections. Exact archive hashes,
packaged Byte Buddy/ASM license metadata, source hashes and each temporary
observer-JAR digest are recorded. No additional application/build dependency,
downloaded vendor source or observer binary is published in this module.

The provider JAR and vendor JARs stay byte-identical. Opt-in JVM tracing records
JDBC preparation/execution/binding entry and errors, server parse/recompile and
DDL/DML/transaction paths, plus the existing row observer. It records exception
type/source location without exception messages. Advice does not replace an
authentication result, query text, parameter, return value or transaction
outcome. The 46 retained baseline cases exercise that bound at native runtime.

For the pinned single-node TCP protocol, client operation events are joined to
server frames by loopback socket pair and per-connection ordinal, with exact
opcode agreement. The handshake callsite is deliberately version-specific.
Duplicate/reused ambiguous keys, opcode disagreement and missing receipt remain
unresolved evidence. An attempted client command is not assumed to have reached
the server. Process epochs, server session IDs and actual MVStore transaction
ID/sequence accompany the records; these are diagnostic identifiers, not grants.

Native request IDs come from server-side request lifecycle hooks. Actual matched
resource methods label observer, admin and issuer scopes. The recorder keys the
backing request context, because a CDI session proxy can be shared across
concurrent requests. The context remains associated through session close and
transaction completion. Neither caller headers, URL labels, SQL comments nor a
reused worker/connection supplies authority or clears a record. Startup,
unmatched HTTP and background activity retains its unresolved classification.

Log records contain stage, operation class, source/route category, process,
thread, span, connection/frame and transaction identifiers, with no SQL,
parameters, bearer/secret values or row contents. A genuine parameter/result
canary and credential probes check redaction. Logger errors, gaps, incomplete
spans, missing terminal health or unclassified operations fail their evidence
gates; equal committed fingerprints cannot erase attempted effects.

## Measured calibration and limits

The [review record](../../attempts-review.json) binds the exact source and result
counts. The bounded run covers 17 named fixture cases, actual database death and
recovery, and a native Admin write interleaved with a genuine provider query.
All 14 detection checks and 46 retained native baseline cases pass. Eleven offline
fault controls reject ambiguous/missing protocol joins, route conflicts, lost
events, unfinished requests, unknown statements and leaked canaries.

The fixture matrix includes server syntax and authorization rejection, client
binding failure, zero-row UPDATE/DELETE, rolled-back rows/savepoints, partial
batch failure, MERGE, nested DDL/implicit commit, actual recompile/parse, a
background write causally released after the caller receives a response, failed
commit after actual server death and recovery of the uncommitted row. Deferred
work has a four-second fixture deadline; no unlimited absence claim follows.

Matched observation scope has zero mutating/unknown server entries and zero row
attempts in this run. Native Admin writes are separately attributed through
commit, including on a pooled connection also used for observations. Native
issuance records include protocol-mapper writes outside observation scope.
Unresolved startup/background records and the deliberate logger/crash faults
remain visible. Whole-runtime attribution/health, every driver/API/storage path,
unbounded delayed effects and full provider qualification remain open.

Earlier diagnostic attempts are retained privately: one unexplained valid-read
503, an invalid tracing stack-map revision, and a shared-CDI-proxy attribution
collision. The final revision passes the baseline; these observations do not
establish general equivalence or supported production instrumentation.

The new interleaved test still returns earlier enabled state after a native
Admin disable commits. The original 18 experiments/nine failed gates and their
native-Admin attribution ambiguity are unchanged. New tracing cannot
retroactively clear old records or repair provider consistency. The next
engineering unit is ADR 0003 R2: exact maintained issuer/API/writer/storage and
conditional-issuance feasibility. All R1 coverage limits and R3–R7 acceptance
remain required before adoption.
