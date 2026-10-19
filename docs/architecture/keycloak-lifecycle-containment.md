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

The [source record](../../infra/keycloak/keycloak_registration_connector/lifecycle-containment-review.json)
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

## Proof sequence and next bounded experiment

1. **Next: integrated native abort/close outcome experiment.** In new owned
   temporary projects, compare unmodified source, the preserved two-catch-site
   control, and one isolated candidate covering LC-01/02/04/05 together. Exercise
   actual pinned native manager/session/abstract transaction/thread-close paths,
   synthetic classified participants and adversarial observational hooks. Retain
   all earlier native negative witnesses and real native-auth/non-creation tests.
   Explicitly withhold success/release on failed/unknown outcome; prove no default
   commit fallback and no duplicate callback/retry. Include prepare no-op/paired/
   independent-effect classifications as limits, not fake real-provider proof.
   A source-only outcome record is not durable admission or full cleanup. Record
   a concrete negative result if this boundary cannot be demonstrated.
2. Only after that bounded result, qualify actual selected provider/JTA/JDBC/cache
   participation and durability (LC-03/06/08), and framework response/denial
   ownership (LC-07), in separately isolated synthetic runtime work. Select exact
   prerequisite builds/licenses/security inputs first; no live issuer/state.
3. Complete mandatory admission, all writers, storage/attempt/recovery, response
   durability and compatibility gates (LC-09/10 and R3–R7) before any successful
   protected issuance or caller adoption. A lifecycle test pass cannot advance
   R2 implementation or R3/R4 by itself. A production fork/version/deployment
   remains a separate later decision.

This review closes the **bounded design task only**. Full cleanup/containment,
HTTP/native SQL durability, bootstrap/admission, writer closure and all old 18
witnesses/nine failed latest-at-response gates remain open, including R1
attribution/health/error/async/driver/deferred-effect and earlier 503 limits.
The proposed point-in-time semantic contract, R3–R7, credential custody/grants/
provisioning/rotation/revocation/CAS/audit, actual claims/JWKS/mappers/scopes/tenant,
paired models/Flyway/RLS/existing-data/upgrades/restore and caller adoption remain
required. The two historical build-helper license declarations and deprecated
test-only API remain limitations; no dependency or artifact is added.

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
