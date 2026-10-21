# Native session, job, context and response ownership qualification

**Bounded source/native qualification result: NO-GO for mandatory pre-effect
ownership or an enforceable exclusion.** This review adds no new native candidate
patch. The [earlier abort experiment](../native_abort/README.md) remains a control,
with all four containment gaps retained. The
[proposed lifecycle contract](../../../../../docs/architecture/keycloak-lifecycle-containment.md)
and [ADR 0004](../../../../../docs/architecture/decisions/0004-issuer-core-storage-and-compatibility.md)
remain research only. No protected issuance, production fork, provider installation,
admission storage or weaker authority contract is adopted.

## Exact native execution and controls

**578 cases pass, zero skips**, plus six preparation rejection controls. The native,
limited and integrated-control projects pass 182, 182 and 214 cases respectively.
They rerun all 512 earlier cases unchanged and add 22 ownership cases per variant
(66 total). A passing suite includes deliberate negative outcomes; it is not a
passing mandatory-ownership, cleanup, SQL or HTTP gate.

Seven additional exact native units compile: KeycloakModelUtils, SessionLookup,
RequestContextHelper, ScheduledTaskRunner, NamedSessionTask, abstract
DefaultKeycloakSessionFactory and DefaultKeycloakContext. The earlier five native
core units and its native/limited/integrated variants remain. Class-location checks
require the compiled source, not replacement fixture algorithms. The new source
is unmodified in all variants; only the earlier research overlays remain.

Factories returning sessions, model providers/objects, tracing fault injection and
AsyncResponse are controlled synthetic boundaries. Job context setters, job/helper/
scheduled-runner and core transaction/session code actually execute. This does
**not** execute the concrete Quarkus factory, augmentation/provider discovery,
HTTP stack, actual timer, native security-cleanup business action, database/JTA,
cache, tracing exporter or real credential/token/data dispatch. Synthetic commit
counters are not durable commit or rollback proof.

| Native observation | Qualification consequence |
| --- | --- |
| Job creates a session, sets request context, begins the transaction, clones realm/client models, then invokes the job body. | An ownership check in the body is too late for the preceding model reads and initialization. Source must establish the boundary earlier. |
| Native job saves and restores the previous thread session, including ordinary job/factory/model errors and nested jobs. | This is distinct from the generic close helper, which clears it. Thread context restoration does not confer authority. |
| Explicit generic close inside the job clears context and closes the session; the implicit second close still throws, while job finally restores the parent. | Restored context and failed lifecycle completion coexist. One verified close/response owner is still missing. The initial successful-return assumption is retained as failed evidence. |
| Actual after-rollback helper opens a fresh child transaction and commits its synthetic effect. After-completion helper does so on both parent outcomes; after-rollback helper does not do so on parent commit. | This strengthens the earlier direct-child witness using the real helper. Independently authorized security/business effects must be classified, not silently dropped. |
| Partial native begin can leave an earlier participant STARTED without rollback; logged provider-close failure can coexist with a returned job result. | Closed/inactive/returned flags do not establish complete cleanup or durable outcomes. |
| Scheduled runner uses the native job lifecycle. Job errors can be logged without an outcome return; tracing lookup is outside its catch. An adversarial tracing provider can drop the task callback. | No verified success or complete diagnostic outcome follows from normal return. This is not an observed defect in the real OTel exporter, which was not run. |
| Actual async response resume happens before a later after-completion failure; false resume return is ignored while the job can return normally. | Completion-list membership is not a global release barrier or delivery receipt. No actual HTTP or usable token is exercised. |
| A worker has its own thread context and can run the native job with copied model context, without an owner check supplied by this helper. | Copied realm/client context is not authenticated operation authority; fresh-session admission remains required. |

The four earlier witnesses remain unchanged: unbound child commit, native error
response resumption before outer close, undetected loss of nested parent context
in generic close, and late attachment leaving active work unfinished/unknown.

## Source and activation review

