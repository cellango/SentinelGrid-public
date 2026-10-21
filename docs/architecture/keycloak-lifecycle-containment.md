# Issuer lifecycle containment and participant contracts

Status: **proposed qualification contract; source review complete, implementation
and runtime qualification open**. This is bounded research under
[ADR 0004](decisions/0004-issuer-core-storage-and-compatibility.md), not production
patch adoption. It defines the lifecycle work required by the
[native admission design](keycloak-native-admission.md). It selects no physical
schema, recovery store, issuer deployment or new public response contract.

The [rollback comparison](../../infra/keycloak/keycloak_registration_connector/qualification/rollback_lifecycle/README.md)
proved limited error observation with synthetic participants: 155 cases per
variant, 310 total, six input controls. It did not finish failed rollback work.
Those are inherited results, **not tests rerun for this source/design review**.
Full lifecycle cleanup, durable rollback, R2 implementation and R3/R4 stay NO-GO.

## Evidence and review boundary

The original [source record](../../infra/keycloak/keycloak_registration_connector/lifecycle-containment-review.json)
pins **39 source/registration units and 80 literal anchors** to Keycloak 26.8.1
commit `24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b`. Its archive SHA-256 is
`f67ec723e2eaf46b2d38f167ecb7578964115f1f2ce203f9b6659322223d9874`.
All 13 earlier source pins match. A separate literal search found 59 matching
lines in 34 files under the five reviewed source roots, including declarations,
comments and a test. These counts are an inventory, **not dynamic/transitive
closure or a total participant count**. SDK and framework internals, other
modules, feature combinations, custom providers and indirect dispatch need
separate proof. No issuer, database, JTA coordinator, cache, tracing exporter,
background job or HTTP stack was executed in this review.

References below resolve to the immutable source commit. A source dependency or
service declaration does not establish the selected runtime implementation.

| Native surface | Observed semantics and qualification consequence |
| --- | --- |
| Manager prepare/main/after lists ([S01]) | Prepare `commit` callbacks run before main `commit`; this list is not evidence of database two-phase prepare. Begin/enlist can begin participants. Direct rollback traverses main and after lists, not prepare. A blanket additional prepare rollback would change contracts without proving cleanup. |
| Manager failure branches ([S01], [S03]) | Prepare failure invokes rollback; main commit failures do not undo successful earlier commits and later main callbacks are still attempted. After callbacks commit only without a main error; their rollback errors on the main-error branch are logged. Completion is marked before tracing/participant calls. A failed abstract participant can remain STARTED; repeated manager completion returns without retry. |
| Native session close ([S02]) | An active unmarked manager commits by default. `isActive` is queried outside the close-transaction catch. Runtime transaction errors are retained, provider close Exceptions logged, and invalidation can throw independently. The closed flag is set in the provider/invalidation finally, not a durable outcome certificate. Trace logging itself queries transaction state before this work. |
| JPA authentication sessions ([S04]) | Prepare commit persists remaining transient authentication-session entities using the session entity manager; prepare rollback and provider close do nothing. Real database rollback belongs to the owning resource transaction. A no-op here is not evidence that a required DB rollback was skipped. |
| Realm and authorization caches ([S05], [S06]) | Prepare adapters establish shared flags; the paired after callback invalidates on commit and rollback and ends revision batches in finally. These pairs need joint semantics, actual cluster effects and failure tests; do not run both callbacks twice by list name. |
| Session cache transaction factory/provider ([S07], [S08], [S09]) | Prepare participation depends on configuration and observed DB isolation. `prepareStep` can lock/move writes into the current transaction and dispatch cache work. After commit can run new DB-update jobs with backoff and await cache stages; rollback joins registered rollback stages. Clearing the provider list on close does not prove those operations completed. |
| Rollback-driven jobs ([S10], [S11], [S12], [S13]) | Code cleanup opens a fresh transaction on rollback. Utility after-rollback/after-completion helpers open independent transactions with cloned realm/client context. Token invalidation/logout and UMA ticket creation use these helpers. They intentionally retain security/business effects across parent rollback; a blanket no-op would change required features. Cloning resolves models before the job body. |
| Direct rollback callers ([S21], [S22]) | Broker and bootstrap paths call the manager directly. Changing only session close misses these callers and their subsequent error/rendering behavior. They need the same outcome contract or an enforced exclusion. |
| Async response and SAML worker ([S14], [S33]) | An after callback resumes a success response on commit; rollback preserves an error response or constructs an ErrorPage. SAML artifact work resolves realm/providers and dispatches HTTP before registering response completion. A callback in this list is not a global barrier after every other callback/provider close. |
| Response close, invocation and CDI disposal ([S15]–[S19], [S31]) | The normal filter closes before returning, but Stream closes via onClose and StreamingOutput closes after writing. The source warns the filter may not run after connection closure. Invocation handles listed async types separately; CDI disposal is fallback close. The shared close helper clears thread context in finally, while job utilities restore the prior context. Runtime ordering, cancellation and body handling remain unproved. |
| Error mapping ([S20]) | The general mapper marks rollback, then may read request context and resolve realm/theme/locale/providers for HTML. It is unsuitable as an unqualified pre-admission denial path. Failure to mark rollback cannot safely enter default native close. |
| JTA, JPA and entity-manager lifecycle ([S23]–[S28], [S34], [S37]) | JTA wrapper suspends/restores an ambient transaction; a finally/resume error can mask an earlier outcome. Resource-local JPA transaction code is a separate source path, not proof it is the active Quarkus path. Quarkus creates synchronized entity managers; provider close delegates to their close. Actual pool/coordinator/driver/enlistment and failure behavior require runtime evidence. |
| Durability optimization ([S26], [S38], [S39]) | Quarkus can register Hibernate async-commit listeners; the PostgreSQL implementation can set transaction-local synchronous_commit off. Source includes rollback completion callback cleanup. Neither manager return nor a JDBC acknowledgement proves the durability required by the protected profile. Exact enabled listeners, entity classifications and DB policy need qualification. No setting is changed here. |
| Tracing and event delivery ([S29], [S30], [S32], [S35], [S36]) | No-op tracing invokes the callback directly; OTel starts a span before it and records/ends around it. Synthetic dropped-callback tests are adversarial controls, not an observed OTel defect. Lookup/start/error/end/logging failures must not own whether required rollback runs. Event queue commit dispatches consumers; rollback clears queues. Delivery/audit and transaction durability are distinct outcomes. |

## Proposed outcome and ownership contract

Keep independent, monotonic facts for each operation. These are logical fields
for qualification, not a new API, database schema or durable authority ledger.
Unknown facts cannot be promoted by a successful catch, a returned error, an
inactive manager, a closed session or zero synthetic commit counters.

| Axis | Required distinctions |
| --- | --- |
| Protected effects | Not started with proven absence of effects; started with rollback requested; rollback completed with resource evidence; commit started/outcome unknown; committed with required durability evidence. A partial main commit is not rollback completion. |
| Participant work | Not called; called once and returned; failed; completion unknown. Record phase, owner and semantic role; callback return alone does not establish its external effect. |
| Resource release | Each owned resource release attempted/completed/failed/unknown; do not infer this from transaction status. Independent resources may continue cleanup only where their contract permits it. |
| Context ownership | Exact operation/session/thread identity, parent frame, reentry/foreign use, and verified restoration/clear outcome. A copied context is not new-session authority. |
| Response ownership | Unreleased; release attempted; bytes possibly released; completed or delivery unknown. Never claim delivery or retract bearer bytes after uncertain release. |
| Failure evidence | First operation failure plus ordered secondary failures with phase/participant identity, independently of Throwable suppression. A bounded overflow indicator makes completeness unknown; it must not overwrite the primary error or imply success. |

One issuer-owned lifecycle coordinator must arbitrate abort, close and response
release for the protected operation. This is a **required core capability**, not
a wrapper already supplied by the current provider. Admission and authorization
remain separate: no outcome object, context marker, catch wrapper or ThreadLocal
grants enrollment, target access, a writer fence, credentials or token issuance.

- Abort intent becomes terminal before invoking fallible tracing, logging, status
  checks, marker/provider callbacks or error rendering. If rollback-only cannot
  be established or queried, prohibit ordinary default-close/commit through a
  reviewed core path. Catch-and-call-close on the current session is insufficient.
- Own the selected native session and resource transaction explicitly. Cover
  begin/enlist partial failures, inactive/completed manager states, null/status/
  marker failures, close and invalidation errors. A failed or unknown participant
  remains so; do not reset completed or automatically replay it.
- Preserve the first failure, every bounded secondary record and any overflow
  outside suppression. Same Throwable identity, disabled suppression, trace/end/
  logging/close/resume failures must not erase earlier evidence. Fatal VM failures
  cannot promise cleanup; retain unknown outcome and withhold success.
- Required callbacks execute at most once per owned attempt independently of
  whether an observational trace wrapper calls, skips, repeats or throws around
  its callback. Do not rerun after a possible effect. Actual supported tracing
  implementations and exporter failure paths still need tests.
- Execute only the classified cleanup/compensation work. Prepare-list membership
  alone grants no rollback mandate. Cache invalidation, independent security
  transactions, external dispatch, event delivery and response resumption require
  their own ownership, ordering and outcome proof. Preserve required revocation,
  invalidation and existing IAM behavior; unqualified profiles stay unavailable.
- A new/nested job/session reacquires issuer admission and operation authority
  **before context cloning/model reads**. Classify every independent write,
  callback and retry under the protected writer contract. Reentry must not reuse
  stale state; foreign-thread/session use denies before effects. Restore only the
  verified owning parent frame; always attempt clear/restore and record failure.
- No automatic retry, compensation, force-close success, new quarantine table or
  recovery store follows. Unknown resource/commit outcomes require explicit
  operational containment and independently verified recovery before reuse.
  The enforcement mechanism and recovery authority remain prerequisites. Logging
  an incident, setting an in-memory flag or removing a node alone is not durable
  multi-node fencing or proof that cleanup completed.

## Denial, uncertain effects and response release

Before admission, a denial path may use only deployment-level fixed bounded
metadata and fixed non-enumerating no-store output. It must avoid realm/theme/
locale/EventBuilder/provider resolution, credential access and all signers. It
must not recursively enter the generic HTML mapper. Prove this before any
protected participant initialization; otherwise classify existing work and run
the abort contract. A static route hint or missing enrollment record is not proof
that effects are absent or that the realm is unmanaged.

A known failure and an unknown rollback/commit outcome both withhold successful
issuance and downstream dispatch. A minimal denial may be released only after
its path cannot resume ordinary managed work or default commit. It must **not**
claim cleanup or undo; if that barrier cannot be guaranteed, terminate the owned
response/connection without a success body and keep containment failed. Exact
HTTP code, mapper precedence, body reading, disposal and disconnect enforcement
remain runtime tests, not an adopted wire change.

For admitted successful work, response release needs a single barrier after
native authentication, target authorization, complete participating transaction
outcomes, durable attempt/fence commit and required release checks. Retain
issuer-native signing. Independent callback failures after an earlier durable
commit are reported as partial/uncertain completion, not invented rollback.
A crash or serialization/disconnect after commit may consume an attempt without
delivery; do not replay stored token bytes or retry an uncertain effect.

Initial protected acquisition must enforce exclusion of async/streaming/native
resume and effectful independent jobs until their authority/transaction/response
contracts are qualified. This is a **proposed scoped exclusion**, not implemented
or proven by a flag. Block before provider construction, protected reads and
external dispatch; validate the immutable build/profile and exercise negative
paths. Ordinary supported features and their migration requirements remain;
no global disabling, silent retirement or blanket admin/error exemption follows.

## Required core changes or enforceable exclusions

Each row is a proposal with an open acceptance gate. The two-site rollback
experiment supplies evidence for part of LC-02 only.

