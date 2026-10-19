# ADR 0004: Issuer-core ownership, storage and conditional acquisition

Date: October 19, 2026.
Status: **accepted for bounded prototype research only**. The repository owner
approved P1 on October 19, 2026. This authorizes isolated feasibility work and
review of the experiment. It does not adopt a production fork, storage, version
upgrade, provider installation, grant, adapter or deployment. Current application
behavior and disabled guards are unchanged.

## Accepted research decision and scope

Proceed with **one bounded, isolated issuer-core feasibility prototype**, with a
hard stop if complete writer and transaction closure cannot be demonstrated.
Do not adopt an extension-only approximation. Do not adopt a production fork as
a consequence of approving research. An alternative is to retain stock Keycloak
and leave this capability unavailable. The owner selected P1; the alternative remains documented for comparison.

For research, this supersedes only the extension-only implementation direction
of proposed [ADR 0002](0002-issuer-association-readback.md) and the implementation
choice left open by [ADR 0003](0003-association-consistency-and-issuance.md).
It preserves their pre-acquisition non-creation/authority requirements and the
explicit proposed point-in-time contract. It does not accept that proposed
contract, repair old latest-at-response failures, or change current wire behavior.
[ADR 0001](0001-case-runtime.md), Temporal and `case_runtime` are unchanged.

| Owner option | Engineering consequence |
| --- | --- |
| P1 — bounded issuer-core prototype, recommended | Authorize isolated experimental patch work and its version-specific build/migration tests after source closure. Stop on a failed gate. Decide long-term support only after evidence; no production fork or deployment is accepted. |
| P2 — stock issuer, feature unavailable | Avoid issuer-core patch ownership. Conditional acquisition and affected IAM/gateway migration acceptance remain open until supported hooks or an explicitly accepted alternative exist. |

No upstream change has been submitted or accepted. A maintained upstream facility
would be preferable to a permanent owned patch, but cannot be assumed to exist.
A weaker pre-token requirement, different issuer or receiver-based substitute
needs its own explicit superseding decision; it is not an automatic fallback.

## Evidence and explicit no-go result

The [source feasibility review](../keycloak-issuer-feasibility.md) pins Keycloak
26.8.1 commit `24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b`. Its account-missing denial
improves on historical 26.0.6; it supplies no full aggregate fence. All 18 old
experiments, nine failed gates and R1 attribution/health limits remain unchanged.

This decision review additionally inspects transaction/entity-manager, Quarkus
augmentation, native Liquibase and bulk/background writer paths. The 22 writer
surfaces remain an inventory, **not complete transitive hook closure**. Therefore:

- **NO-GO:** R3/R4 implementation, enrolled issuance or caller adoption now.
- **Approved research only:** prove or reject the missing core boundaries before
  implementing snapshot/grant/storage behavior. Approval of P1 cannot turn an
  unproved hook into a passing gate.
- **Owner decision received:** P1 bounded research; production fork ownership remains a separate decision.

`runAsReadOnly` is a session flag. The reviewed entity-manager proxy changes query
flush mode in that scope, and tracks some update calls for durability; it still
invokes the underlying operations. This is not database-enforced read-only
snapshot isolation or a universal writer guard. Model adapters dirty entities,
bulk queries call `executeUpdate`, and explicit flushes occur before request end.
A commit listener or REST wrapper is too late to establish the shared boundary.

## Candidate patch boundary and writer closure

These are **required new core changes**, not APIs already supplied by Keycloak.
Exact changed methods and proof of every transitive call remain an exit gate.

