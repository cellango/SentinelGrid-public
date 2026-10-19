# Integrated native abort/close outcome experiment

**Opt-in deny-only research; never install or deploy the output.** The experiment
implements a temporary source overlay following the
[proposed containment contract](../../../../../docs/architecture/keycloak-lifecycle-containment.md)
and [ADR 0004](../../../../../docs/architecture/decisions/0004-issuer-core-storage-and-compatibility.md).
It improves selected owned abort-path behavior. **Full containment and cleanup
remain NO-GO**, with four explicit negative witnesses. No successful issuance,
production patch/fork, storage or authority is implemented.

## Compared code and observed result

Three disposable projects use exact Keycloak 26.8.1 commit
`24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b` and the same reviewed SDK/build inputs:

| Variant | Native surface | Passing cases |
| --- | --- | ---: |
| Native | Unmodified manager/session/helper; earlier guarded realm resolver retained | 160 |
| Limited | Previous two-catch-site rollback error-observation overlay | 160 |
| Integrated | Three native units overlaid plus the limited control's unbound behavior and new opt-in state | 192 |

**512 cases pass, zero skips**, plus six input/preparation rejection controls.
Each project reruns the 155 earlier cases (25 rollback, 96 realm/lifecycle and
34 actual native-authentication/non-creation) and five new comparisons. The
integrated project adds 32 candidate cases. Original source/oracle bytes are
unchanged: the previous explicit native-versus-candidate fault-observation
comparison and unfinished-participant assertions remain. These results include
expected negative witnesses; passing tests do not mean containment passed.

Five native source units are compiled: manager, session, abstract transaction,
thread-close helper and async response transaction. Only the first, second and
fourth are changed in the integrated project. Code-source checks require the
actual compiled classes. Model/context/provider boundaries are synthetic;
`JTAPolicy.NOT_SUPPORTED` is used. There is no real JTA, JDBC/PostgreSQL, cache,
tracing exporter, server/HTTP stack, real workload credential/token or data path.

## Candidate surface and limits

`prepare.py` validates native and earlier fixture SHA-256 inputs before output.
It changes only temporary copies:

- **Manager:** bind an exact session/thread-owned research state before work;
  remember registrations before fallible native begin; bound commit always
  denies; abort becomes terminal without status/rollback-only/default-commit
  gates. Main/after callbacks are attempted once independently of observational
  tracing. Prepare callbacks are not blindly rolled back. Late binding and a
  completed manager remain unknown; no retry or reset follows.
- **Session:** a bound close enters the deny-only abort path before original
  logging/status/default-close logic. Provider closes and deferred invalidations
  record failures; independently owned cleanup continues where tested. A native
  closed flag is not resource-release or durable rollback evidence.
- **Thread-close helper:** a bound native session bypasses the fallible isClosed
  query; finally uses the existing context-clear primitive through the outcome
  recorder. This still does not restore a nested parent frame.
- **Research state:** bounded ordered primary/secondary failures independent of
  Java suppression, an overflow/unknown indicator, exact owner checks and
  per-role/object attempt tracking. Registration has a finite bound. Fatal
  failures retain unknown outcome when recording is possible; cleanup is never
  promised for VM failure. This state grants no enrollment, fence or recovery
  authority and stores nothing durable.

In the tested owned scope, unmarked close and explicit commit cannot commit the
synthetic main transaction. Marker-lookup/status/getter/isClosed failures do not
fall through native default commit. Required rollback still runs once with
lookup/null/before/after/drop/repeat/reentrant observational hooks. First/secondary
errors survive disabled suppression, reused Throwable identities, overflow,
participant/provider/deferred-invalidation failures. Actual resource release is
not established by those synthetic callback outcomes.

## Negative containment witnesses retained