| ID | Required surface and acceptable treatment | Evidence needed before acceptance |
| --- | --- | --- |
| LC-01 | Manager begin/enlist/commit/abort plus direct callers: terminal abort intent and independent outcome facts; deny native default commit after a failed marker/status check. | Partial-begin/enlist, direct/session close, reentry/completed, first and later commit failures; original native control retained. |
| LC-02 | All manager failure branches, provider close/invalidation/JTA resume and diagnostics: bounded independent error collection. | First/secondary ordering, same instance, suppression disabled, overflow, trace/logging faults and fatal outcome limits. No silent log-only success. |
| LC-03 | Prepare/main/after semantic registration and provider activation: classify paired/no-op/resource/independent job/response roles; do not blindly add a rollback loop. | Actual selected JPA/cache/provider contracts, ordering and fault tests; unclassified providers denied before activation. |
| LC-04 | Manager tracing and lifecycle instrumentation: required work cannot depend on an observational callback. | Lookup/null/before/after/drop/repeat/recursive callbacks; at most once and no masked original failure; actual supported tracing providers separately tested. |
| LC-05 | Session transaction close, provider release, invalidation and context cleanup: owned abort path and complete outcome reporting. | Failed status/marker/isClosed/close/provider/invalidation/clear/restore; no automatic commit fallback, resource re-use or success from closed flag. |
| LC-06 | Model job helpers, rollback-driven tasks, cache DB retries and direct internal jobs: fresh pre-read authority and explicit independent-effect contract, or enforced profile exclusion. | Real cloned-context paths, nested/new/foreign sessions, retry budgets and committed child effects; security cleanup preserved. |
| LC-07 | Response filter/invoker/CDI/async callbacks/error mapper: one release/abort owner, fixed pre-admission failure path; initial async/streaming exclusions enforced. | Actual framework mapper/filter/body/serialization/cancel/disconnect/disposal order, duplicate close/resume and zero usable bearer bytes before durable barrier. |
| LC-08 | Actual JTA/JDBC/PostgreSQL/Hibernate/entity-manager/cache participants and durability policy. | Coordinator/driver failures, pool release, partial commit, async-commit listeners, rollback completion, crash/restart/partition and HA evidence. Resource-local fixture cannot stand in for Quarkus JTA. |
| LC-09 | Immutable build/provider/feature admission and all native front doors/writers. | A0/A1/A2, earlier 18 entry families/10 grants/13 locator variants and all 22 writer categories participate or are enforceably excluded before effects. Literal inventories remain incomplete. |
| LC-10 | Recovery, replay and operator handling of uncertain state. | Authorized durable containment/recovery mechanism, fresh epoch after restore, independent verification, no automatic replay; no new physical schema selected here. |

## Coherent core patch design

This revision adds a source/design plan across **50 pinned units and 104 literal
anchors** in the [core design record](../../infra/keycloak/keycloak_registration_connector/core-lifecycle-design-review.json).
All 33 pins from the session-ownership review were reverified. Counts describe
reviewed source, not transitive closure, compiled activation or runtime proof.
The inherited 578 cases/six preparation controls were **not rerun** for this
documentation change. No candidate, build input, production code or schema is added.
All mandatory admission, cleanup and response-exclusion gates remain **NO-GO**.

### Authority before ordinary session work

The following interfaces and states are **required new logical contracts**.
They are not existing Keycloak APIs, implemented storage or authorization receipts.

| Stage | Required input and result | Failure and ordering rule |
| --- | --- | --- |
| A0 build and bootstrap | An independently verified immutable artifact/provider/factory/feature set and exact core activation identity. | Verify before loading or constructing privileged plugins, and recheck before factory init/postInit. A plugin already loaded can execute server-privileged code; this design is not a plugin sandbox. Unknown build stays unavailable. |
| A0 restricted session birth | Core-owned identity for exact factory/session/operation/thread and verified parent, created before manager/context/logging initialization. | Creates only a `BORN_RESTRICTED` shell. No realm/model/provider/auth/write/signing authority. Cover constructor, concrete factory, internal/worker/CDI creation; a later attach hook is insufficient. |
| A1 `readPrimaryAdmission(selector)` | Bounded untrusted realm name/UUID/issuer hint used only to locate exact authoritative realm UUID/incarnation, recovery incarnation, enrollment state, immutable profile version and non-wrapping revision. | A minimal issuer-primary scalar adapter must not resolve normal models/cache/providers or recursively create a session. Missing, duplicate, stale, inaccessible or unsupported state is `UNKNOWN`, never unmanaged. No credential/token is an input or result. |
| A1 classification | `MANAGED_PENDING_AUTH`, authoritatively `EXPLICIT_UNMANAGED`, `MAINTENANCE_CLOSED`, or `UNKNOWN`. | Classification grants no operation permission. Protected normal model/auth-dependency reads require revalidation inside the same issuer-primary durable scope/fence; an earlier lookup/TTL/independent lease leaves a race. This is not the R3 association snapshot. |
| A2 bounded native-auth scope | Server-owned operation definition and exact target identity permit only reviewed native-auth dependencies/counters, under the applicable writer boundary. | Native client authentication and target authorization still precede acquisition. Authentication side effects are classified, not exempt. Never provision/repair a missing account or mapper as a fallback. |
| A2 fixed authorized scope | Verified native principal, exact target tenant UUID, operation/profile and current primary authority. | Only then allow fixed protected work/native signing with the shared writer/attempt scope. Admin principal realm and operation target are distinct; no master/admin/public/error bypass. Cross-realm combinations stay unavailable until qualified. |

The logical `openBootstrapPrimary(reviewedBuild, maintenanceOwner)` contract must
return only a trusted issuer-primary scalar-read/resource owner, or fail closed.
Both inputs must be established by reviewed deployment/maintenance authority,
not request fields, an extension-supplied object or a fabricated receipt. It
cannot grant model/auth/write/signing access or declare serving ready. Mapping,
connection acquisition/release and recovery-state validation still need separate
source and runtime qualification; this name does not make an adapter exist.

Bootstrap is deliberately separate from a request: verify artifacts without
executing unreviewed provider code; establish a narrowly trusted issuer-owned
primary adapter; enter all-node maintenance for required issuer-native mapping/
migration work; classify existing realms explicitly; run only reviewed bootstrap
initializers/jobs; open serving only after authority/recovery verification. A
bootstrap boolean is not authority. A job needing models needs its own reviewed
maintenance or operation contract. The primary bootstrap adapter, trusted
connection lifecycle, scalar query, mapping and durable scope are **missing
implementation prerequisites**. Neither app DB credentials, a second authority
database, an in-memory map nor a caller hint fills that gap. No physical table,
lock primitive or transaction implementation is chosen by this design.

The concrete factory is `QuarkusKeycloakSessionFactory.create`, not the abstract
`DefaultKeycloakSessionFactory` ([D01], [D02], [D03]). Its constructor initializes
provider factories; the recorder/processor select and assemble them ([D18],
[D19]). `DefaultKeycloakSession` constructs its manager and virtual context then
logs; Quarkus creates a framework context ([D04], [D05], [D06], [D16]). Birth must
precede these steps, and provider/model overloads must enforce subsequent scope
**before** `providerFactory.create`, datastore access or invalidation ([D05]).
Review Java static/instance initializers and superclass/virtual dispatch as well
as constructor bodies. A body guard cannot run before earlier JVM initialization;
the verified build/classloading boundary must precede privileged static code, and
earlier instance initialization must be proven effect-free or moved behind birth.
Failure to establish that order is NO-GO, not a constructor-fixture pass.
The permissions constructor assigns fields ([D34]); that observation does not
qualify later permission methods or arbitrary context/provider constructors.

### Lifecycle transitions, ownership and failures

| Transition | Required owner action | Failure result |
| --- | --- | --- |
| `BOOT_CLOSED` → `BORN_RESTRICTED` | A0 verifies activation and allocates an internal exact birth/frame owner before native initialization. | Fail before native begin/context/provider effects. No synthetic admission allow receipt. |
| `BORN_RESTRICTED` → `CLASSIFIED` | A1 primary scalar classification before realm/client model resolution or cloning. | Fixed bounded denial or maintenance-closed; unknown cannot enter legacy behavior. |
| `CLASSIFIED` → `AUTHENTICATING` → `AUTHORIZED_FENCED` | Revalidate in protected scope; permit only reviewed native-auth reads/writes; authenticate and authorize exact target before acquisition. | Native auth denial can require separately authorized security cleanup. No credentials/signing on failed auth. |
| Owned operation → `FINALIZING` | Register participants/resources before fallible initialization/enlist/begin; fix commit/abort intent before status/tracing; complete classified work once. | Partial begin, failed enlist/status/marker or earlier commit stays partial/unknown. Native completed/active/closed flags cannot attest rollback or durability. |
| `FINALIZING` → `RELEASE_READY` | Verify actual durable resource outcome, required child effects, provider/invalidation release and exact context restoration; freeze private response intent. | Any required failure/unknown withholds successful response. Do not relabel an earlier commit as rollback. |
| `RELEASE_READY` → `TERMINAL` | Single response owner releases once, records delivery separately. | False resume, cancellation/disconnect or serialization uncertainty means delivery unknown; no token-byte replay. |
| Any nonterminal state → terminal abort intent | One coordinator owns rollback/release/denial; other invoker/filter/CDI/job disposers join its result. | Secondary closes cannot commit, replay or mask the first outcome. Foreign/stale/reentrant use denies; fatal/overflow outcomes stay unknown. |

These stages describe an ordering obligation, not a universal single transaction:
native authentication, declared independent security work and the protected
attempt can own separate resources. Each needs its own exact permitted effects
and scope. A restricted session may wait for classification; it cannot begin
ordinary resource work to discover whether it is protected. Preserve the native
job helper's verified parent restore, but replace generic unconditional clear and
implicit double-close with one exact frame/close owner ([D07], [D15], [D33]).
Thread switches need an explicit verified handoff, never inherited ThreadLocal
authority. A copied realm/client/request context is only data after new authority.

Keep bounded ordered failure records outside Throwable suppression: phase,
participant/owner, first/secondary errors, same-instance recurrence and overflow.
Record status/marker/trace/logger/provider/invalidation/JTA resume/context failures
independently. Diagnostics must observe required work without controlling whether
it runs, drops, repeats or reenters ([D10], [D35], [D42]). Continue independent
release only where its resource contract permits. This finite evidence is neither
durable admission, an effect receipt, recovery storage nor a proof of complete
cleanup. Unknown commit/rollback/resource release requires explicit containment
and independently verified authorized recovery; no reset, automatic retry,
compensation or fabricated quarantine record follows. The durable multi-node
containment mechanism is still unimplemented; those paths cannot qualify now.

### Participant and independent-effect migration

Every registration needs a reviewed definition binding caller, target, semantic
role, resource, phase/order, authority prerequisite and failure/retry contract.
A role enum, callback class/name or allowlist alone cannot enforce this. Migrate
both registration and actual resource/worker entry before claiming coverage.

| Native behavior | Proposed ownership and ordering; required compatibility proof |
| --- | --- |
| Resource transaction / prepare work / paired cache invalidation | Register ownership before fallible enlist/begin. Classify JPA prepare persistence and paired cache prepare/after work jointly using the earlier source record. No blanket rollback of all prepare callbacks, suppression of after lists or claim of SQL two-phase prepare from list order. Actual provider/resource/JTA/DB outcomes remain mandatory. |
| Code invalidation, token/session revocation, logout/client-session detach, password/auth-session removal ([D24]–[D28]) | Preserve each required denial/security effect. Finish the parent's known rollback/commit and release its scope before a required independent job acquires fresh A1/A2/fence and resolves/clones models. Keep parent rollback and child security commit as separate declared outcomes. Unknown parent resource/locks cannot safely launch or replay a child. |
| UMA tickets ([D29]) | Independent business transaction; fresh authority/target/writer scope and required outcome after the parent boundary. A child commit cannot be described as parent rollback undoing everything. |
| Session-cache DB updates/retries ([D30]) | Separate resource/cache stage outcomes; fresh primary authority per independent write. Retry only a specifically qualified idempotent operation within its budget after a known outcome. No generic retry of uncertain effects. |
| Brute-force thread/map/semaphore/lock cleanup ([D31], [D32]) | Exact acquired-resource release owner, even when the parent fails; retain native security counters/transactions where required. Local lock release is distinct from durable authority and must not be suppressed with write callbacks. |
| Scheduled/timer/other internal jobs ([D07]–[D12]) | Birth and fresh operation authority before begin/clone/model reads; observation cannot own task execution. Logged task error or returned result is not an independent-effect receipt. Unsupported job/provider combinations remain closed before dispatch with restoration ownership. |
| Response, event or external dispatch | Response intent is distinct from an independent effect; required audit/event delivery has its own contract. External work needs authority before dispatch, not merely registration of a later callback. SAML dispatch occurs before response callback registration ([D23]). |