| Boundary and actual source seams | Required change or enforceable exclusion |
| --- | --- |
| `TokenEndpoint`, `AuthorizeClientUtil`, native authentication processor and all grant factories | Resolve trusted enrollment before relevant effects; retain real native client authentication; allow only the fixed conditional profile for enrolled clients. `preProcess` runs before ordinary native authentication and special grants differ. |
| Authorization/browser/broker/SAML, exchange, refresh, password, device, CIBA, JWT, UMA and pre-authorized paths | Prove mandatory enrolled-profile denial on every entry, including direct route and alternate authenticator calls. Realm/client settings alone are insufficient. |
| `RealmCacheSession`, JPA adapters/providers, new-session and entity-manager lifecycle | Read fresh immutable projections with known isolation and cardinality; never reuse the stale request-managed association for signing. Separate authentication context from the protected snapshot. |
| Admin REST/UI/SDK, realm/client/user lifecycle, mappers/scopes/roles/groups/credentials and registration | Enter the same protected writer scope before protected reads or entity mutation, not at flush. Preserve authorization and request compatibility; advance revisions atomically. |
| `JpaRealmProvider`, `JpaUserProvider`, `JpaUserCredentialStore`, client/group/role adapters, bulk/native queries | Include explicit flush, cascade delete, bulk update and dependent rows. ORM entity callbacks alone cannot cover bulk/native paths. |
| Representation/partial imports, bootstrap/migrations, operator recovery | Fence or stop every issuer node and enter maintenance. An offline writer cannot run concurrently with enrolled issuance. |
| Federation/synchronization, native lifecycle workflows, custom providers/mappers and background jobs | Either prove the same scope or deny the profile. Unknown provider/store/image builds cannot enroll. A provider executes with server privileges, not in a sandbox. |
| `TokenManager`, transaction manager, synchronous `CloseSessionFilter`, async/streaming handlers | Bind native signing/mapping to verified state; prove durable commit before any usable response bytes. Forbid streaming/async acquisition in the initial profile. |

The complete category list includes keys/signing policy, secret/registration
rotation, revocation/logout and direct database/operator actions. Source seams
do not enforce participation. A malicious provider or arbitrary issuer DB writer
has server-level authority and is outside a plugin-sandbox promise. Supported
online builds must be immutable and restricted to reviewed providers; unreviewed
changes force unavailable/maintenance and requalification.

## Proposed storage contract

Candidate: the **issuer primary PostgreSQL transaction**, with issuer-owned JPA
mappings and native Liquibase lifecycle. No application vendor-DB credentials,
second application registry, distributed lease or independent authority store.
The following are logical design records, not adopted table/column names or DDL.
No database release, physical schema, lock primitive or deployment configuration
is selected by this document.

| Logical record | Required fields and invariants |
| --- | --- |
| Enrollment/recovery | Exact realm UUID/incarnation, externally replaced deployment-recovery incarnation, immutable profile version, disabled/enrolled/maintenance state and non-wrapping monotonic revision. Normal observation cannot provision it. |
| Realm authority generation | Realm/recovery incarnation and non-wrapping monotonic sequence. Conservatively invalidate on every covered identity/tenant/policy/mapper/scope/role/group/credential/grant/key dependency change. Do not use timestamps, policy hashes, UUID alone or token IDs as the sequence. |
| Acquisition attempt | Realm/recovery incarnation, authenticated internal client UUID, bounded attempt ID, condition digest, fixed operation profile, terminal consumed state and issuer expiry. Enforce uniqueness and exact binding atomically. Store no token, secret or reusable response. |

Realm-wide serialization is the initial design candidate; dependency-specific
versions require a later proof. It can limit throughput within a realm. Capacity,
deadlock/starvation and availability must be measured; no performance estimate or
HA guarantee follows from the design.

## Transaction, snapshot and recovery semantics

1. Provision enrollment and fresh incarnations only through protected, audited
   maintenance. No observation creates or repairs identity, mapper or enrollment
   rows. Resolve exact IDs and reject ambiguous/missing state.
2. For observation, create a clean issuer-owned transaction before the first
   protected read. Prove a primary-store consistent snapshot, database read-only
   enforcement and immutable scalar projections independent of request/JPA caches.
   Authenticate the management principal normally and verify its current grant
   within the declared consistency boundary. A session flag is insufficient.
3. For acquisition and all participating writers, establish the same durable
   serialization boundary **before protected reads and mutation**. Re-reading
   after a stale model was already modified is insufficient. Candidate order is
   deployment/enrollment/recovery, then realm barriers in canonical UUID order,
   then attempt uniqueness, then dependency projection. Initial scope rejects
   cross-realm operations. Exact lock/isolation APIs and transaction coupling
   still need source proof and explicit selection.
