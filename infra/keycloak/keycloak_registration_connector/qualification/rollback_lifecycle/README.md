# Native rollback lifecycle comparison

**Isolated candidate experiment; never install or deploy the output.** This
continues the approved research in [ADR 0004](../../../../../docs/architecture/decisions/0004-issuer-core-storage-and-compatibility.md)
and the [early denial lab](../realm_entry/README.md). It fixes one synthetic
error-observation path in the candidate overlay. **Complete cleanup, native SQL
rollback, universal admission and R2 implementation/R3/R4 remain NO-GO.**
No production issuer patch or upstream change is adopted.

## Comparison and candidate surface

Both projects compile the exact `DefaultKeycloakTransactionManager.java` source
from Keycloak 26.8.1 commit `24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b`.
The native manager control is unmodified. The candidate changes **two catch
sites** in the ordinary and after-completion rollback participant loops: retain
the first runtime exception, attach later distinct exceptions as suppressed,
and continue attempting the remaining participants. It does not change the
prepare list, commit branches, tracing contract, session/provider close,
transaction outcome persistence or any database operation.

Both projects retain the earlier one-line realm-denial overlay and reuse its
hash-verified original fixtures. For its one swallowed-failure assertion only,
the temporary test copy now explicitly compares the native versus candidate
observed-fault result. The original test, failed expectation, unfinished
participant assertion and failed complete-cleanup gate are preserved. This
oracle comparison is recorded in the preparation receipt; it does not redefine
cleanup success or edit the earlier lab's source.

**155 test cases pass per variant (310 total), zero skips:** 25 new lifecycle
cases, 96 reused realm/lifecycle cases and 34 reused actual native-authentication
controls each. The native control preserves the swallowed participant failure;
the candidate propagates it to native session close and the directly invoked
minimal mapper. Both retain the fixed denial, actual authentication failures and
missing-account non-creation. No workload credential/token is acquired or issued.
Six preparation controls reject manager/reused-input drift, symlinks, wrong mode,
output in the source tree and replacement of existing output.

## Qualified observations and explicit remaining failures

| Path | Native control | Candidate and qualification limit |
| --- | --- | --- |
| First/last/multiple failures in ordinary or after-completion rollback loops | A null initial accumulator can swallow the failures. | First callback runtime failure propagates; later distinct failures are suppressed in tested order. Remaining participants are attempted. Self-suppression is avoided. Failed participants remain unfinished. |
| Prepare commit fails, then rollback callbacks fail | Later rollback failure replaces the original prepare cause in this control. | Original prepare failure is retained with later rollback failures suppressed. No prepare/database cleanup contract is added. |
| Native session close and thread-bound close helper | Can report closed with no propagated participant failure. | Candidate failure reaches the caller/mapper; native close still reports closed and failed participant remains unfinished. This proves observability only. |
| Prepare participant on direct rollback | Synthetic prepare participant is not rolled back. | Unchanged. Real prepare callbacks include no-op and cache/provider-specific behavior; classification and actual-provider proof remain required. |
| Main commit fails, after-completion rollback also fails | Main failure propagates, later rollback error is logged without inclusion. | Unchanged separate commit branch. Candidate does not prove complete failure aggregation or atomicity. |
| Tracing lookup throws, returns null, throws around a callback or drops the callback | Can skip rollback; completed/active/participant states differ. | Lookup still fails before the loops. The candidate exposes some errors caught by the loops but cannot make an unexecuted callback roll back. A silent dropped callback remains undetected. |
| Provider close throws | Error is logged; later providers are attempted and session can report closed. | Unchanged. Provider resource release and complete close-failure propagation remain unproved. |
| Primary exception disables suppression | Later details are unavailable. | Candidate returns the primary error but cannot retain later errors using disabled Java suppression. |
| Rollback retried on completed manager | Remaining unfinished work is not retried. | Unchanged; no recovery/retry protocol or durable outcome follows. |

These tests use real native manager/session/transaction code and synthetic
in-memory participants, with context/provider boundaries controlled by the
fixture. They use `JTAPolicy.NOT_SUPPORTED`; no JTA coordinator, JDBC, PostgreSQL,
Infinispan store, federation, actual tracing/export provider or HTTP server is
executed. A counter recording zero commits, a returned exception, inactive
manager or closed session is **not durable rollback proof**.

The [review](../../rollback-lifecycle-review.json) pins 13 source units covering
actual session close, direct callers, prepare registrations, rollback-driven
jobs and async response handling. Those source references are not a resolved
transitive callgraph or qualification of the actual provider/job/HTTP behavior.
The [lifecycle containment review](../../../../../docs/architecture/keycloak-lifecycle-containment.md)
now defines the proposed outcome/participant contract and ten open core-change
or exclusion gates. Next is an integrated native abort/close outcome comparison;
actual provider/SQL/JTA/HTTP and admission/storage qualification remain open.

## Reproduce in owned temporary projects

Keep this directory beside both `realm_entry` and `entry_guard`. `inputs.json`
pins the native manager and all reused source/oracle/recipe bytes. The recipe
verifies them before output; it does not download, run Maven or modify vendor
source. No upstream source, JAR, JDK or built binary is redistributed here.
Use the exact separately reviewed archive from the
[feasibility review](../../../../../docs/architecture/keycloak-issuer-feasibility.md),
an owned JDK 21 and Maven 3.9.11. Recorded execution used Temurin 21.0.12.1+1.

```sh
python3 prepare.py /path/to/keycloak-source /path/to/new-native-project native
python3 prepare.py /path/to/keycloak-source /path/to/new-candidate-project candidate
```

Use a new Maven home/cache, credential-free explicit settings mirroring only
Maven Central and no injected Java/Maven options. Resolve the classpath and verify
it with `../entry_guard/verify_sdk.py`. All 206 SDK/test-classpath and 290 build/SDK
JARs matched the previous reviewed coordinate/hash/license set. The two historical
build-helper license declaration gaps and deprecated test-only native API remain;
this supplies no production security/distribution/license clearance.

Run `test` in each prepared project with the same explicit settings/cache and
`-DentryGuard.guarded=false -DrealmEntry.guarded=true`. Set
`-Drollback.candidate=false` in the native project, `true` in the candidate. Use
offline mode after reviewed build plugins are cached. The final JVM uses
reflection-only doubles with dynamic agent loading disabled. Expected synthetic
error traces stay in private reports. Remove owned projects/cache/extraction
when done. Never `install`, `deploy` or copy output into a providers directory.

## Gate state

The candidate passes the **limited participant-loop runtime-error propagation
controls**. Full lifecycle cleanup/containment stays failed/unproved, as do HTTP
mapper/filter/serialization/async/disconnect behavior, issuer-primary bootstrap,
A0/A1/A2 admission, all 22 writer categories and native signing/response durability.
All earlier 18 witnesses/nine failed latest-at-response gates, R1 limits/earlier
503, semantic contract review, R3–R7 and IAM/service-restoration requirements stay
open. No existing application/provider artifact, guard, grant, caller, schema,
migration, runtime dependency, manifest or default changes follow. Temporal,
`case_runtime` and deferred engine-replacement governance remain unchanged.

The subsequent [integrated native abort comparison](../native_abort/README.md)
retains this lab unchanged as native/limited controls. Its 512-case result
improves scoped deny/error observation but preserves four containment failures;
full cleanup and all provider/SQL/JTA/HTTP/admission gates remain unqualified.