Never hold the parent's realm barrier and synchronously wait for a child to take
that same barrier. Separate classified deferred work from the stock manager's
inline callback loop: finish/verify the parent's resource outcome, release its
scope, then run required independent child work under fresh authority. Keep the
parent response withheld until required child results and resource releases are
known. Parent unknown cannot be solved by waiting, dropping security work or
replaying it. Qualify recovery separately; retain feature restoration requirements
while the protected profile remains unavailable. Nested same-resource work needs
a separately qualified contract; it cannot silently become an independent child.

### Complete response barrier and exclusions

After actual native authentication, exact target authorization and fixed profile/
fence checks, issuer-native signing may prepare a **private bounded native
buffer inside the authorized scope**. This preserves the proposed ADR 0003
point-in-time semantics; it does not introduce a proxy signer or usable bytes
before durable commit. Prepare bounded serialization/rendering while models and
providers remain legally owned. After resource closure, no realm/theme/locale/
entity-manager reentry may be needed to release bytes. Discard private buffers on
error. The barrier is known durable attempt/fence outcome **plus** every required
participant/independent security effect, resource release, frame completion and
single response owner. None of those durable attempt/fence mechanisms exists yet.

`AsyncResponseTransaction` currently resumes within the after list ([D20]); that
must become a response intent, or the combination must be mandatorily excluded
before provider construction/read/work. The real filter defers stream closure
until onClose or after writing ([D21]); actual invoker/CDI/HTTP disposal needs the
same owner ([D13]–[D17]). Initial unqualified protected async/streaming/direct-resume/
worker/external-dispatch combinations stay unavailable at their earliest entry,
including before SAML worker dispatch. A late exception, endpoint flag or named
unsupported list is not enforceable exclusion. Preserve a restoration owner and
tests for every affected feature; no feature is retired globally.

Pre-admission denial uses fixed bounded no-store non-enumerating output without
realm/theme/locale/EventBuilder/provider/signing work. Do not recursively use
the general HTML error mapper ([D22]). If rollback-only/status fails, terminal
core intent must prevent native default close/commit. A minimal denial is allowed
only when no subsequent ordinary native effects can resume; otherwise terminate
the owned response and retain unknown containment. No new HTTP status/mapper
precedence is adopted here; earlier 503 and runtime limits remain. A crash or
post-commit serialization/disconnect can consume an attempt without delivery.
False resume/cancel/delivery unknown cannot authorize replay of a token or effect.

### Exact patch, dependency and proof matrix

Every row below is **proposed/unimplemented/unqualified**. Reference links resolve
to exact native source anchors; the machine-readable record includes every path,
hash and literal. P01–P10 are design groupings, not approved independent releases.
Dependencies that form a lifecycle cycle require coherent integration before a
protected profile opens. Source inventory and expected-negative fixtures cannot
substitute for mandatory before-effect activation or actual runtime proof.

| Unit / coverage | Exact native seam | Required change or exclusion | Dependencies and proof still required |
| --- | --- | --- | --- |
| P01 / A0, LC-01, LC-09, LC-10 | KeycloakProcessor.configureKeycloakSessionFactory/loadFactories/configureResteasy; KeycloakRecorder.createSessionFactory; QuarkusKeycloakSessionFactory constructor/create; DefaultKeycloakSession constructor; createKeycloakContext and DefaultKeycloakContext constructor ([D01], [D02], [D03], [D04], [D05], [D06], [D13], [D16], [D18], [D19], [D34]) | Verify build before provider class loading/instantiation, recheck activation before factory init/postInit, require restricted birth ownership before manager/context/logging construction; cover direct, internal, worker and CDI creation. Unreviewed artifact/provider/build or construction route has no serving activation; no bootstrap bypass. | reviewed immutable runtime artifact and provider closure; separate fenced maintenance/bootstrap contract. Exact constructor and concrete Quarkus factory/build negative controls, alternate constructors/subclasses/direct creation, first instruction ordering and actual augmentation/classloading proof; stop if any path can begin/read/init before ownership. |
| P02 / A1, LC-01, LC-09, LC-10 | RealmsResource.resolveRealmAndUpdateSession; RealmManager.getRealm/getRealmByName; AdminRoot.resolveRealmAndUpdateSession/authenticateRealmAdminRequest; RealmsAdminResource.getRealmAdmin; cloneContextToSession and SessionLookup constructor ([D05], [D06], [D07], [D08], [D37], [D38], [D39], [D40]) | Primary-only scalar classification before ordinary model/context reads, then fresh classification in the protected durable scope before protected dependencies; bind exact UUID/incarnations/profile/revision. Missing/duplicate/stale/unknown classification cannot fall through to legacy unmanaged access. | P01; missing issuer-primary bootstrap adapter and authority read; future proven shared durable scope/fence. Primary outage/ambiguity/rename/ABA/restore/enrollment-change races before each resolver/clone/model read; primary-only and no cache/model recursion evidence. |
| P03 / A2, LC-01, LC-06, LC-09 | TokenEndpoint.processGrantRequest and native authentication/grant dispatch; admin target resolution; model/provider/context entry and internal operation entry ([D05], [D06], [D07], [D37], [D39], [D40], [D41]) | Separate bounded native-auth dependency authority from authenticated fixed operation authority; retain real native auth, exact target authorization and account-missing non-creation before acquisition. Unknown route/grant/provider/target combination cannot construct its effectful implementation; cross-realm operations unavailable until independently qualified. | P01; P02; reviewed operation definitions and all entry/target coverage. All 18 route families/13 locators/10 grants plus unknown extensions, native auth failures, no provisioning repair, target mismatch/admin-principal-realm separation, internal callers. |
| P04 / A2, LC-02, LC-03, LC-04, LC-05, LC-08 | DefaultKeycloakTransactionManager.begin/enlist/enlistPrepare/enlistAfterCompletion/commit/rollback/setRollbackOnly; AbstractKeycloakTransaction; DefaultKeycloakSession.close/closeTransactionManager/invalidate/enlistForClose; actual JTA/JPA/entity-manager/async-commit participants ([D05], [D35], [D36], [D42], [D43], [D44], [D45], [D46], [D47], [D48], [D49], [D50]) | Own registration before fallible initialization/enlist/begin; semantic paired participants and terminal abort; outcomes independent of native flags; actual resource durability/release required. Untyped/unknown protected participant or unqualified durability policy denied before construction/effect; no prepare-list blanket rollback. | P01; P02; P03; selected runtime participant and coordinator contract. Partial begin/enlist, status/marker/completed errors, earlier commit/later failure, prepared resources, paired cache cleanup, JTA suspend/resume masking, JDBC/pool/async durability/crash outcomes. |
| P05 / A1, A2, LC-03, LC-04, LC-06, LC-08, LC-09, LC-10 | KeycloakModelUtils.runJobInTransactionWithResult/enlistAfterRollback/enlistAfterCompletion/cloneContextToSession; CodeGenerateUtil.RollbackDrivenTransaction; ScheduledTaskRunner.run/runTask; BasicTimerProvider.scheduleTask; native security/cache/brute-force callers ([D07], [D08], [D09], [D10], [D11], [D12], [D24], [D25], [D26], [D27], [D28], [D29], [D30], [D31], [D32]) | Register independent security/business intent before effect; after parent known resource completion and scope release, child reacquires fresh authority/fence before clone/read/begin/effect; explicit retry and release semantics. No child inherits admission from ThreadLocal/request context or runs while parent synchronously holds its needed barrier; unknown parent/child outcome prevents success/replay. | P01; P02; P03; P04; P06; P07; fresh child authority and writer participation. Actual rollback and completion jobs, code/revocation/logout/password/UMA/cache retry semantics, worker admission before tracing/model reads, partial parent outcomes and no parent-child fence deadlock; security cleanup preserved. |
| P06 / A0, A2, LC-01, LC-05, LC-06, LC-07 | Native session/job creation/finally; KeycloakSessionUtil; TransactionalSessionHandler.handle/close; KeycloakBeanProducer.getKeycloakSession/dispose; handler chain; CloseSessionFilter ([D03], [D04], [D05], [D07], [D09], [D10], [D13], [D14], [D15], [D16], [D17], [D21], [D33]) | Exact internal frame binds operation/factory/session/thread/parent; one lifecycle close owner; other disposers join terminal result, cannot close/commit a second time; verified clear/restore. Foreign/reentrant/stale/unowned work and unsupported worker/async transfer rejected before use; no copied context permission. | P01; P04; one owner protocol across all disposers. Generic-clear and job-restore comparison, explicit plus implicit close, nested/foreign/thread switches, fallback CDI disposal, cancellation and parent loss all independently observed. |
| P07 / A0, A2, LC-02, LC-04, LC-05, LC-06, LC-08, LC-10 | Manager/session/worker diagnostic and error paths, tracing invocation, provider/invalidation/JTA resume outcomes ([D05], [D10], [D35], [D36], [D42], [D47], [D48]) | Required work executes independently of observational callbacks; first plus bounded ordered secondary evidence independent of Throwable suppression; record unknown/fatal/overflow without success. Diagnostic failure cannot skip/repeat required work or trigger default commit; uncertain resource cannot be reused on an in-memory success marker. | P01; P04; P06; separate durable containment/recovery authority still missing. Same Throwable, suppression disabled, overflow, trace lookup/start/drop/repeat/reentry/end/log failure, provider/invalidation/clear/restore failures; actual exporter and fatal limits. |
| P08 / A2, LC-04, LC-05, LC-07, LC-08, LC-09, LC-10 | AsyncResponseTransaction.finishAsyncResponseInTransaction/commit/rollback; CloseSessionFilter.filter; invoker/CDI close; KeycloakErrorHandler.getResponse; SamlService.ArtifactResolutionRunnable.run and native signing/response producers ([D13], [D14], [D15], [D17], [D20], [D21], [D22], [D23], [D41]) | Replace direct response release with owned intent; prepare bounded private native signed/serialized buffer only in authorized scope; release after durable outcome plus required child/resource/context barrier. Initial unqualified async/streaming/SAML worker/direct response/external dispatch combinations blocked before provider/read/worker dispatch; fixed pre-admission denial avoids realm/theme/locale/EventBuilder. | P01; P02; P03; P04; P05; P06; P07; actual framework and durable attempt/fence proof. Early resume/later failure, false resume, cancellation/disconnect/duplicate/streaming/body/serialization/error mapper/filter precedence; zero usable bytes before barrier and no post-close model access. |
| P09 / A0, A1, A2, LC-01, LC-03, LC-06, LC-08, LC-09 | Every provider overload/component factory, datastore/model access, native/bulk/SQL/flush/internal/worker/config/signing path and all 22 writer categories below ([D02], [D05], [D07], [D19], [D30], [D37], [D38], [D39], [D40], [D41], [D48]) | Before protected dependencies/effects each path joins the same primary durable scope and atomic generation/fence contract or is mandatorily excluded. Endpoint flag/list or named allowlist is not enforcement; unknown provider/feature/caller fails closed at earlier construction/read/mutation seam. | P01; P02; P03; P04; P05; P08; complete transitive native/provider/writer inventory and runtime coverage. Per-category participating and excluded negative tests including AdminAPIv2/shared clients/native SCIM/feature profiles, bulk/model/SQL/import/federation and signing; selected provider identity and all nodes covered. |
| P10 / A0, A1, A2, LC-08, LC-09, LC-10 | Build/boot/provider initialization, issuer-native migration/maintenance/import/restore entry and compatibility activation ([D02], [D03], [D18], [D19], [D42], [D43], [D44], [D45], [D46], [D49], [D50]) | All-node maintenance before import/migration/operator writes; explicit inventory classification and externally replaced recovery incarnation; reconcile and independently requalify before serving. No online mixed old/new core or unclassified legacy fallback; no normal request repairs enrollment or automatic recovery/compensation. | P01; P02; P04; P09; separate issuer mapping/native migration/recovery and compatibility qualification. Upgrade/rollback/restore/node skew/recovery epoch/key/grant/provider reconciliation; legacy explicitly-unmanaged compatibility; no stale node can issue or write after maintenance. |