The [source record](../../session-ownership-review.json) pins **33 source/interface/
assembly units and 63 literal anchors** to Keycloak 26.8.1 commit
`24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b`. The independently verified archive
SHA-256 is `f67ec723e2eaf46b2d38f167ecb7578964115f1f2ce203f9b6659322223d9874`.
A separate search found 80 matching lines in 56 files under five roots, including
comments/tests/declarations. Neither inventory is a complete transitive/dynamic
callgraph. Matching earlier source pins and class-location tests do not qualify
selected runtime provider/build activation.

The base factory is **abstract and does not implement create**. The reviewed
Quarkus factory creates a concrete Quarkus session; its context is constructed
inside the session constructor. CDI lazily creates sessions, the invocation chain
begins transactions, and disposal/close/async paths complete them differently.
Recorder/processor code connects factory creation and the custom handler chain.
A test factory returning native sessions cannot prove mandatory Quarkus activation.
A constructor-time carrier without a resolved, verified target is not A1 realm
admission. The authoritative primary admission lookup is still missing.

## Required coherent core boundary before another candidate

These are **design prerequisites, not implemented hooks or new architecture
acceptance**. They refine the existing LC/A0/A1/A2 gates rather than replace them.

| Boundary | Concrete required change or enforceable exclusion |
| --- | --- |
| Session birth and build identity | Cover the actual concrete factory, native constructor/context/provider initialization and all new/internal session paths. A0 must restrict the immutable build/provider/factory set. A pre-effect operation carrier alone grants no realm authority. Unknown implementations cannot enroll. |
| Primary admission and job entry | A1 must resolve exact authoritative realm/incarnation/recovery/profile/revision state before ordinary model/context cloning and protected reads. Put mandatory checks in native creation/job entry before begin/clone/body as required, with explicit bootstrap ordering. Absent rows, caller hints and inherited ThreadLocal state cannot classify unmanaged authority. |
| Semantic participant and job registration | Distinguish resource release, protected writes, independent security/business jobs, external dispatch and response intentions. Enforce ownership before registration/initialization and effects; the stock phase lists alone are insufficient. No unproved callback whitelist or blanket suppression after effects have started. |
| Parent/context/close ownership | One owner must cover normal job finally, direct close, CDI/invocation/async disposal, foreign/reentrant/new workers, partial begin/enlist, error masking and verified parent restoration. Record unknown release/commit outcomes and never replay them automatically. |
| Response ownership | Mediate response intentions until the complete required outcome/durable barrier; handle false resume, cancellation, duplicate release, serialization/disconnect and later callback/provider failures. The native async callback is not that barrier. Deny unqualified protected async/streaming paths before resource/provider/read/dispatch effects, with actual activation proof. |
| Required cleanup compatibility | Preserve native code/session revocation, logout, authentication-session removal, UMA tickets, cache DB-update retries and lock release. Give independent jobs fresh scoped authority and writer participation. A pre-admission no-store denial differs from an admitted authentication failure that legitimately requires security cleanup. |
| Runtime and recovery proof | Qualify actual Quarkus/provider/HTTP/JTA/JDBC/PostgreSQL/Hibernate/cache/HA/error/restore/recovery behavior and every required entry/writer. No finite outcome object, closed flag, source matrix or synthetic counter creates durable fencing or recovery authority. |

Actual source examples matter: authorization-code reuse detaches client sessions;
refresh/logout/revocation and password-grant failures register cleanup; code
invalidation runs a fresh job; UMA permissions create independent tickets; cache
updates can retry separate transactions. Blocking/locking brute-force callbacks
also release thread/map/semaphore state. Suppressing every after callback would
change security behavior or strand resources. No feature is retired by this result.

