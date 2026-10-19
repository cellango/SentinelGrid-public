# Keycloak issuer feasibility review

Status: **source review complete; stock-extension implementation is NO-GO**.
Reviewed October 19, 2026. This is a proposed architecture direction, not an
accepted issuer change or runtime qualification. The current provider remains
disabled and the existing caller guard remains closed.

## Exact candidate and evidence

Review Keycloak **26.8.1**, commit
`24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b`, released October 13, 2026.
It is the current [upstream download](https://www.keycloak.org/downloads) at review
time; upstream [security policy](https://www.keycloak.org/security) directs users
to the current release stream. This selects a source-review candidate only.
Historical 26.0.6/H2/Java 21 experiments establish no behavior for this release.
See the [release fixes](https://www.keycloak.org/2026/10/keycloak-2681-released)
and [machine-readable review](../../infra/keycloak/keycloak_registration_connector/issuer-feasibility-review.json).

The commit-addressed upstream archive is 51,988,209 bytes, SHA-256
`f67ec723e2eaf46b2d38f167ecb7578964115f1f2ce203f9b6659322223d9874`.
HTTPS metadata plus these hashes provide reproducibility, not independent
signature verification. Upstream [license](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/LICENSE.txt)
is Apache-2.0. No upstream code, binary, dependency, image or manifest is added
to this repository by the review. Transitive artifacts, image digest, SPI/build
compatibility, current advisories and deployment qualification remain separate.

## A material change from the historical candidate

In 26.8.1 [ClientCredentialsGrantType](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/protocol/oidc/grants/ClientCredentialsGrantType.java#L68),
an absent service account returns an error. The method no longer calls the
historical account/default-mapper repair fallback. This is an improvement in
the reviewed source, not a new runtime result or clearance of the old failures.
It still creates authentication/session context and invokes native mappers;
those effects need their own instrumentation and authority classification.

[ClientManager](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/managers/ClientManager.java#L160)
still provisions accounts and service-account scopes through admin/registration
paths. A missing default scope must have an explicit deny policy; source removal
of repair does not prove the expected token claims. The historical requirement
remains: no credential acquisition or repair before the condition is enforced.

## Source/API decision matrix

| Boundary | Exact source finding | Decision |
| --- | --- | --- |
| Native client auth and grants | `TokenEndpoint` calls grant pre-processing before native client authentication, then normally dispatches `grant.process`. UMA and pre-authorized grants have special paths. | Useful seam; no universal condition guard. |
| Snapshot and cache | `RealmCacheSession` retains request-managed clients; `JpaUserProvider` uses managed entities. A new session utility exists, but provider entity managers use AUTO flush and do not supply a qualified immutable multi-object snapshot. | No stock snapshot contract proved. |
| Generations | Reviewed realm/client/user/scope/mapper entities have no aggregate incarnation/generation. `CredentialEntity` has its own optimistic version. | Credential version cannot substitute for the whole dependency revision. |
| Complete writer fence | Admin/model/registration/import/federation/background paths mutate independently. | No common durable fence established. |
| Conditional native issuance | OAuth grant SPI and native response/signing builders exist; no reviewed API atomically compares this aggregate condition and issues. | New grant alone is insufficient. |
| Anti-replay | JPA single-use objects implement atomic insertion and locked removal. | A replay record does not serialize unrelated identity/policy writers. |
| Before-response commit | Ordinary synchronous entity responses pass `CloseSessionFilter`, which closes the session; transaction errors propagate. Streaming output closes after writing, and async handlers differ. | Candidate synchronous seam only; failure/serialization/HTTP proof required. |
| Durable commit | Current source permits asynchronous commits for some ephemeral session/event-only transactions. | A future condition/attempt transaction must force and verify its required durability; no default assumption. |
| Storage extension | Custom JPA entities use Liquibase; upstream calls this API unsupported. `getEntities()` is deprecated and ignored in production in this tag. | Exact augmentation/entity discovery and core/storage lifecycle must be designed and qualified. |

Source locations for the matrix are pinned in the reference table below. These
findings establish a **NO-GO for treating the existing extension as sufficient**.
They are not a proof that no possible issuer implementation could meet the contract.

## Writer and bypass coverage required

The review groups 22 writer surfaces. This is a boundary inventory, not a complete
transitive call graph or proof that every extension participates.

| Surface | Required treatment |
| --- | --- |
| Admin REST/UI and SDK client/user operations | Fence create/delete/disable/rebind, attributes, account setup, grants and credentials. UI/SDK transport shares APIs but adds no fence. |
| Realm/authentication policy, mappers, scopes, roles/composites and groups | Include every effective token/tenant/permission dependency, not only the client/user row. |
| Credentials, registration access, secret rotation, revocation and logout | Couple current authority and revisions; distinguish already-issued token admission. |
| Dynamic registration and service-account provisioning | Enforce enrolled-profile restrictions before provisioning or claim-policy changes. |
| Representation/partial/offline import and bootstrap/migrations | Review paths that bypass individual resources. Offline work requires all-node quiescence and recovery-epoch replacement. |
| Federation, synchronization and custom stores | Exclude unsupported sources enforceably; rejecting one federated subject is not complete writer coverage. |
| Native issuer lifecycle workflows | Disable/delete user/client steps are real background model writers in this release. Include or deny them. |
| Native issuance, model setters and custom providers | Native auth, mapper execution, session writes and provider code cannot bypass the same barrier. Unknown writers deny enrollment. |
| Operator restore or direct database changes | No online guarantee. Quiesce, replace a recovery epoch outside the restored snapshot, reconcile and requalify before reopening. |

Enrollment must forbid stock client credentials, refresh, password, code/browser,
exchange, device/CIBA/JWT/pre-authorized/UMA and alternate protocol/authentication
routes unless each exact path is admitted. A grant `preProcess` hook lacks the
authenticated principal at that point; a late service-account policy or internal
token postprocessor is not an all-entrypoint guard. Settings alone do not prevent
an administrator from restoring a bypass. A mandatory issuer-owned enrollment
check and protected writer policy are necessary before granting this capability.

## Proposed version, storage and compatibility direction

Keep the present implementation closed. If this consistency contract is retained,
the next decision must explicitly choose ownership of an upstreamable issuer-core
change or a maintained issuer fork. **Do not implement R3/R4 with an approximate
extension-only fence.** No fork or vendor-storage schema is adopted by this review.

The candidate storage design is issuer-owned state on its primary PostgreSQL
transaction, with paired issuer JPA mappings and native Liquibase lifecycle.
Application SQLAlchemy/Flyway continues to own application state only. No
SentinelGrid application receives vendor database credentials. Physical tables,
lock primitives, isolation configuration and a PostgreSQL release are undecided.

The decision must specify these coupled logical records and lifecycle semantics:

- A protected realm enrollment/recovery incarnation and monotonic authority epoch.
- A conservative realm-wide change sequence and retained deletion/tombstone
  semantics covering all enrolled dependency writers, including credential/grant
  revocation. Scoped generations are a later optimization.
- Bounded attempt records binding authenticated client, condition digest and
  operation, atomically committed with the comparison; never token bytes. Expiry,
  replay, duplicate conflict, cleanup and restore must not resurrect authority.

All relevant writers must acquire the same issuer-owned transaction barrier
before reading/modifying protected dependencies and advance the sequence in the
same successful transaction. A pre-existing realm barrier can cover missing-row
and phantom cases only after every writer is enforced. Read observation must not
create rows; immutable projections need a separately proved snapshot/cache/flush
boundary. Attempt state and generation cannot be in an independent application
database or an expiring distributed lease. This is a design obligation, not a
selected row-lock implementation or proof of feasibility.

Acquisition remains native authentication and signing, with an observation-v2
condition and versioned conditional grant. Native builders must consume the
verified state under the barrier, deny missing account/scope/mapper/grant state,
and release an ordinary non-streaming token response only after durable commit.
Crash after commit can consume an attempt without delivery; timeout means no
downstream dispatch. No token is replayed from a stored attempt.

The new point-in-time contract in [ADR 0003](decisions/0003-association-consistency-and-issuance.md)
requires explicit review. It does not satisfy the old latest-at-response oracle.
Disabling after issuance still needs a separately accepted receiver revocation
policy. The existing Python metadata reader, stock-response association guard,
local lease, IAM validation and fixed-ticket client are unchanged. R6 must review
both response and acquisition compatibility before an adapter is introduced.

## Ownership cost and next gate

Core ownership means tracking every upstream patch/security release, rebasing and
testing model and grant hooks, all admitted providers, build augmentation,
transaction/cache behavior, schema upgrades/rollback/restore, HA failover, key and
credential lifecycle and operational incident response. Adding one provider JAR
does not purchase those guarantees. If that ownership is unacceptable, stop and
make a superseding contract/issuer decision; do not relax the boundary implicitly.

**R2 source review is delivered; its implementation-decision gate remains open.**
Next prepare the concrete issuer-core ownership, storage and compatibility ADR,
including exact hook placement, writer closure/exclusions and a go/no-go gate.
R3 snapshot and R4 conditional issuance cannot start from this review alone.
Remaining R1 instrumentation limits, all 18 historical witnesses/nine failed
gates and full R3–R7 runtime/custody/data/caller qualification remain required.
All existing IAM and service restoration obligations remain migration work.

## Concrete ownership and storage proposal

The proposed [ADR 0004](decisions/0004-issuer-core-storage-and-compatibility.md)
compares a bounded owned core prototype with retaining stock/unavailable behavior.
It details logical storage, transaction ordering, writer exclusions, recovery and
maintenance costs. The owner approved P1 bounded prototype research. Complete
hook closure and R3/R4 admission remain open; no production fork or deployment
is adopted. The R2 implementation NO-GO remains.

## Pinned source references

| Topic | Primary source |
| --- | --- |
| Auth and grant dispatch | [TokenEndpoint](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/protocol/oidc/endpoints/TokenEndpoint.java#L130), [AuthorizeClientUtil](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/protocol/oidc/utils/AuthorizeClientUtil.java#L48) |
| Cached and JPA lookups | [RealmCacheSession](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/infinispan/src/main/java/org/keycloak/models/cache/infinispan/RealmCacheSession.java#L1187), [JpaUserProvider](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/jpa/src/main/java/org/keycloak/models/jpa/JpaUserProvider.java#L712) |
| Entity manager and new session | [AbstractJpaConnectionProviderFactory](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/storage/database/jpa/AbstractJpaConnectionProviderFactory.java#L120), [KeycloakModelUtils](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/models/utils/KeycloakModelUtils.java#L524) |
| Commit and response | [CloseSessionFilter](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/jaxrs/CloseSessionFilter.java#L51), [DefaultKeycloakSession](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/DefaultKeycloakSession.java#L380) |
| Native encode and postprocessing | [TokenManager](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/protocol/oidc/TokenManager.java#L1462) |
| Anti-replay primitives | [JpaSingleUseObjectProvider](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/jpa/src/main/java/org/keycloak/singleobject/jpa/JpaSingleUseObjectProvider.java#L73) |
| Unsupported JPA extension and durability | [Extension documentation](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/docs/documentation/server_development/topics/extensions.adoc#L100), [database documentation](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/docs/guides/server/db.adoc#L301) |
| Background writer examples | [DisableUserStepProvider](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/models/workflow/DisableUserStepProvider.java#L48), [DeleteClientStepProvider](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/models/workflow/client/DeleteClientStepProvider.java#L53) |