### All 22 writer categories remain open

Each category must join the same issuer-primary durable generation/fence before
protected dependency reads or mutation, with its revision update atomic with the
write, **or** have enforceable pre-effect exclusion/all-node maintenance. The
earlier category inventory remains incomplete as a transitive callgraph. Original
paths are pinned in the design record; no row is implementation acceptance.

| ID | Original writer category | Required design units | Closure |
| --- | --- | --- | --- |
| W01 | Admin REST and UI client changes | P03, P09 | Open; participate or enforce before-effect exclusion/maintenance. |
| W02 | User lifecycle and JIT/ITDR effects | P03, P05, P09 | Open; participate or enforce before-effect exclusion/maintenance. |
| W03 | Realm policy and authentication configuration | P03, P09 | Open; participate or enforce before-effect exclusion/maintenance. |
| W04 | Protocol mappers | P03, P09 | Open; participate or enforce before-effect exclusion/maintenance. |
| W05 | Client scopes | P03, P09 | Open; participate or enforce before-effect exclusion/maintenance. |
| W06 | Roles and composites | P03, P09 | Open; participate or enforce before-effect exclusion/maintenance. |
| W07 | Groups and inherited authority | P03, P09 | Open; participate or enforce before-effect exclusion/maintenance. |
| W08 | Account credentials | P03, P05, P09 | Open; participate or enforce before-effect exclusion/maintenance. |
| W09 | Dynamic registration | P03, P09 | Open; participate or enforce before-effect exclusion/maintenance. |
| W10 | Admin SDK | P03, P09 | Open; participate or enforce before-effect exclusion/maintenance. |
| W11 | Representation import and partial import | P09, P10 | Open; participate or enforce before-effect exclusion/maintenance. |
| W12 | Startup/offline import | P01, P10 | Open; participate or enforce before-effect exclusion/maintenance. |
| W13 | Bootstrap and migrations | P01, P10 | Open; participate or enforce before-effect exclusion/maintenance. |
| W14 | Model adapters and native provisioning | P03, P04, P09 | Open; participate or enforce before-effect exclusion/maintenance. |
| W15 | Federation and synchronization | P01, P05, P09 | Open; participate or enforce before-effect exclusion/maintenance. |
| W16 | Issuer workflow background writers | P05, P09 | Open; participate or enforce before-effect exclusion/maintenance. |
| W17 | Credential and registration policy | P03, P05, P09 | Open; participate or enforce before-effect exclusion/maintenance. |
| W18 | Native issuance and refresh | P03, P05, P08, P09 | Open; participate or enforce before-effect exclusion/maintenance. |
| W19 | Browser and direct access | P03, P05, P08, P09 | Open; participate or enforce before-effect exclusion/maintenance. |
| W20 | Revocation and logout | P03, P05, P09 | Open; participate or enforce before-effect exclusion/maintenance. |
| W21 | Keys and signing | P03, P08, P09 | Open; participate or enforce before-effect exclusion/maintenance. |
| W22 | Operator restore and direct database changes | P01, P10 | Open; participate or enforce before-effect exclusion/maintenance. |

AdminAPIv2, shared-client changes, native SCIM and feature-profile variants stay
inside these categories, together with every internal/constructor/worker/bulk/
model/SQL/flush/cache/import/bootstrap/federation/key/signing/operator/restore path.
No REST-only or Python-only inventory can close them. Direct operator database
writes require all-node maintenance; online fencing cannot constrain an operator
outside the qualified protocol.

### Compatibility, migration and recovery

The proposed typed core contract needs explicit migration of all native/custom
providers, participants, factories, workers, grants and disposers. Inventory old
registrations before replacing phase-list behavior. Legacy client wire behavior
may continue only for **authoritatively classified unmanaged** paths under the
reviewed build and owner protocol. Unclassified legacy realms do not default to
unmanaged. No mixed old/new serving nodes, silent provider fallback or protected
registration adapter bypass is accepted. Preserve native auth, non-creation,
target authorization, signing, required security cleanup and existing capabilities.

Future issuer-owned storage changes require paired issuer mapping and native
Liquibase migration qualification under ADR 0004; this revision selects no DDL,
table, lock or transaction primitive. Application SQLAlchemy/Flyway remain
unchanged. Initial inventory/migration/restore happens with every issuing node
quiescent; replace recovery incarnation from outside the restored backup,
reconcile grants/keys/providers and independently requalify before reopening.
Unknown effects require authorized containment/recovery proof, never automatic
compensation or replay. Upgrade, rollback, node skew, historical grant/credential
custody and durable failover remain separate acceptance gates.

## Mandatory A0 prerequisite result: NO-GO before candidate

The [session-birth preflight record](../../infra/keycloak/keycloak_registration_connector/session-birth-preflight-review.json)
reverifies all 50 earlier source pins and adds 18 native/build units: **68 units,
158 literal anchors** at the same immutable commit. That earlier preflight reviewed
source and inherited manifest evidence only. No candidate, native test, augmentation,
JAR fetch, SDK build or provider operation ran in that preflight. The 578 cases/six controls are inherited
results, not rerun. **The mandatory A0 prototype remains open.** The prescribed
prerequisite stop fired; this is not a passing denial/constructor experiment.

The source shows why a session-only guard cannot establish A0:

1. `KeycloakProcessor.configureKeycloakSessionFactory` calls `loadFactories`;
   `Providers.getProviderManager`, `ProviderManager` and `DefaultProviderLoader`
   participate in SPI/factory discovery through ServiceLoader. Factory instances
   and deployed script factories are obtained before the processor's `isEnabled`
   filter. Supplied deployment/filesystem loaders add inputs ([B19], [B51]–[B58]).
   This is source ordering, not an observed runtime trace or exhaustive callgraph.
2. The recorder constructs the concrete Quarkus factory; its constructor can
   reflectively instantiate provider factories and calls `init`. The abstract
   factory's later `init` invokes dependency-aware `postInit`. Neither an enabled
   flag, provider ID nor the symbolic pre-init build item attests prior safe class
   loading ([B02], [B03], [B18], [B62]). Privileged providers need an immutable
   reviewed artifact/classloader/descriptor/feature boundary before discovery.
3. `DefaultKeycloakSession` has instance collection initializers and a static
   logger; its constructor body creates the transaction manager, invokes virtual
   context construction and logs. Quarkus delegates to the superclass and creates
   its framework context ([B04], [B05], [B06], [B16], [B34], [B35]). A body-only
   guard cannot precede earlier JVM initialization. Source review does not prove
   the selected JVM/logger/framework initialization safe or qualify direct paths.
4. Startup invokes factory init/postInit and transactional bootstrap; Quarkus can
   schedule startup asynchronously. The native app build config includes a
   `dev-file` DB setting, and `exit_before_bootstrap` is checked **after** factory
   init ([B59], [B60], [B68]). No native command was run; a future harness must
   prevent unintended DB/import/listener/provider/secret effects before use.

### Build-input gap and exact return conditions

The earlier 290-JAR evidence record contains 21 coordinates under `io.quarkus`,
but does **not** contain these 11 minimum source-declared module/input seeds.
Comparison rereads recorded coordinates/hashes; it neither fetches nor rechecks
JAR bytes. Module versions and Quarkus properties come from the pinned POMs
([B64]–[B68]). Effective BOM/profile/plugin/transitive resolution has **not** run.
These seeds are not a complete dependency graph, artifact lockfile, security/
license clearance or evidence that a source-built alternative is impossible.

| Coordinate seed | Native role | In inherited reviewed JAR record |
| --- | --- | --- |
| `org.keycloak:keycloak-quarkus-server:26.8.1` | native runtime module | Absent. |
| `org.keycloak:keycloak-quarkus-server-deployment:26.8.1` | native augmentation module | Absent. |
| `org.keycloak:keycloak-quarkus-server-app:26.8.1` | native server assembly | Absent. |
| `io.quarkus:quarkus-core-deployment:3.40.1` | augmentation dependency | Absent. |
| `io.quarkus:quarkus-arc-deployment:3.40.1` | CDI build dependency | Absent. |
| `io.quarkus:quarkus-rest-deployment:3.40.1` | REST build dependency | Absent. |
| `io.quarkus:quarkus-hibernate-orm-deployment:3.40.1` | ORM build dependency | Absent. |
| `io.quarkus:quarkus-bootstrap-core:3.40.1` | bootstrap dependency | Absent. |
| `io.quarkus:quarkus-maven-plugin:3.40.1` | executing build plugin | Absent. |
| `io.quarkus:quarkus-extension-maven-plugin:3.40.1` | generated extension descriptor plugin | Absent. |
| `io.quarkus:quarkus-extension-processor:3.40.1` | executing annotation processor | Absent. |

The native runtime/deployment/server POMs declare 102/26/6 direct dependencies;
those literal declarations do not establish the effective graph or selected
providers. Native extension-descriptor generation, annotation processing and the
Quarkus build plugin also differ from the earlier services/SPI fixture, which
disables annotation processing. Source-building the native modules still needs
reviewed dependency/plugin inputs, exact output identity and isolation. Do not
fill gaps with arbitrary SDKs, default repositories or real server startup.

| Gate | Required evidence before returning to the candidate | Current result |
| --- | --- | --- |
| PF-01 — Reviewed artifact/build input closure before execution | Review metadata/BOM/profile/plugin/processor/provider closure and exact provenance/hash/license/security inputs; source-built modules need source/output identity and isolation too. | Unqualified; stop before candidate. |
| PF-02 — Provider admission before discovery/initialization | Verify the exact immutable build/classloader/provider/descriptor/feature set before class loading or factory construction; a late enabled flag or ID allowlist is insufficient. | Unqualified; stop before candidate. |
| PF-03 — Restricted birth before native initialization | Qualify JVM superclass/static/instance/virtual order and source/bytecode origin; prove earlier initialization effect-free or place ownership earlier; no body guard can retroactively protect earlier work. | Unqualified; stop before candidate. |
| PF-04 — Concrete native factory/augmentation activation | Actual isolated Quarkus augmentation and selected provider/classloading proof; no synthetic factory receipt, abstract interface or direct constructor fixture can pass. | Unqualified; stop before candidate. |
| PF-05 — Startup/maintenance before model work and job creation | Safe owned harness must fence bootstrap and block DB/listener/import/secret/provider effects before use; never run native defaults or use exit-before-bootstrap as proof that init was prevented. | Unqualified; stop before candidate. |
| PF-06 — Direct/internal/new/nested/worker/CDI session ownership | Fresh exact restricted lifecycle owner before initialization; missing/stale/foreign/reentry/worker denial with controls; birth grants no primary realm/auth/read/write/signing authority. | Unqualified; stop before candidate. |
| PF-07 — Historical fixture versus actual framework proof | Keep historical 578 cases/six controls and all failures unchanged; distinguish any later rerun and new oracle; actual framework/provenance proof remains mandatory before A0 passes. | Unqualified; stop before candidate. |

## Static seed-input review and candidate identity lock

The [augmentation input record](../../infra/keycloak/keycloak_registration_connector/augmentation-input-review.json)
now pins **11 reviewed seed artifacts**, **38 POMs**, and **69 native source/build
units with 162 literal anchors**. All 68 earlier source pins match. This is a
bounded static seed review and harness plan; **the full effective build-input
lock and A0 qualification remain NO-GO**. The existing P1 research approval
persists. No new production decision follows from inspecting these inputs.

Only fixed credential-free Maven Central URLs were fetched. Data stayed in owned
private review paths; no existing Maven home/settings/repository or credentials
were used. Nothing invoked Maven, a JVM, a plugin/annotation processor, Quarkus
augmentation, native tests, a server, a database or provider code. ZIP members
were read without extraction or class loading. No binary enters public source;
owned quarantine binaries are removed after recording hashes and static metadata.