**Stop further optional-hook/local-catch candidate work.** Mandatory pre-effect
ownership and enforceable exclusions have not been demonstrated. The subsequent
[coherent core design](../../../../../docs/architecture/keycloak-lifecycle-containment.md#coherent-core-patch-design)
now records those proposed seams, logical primary interfaces, participant/job
semantics, response/close ordering, compatibility and proof prerequisites. It
does not rerun or change this lab's historical results. Next research qualifies
only a mandatory A0 session-birth deny gate with exact native/Quarkus prerequisites;
it cannot grant primary admission or operation authority. The subsequent
[preflight record](../../session-birth-preflight-review.json) stops before a candidate
because actual native augmentation/provider initialization inputs remain
unqualified. The prototype stays open. The subsequent
[seed-input review](../../augmentation-input-review.json) statically inspects
POMs/JAR metadata and proposes the effect-disabled harness. It establishes no
effective input/provider/isolation or A0 gate; close those prerequisites before
returning to a candidate. Neither review reruns or changes this lab's historical
578 cases/six controls, source, oracles or failure results.
Do not invent physical tables, recovery stores or automatic compensation/replay;
R3 snapshots/R4 conditional grants/storage implementation remain NO-GO. Production
fork/version/deployment still need a later decision and qualification.

## Reproduce in disposable projects

Keep `session_ownership` beside the unchanged `native_abort`, `rollback_lifecycle`,
`realm_entry` and `entry_guard` labs. `inputs.json` pins all added native units and
reused fixture/recipe bytes before output. The recipe copies source; it does not
fetch, run Maven, install a provider or implement a new core patch.

```sh
python3 prepare.py /owned/keycloak-source /owned/new-native-project native
python3 prepare.py /owned/keycloak-source /owned/new-limited-project limited
python3 prepare.py /owned/keycloak-source /owned/new-integrated-project integrated
```

Use the exact reviewed JDK 21/Maven 3.9.11, new Maven home/cache, explicit
credential-free Maven Central mirror settings and owned per-project Maven/JVM
temporary directories from the [earlier lab](../native_abort/README.md). Recorded
JDK is Temurin 21.0.12.1+1. Verify the same 206 SDK JARs using
`../entry_guard/verify_sdk.py` and all 290 SDK/build JAR hashes/coordinates/licenses.
The two historical build-helper license declarations and deprecated test-only API
remain qualification limits; no runtime dependency or distribution is adopted.

After resolving reviewed build inputs, run offline `test` with
`-DentryGuard.guarded=false -DrealmEntry.guarded=true`. Native uses
`-Dabort.mode=native -Drollback.candidate=false`; limited uses
`-Dabort.mode=limited -Drollback.candidate=true`; integrated uses
`-Dabort.mode=integrated -Drollback.candidate=true` and quoted
`-Dtest=*Test,AbortCandidateCases`. Retain reflection-only/dynamic-agent-disabled
JVM settings. Six controls reject native drift/symlinks, mode drift, output inside
source, prior-control drift and replacement of existing output. Remove only owned
extraction/projects/cache/temp state after retaining reports. No binary is shared.

Initial synthetic mock setup errors were corrected. Initial evidence also exposed
native double-close failure; the final new case explicitly records that failure
and parent restoration instead of asserting successful lifecycle completion. All
512 earlier control/oracle sources remain unchanged; raw initial reports remain
private. No model/provider/SDK runtime or ownership acceptance follows from the
passing expected-negative cases.

All earlier 18 witnesses/nine failed latest-at-response gates, R1 limits/earlier503,
semantic point-in-time review, LC-01–10/A0/A1/A2/R2 implementation/R3–R7, complete
entry/writer closure, actual claims/grants/custody/tenant/data/upgrade/restore and
caller-adoption gates stay open. IAM ITDR/SCIM/user/JIT and every service/source/
data/action/approval/SoD/audit/durability/recovery/verification restoration remain
requirements. No MCP operations, production application/provider code, artifact,
schema, runtime dependency/default, IAM guard, caller, lease or metadata changes.
Temporal, case_runtime and deferred engine-replacement governance remain unchanged.

The [selected metadata review](../../../../../docs/architecture/keycloak-lifecycle-containment.md#selected-metadata-ancestry-and-child-model-input-plan)
closes the original 121 POM gaps and static parent/root-BOM ancestry within the
bounded selection. The 456-POM input plan covers 265 target GAVs; the expanded
child-model driver has not run. Next qualify that offline model-only expansion
with the existing six libraries and all integrity/effect controls. Full transitive
input closure, native issuer isolation and A0 remain open.