| Witness | Actual observation and open requirement |
| --- | --- |
| Fresh child session | A callback opens an unbound real native child session; child close commits its synthetic transaction while the parent aborts. The actual job-helper/context-cloning/provider path was not run. Mandatory fresh-session pre-read ownership is missing (LC-06/09). |
| Native async callback | The actual AsyncResponseTransaction rollback resumes an error Response through an AsyncResponse double before outer close finishes. No HTTP transport or usable token is exercised. Callback registration does not enforce one complete release barrier (LC-07). |
| Nested context | Native helper close clears the context instead of restoring the existing parent; the candidate does not detect that loss. No complete frame restoration or error contract follows (LC-05/06). |
| Late attachment | Already-active native work is not retroactively owned; its participant remains STARTED with no rollback or commit, and the candidate records unknown outcome. The required boundary must precede lifecycle work (LC-01/09). |

Failed rollback also retains its unfinished native participant; returning an error
cannot repair it. Prepare/no-op/paired cache/independent-effect semantics need
actual provider qualification. The full LC-01/02/04/05 acceptance is **not met**;
the scoped deny/error-observation controls alone pass. All ten contract gates,
full cleanup/native failure contract, A0/A1/A2, all entry/writer closure, R2
implementation/R3/R4 and SQL/JTA/HTTP/durability/recovery remain open.

Next, qualify mandatory session creation, native job/context ownership and native
response callback/exclusion boundaries against the pinned source, retaining these
counterexamples. A wrapper, context marker or optional late bind cannot close
them. Stop and record NO-GO if a mandatory pre-effect boundary cannot be shown;
do not proceed to storage/admission or further local catch fixes on that basis.
Required security cleanup and IAM/service features stay requirements, including
ITDR/SCIM/user/JIT, not silent exclusions or retirement.

## Reproduce only in owned temporary state

Keep `native_abort` beside `rollback_lifecycle`, `realm_entry` and `entry_guard`.
Use the exact independently reviewed archive/toolchain and credential-free
settings described in the [rollback lab](../rollback_lifecycle/README.md).
`inputs.json` pins all reused code/recipes/control inputs; no native source,
JAR/JDK or built binary is redistributed. The recipe does not fetch or run Maven.

```sh
python3 prepare.py /owned/keycloak-source /owned/new-native-project native
python3 prepare.py /owned/keycloak-source /owned/new-limited-project limited
python3 prepare.py /owned/keycloak-source /owned/new-integrated-project integrated
```

Use JDK 21 (recorded Temurin 21.0.12.1+1), Maven 3.9.11, explicit `-s` and `-gs`
settings mirroring only Maven Central, a new Maven home/cache and per-project
Maven/JVM temporary directories. Resolve/review inputs first, then run offline
`test` with `-DentryGuard.guarded=false -DrealmEntry.guarded=true`. Set
`-Dabort.mode=native -Drollback.candidate=false` for native;
`-Dabort.mode=limited -Drollback.candidate=true` for limited;
`-Dabort.mode=integrated -Drollback.candidate=true -Dtest=*Test,AbortCandidateCases`
for integrated (quote the test selector when using a shell).

Validate the 206 SDK classpath JARs with `../entry_guard/verify_sdk.py`; all 290
SDK/build JARs must match the earlier reviewed coordinate/hash/license set.
No new dependency is added. Two historical build-helper license declarations and
deprecated test-only API remain unresolved qualification limits. Reflection-only
doubles/dynamic-agent-disabled JVM settings are retained. Six controls reject
input drift/symlinks, unknown modes, output inside source, prior-fixture drift and
replacement of existing output. Remove only owned extraction/projects/cache/JVM
temp state after retaining reports. Never install/deploy/package as a provider.

Initial test failures detected an omitted native abstract-transaction source copy
and incorrect setup for a deferred invalidation; the fixture was corrected while
retaining the source-location/failure assertions. A parallel Surefire shared-temp
warning led to final sequential runs with owned per-project temporary state.
Final results above have no skipped cases or that warning. Prior reports remain
private. The [review](../../native-abort-review.json) pins the final fixture and
source inputs and distinguishes observations from unmet acceptance.