| Reviewed evidence | Exact scope and limits |
| --- | --- |
| POM ancestry/BOM metadata | 38 seed, parent and root-imported-BOM POMs have local SHA-256/SHA-512 pins. 35 match publisher SHA-512 metadata; three Apache-directory/Apache ancestor POMs return 404 for that checksum file and retain local hashes only. This is not effective profile/dependency resolution or independently signed provenance. |
| Source versus publication | Five native POMs (root, Quarkus parent, runtime, deployment and server) match the pinned source byte for byte. The candidate plan uses exact source-built changed native units; the three published native JARs are static/native control references, not a patched candidate or adopted issuer. Compiled source/output equivalence remains unproved. |
| Seed artifact identity | All 11 quarantined JARs match their pre-pinned publisher SHA-512 values: three native controls and eight framework/plugin/processor seeds from the previous gap list. The record includes their SHA-256/SHA-512, exact URLs and metadata. Seed identity alone cannot approve the remaining graph or execution. |
| License/security boundary | All 11 seed POM license chains declare Apache-2.0; eight framework JARs contain inspected Apache-2.0 license text. The three native JARs lack inspected LICENSE/NOTICE entries; their POM/source declarations are separate evidence. PGP signatures, full transitive licensing/SBOM/CVE/security and distribution clearance are not established. Two historical helper-license declarations and the deprecated test-only API remain limits. |
| Static artifact metadata | 54 entry hashes, nine native class-entry hashes and 16 runtime service descriptors were reviewed. All 16 source service-descriptor files match the published runtime JAR byte for byte. Those declarations are not proof of selected runtime providers or initialization safety. |
| Plugin input gap | Two plugin descriptors declare 183 dependency entries, 133 unique coordinates. **99 are absent from the earlier 290-JAR record.** This is a declared input pool, not a Maven-effective/transitive closure or approval to auto-fetch/execute them; prior presence also does not establish current reuse clearance. |

The runtime artifact's generated extension metadata points to the exact native
deployment coordinate. Its packaged build-step list names **both**
`KeycloakProcessor` and `LiquibaseProcessor`. The added source pin shows
`LiquibaseProcessor.configure` collects indexed service implementations using the
datasource kind and records Liquibase service configuration ([B69], [B18]). This
does not demonstrate a DB connection or migration ran; none was executed. It
does mean a guard covering only Keycloak factory creation cannot establish the
whole augmentation boundary. Framework build-step declarations also include
Docker/Podman/dev-services related processors; names alone prove neither their
execution nor their exclusion. The complete reached graph still needs proof.

### Effect-disabled harness plan and open input gates

The record's IN-01–07 matrix distinguishes static identity checks from unqualified
execution/activation gates. Required ordering remains:

1. Fix the exact candidate/control source and artifact identities, root POM/BOM/
   profile selections, extensions, plugin dependencies/Mojos, annotation processors,
   generated descriptors/indexes and provider/classloader inputs. The current
   eleven-seed lock is **not** a complete executable classpath. No repository URL
   embedded in a downloaded POM may cause an automatic request or unreviewed fetch.
2. Close the remaining effective/transitive input graph, including the 133 plugin
   coordinate pool and native dependencies, with reviewed provenance/hashes/
   licenses/security limits before use. Any future executable model check must
   use separately reviewed inputs, owned settings/cache/home and a fixed permitted
   input set; this input-only substep executes none. Missing input denies, rather
   than activating extensions or fetching arbitrary dependencies.
3. Implement and verify an outer owned isolation boundary **before** JVM/build-step/
   provider/static initialization. It must enforce the required network/DNS,
   process/container/service/DB/listener/secret/unowned-file exclusions and confine
   environment and writes to owned state. Select and qualify the actual mechanism
   separately; no mechanism is adopted or proved here. Flags, a classpath list,
   synthetic factory or tests that start after initialization cannot prove this.
   Native main/startup/dev-file DB defaults and both native processors require
   explicit treatment; no global feature retirement or silent suppression.
4. Only then return to the same open mandatory session-birth prototype, in fresh
   owned comparison projects with exact class-origin checks. Prove denial for
   missing/stale/foreign/unreviewed activation before manager/context/provider/
   begin/clone/read/effect, using actual selected Quarkus activation. A restricted
   birth owner grants no A1/A2 realm/model/auth/write/signing authority. Preserve
   the 578 historical cases/oracles/six controls and rerun affected cases when
   a candidate actually reaches them. No native cases ran for this static review.

## OS boundary and executable-input prerequisite result

The subsequent [harness-boundary review](../../infra/keycloak/keycloak_registration_connector/harness-boundary-review.json)
reverified all **69 source units/162 anchors** and inspected **263 POMs** from
fixed credential-free Maven Central URLs. **192** match publisher SHA-512 files;
**71** checksum files returned 404 and retain local SHA-256/SHA-512 pins only.
All 133 declared plugin coordinates now have POM/nearest-parent license metadata.
This closes their explicit parent/root-imported-BOM metadata ancestry only. It
does **not** resolve effective profiles, mediation, transitive artifacts, scopes,
classifiers, exclusions, selected processors/providers or the executable graph.
No new JAR was fetched or automatically resolved through a POM repository.

Two legacy namespace-free Maven POMs needed a parsing-only element-name
projection; original response bytes and initial strict-reader failures were
retained privately. DTD/entities remain forbidden. Nearest-parent declarations
include Apache, MIT, BSD, EPL, GPL with Classpath Exception and UPL variants,
plus a custom named declaration. Nine plugin dependency families have multiple
declared versions. Literal POM declarations and checksums establish neither
binary/transitive licensing, version mediation, security nor distribution
clearance. The historical two helper-license declarations/deprecated test API,
all earlier SPI/version/HA/image/security limits, and source-output/class-origin
requirements remain.

### Trusted OS sentinels: limited result, inherited-FD failure retained

The opt-in [OS research recipe](../../infra/keycloak/keycloak_registration_connector/qualification/os_boundary/README.md)
passed **42 expected observations** and **nine preparation/integrity controls**
on pinned macOS 15.5 arm64/Python 3.14.4. Its Apple `sandbox-exec` default-deny
profile precedes the child payload, imports only pinned dyld support and confines
writes to owned work. It allows trusted read-only Python/system trees and sysctl
reads; that TCB is not a complete immutable runtime closure. The OS command is
deprecated and SBPL private API; this is not a production isolation choice.

With closed inherited descriptors and minimal environment, the trusted payload
can read/write owned work while outside-work owned canary access, symlink/hardlink
escape, owned TCP/Unix connect, socket bind, fork and unapproved exec return EPERM.
The controller only binds new sockets and never listens. Baseline TCP/Unix
connect times out/refuses, so there is no positive network-delivery comparator.
Guarded `localhost` lookup fails, but external DNS and arbitrary Mach/bootstrap/
service/container/DB/host-secret operations were not tested. No genuine secret or
existing service was accessed. Resource/side-channel/arbitrary-native coverage
also remains open. Nested tool-sandbox policy installation initially failed
exit71/EPERM; a separately reviewed host launch worked. No fallback weakened
the policy after failure.

The **intentional inherited-FD control writes the outside-work owned canary**
under the same deny profile. The secure comparison closes that descriptor
(EBADF; canary unchanged). Therefore descriptor/capability sanitization must
precede installation; the policy alone is insufficient. Both the negative witness
and initial Python runtime/bootstrap failures remain in private evidence. The
recipe verifies trusted policy text, rather than trusting a caller state digest.

### Initial JVM prerequisite stop (retained evidence)

The pinned JDK 21.0.12.1+1 and Maven 3.9.11 archives were revalidated, including
all **459 JDK and 96 Maven installed files**, with no extra files or symlinks.
Only an isolated **JDK version-print** control was attempted under a separate
default-deny policy with closed descriptors, owned home/tmp, interpreted mode,
attach/performance/core-dump settings disabled, and network/fork/file-link denied.
It exited **-11 (SIGSEGV)** before stdout, stderr or an owned JVM error report.
There was no unguarded Java comparator; the cause is **unknown**. This is a failed
compatibility/startup control, not proof of which policy operation caused failure
or of safe JVM execution. No dynamic-code-generation permission was added to
make it pass. The exact pinned inputs, flags and policy digest are in the record.

**No Maven CLI/model resolver, plugin, processor, Quarkus augmentation, issuer
build, provider or A0 candidate executed.** The Python sentinels do not qualify
the JVM. The 578 historical native cases/six controls are inherited unchanged
and were not rerun. Every old failure/oracle remains applicable.

## Compatible JDK-only control qualification

The [JDK-only comparison record](../../infra/keycloak/keycloak_registration_connector/jvm-boundary-review.json)
now qualifies one bounded **trusted JDK startup/owned-sentinel** control, with
**51 observations and 12 preparation/integrity controls**. The [opt-in recipe](../../infra/keycloak/keycloak_registration_connector/qualification/jvm_boundary/README.md)
pins the archive/all 459 installed JDK files and reconstructs the same default-deny
resource policy. The old JVM failure and every earlier witness remain recorded.
This closes neither the effective executable graph nor the full issuer harness.