4. Native authentication must bind the exact client and current credential state
   under that boundary; no auth-result injection. Recheck fixed grants, subject
   link, enabled states, generation and all effective token dependencies before
   native token building. Missing account, mapper, scope or uncertain state denies;
   no repair. Sign only native claims and never accept caller-selected identities,
   tenant, audience, scope, target or arbitrary grant parameters.
5. Atomically consume the bound attempt with successful comparison. Do not return
   a usable token until the real durable transaction commits. Native session/event
   side effects must be classified and included. Never infer synchronous durability
   from HTTP success or from the stock ephemeral async-commit policy.
6. A timeout, lost node/fence, rollback, persistence failure, partition or deadline
   while waiting denies release and downstream dispatch. Canonical ordering and
   bounded deadlines must prevent indefinite waits; retry with a fresh observation
   and bounded budget. Transaction ownership cannot be an expiring process lease.
7. Crash after durable commit can consume an attempt without delivery. Reusing the
   same attempt never returns stored bearer bytes. A conflicting duplicate denies.
   A new attempt requires fresh observation and a new current authorization check.
8. Reject expired conditions. Attempt cleanup must wait beyond condition validity,
   clock/skew and replay/retry windows, or retain a tombstone. No cleanup may allow
   a still-valid old condition to replay. The exact bounds are qualification inputs,
   not implicit defaults.
9. Retain a parent epoch/tombstone across delete/recreate and disable/re-enable.
   Restore cannot trust an epoch in the restored backup: quiesce all nodes, replace
   an external recovery incarnation, reconcile grants/keys/credentials and validate
   the entire profile before reopening. A direct online vendor DB change is not
   made safe by a cache TTL or event listener.

Disabling after issuance does not revoke an already-issued token automatically.
Receiver-side online revocation/generation checks, outage behavior or explicitly
accepted bounded lifetime require a separate compatibility decision. Current
offline JWT/JWKS validation and local lease remain unchanged.

## Mapping, migration and build ownership

Any eventual issuer schema change must include paired issuer mappings and native
Liquibase change/validation/upgrade tests. Application SQLAlchemy/Flyway remains
the owner of application tables; do not use it to mutate vendor storage. This
document contains no schema change and grants no migration exception.

In the pinned source, Quarkus build steps configure entity discovery and contribute
standalone `orm.xml` to the default persistence unit; custom units have separate
rules. `JpaEntityProvider.getEntities()` is ignored in production, while native
Liquibase still visits custom provider changelogs. These are separate mechanisms.
An isolated future fixture must demonstrate exact default-unit mapping, no second
authority datasource, installed entity metadata, change validation, constraints
and rollback/upgrade/restore behavior. An unexecuted upstream test is not our proof.

Custom JPA extension APIs are explicitly unsupported. Provider installation also
requires a reviewed server build/augmentation; a copied JAR is not proof that
entities, guards or images are active. No API/build compatibility across releases
is promised. No code or dependency is added in this decision review.

## Ownership and go/no-go gates

P1 requires a named maintainer before experimental patch work and named long-term
release, migration, security and incident owners before any deployment. No people,
support contract or funding are assigned by this document. Owning a patch entails:

- Tracking upstream security releases, reviewing diffs and rebasing exact hooks;
  no claim of upstream support or an automatic backport path.
- Rebuilding and checking source/dependency/license/image provenance and provider
  admission, native authentication, mapping/signing and all old negative cases.
- Qualifying PostgreSQL primary/replication durability, distributed caches, supported
  stores, restart/failover/partition, concurrency/deadlock/replay and recovery epochs.
- Preserving schema history, populated upgrades, rollback restrictions, backup and
  restore, protected credential/grant distribution and audit operations.

| Gate | Present result |
| --- | --- |
| Owner selects P1 or P2 | P1 approved for bounded research; production ownership unassigned |
| Exact mandatory entry/writer hook closure | Not proved; NO-GO |
| Paired storage, entity discovery and durable transaction contract | Proposed only; NO-GO |
| R3/R4 prototype admission | Blocked until the required decision and closure gates pass |
| R5 full provider/native SQL/maintained-version/security/license/image/runtime qualification | Open |
| R6 scoped stock-response/acquisition compatibility and caller adapter | Open |
| R7 rights/custody/provisioning/rotation/revocation/data/actual caller adoption | Open |

