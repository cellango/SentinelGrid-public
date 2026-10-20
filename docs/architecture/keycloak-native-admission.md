# Native issuer admission design review

Status: **proposed core patch design; full admission closure remains NO-GO**.
Reviewed October 19, 2026 under the bounded research approval in
[ADR 0004](decisions/0004-issuer-core-storage-and-compatibility.md).
No application/provider implementation, runtime dependency, schema, deployment,
production fork or current guard changes are supplied by this review.

The [native token experiment](../../infra/keycloak/keycloak_registration_connector/qualification/entry_guard/README.md)
established one early **method-body** interception point. Its 68 native/control
tests and eight input controls are retained evidence, not rerun results here.
This review compares **54 exact source/service units and 85 location anchors**
with the pinned Keycloak 26.8.1 archive at commit
`24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b`. The
[machine-readable review](../../infra/keycloak/keycloak_registration_connector/native-admission-review.json)
records hashes, source anchors, all ten grant declarations, required treatment
and explicit unknowns. No vendor classes, issuer, database, actual workload
credential/token acquisition or network provider operation was run in this unit.

## Concrete gaps before and around token dispatch

1. [The invocation handler](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/resteasy/TransactionalSessionHandler.java#L67) establishes request scope, unwraps the session and may begin a transaction before invoking resource methods. [The handler customizer](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/resteasy/KeycloakHandlerChainCustomizer.java#L50) also adds form handling before method invocation. [The CDI producer](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/cdi/KeycloakBeanProducer.java#L39) creates sessions lazily and explicitly defers JTA work out of the event loop. These declarations do not prove the complete deployed filter/body-reader/provider ordering; a method hook is too late to claim it.

2. [The protocol locator](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/resources/RealmsResource.java#L109) calls realm resolution, looks up the protocol factory and constructs EventBuilder before creating the endpoint. [Realm resolution](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/resources/RealmsResource.java#L188) returns an ordinary RealmModel through RealmManager and [the realm cache](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/model/infinispan/src/main/java/org/keycloak/models/cache/infinispan/RealmCacheSession.java#L528). Setting context also invokes [tracing](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/DefaultKeycloakContext.java#L269) and MDC provider paths. [EventBuilder construction](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/events/EventBuilder.java#L68) reads event policy and initializes configured/global listener providers. These are real earlier reads/provider calls, not qualified admission bootstrap.

3. Native dispatch reaches preprocessing before ordinary client authentication; [UMA and pre-authorized grants differ](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/protocol/oidc/endpoints/TokenEndpoint.java#L160). The ten factory declarations do not cover authorization initialization, callbacks or unknown extension providers. [Authorization code directly constructs LoginActionsService](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/protocol/oidc/endpoints/AuthorizationEndpoint.java#L260); [broker code does too](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/resources/IdentityBrokerService.java#L1275); [IdpLinkAction constructs the broker service](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/broker/provider/IdpLinkAction.java#L164). A locator-only hook misses direct internal construction. Literal caller searches found one TokenEndpoint, two broker and three login-action constructor sites in services/main and quarkus/runtime/main; this is not resolved or complete transitive/dynamic caller closure.

4. [SAML artifact handling schedules work](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/protocol/saml/SamlService.java#L438) through [a fresh transaction/session](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/server-spi-private/src/main/java/org/keycloak/services/scheduled/ScheduledTaskRunner.java#L54). [The worker](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/protocol/saml/SamlService.java#L1470) rebinds HTTP context, looks up the realm, builds an event and dispatches an upstream artifact request. Earlier code can also sign an artifact request. An HTTP thread-local guard or token encoder guard covers neither sequence.

5. [The generic error mapper](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/error/KeycloakErrorHandler.java#L65) marks rollback, but its HTML branch [resolves the realm again](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/error/KeycloakErrorHandler.java#L162) and invokes theme/locale/rendering providers. An early guard that throws through that branch can re-enter protected reads. [The rollback exception](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/services/src/main/java/org/keycloak/services/RollbackWebApplicationException.java#L37) depends on the thread-bound session, and [response close](https://github.com/keycloak/keycloak/blob/24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b/quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/integration/jaxrs/CloseSessionFilter.java#L51) treats streaming specially. Neither proves safe pre-admission failure or commit-to-HTTP durability.

## Proposed core boundary

This needs three cooperating patch layers. They are design obligations, not
existing Keycloak APIs or sufficient closure proofs:

| Layer | Exact candidate patch surface | Required behavior and unresolved proof |
| --- | --- | --- |
| A0: request/deployment gate | Quarkus router registration, method scanner/handler chain and session producer, before ordinary resource/provider construction | Require an immutable reviewed build and available admission authority; normalize/classify routes without trusting forwarded/path/body hints as identity. Establish safe blocking lifecycle before any primary-store work. Framework filters, body readers, exception paths and non-realm routes still need actual ordering proof. |
| A1: minimal realm admission | New issuer-owned lookup before `RealmsResource.resolveRealmAndUpdateSession` calls `RealmManager`; independent admin/worker/internal entries require equivalent lookup | Read only canonical realm UUID/incarnation and protected enrollment/recovery/profile/revision data. Do not fetch ordinary cached/managed RealmModel or initialize events/identity providers to decide admission. Exact primary-store API, isolation and transaction coupling are unproved. |
| A2: native operation scope | Protocol/resource factories, internal constructors/operations, authentication processors, workers, writers and native response/signing paths | Require the correct scope before protected effects; retain real native auth and target authorization. Revalidate on reentry, realm binding, resume/retry and native emission. Every writer must share the durable barrier or be enforceably excluded. No new signer or parallel identity authority. |

A guard in `DefaultKeycloakContext.setRealm` can detect an invalid transition
before trace/MDC calls, but the realm may already have been fetched. It cannot
replace A1. A guard in the native encoder can detect unscoped emission, but
authentication, mappers, grants, sessions, SAML or credential builders may already
have effects. It cannot replace A0/A1/A2 operation entry or the writer fence.

### Admission identity and bootstrap reads

Treat a decoded realm path, alias, client ID or unverified token issuer as an
**untrusted target hint**. Resolve it through issuer-owned primary admission
authority to an exact canonical UUID and incarnation. Bind deployment/recovery
epoch, enrollment state, profile version, revision and operation identity.
This lookup establishes target classification, never caller authentication.
Native authentication must still establish the principal and authorization must
bind that principal to the target tenant and exact operation. Downstream
SentinelGrid programmatic interfaces remain UUID-only.

An admission lookup is a narrow exception for the data needed to decide whether
ordinary protected reads may begin. It must not load user/client/credential/grant/
mapper/scope/policy/key/session data, eagerly hydrate an ordinary realm adapter,
create missing records, trigger repair, or obtain workload credentials/tokens.
The current cache/RealmManager path has not proved that exception. The required
new primary-store read interface and transaction boundary are an explicit
prerequisite; a lookup stub or an in-memory map cannot qualify them.

Only an **authoritative explicit unmanaged classification** can preserve the
unmanaged native path. Absent enrollment rows are not proof of unmanaged state.
Unknown, ambiguous, stale, unavailable, restored or mismatched epoch/revision/
profile/build state must stay closed. No TTL cache, route allowlist, application
registry, independent-store lease, client header or thread-local fixture can grant
admission. Provisioning, rename/delete/recreate and recovery must maintain the
admission directory under the same protected lifecycle; no physical storage or
native migration implementation is selected here.

Before ordinary managed state is exposed, establish the required issuer-owned
operation/fence scope. Any preliminary auth-provider reads/writes, brute-force
counters, audit/provider initialization or repair must be classified within it;
calling native authentication does not waive those effects. Native authentication
still precedes credential/token acquisition. Reacquire/revalidate on every job,
nested operation, new session, realm/client transition, retry or resume. Never
serialize a thread-local admission object as a reusable bearer capability.

Admin requests illustrate the distinction: `AdminRoot` parses the issuer as a
lookup hint before native bearer verification, while `RealmsAdminResource` later
selects an operation target. Principal and target realms need separate explicit
classification, native verification and target authorization. Do not give admin,
master realm, discovery or error handling a blanket exemption. The initial
single-realm restriction and any required management bootstrap flow remain
compatibility work; this review does not silently authorize cross-realm effects.

## Route-to-hook closure matrix

Each row remains **unproved for complete transitive and runtime closure**. These
18 review families are not a total endpoint count or a retirement list. The
machine-readable record binds every row to exact source locations.

| Family | Required treatment before relevant effects |
| --- | --- |
| OIDC token: all ten declared grants and unknown extensions | Early realm admission, then fixed operation classification before any grant/provider preprocessing; real native authentication remains mandatory. |
| OIDC auth, registration and forgotten credentials | Before EventBuilder/protocol/resource construction and before browser policy, client/session lookup or redirect/code generation. |
| Login-actions, action tokens, required actions and reset/registration flows | Both resource locator and internal constructor/operation calls need the same scope; a request filter alone cannot cover direct calls. |
| Broker login, callbacks, linking and stored provider tokens | Before provider creation/callback, federated lookup/update or upstream credential acquisition; internal entry must revalidate scope. |
| SAML redirect/POST, IdP-initiated SSO, SOAP and artifact resolution | Deny unqualified enrolled-profile paths before parsing/provider/model/signing effects; separate SAML signing boundary. |
| SAML artifact worker / fresh scheduled transaction | Fresh issuer admission and durable scope per job; copied HTTP context/thread-local state is not authority. Deny before remote artifact dispatch. |
| Device authorization/user approval versus later device-code token grant | Guard initialization/approval independently from the token endpoint; source feature gate is not admission. |
| CIBA authentication request and callback versus later token grant | Guard before resolver/channel provider, request persistence or external authentication dispatch; guard callback separately. |
| Pushed authorization request | Guard before client authentication/request storage; later browser/token entry is a separate admission. |
| OpenID credential issuer / credential request | Independent protocol endpoint; token grant interception does not cover verifiable-credential issuance or its builders. |
| Realm and OIDC extensions / unknown protocols or provider builds | Reject unreviewed provider/route identity before getProvider/getResource/createProtocolEndpoint; never treat absent mapping as unmanaged. |
| Dynamic registration, client management, account and related identity writes | Classify before constructors/native auth/provisioning and include all protected writer dependencies; no wholesale feature retirement. |
| Admin authentication realm versus operation target realm | Issuer claim is an untrusted lookup hint until verified; classify principal and target realms separately, enforce native auth and target authorization, deny unqualified cross-realm work. |
| Client Admin API v2/shared client providers and native realm SCIM | Apply before provider construction/auth/model reads and every mutation, including feature changes. Retain all 22 writer families. |
| Discovery, public realm data, JWKS, userinfo, introspection and revocation/logout | Require an explicit operation classification. Public visibility or read-shaped HTTP verbs do not waive protected-read or revocation/writer analysis. |
| Native token response / encoder and separate SAML/credential builders | Defense against direct/internal emission only after complete native-auth/profile/dependency checks; late signing guards cannot repair earlier effects. |
| Error mapping, HTML rendering, rollback and response close | Dedicated minimal pre-admission denial must not resolve a realm/theme/provider again; prove rollback, close, cancellation and zero usable response bytes. |
| Background/native/model/SQL/import/bootstrap/operator paths | Explicit issuer-owned operation scope or enforced maintenance/exclusion. HTTP hooks and mutable context cannot establish complete writer closure. |

All ten declared grant factories remain obligations: authorization code, client
credentials, refresh, password, token exchange, UMA permissions, device, CIBA,
pre-authorized code and JWT authorization. UMA/pre-authorized native auth
exceptions require separate proof. Feature/profile/realm flags and provider
selection were not activated or tested. Unknown/new grants and providers deny
until admitted; names, declarations and settings cannot establish participation.

Client Admin API v2 `createOrUpdateClient`/`deleteClient`, shared client provider
`onCreate`/`onUpdate`/`onDelete` and native SCIM `create`/`update`/`delete`/`patch`
are concrete obligations inside the existing **22 writer categories**. Preserve
all credential/grant/key/realm/tenant/mapper/scope/role/group, native/bulk/SQL/model
setter/flush/cache/session, registration/import/bootstrap/federation/background/
operator/restore paths. A request admission design supplies none of their durable
writer coupling. Temporary unavailability or a candidate exclusion does not
retire IAM/user/JIT/SCIM/ITDR or any service-restoration requirement.

## Failure and response contract to qualify

Pre-admission denial needs a dedicated minimal path: fixed non-enumerating
no-store output, no realm/theme/locale/EventBuilder/provider lookup, no signers,
no credentials or usable token bytes. Missing/unknown state, lookup failure,
unsupported route/profile/build and stale incarnation/revision must deny.
The exact HTTP code, mapper registration/precedence and compatibility behavior
remain to be tested; no new wire response is adopted here.

If a transaction/session already exists, mark rollback before response handling,
close owned resources and clear per-operation state on every error, cancellation,
serialization failure and disconnect. Audit only safe deployment-level denial
metadata until realm access is admitted. Avoid recursive error rendering or a
catch/fallback that resumes unmanaged native work. Native auth failures on an
admitted path must retain native semantics. Successful issuance still requires
verified native signing/mapping, durable attempt/fence commit and synchronous
response release; the source of a close filter alone is insufficient.

## Exit decision and next experiment

**NO-GO for declaring universal admission or proceeding to R3/R4 implementation.**
There is no demonstrated single stock seam: the token method hook, ordinary realm
resolver, context setter, HTTP filter alone and encoder alone each miss concrete
required work. A0/A1/A2 is a proposed core patch surface with a missing primary
admission lookup and unproved framework/provider/internal/worker closure.

The [early realm-denial experiment](../../infra/keycloak/keycloak_registration_connector/qualification/realm_entry/README.md)
now supplies a one-line exact-source resolver hook and directly invoked minimal
mapper. Both variants pass 130 test cases each, including reused native auth
controls; six preparation controls pass. The guarded locator invocations stop
before ordinary realm lookup. This does not qualify HTTP ordering or durable
admission. Native HTML failure mapping still attempts realm lookup after denial.

A new synthetic lifecycle witness keeps cleanup **NO-GO**: a throwing rollback
participant remains unfinished while the native manager returns and the session
reports closed, without propagating the failure to the mapper. Unmarked native
close also commits the control transaction. These are in-memory native lifecycle
results, not SQL/JDBC durability qualification. A missing/failed rollback marker
cannot safely fall through default-close; some fixture fault cleanup is incomplete.
The [rollback lifecycle comparison](../../infra/keycloak/keycloak_registration_connector/qualification/rollback_lifecycle/README.md)
now tests an isolated two-site candidate retaining the first participant-loop
runtime error and suppressing later distinct errors: 155 cases per variant,
310 total, plus six preparation controls pass. The original native witness and
unfinished participant requirement remain. The candidate exposes the selected
fault to native close/the fixture mapper; complete cleanup stays NO-GO because
tracing, prepare/commit branches, provider close, retry and durable outcomes remain
unqualified. The [lifecycle containment contract](keycloak-lifecycle-containment.md)
now classifies actual prepare/cache/new-job/response participants, independent
outcome facts and required changes/exclusions. Its scoped abort/close experiment is recorded separately. The [completed comparison](../../infra/keycloak/keycloak_registration_connector/qualification/native_abort/README.md)
passes 512 cases/six input controls but retains four containment failures;
the [native ownership qualification](../../infra/keycloak/keycloak_registration_connector/qualification/session_ownership/README.md)
now supplies 578 expected-outcome cases/six input controls and a NO-GO result for
mandatory pre-effect ownership or enforceable exclusions. The coherent core
design is now recorded below; optional-hook candidates remain stopped. Full lifecycle,
provider/SQL/JTA/HTTP and all admission/storage gates remain open.
No further admission/storage qualification, R3 snapshot, R4 conditional grant or
successful issuance follows from the passing tests.

All old 18 witnesses/nine failed latest-at-response gates, remaining R1 attribution/
health/error/async/driver/deferred-effect limits and earlier 503, proposed semantic
contract review, R3–R7 storage/transaction/HA/recovery/native-SQL/provider/version/
security/license/image/transport/compatibility/custody/provisioning/claims/tenant/
existing-data and caller-adoption gates remain. The two unresolved historical
build-helper license declarations and deprecated test-only SDK API remain
limitations; this unit adds no SDK/build dependency. All IAM and other service
restoration requirements remain open. Temporal, `case_runtime` and deferred
engine-replacement governance are unchanged.

## Coherent lifecycle design and remaining boundary

The [coherent core patch design](keycloak-lifecycle-containment.md#coherent-core-patch-design)
now maps A0/A1/A2, LC-01–10 and all 22 writer categories to proposed exact native
seams, before-effect exclusions, dependencies and proof gates. Its primary-only
admission/bootstrap interfaces are missing logical prerequisites, not current
APIs or storage. A restricted birth owner grants no realm authority. Revalidate
primary classification in the protected durable scope before ordinary protected
dependencies; no lookup/TTL/caller hint/missing-row unmanaged fallback suffices.
Required independent security jobs acquire fresh authority after the parent's
known resource boundary without holding its barrier; response release waits for
all required outcomes. No native test was rerun for this documentation revision.
The [A0 prerequisite review](keycloak-lifecycle-containment.md#mandatory-a0-prerequisite-result-no-go-before-candidate)
stopped before a candidate: actual augmentation/provider initialization inputs
are not qualified. It reviews 68 source/build units/158 anchors and 11 minimum
missing input seeds, not a complete resolved graph. The A0 prototype stays open;
next is isolated Quarkus build-input review before returning to it. No native
tests/builds ran. A1/A2, full cleanup/durable writer closure and R2/R3/R4 stay NO-GO.