The vendor [native startup source](https://github.com/adoptium/jdk21u/blob/1c417fbfc2f70ab03a565b0af0a5a3c6f5e15ad6/src/hotspot/os/bsd/os_bsd.cpp#L259)
reads native home from environment or user lookup, then uses its length without
a null guard. Java `-Duser.home` alone does not supply that earlier native value.
The same-policy version A/B/A comparison returned **SIGSEGV(-11), success(0),
SIGSEGV(-11)** when toggling only native child home. Configuring child native
home to the same new owned home as Java resolves this observed startup failure.
The source supports that mechanism; no native crash backtrace was collected.
The controller environment is unchanged; no existing home/settings/credentials
are read or changed. **No new dynamic-code, network, Mach, service, process or
file permission was added.** The normalized resource policy is byte-identical
to the earlier failing control after substituting owned output paths.

Only the revalidated JDK compiler and new trusted sentinel ran. Compilation uses
`jdk.compiler` with annotation processing disabled, empty source/dependency paths
and owned output; execution limits modules to `java.base`. The two generated
class hashes are recorded. That JDK-only unit ran **no Maven CLI/model resolver, plugin,
annotation processor, Quarkus augmentation, issuer/provider or A0 candidate**.
All69Keycloaksource/162anchors and263POMpins were reverified. JDK459/Maven96
installed files still match pinned archives; Maven was not executed.

| Actual JVM observation | Result and qualification limit |
| --- | --- |
| Main and Java worker thread | Owned work IO succeeds. Outside-work owned canary/file/link and socket operations get EPERM; one worker retains tested read/bind denials. No issuer session/CDI/parent/async lifecycle proof follows. |
| Owned socket connect/bind | Guarded EPERM; targets only bound TCP/Unix sockets, never listening. Baseline connect times out/refuses, not a positive delivery comparator. No real DB/service/container/host-secret or external target is used. |
| Child process path | Baseline `/usr/bin/true` exits0; guarded ProcessBuilder returns generic spawn-helper failure. The API does not expose a reliable raw fork/exec errno or every-process-path proof. |
| Resolver limit | **Guarded Java resolves `localhost` to127.0.0.1.** The older Python lookup failure cannot generalize to JVM/external DNS/Mach/bootstrap isolation. |
| Inherited capability | Deliberately inherited FD0 lets the guarded JVM read the outside-work canary. Secure DEVNULL stdin returns EOF. Retain this witness and the earlier Python inherited-write bypass; capability sanitization precedes policy installation. |

Initial new-lab expectations assumed exact baseline environment and EPERM text
from ProcessBuilder. The unguarded runtime adds `__CF_USER_TEXT_ENCODING`, and
the Java spawn-helper error is generic. Raw initial reports/input revisions were
retained; final assertions reflect these actual observations and do not call the
generic error EPERM. Existing native sources/oracles and578cases/six controls
remain unchanged and inherited, not rerun. The separate twelve integrity controls
reject input/policy/payload/output/compiled-class drift before compiler execution.

Trusted read-only JDK/system/cryptex inputs and sysctl access are TCB assumptions,
not full immutable OS or arbitrary-native isolation proof. External DNS/Mach/
bootstrap/IOKit/service/container/DB/secret/resource/side-channel mediation and
actual selected native provider/classloader/initialization remain unqualified.
The private/deprecated Apple API is an exact-host research mechanism, not a
production choice. Interpreted mode and absence of an explicit dynamic-code allow
do not establish dynamic-code enforcement or authority for unknown provider code.

## Offline selected-model prerequisite qualification

The [offline model record](../../infra/keycloak/keycloak_registration_connector/offline-model-review.json)
qualifies a bounded **model-library API input and boundary** check, with
**15 model/boundary assertions and 16 preparation/integrity controls**. The
[opt-in recipe](../../infra/keycloak/keycloak_registration_connector/qualification/offline_model/README.md)
uses six hash-pinned Maven 3.9.11 model/Plexus libraries and the revalidated JDK,
without Maven CLI/core/transport/plugin/Guice/Sisu/ASM runtime on the classpath.
Eighteen exact Apache source units and425 static classes were inspected; this is
not a complete dynamic callgraph or native provider qualification.

The explicitly constructed [model API](https://github.com/apache/maven/blob/3e54c93a704957b63ee3494413a2b544fd3d825b/maven-model-builder/src/main/java/org/apache/maven/model/building/DefaultModelBuilder.java)
uses checked byte-array sources, not file/URL/ModelSource2, and an exact offline
resolver. POM hash/coordinate checks and DTD/entity rejection precede parsing.
Repository callbacks record IDs as data and never use transport. Automatic host/
file/JDK/OS/environment/default-profile activation is replaced by explicit profile
selection; request properties are empty, and plugin processing is disabled. No
settings/workspace/lifecycle-extension listener or POM-supplied fetch is used.

The outer deny policy precedes JVM/library initialization. Its only new scope is
a **task-owned read-only input tree**; external file/network/process/Mach/service
permissions remain unchanged. Outside-canary read, input-write and socket-bind
denials plus owned write/stdinEOF controls run before builder construction. Child
native/Java home, environment and descriptors are confined as before. Copied
hashes and policy are reconstructed from trusted fixture definitions; forged state
cannot authorize changed JARs or POM tables. Class-origin logs resolve only to the
JDK, six exact libraries and owned code, following generated lambda origins to
their verified defining classes. The inputs remain byte-identical after the run.

All five models succeed under **explicit `crypto-default` plus `upstream-adapters`**:

| Model | Direct dependency declarations | Managed entries |
| --- | ---: | ---: |
| Root parent / Quarkus parent | 0 each | 2419 each |
| Native runtime | 102 | 2419 |
| Native deployment | 26 | 2419 |
| Native server app | 6 | 2419 |

All 134 direct dependency versions are interpolated. The initial crypto-only plan
omitted EE coordinate properties from the pinned root's `upstream-adapters`
profile and failed all five models. That incomplete-profile failure is retained
as a negative; host-default activation was not enabled to get a pass. This is an
upstream non-FIPS model plan, not default/native/production build equivalence or
feature retirement. Raw effective XML, tuples, lookup requests and class logs stay
private; public metadata contains selected declarations and hashes.

Only existing six libraries/JDK and263 pinned POMs plus three synthetic fixture POMs
were used; no new JAR was fetched. All 69 source units, 162 anchors, 263 POMs and 459 JDK / 96 Maven
installed pins were reverified. Four `ModelSource` deprecation warnings, historical
helper-license/deprecated API limits, source-output/class-origin limits and all
full license/CVE/PGP/SBOM/security/distribution gates remain. Apache declarations
and archive notices (including Indiana parser attribution) do not clear unrelated
bundle components or the future native distribution.

No Maven CLI/plugin/extension/annotation processor, Quarkus augmentation, native
build, issuer/provider operation or A0 candidate ran. The 578 native cases and six controls
were not rerun or changed. Earlier failed startup/inherited FD/stdin witnesses,
Java localhost success and unqualified arbitrary-native/DNS/Mach/bootstrap/IOKit/
service/container/DB/secret/resource/sidechannel scope remain. Private/deprecated
Apple API and trusted controller/JDK/system/cryptex/sysctl scope are research limits.

## Selected executable-input declaration frontier

The initial [frontier record](../../infra/keycloak/keycloak_registration_connector/selected-input-frontier.json)
reconciled the five explicit-profile models with the two packaged plugin
descriptors. Its original metadata gaps are closed by the subsequent review below;
the historical frontier JSON remains unchanged. **This completes a declaration inventory, while full executable
input closure and native issuer isolation remain NO-GO.** It is not a lockfile,
dependency resolver, build recipe or approval to execute the listed artifacts.

| Retained input layer | Result |
| --- | --- |
| Direct dependencies | 134 occurrences, 131 distinct GAVs: 126 compile, 3 provided, 5 test |
| Declared build plugins | 7 declarations, 5 distinct plugins |
| Explicit annotation-processor paths | 2 declarations of the Quarkus extension processor |
| Packaged plugin dependency pools | 183 occurrences, 133 distinct GAVs, kept in separate plugin realms |
| Source-root Maven bootstrap extension | `maven-build-cache-extension:1.2.0` |
| Combined declaration frontier | 265 distinct GAVs; initially 144 had pinned POM metadata and **121 lacked it** |
| Multiple-version families | 9; no global winner or classloader equivalence claimed |
| Keycloak source/control identities | 39 GAVs mapped to source POM paths; published binaries are not source-built candidates |

Every occurrence retains owner/order, version, literal type/classifier/scope/
optional/exclusions and its selection reason. Provided and test declarations
remain visible; neither scope nor optional status proves safe provider exclusion.
The 2,419 management entries in each model supply version-management context,
not a transitive graph or artifact selection. Each model also contains 33
plugin-management entries; management alone does not select an executable plugin.
Raw selected-POM declarations and management provenance stay in private evidence;
the public record contains selected declarations, hashes and exact missing GAVs.

The source [`.mvn/extensions.xml`](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/.mvn/extensions.xml)
declares the build-cache extension, outside the model API's project-extension
view. The server model declares `quarkus-maven-plugin` with `extensions=true`,
the `build` goal and **`kc.db=dev-file`**. The runtime binds the extension-descriptor
goal and both runtime/deployment compiler configurations specify the Quarkus
annotation processor. A source-root Maven launch would need those bootstrap/
plugin/processor inputs reviewed separately. No Maven lifecycle/default packaging
bindings were injected by the model-only check, so absent resource/jar/test goals
cannot be inferred absent from an eventual build. No such launch occurred.

Both packaged native build steps, **KeycloakProcessor and LiquibaseProcessor**,
and the 16 source/runtime service-descriptor matches remain in the frontier.
They do not prove provider reach, constructor/init/postInit behavior or safe
exclusion. Generated extension descriptors/indexes/classes, conditional deployment
dependencies, devservices/container/native paths and classloader realms still
need actual selected-input and effect evidence. Earlier static/superclass/instance/
virtual/logger/context initialization findings remain applicable.

All 69 source pins/162 anchors, 263 POM pins, five model-output hashes, 54 seed
metadata entries, six model libraries and all 459 JDK/96 Maven installed files
were reverified without running Java or Maven. The POM corpus still has 192
publisher checksum matches and 71 missing publisher checksums. Nearest-parent
license declarations are metadata only; binary notices/license/security/CVE/PGP/
SBOM/distribution and source-output equivalence remain unqualified. No new
network fetch, binary, upstream source or raw POM is published by this unit.
The 578 native cases and six controls remain inherited and unchanged.

## Selected metadata ancestry and child-model input plan

The [selected metadata record](../../infra/keycloak/keycloak_registration_connector/selected-metadata-review.json)
closes the initial **121 reviewed-corpus POM gaps**: 34 use exact source-archive
POMs and 87 use newly reviewed external POM metadata. It also records all required
literal parents and root imported-BOM metadata within this bounded selection.
**Zero pending static ancestry coordinates does not establish effective child
models, transitive dependency mediation or executable input closure.**

| Metadata result | Count |
| --- | ---: |
| Previously pinned published POMs | 263 |
| Source POMs with checked identities and source-parent ancestry | 46 |
| Source POMs matching prior published bytes | 5 |
| New unique source POM coordinates | 41 |
| New external POMs | 152: 87 selected, 65 parents/root imported BOMs |
| Reviewed external retrieval waves | 5: 87, 46, 10, 8, 1 coordinates |
| Expanded unique metadata corpus | **456** |
| New publisher SHA512 matches / checksum HTTP 404 | 109 / 43 |
| Prior publisher SHA512 matches / checksum HTTP 404 | 192 / 71 |

All 39 selected Keycloak GAVs have checked source POM identities; the additional
source POMs supply ancestry. Source paths, declared/inherited group/version and
each source-parent identity were checked inside the pinned archive. All five
source/published overlaps match byte for byte. The planned model input selection
uses **46 source POMs and 410 published metadata POMs**, retaining both provenance
records for the five identical overlaps. This is POM identity evidence, not
source-built binary equivalence. No published Keycloak binary substitutes for a
candidate output. UTF-8/namespace checks reject DTD/entity input; the two legacy
namespace-free POMs remain parse-only projections with original bytes unchanged.

Every new coordinate was reviewed before retrieval, in explicit ancestry waves.
Only fixed credential-free Maven Central POMs and adjacent SHA512 metadata were
requested. No POM repository URL, redirect, proxy, authentication, existing Maven
settings/home/cache/repository or executable download was used. Source and fetched
POM bytes remain private review inputs; public records contain pins and declarations.
All 265 selected GAVs now have a nearest-parent declared license. Those declarations,
including mixed license families, are not full binary/transitive notices, security,
CVE/PGP/SBOM/distribution or source-output approval. Missing publisher checksums
remain explicit gaps. Static ancestry applies no automatic or default profiles.

A **data-only expanded child-model input plan** pins 456 POMs and 265 target GAVs.
The existing five-model fixture, six-library classpath, policy, driver and its
15 model/boundary assertions plus 16 integrity controls are unchanged. No expanded
model API, JVM, Maven CLI/plugin/build extension/annotation processor, Quarkus
augmentation, native issuer/provider or candidate ran in this metadata unit.
The 578 native cases and six controls remain inherited and unchanged.

The source-POM review also records 41 build-plugin declarations, including frontend
tooling and resource generation. These are literal declarations, not selected
effective versions/lifecycle bindings or permission to run Node/package tools.
Source-root build-cache, Quarkus `extensions=true`/`build`/`dev-file`, both native
processors, generated descriptors/indexes, conditional deployment, provider discovery/
initialization, classloader, devservices/container/native and early initialization
effects all remain full-graph and harness prerequisites.

## Expanded offline child-model qualification

The separate [expanded recipe](../../infra/keycloak/keycloak_registration_connector/qualification/offline_child_models/README.md)
and [result record](../../infra/keycloak/keycloak_registration_connector/offline-child-model-review.json)
qualify the **bounded model-library API inputs and owned boundary** for 456 POMs
and 265 targets. The original 263-POM/five-model fixture and evidence are unchanged.
All **15 model/boundary assertions and 20 integrity controls** pass: the original
16 integrity controls plus four fixed-manifest/target tampering checks.

The resolver, byte `ModelSource`, explicit profile selector, empty request
properties, plugin-processing-off and deny-policy functions are unchanged. Only
the six reviewed libraries and pinned JDK execute. No CLI/core/transports/plugin/
Guice/Sisu/ASM runtime is added. Trusted recipe definitions fix POM/library/target
digests and copied-input/policy identities; caller state cannot widen them. Early
outside-read/input-write/socket-bind denials precede builder construction; owned
write/stdin EOF, closed descriptors, minimal environment/owned native-Java home,
read-only inputs and verified class origins pass. Inputs remain unchanged.

All 265 outcomes were retained: **263 successful child models and two NO-GO**.
The successful outputs contain 2,054 ordered direct declarations and 216,965
managed-entry occurrences, with no unresolved direct-dependency scalar properties.
These contextual occurrences are not unique mediated executable artifacts.
The 789 raw XML/tuple/provenance files total about 49 MB and remain private review
evidence, with per-target public hashes/counts. Exactly 1,114 resolver requests
were recorded; the only unexpected selected-model coordinate was the denied JUnit
BOM below. The intentional synthetic range denial remains separate.

| Target | Unresolved model qualification |
| --- | --- |
| `maven-surefire-plugin:3.5.6` | Its child context requires unpinned `org.junit:junit-bom:5.12.2`, also leaving the vintage-engine dependency version missing. |
| `jctools-core:4.0.5` | Two raw main-build `maven-bundle-plugin` declarations fail the selected `MAVEN_3_1` validation level. |

This validation level and explicit `crypto-default`/`upstream-adapters` selection
apply to one research plan across multiple target roles. They do not establish
stock/default/native/production or dependency-descriptor context equivalence.
The JCTools failure is not proof of a binary defect or unsafe dependency. No POM
was edited, target dropped, validation relaxed or missing input auto-fetched.
Static parent/root-BOM ancestry closure did not close every child-context import.

Compiler flags remain `--release 21`/`-proc:none`/`-implicit:none`, with an empty
source path. The model-only batch has a 600-second limit (compiler 90 seconds),
128 MiB heap and unique CREATE_NEW output IDs, bounded to 8 MiB per target file/
256 MiB total target output. New provenance accessors were statically inspected
in the pinned model library. All 69 source/162 anchors/456 POM/54 seed metadata/
18 Maven source-unit/six-library/JDK459/Maven96 pins were reverified. Four
ModelSource deprecation warnings and all prior license/security/checksum/CVE/PGP/
SBOM/distribution/source-output limits remain. No new JAR/network fetch or native/
plugin/processor/extension/Node/Quarkus/issuer/provider/A0 candidate ran. The 578
native cases and six controls remain inherited and unchanged.

## Child-model blocker and validation-context review

The separate [context diagnostic](../../infra/keycloak/keycloak_registration_connector/qualification/model_context_review/README.md)
and [result record](../../infra/keycloak/keycloak_registration_connector/model-context-review.json)
complete the bounded review of the two prior model blockers. **17 model/boundary
assertions and 22 integrity controls pass**, preserving all earlier controls.
Four fixed cases cover two GAVs: three successful models and one expected strict
denial. The original five-model and 265-target fixtures/results are unchanged;
this is not a rerun or success claim for all 265 strict models.

One new POM, `org.junit:junit-bom:5.12.2`, raises the corpus to 457 (46 source/
411 published metadata POMs). It has no parent/root BOM imports, matches publisher
SHA512 and declares EPL v2.0. Surefire's parent overrides `versions.junit5` to
5.12.2 while its inherited Maven-parent import has a 5.14.2 default. With the
reviewed child-context BOM, the Surefire model succeeds at the unchanged research
level 31 and resolves vintage-engine to 5.12.2. Removing the pin in a controlled
negative still denies without fetch. Metadata is not binary/license/security or
distribution clearance; no new JUnit JAR or production dependency was introduced.

Four version-pinned Apache Maven source units explain validation contexts:

- The artifact-descriptor reader selects `MINIMAL` (0) and plugin processing off.
- Project requests default to `STRICT`, which aliases `MAVEN_3_0` (30) in 3.9.11.
- The earlier research request explicitly used `MAVEN_3_1` (31).
- The validator's duplicate-plugin severity and model normalizer account for
  rejection versus warning/normalized model data.

| JCTools 4.0.5 comparison | Observed result |
| --- | --- |
| Earlier research level 31 | Duplicate-plugin rejection retained as the strict witness |
| Project-default validation dimension, level 30 | Model succeeds with the duplicate-plugin warning |
| Descriptor-validation dimension, level 0 | Model succeeds; raw duplicate declarations remain evidence |

The context matrix is immutable and target-scoped; levels 30/0 cannot be requested
for arbitrary targets. The default research method stays at 31. Both raw bundle
plugin declarations remain unchanged, and each successful effective model contains
one normalized entry. That merge is not a plugin exclusion, configuration-reach
or execution proof. No target was dropped, POM patched or global validation changed.

The diagnostic matches only the reader's validation dimension. It retains our
checked byte sources, exact offline resolver, empty properties and explicit
profile policy. The actual Maven reader uses file/session/cache/repository paths;
neither it nor the project builder/resolver pipeline ran. The six-library classpath,
effect policy, source-first copies, hash/context forgery rejection, early outside-
read/input-write/bind denials, closed descriptors/owned home/stdin/class origins
and read-only input checks pass. Original 15 model assertions/20 integrity controls
remain, with two new controls in each group. Twelve raw model/tuple/provenance/
problem files remain private. No unexpected selected coordinate was requested.

All 69 source/162 anchors/457 POM/54 seed metadata/18 prior plus four new Maven
source units/six-library/JDK459/Maven96 pins were reverified. New network inputs
were one explicitly reviewed POM/checksum and four exact-commit source texts only.
No JAR, actual Maven descriptor/project pipeline, CLI/plugin/extension/processor/
Node/Quarkus/native issuer/provider/A0 candidate ran. Four ModelSource warnings
and all previous license/security/checksum/source-output/effect-boundary limits
remain; the 578 native cases and six controls remain inherited and unchanged.

## Role-aware model and next-hop declaration frontier

The [static frontier record](../../infra/keycloak/keycloak_registration_connector/role-transitive-frontier.json)
now maps **265 model data templates to 332 distinct original role occurrences**.
It reuses the prior 263 successful strict research models, the new strict Surefire
model and the scoped JCTools descriptor-validation model. Their exact POM/output
hashes, validation levels, explicit profile/model provenance and ordered parent/BOM
requests remain attached. JCTools' strict denial, project-default warning and both
raw bundle-plugin declarations remain witnesses. This is **264 strict model data
results plus one limited validation-dimension result**, not a rerun or a passing
265-target strict suite. None establishes an actual role's descriptor/project context.

| Original role | Occurrences preserved |
| --- | ---: |
| Project dependency declarations | 134 (126 compile, 3 provided, 5 test) |
| Packaged plugin dependency-pool entries | 183, across 133 GAVs |
| Declared build plugins | 7, across 5 identities |
| Explicit processor paths and bootstrap extension | 2 and 1 |
| Parent-model and source-native-module contexts | 2 and 3 |

Every occurrence retains its owner, original list position, dependency ordinal
where available, type/classifier/scope/optional/exclusions and source/control role.
A shared data-template reference does not choose a globally authoritative model,
artifact, version or context. Packaged plugin pools are not resolved parent paths.
The 39 source/control mappings, 16 service descriptors, nine original realm-specific
multiversion families and both native processors remain required.

The templates contain **2,068 ordered dependency declarations**, projecting to
**2,731 role-specific next-hop candidates** and 923 distinct target expressions.
The separately hashed 217,020 managed declarations are not selected dependencies;
the original five roots' 2,419 management entries each remain data. Matching owner
management entries are retained per edge without claiming consumer management or
field-level parent/BOM origin tracing. Scope/optionality propagation and conflict
resolution remain explicit NO-GO for every path. The 363 candidate incoming-exclusion
matches do not prove an excluded artifact or safe effect boundary.

The exact next-input frontier is **676 missing POM coordinates**: 675 ordinary
next-hop coordinates and two relocation targets, with one shared between those
sets. Three additional expressions are unresolved version ranges, kept separately
without a guessed version or fetch URL. They occur in the HTML sanitizer model:
`commons-codec:[1.15,)`, FindBugs `jsr305:[2.0.1,)` and `annotations:[2.0.1,)`.
Three more next-hop coordinates already have pinned POMs but no reviewed target
model: Quarkus BOM, bootstrap BOM and bootstrap BOM test, all 3.40.1. Metadata
presence is not a model, artifact or selection qualification.

The Quarkus `quarkus-junit5-internal` and `quarkus-junit5-mockito` 3.40.1 models
contain relocation records to `quarkus-junit-internal` and `quarkus-junit-mockito`.
Neither relocation was applied. The record retains target identity, input need and
unqualified relocation/cycle semantics. No system paths or cycles among the 265
available declaration templates were found; missing/unmodeled/relocated nodes and
unqualified role semantics prevent a complete graph or cycle-clearance claim.
The 108 cross-template multiversion families retain every version and edge; no
cross-realm winner is chosen. Literal dependency types include `test-jar`, `pom`
and `zip`. Projected `jar`/empty-classifier comparison keys are assumptions pending
artifact-handler review, not approved classifier, extension or classpath mappings.

This unit performs **no fetch, JVM/model run, binary resolution or native execution**.
All 69 source/162 anchors/457 POM/54 metadata/18 prior plus four context Maven source/
six-library/JDK459/Maven96 pins and five original model hashes were reverified.
The three opt-in model recipes, all prior code and native controls remain unchanged.
The canonical record carries exact edge IDs for each missing input and the role,
mediation, handler, generated-effect and binary/harness NO-GO gates. Candidate URLs
are review destinations only; they authorize no automatic fetch or input use.

## Version-pinned collection semantics and next-input plan

The [source review and input plan](../../infra/keycloak/keycloak_registration_connector/collection-semantics-review.json)
records **37 exact-commit source texts, 67 anchors and 12 semantic findings** for
Maven 3.9.11 and its bundled Resolver 1.9.24. Resolver's tag resolves to
`7176b8c476c35b301e21e910dcf96d0792c24397`; pinned archive `pom.properties` entries
confirm the version. This is source/version evidence, not executed collector or
complete source/binary equivalence. No new dependency POM, library or binary was
retrieved; the only new network inputs were fixed source texts and tag metadata.

| Boundary | Source-backed finding | Remaining qualification |
| --- | --- | --- |
| Project and plugin roots | Project requests supply a root artifact/direct/managed lists. Plugin requests use a root dependency, plugin filters and runtime treatment of explicit plugin dependencies except system. | Root/depth/owner/session and resolution filters differ; a packaged plugin pool is not a selected tree. |
| Management and selectors | Maven's helper installs Classic management, depth-sensitive scope/optional selectors and inherited exclusions. Consumer management and pre-managed fields are separate. | Do not drop all test/provided/optional declarations or use child management as consumer selection. |
| Conflict handling | Actual identity uses extension/classifier and relocation/alias keys. Nearest selection honors range constraints; sibling candidates compare versions, other candidates compare depth. | Preserve graph order and complete conflict groups; no global version winner or generic first-declaration rule. |
| Artifact types | The stock core handler resource maps `test-jar` to extension `jar`, classifier `tests`. Its bytes match the reviewed archive resource. | Real handler contributions and model/session context remain unqualified; old comparison keys stay unchanged. |
| Bootstrap and processors | Core extensions use plugin-like resolution plus request interpolation and realm/core-export rules. | Build-cache/bootstrap remains required. Compiler-plugin 3.13.0 processor-path source still needs its own exact-commit review. |

The [Maven session helper](https://github.com/apache/maven/blob/3e54c93a704957b63ee3494413a2b544fd3d825b/maven-resolver-provider/src/main/java/org/apache/maven/repository/internal/MavenRepositorySystemUtils.java)
sets Classic management and graph policies. The actual core session factory adds
settings/request/cache/workspace state and replaces the helper's type registry
with handler-manager lookup. These defaults are evidence to review; they do not
change the empty-property, explicit-profile, checked-byte research recipes or
permit settings, caches, credentials, transports or host workspace discovery.

The prior 2,068 declarations include 1,985 absent XML types, 67 `pom`, 15 `test-jar`
and one `zip`. Source-backed stock projections are recorded separately. Model type
has a `jar` default; compile scope is injected after management, not a simple MDO
field default. Unknown handler types have a source fallback, but that fallback is
not adopted as runtime policy. Packaging `bundle` alone is not a dependency-type
mapping. No old frontier, raw null, classifier, selected input or capability is
rewritten by the stock projections.

Collector sources also distinguish range metadata, descriptor relocations, cycle
records and traversal from final conflict selection. The three existing ranges
remain unsupported and no version was guessed. Both Quarkus JUnit relocations
remain unapplied. No live repository version metadata or workspace was queried.
No collector, model API, JVM, CLI, plugin, extension, processor, Node, Quarkus,
native issuer/provider or A0 candidate ran. The three old model recipes, all prior
code, 578 native cases/six controls and all effect-boundary limits are unchanged.

## Proof sequence and next bounded work

The next fixed metadata wave contains only two explicitly named relocation targets:
`io.quarkus:quarkus-junit-internal:3.40.1` and
`io.quarkus:quarkus-junit-mockito:3.40.1`, with their adjacent publisher SHA512
metadata. The plan records exact Maven Central destinations, original needed-by
edges/contexts and why each is needed. **They have not been fetched.** Their license
ancestry and hashes remain unknown. Review any newly discovered parent/import/
property/relocation input before another fixed wave. This small review wave does
not establish runtime priority, selection or authority to fetch all 676 coordinates.

The remaining 674 exact missing coordinates, three ranges and three already pinned
Quarkus BOMs lacking reviewed target models remain preserved. Before processor
collection design, pin compiler-plugin 3.13.0's source and review its actual path,
management,scope/classifier and discovery rules. Any later model/collector driver
needs separate source/API/input/context/controller and effect-boundary review;
this unit authorizes no execution or broader validation/default policy.

Full transitive binary/plugin/processor/extension/provider/classloader/generated-
output/source-built effect closure and independent native issuer isolation remain
NO-GO. Source/bootstrap/build-cache/Quarkus extension/build/dev-file/frontend/
resource/default lifecycle, both native processors and early/provider initialization
remain requirements. No native build may discover its own inputs. Both full gates
precede the same open A0 deny-only prototype. All old FD/stdin/localhost/OS/JDK/
controller/private Apple API/Mach/DNS/service/container/DB/secret/native/resource/
sidechannel and capability-restoration limits remain unchanged.

The A0 prototype remains open. All LC-01–10/A0/A1/A2, full entry/all-22-writer
closure, native cleanup/response, actual HTTP/JTA/JDBC/cache/durable effects,
R2 implementation/R3–R7 and compatibility/recovery gates remain. No optional
late attach/catch fix, fake primary map/ThreadLocal/caller hint/missing-row
unmanaged fallback, replay or security-cleanup suppression follows. Production
fork/version/storage/deployment remains a separate later decision.

This review closes the **bounded design task only**. Full cleanup/containment,
HTTP/native SQL durability, bootstrap/admission, writer closure and all old 18
witnesses/nine failed latest-at-response gates remain open, including R1
attribution/health/error/async/driver/deferred-effect and earlier 503 limits.
The proposed point-in-time semantic contract, R3–R7, credential custody/grants/
provisioning/rotation/revocation/CAS/audit, actual claims/JWKS/mappers/scopes/tenant,
paired models/Flyway/RLS/existing-data/upgrades/restore and caller adoption remain
required. The two historical build-helper license declarations and deprecated
test-only API remain limitations; no production dependency or artifact is added.

Existing IAM ITDR, SCIM and user/JIT lifecycle and all other service/source/data/
action/approval/SoD/audit/durability/recovery/verification restoration requirements
remain required. This review executes no MCP operations or provider actions and
changes no application/provider code, schema, runtime manifests, defaults,
guards, leases, metadata or caller. Temporal, `case_runtime` and deferred engine
replacement governance remain unchanged.

## Immutable primary references

[S01]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/DefaultKeycloakTransactionManager.java#L98
[S02]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/DefaultKeycloakSession.java#L380
[S03]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi/src/main/java/org/keycloak/models/AbstractKeycloakTransaction.java#L52
[S04]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/jpa/src/main/java/org/keycloak/authentication/jpa/JpaAuthenticationSessionProvider.java#L69
[S05]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/infinispan/src/main/java/org/keycloak/models/cache/infinispan/RealmCacheSession.java#L182
[S06]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/infinispan/src/main/java/org/keycloak/models/cache/infinispan/authorization/StoreFactoryCacheSession.java#L121
[S07]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/infinispan/src/main/java/org/keycloak/models/sessions/infinispan/transaction/DefaultInfinispanTransactionProviderFactory.java#L53
[S08]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/infinispan/src/main/java/org/keycloak/models/sessions/infinispan/transaction/DefaultInfinispanTransactionProvider.java#L65
[S09]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/infinispan/src/main/java/org/keycloak/models/sessions/infinispan/transaction/NonBlockingTransaction.java#L46
[S10]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/managers/CodeGenerateUtil.java#L180
[S11]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/models/utils/KeycloakModelUtils.java#L363
[S12]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/protocol/oidc/TokenManager.java#L193
[S13]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/authorization/policy/evaluation/PermissionTicketAwareDecisionResultCollector.java#L102
[S14]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/transaction/AsyncResponseTransaction.java#L33
[S15]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/jaxrs/CloseSessionFilter.java#L51
[S16]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/resteasy/TransactionalSessionHandler.java#L51
[S17]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/transaction/TransactionalSessionHandler.java#L44
[S18]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/cdi/KeycloakBeanProducer.java#L39
[S19]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/resteasy/KeycloakHandlerChainCustomizer.java#L40
[S20]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/error/KeycloakErrorHandler.java#L65
[S21]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/resources/IdentityBrokerService.java#L1621
[S22]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/resources/WelcomeResource.java#L159
[S23]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/transaction/JtaTransactionWrapper.java#L45
[S24]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/jpa/src/main/java/org/keycloak/connections/jpa/JpaKeycloakTransaction.java#L47
[S25]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/storage/database/jpa/AbstractJpaConnectionProviderFactory.java#L55
[S26]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/storage/database/jpa/QuarkusJpaConnectionProviderFactory.java#L106
[S27]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/jpa/src/main/java/org/keycloak/connections/jpa/DefaultJpaConnectionProvider.java#L42
[S28]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/connections/jpa/support/EntityManagerProxy.java#L93
[S29]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/tracing/NoopTracingProvider.java#L58
[S30]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/tracing/OTelTracingProvider.java#L116
[S31]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi/src/main/java/org/keycloak/utils/KeycloakSessionUtil.java#L38
[S32]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/events/EventListenerTransaction.java#L59
[S33]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/protocol/saml/SamlService.java#L1445
[S34]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/transaction/QuarkusJtaTransactionManagerLookup.java#L36
[S35]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/tracing/OTelTracingProviderFactory.java#L76
[S36]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/resources/META-INF/services/org.keycloak.tracing.TracingProviderFactory#L18
[S37]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/resources/META-INF/services/org.keycloak.transaction.JtaTransactionManagerLookup#L18
[S38]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/jpa/src/main/java/org/keycloak/connections/jpa/AsyncCommitIntegrator.java#L80
[S39]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/jpa/src/main/java/org/keycloak/connections/jpa/PostgreSQLAsyncCommitIntegrator.java#L51

[D01]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi/src/main/java/org/keycloak/models/KeycloakSessionFactory.java#L37
[D02]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/DefaultKeycloakSessionFactory.java#L58
[D03]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/QuarkusKeycloakSessionFactory.java#L35
[D04]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/QuarkusKeycloakSession.java#L28
[D05]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/DefaultKeycloakSession.java#L93
[D06]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/DefaultKeycloakContext.java#L77
[D07]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/models/utils/KeycloakModelUtils.java#L363
[D08]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/models/utils/SessionLookup.java#L22
[D09]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/transaction/RequestContextHelper.java#L57
[D10]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/services/scheduled/ScheduledTaskRunner.java#L54
[D11]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/services/scheduled/NamedSessionTask.java#L31
[D12]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/timer/basic/BasicTimerProvider.java#L80
[D13]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/cdi/KeycloakBeanProducer.java#L39
[D14]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/resteasy/TransactionalSessionHandler.java#L67
[D15]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/transaction/TransactionalSessionHandler.java#L44
[D16]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/resteasy/QuarkusKeycloakContext.java#L36
[D17]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/resteasy/KeycloakHandlerChainCustomizer.java#L40
[D18]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/KeycloakRecorder.java#L223
[D19]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/deployment/src/main/java/org/keycloak/quarkus/deployment/KeycloakProcessor.java#L834
[D20]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/transaction/AsyncResponseTransaction.java#L33
[D21]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/jaxrs/CloseSessionFilter.java#L51
[D22]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/error/KeycloakErrorHandler.java#L65
[D23]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/protocol/saml/SamlService.java#L1445
[D24]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/managers/CodeGenerateUtil.java#L180
[D25]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/protocol/oidc/TokenManager.java#L193
[D26]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/protocol/oidc/grants/AuthorizationCodeGrantType.java#L92
[D27]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/protocol/oidc/grants/ResourceOwnerPasswordCredentialsGrantType.java#L129
[D28]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/protocol/oidc/refresh/AbstractRefreshTokenProvider.java#L260
[D29]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/authorization/policy/evaluation/PermissionTicketAwareDecisionResultCollector.java#L102
[D30]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/infinispan/src/main/java/org/keycloak/models/sessions/infinispan/transaction/DefaultInfinispanTransactionProvider.java#L86
[D31]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/managers/DefaultBlockingBruteForceProtector.java#L86
[D32]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/managers/DefaultLockingBruteForceProtector.java#L123
[D33]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi/src/main/java/org/keycloak/utils/KeycloakSessionUtil.java#L38
[D34]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/DefaultPermissions.java#L35
[D35]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/DefaultKeycloakTransactionManager.java#L51
[D36]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi/src/main/java/org/keycloak/models/AbstractKeycloakTransaction.java#L30
[D37]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/resources/RealmsResource.java#L188
[D38]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/managers/RealmManager.java#L113
[D39]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/resources/admin/AdminRoot.java#L146
[D40]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/resources/admin/RealmsAdminResource.java#L220
[D41]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/protocol/oidc/endpoints/TokenEndpoint.java#L130
[D42]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/transaction/JtaTransactionWrapper.java#L45
[D43]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/jpa/src/main/java/org/keycloak/connections/jpa/JpaKeycloakTransaction.java#L47
[D44]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/transaction/QuarkusJtaTransactionManagerLookup.java#L36
[D45]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/storage/database/jpa/AbstractJpaConnectionProviderFactory.java#L55
[D46]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/storage/database/jpa/QuarkusJpaConnectionProviderFactory.java#L106
[D47]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/jpa/src/main/java/org/keycloak/connections/jpa/DefaultJpaConnectionProvider.java#L42
[D48]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/connections/jpa/support/EntityManagerProxy.java#L93
[D49]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/jpa/src/main/java/org/keycloak/connections/jpa/AsyncCommitIntegrator.java#L80
[D50]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/jpa/src/main/java/org/keycloak/connections/jpa/PostgreSQLAsyncCommitIntegrator.java#L51

[B01]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi/src/main/java/org/keycloak/models/KeycloakSessionFactory.java#L37
[B02]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/DefaultKeycloakSessionFactory.java#L58
[B03]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/QuarkusKeycloakSessionFactory.java#L35
[B04]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/QuarkusKeycloakSession.java#L28
[B05]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/DefaultKeycloakSession.java#L93
[B06]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/DefaultKeycloakContext.java#L77
[B07]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/models/utils/KeycloakModelUtils.java#L363
[B08]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/models/utils/SessionLookup.java#L22
[B09]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/transaction/RequestContextHelper.java#L57
[B10]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/services/scheduled/ScheduledTaskRunner.java#L54
[B11]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/services/scheduled/NamedSessionTask.java#L31
[B12]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/timer/basic/BasicTimerProvider.java#L80
[B13]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/cdi/KeycloakBeanProducer.java#L39
[B14]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/resteasy/TransactionalSessionHandler.java#L67
[B15]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/transaction/TransactionalSessionHandler.java#L44
[B16]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/resteasy/QuarkusKeycloakContext.java#L36
[B18]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/KeycloakRecorder.java#L223
[B19]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/deployment/src/main/java/org/keycloak/quarkus/deployment/KeycloakProcessor.java#L834
[B33]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi/src/main/java/org/keycloak/utils/KeycloakSessionUtil.java#L38
[B34]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/DefaultPermissions.java#L35
[B35]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/DefaultKeycloakTransactionManager.java#L51
[B51]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/Providers.java#L25
[B52]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/provider/ProviderManager.java#L44
[B53]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/provider/DefaultProviderLoader.java#L44
[B54]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/provider/DeploymentProviderLoader.java#L40
[B55]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/provider/FileSystemProviderLoaderFactory.java#L41
[B56]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/provider/DefaultProviderLoaderFactory.java#L31
[B57]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/resources/META-INF/services/org.keycloak.provider.ProviderLoaderFactory#L19
[B58]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/provider/KeycloakDeploymentInfo.java#L24
[B59]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/resources/KeycloakApplication.java#L76
[B60]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/jaxrs/QuarkusKeycloakApplication.java#L74
[B61]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/KeycloakMain.java#L68
[B62]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/deployment/src/main/java/org/keycloak/quarkus/deployment/KeycloakSessionFactoryPreInitBuildItem.java#L26
[B63]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/resources/META-INF/quarkus-extension.yaml#L2
[B64]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/pom.xml#L43
[B65]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/pom.xml#L30
[B66]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/pom.xml#L14
[B67]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/deployment/pom.xml#L16
[B68]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/server/pom.xml#L17

[B69]: https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/deployment/src/main/java/org/keycloak/quarkus/deployment/LiquibaseProcessor.java#L34