The P1 approval authorizes bounded research, not acceptance of these gates. If full
closure cannot be demonstrated, record the negative result and retain unavailable
authority; do not replace it with a token proxy, second signer, local CAS or
weaker pre-acquisition boundary. Existing IAM/service restoration remains required
Phase 1 migration work. Tasks 6/7 and private-repository retirement remain open.

## First bounded prototype evidence

The [compiler-assisted core audit](../../../infra/keycloak/keycloak_registration_connector/qualification/core_audit/README.md)
is now an executable opt-in research component. Two final runs verify and parse
6,441 main-source-layout Java files and 299 service declarations identically;
testsuite/helper modules are reported separately. All 15 fault controls pass.
This is syntax inventory, not a production callgraph, vendor build or core patch.
It identifies Client Admin API v2 and native realm SCIM writer entry families
that expand the concrete source map within the existing 22 writer categories.
Their feature/profile activation and complete enforcement remain unproved.
R2 implementation/R3/R4 and all R5–R7/ancestor gates remain open.

The paired [native token-entry experiment](../../../infra/keycloak/keycloak_registration_connector/qualification/entry_guard/README.md)
now compiles the exact endpoint source and a one-line early method-body overlay
against the matching 26.8.1 SDK. Both variants pass 34 tests, including real native
client-secret authentication and missing-account denial; eight input controls
pass. Closed/unknown fixtures stop before grant lookup or preprocessing. Test-owner
unmanaged controls preserve native negative outcomes without issuing tokens.
This is not durable enrollment, an HTTP admission boundary or all-grant execution.
The [native admission review](../keycloak-native-admission.md) now traces the
front-door, construction, alternate entry and failure paths against 54 pinned
source/service units. It identifies earlier realm/event-provider reads, internal
constructors, fresh-session SAML artifact work and HTML error-path realm resolution.
It proposes deployment, minimal primary admission lookup and native operation
scope layers; none are implemented or fully closed. The paired
[early realm-denial experiment](../../../infra/keycloak/keycloak_registration_connector/qualification/realm_entry/README.md)
now tests the resolver hook, native authentication controls and minimal direct
failure path: 260 test cases/six preparation controls pass. A synthetic rollback
participant failure is not propagated by the native manager despite reported
session close. The [rollback lifecycle comparison](../../../infra/keycloak/keycloak_registration_connector/qualification/rollback_lifecycle/README.md)
now demonstrates a limited two-site candidate for participant-loop runtime-error
propagation (310 test cases/six input controls). Full cleanup, tracing/provider/
prepare/commit branch behavior and durable outcomes remain NO-GO/unqualified.
The next bounded review defines lifecycle containment and participant contracts.
All entry/writer/storage/compatibility gates remain unqualified. No production
fork, provider artifact, current guard or application behavior is adopted.

## Primary source references

All code links use the reviewed immutable upstream commit. No upstream server or full vendor
test suite was run. The bounded native-source fixture is documented separately. The [decision record](../../../infra/keycloak/keycloak_registration_connector/issuer-core-decision-review.json)
distinguishes proposal, source evidence and unmet implementation gates.

- [Entity-manager proxy](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/connections/jpa/support/EntityManagerProxy.java),
  [session read-only flag](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/DefaultKeycloakSession.java#L158).
- [Quarkus entity/persistence build steps](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/deployment/src/main/java/org/keycloak/quarkus/deployment/KeycloakProcessor.java#L510),
  [native custom changelog lifecycle](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/jpa/src/main/java/org/keycloak/connections/jpa/updater/liquibase/LiquibaseJpaUpdaterProvider.java#L114).
- [Bulk user deletion](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/jpa/src/main/java/org/keycloak/models/jpa/JpaUserProvider.java#L172),
  [workflow transaction tasks](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/models/workflow/WorkflowTransactionalTask.java).
- [Unsupported custom JPA API](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/docs/documentation/server_development/topics/extensions.adoc#L100),
  [provider build and privilege model](https://www.keycloak.org/server/configuration-provider),
  [upstream security maintenance policy](https://www.keycloak.org/security).
