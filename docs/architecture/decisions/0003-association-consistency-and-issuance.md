# ADR 0003: Association consistency and conditional issuance

Date: October 18, 2026.
Status: **proposed; design review only**. No implementation, schema, grant,
provider installation, production version or caller compatibility change is
approved. [ADR 0002](0002-issuer-association-readback.md) remains proposed.
This document proposes the consistency contract needed to continue that work;
it does not supersede executable guards or accept the failed qualification gates.

## Decision proposed for review

Pursue two separate boundaries: a fresh, consistent provider observation, then
issuer-enforced conditional acquisition against the same durable generation.
An observation alone cannot authorize acquisition. Keep the current provider and
Python caller disabled by default and preserve the missing-association denial.
Do not attach the current observation to the stock token request as though it
were an enforced condition.

The historical 26.0.6 source exposes useful extension points, but **does not
provide the required complete generation/fence contract**. No drop-in fix or
production-ready extension has been established. The preferred design below
requires a maintained issuer implementation with an enforceable common boundary
for all relevant writers and issuance. A version-specific feasibility decision
must choose an upstream facility, reviewed issuer change, or fully covered
extension before implementation. If that cannot be demonstrated, adoption stays
unavailable. Keep the nine failed gates open while working through the sequence.

## Evidence and actual call paths

The [controlled review](../../../infra/keycloak/keycloak_registration_connector/controlled-failures-review.json)
records 18 experiments and nine unmet case gates. Its 46 baseline runtime cases
passed again. These counts describe different evidence; nine unmet gates are
not nine proved vulnerabilities. No current caller consumes the provider.

| Boundary | Reviewed behavior and implication |
| --- | --- |
| Provider observation | The [resource](../../../infra/keycloak/keycloak_registration_connector/src/main/java/ai/sentinelgrid/keycloak/registration/AssociationResource.java) authenticates native bearer bytes, checks an owned grant, loads a client and local JPA subject, and repeats relationship reads. It returns enabled booleans and a response-time clock. Repetition is neither persistent freshness nor a consistent snapshot. |
| Cache and JPA | Pinned [realm lookup](https://github.com/keycloak/keycloak/blob/26.0.6/model/jpa/src/main/java/org/keycloak/models/jpa/RealmAdapter.java) delegates to the client provider. [Realm cache lookup](https://github.com/keycloak/keycloak/blob/26.0.6/model/infinispan/src/main/java/org/keycloak/models/cache/infinispan/RealmCacheSession.java) can reuse a request-managed client. [JPA user lookup](https://github.com/keycloak/keycloak/blob/26.0.6/model/jpa/src/main/java/org/keycloak/models/jpa/JpaUserProvider.java) uses `EntityManager.find`; its service-account query returns null or an existing relationship and rejects multiplicity. Separate repeated calls need not fetch new entity state. |
| Observation witnesses | A supported Admin REST disable commits while an observation is paused, yet its response reports enabled. An unsupported direct-SQL cache-bypass disable before a warm request is also stale. Early rebind/delete/recreation deny; late changes can return the earlier association. No coherent cross-object snapshot was proved by these results. |
| Native acquisition | Pinned [client-credentials processing](https://github.com/keycloak/keycloak/blob/26.0.6/services/src/main/java/org/keycloak/protocol/oidc/grants/ClientCredentialsGrantType.java) can call `enableServiceAccount` when the account **or the default client-ID mapper** is missing. [ClientManager](https://github.com/keycloak/keycloak/blob/26.0.6/services/src/main/java/org/keycloak/services/managers/ClientManager.java) can enable service accounts, add a user and add service-account mappers. Thus preflight existence followed by stock acquisition does not establish non-creation. Its service-account token-request policy callback occurs after this fallback. This is source evidence, not a newly demonstrated runtime exploit. |
| Token entry and signing | The pinned [token endpoint](https://github.com/keycloak/keycloak/blob/26.0.6/services/src/main/java/org/keycloak/protocol/oidc/endpoints/TokenEndpoint.java) performs native client authentication and dispatches by [grant provider](https://github.com/keycloak/keycloak/blob/26.0.6/server-spi-private/src/main/java/org/keycloak/protocol/oidc/grants/OAuth2GrantType.java). [TokenManager](https://github.com/keycloak/keycloak/blob/26.0.6/services/src/main/java/org/keycloak/protocol/oidc/TokenManager.java) builds access-token responses through native token encoding. These are integration seams, not an existing atomic compare-and-issue API. |
| Python readback | [IssuerRegistrationReader](../../../backend/libs/sg_core/workload_registration.py) makes separately authenticated metadata GETs and still requires the stock user response's association field, which reviewed stock versions omit. Its digest is a hash of the expected policy, not a provider revision. Its management profile is distinct from the association profile. |
| Reference caller | [FixedTicketReadClient](../../../backend/libs/sg_core/workload_read_client.py) snapshots a local lease, inspects registration, rechecks the lease, then posts stock `client_credentials`. It validates the signed workload token through current IAM before the fixed ticket GET and rechecks the lease before dispatch. Local CAS cannot synchronize an issuer transaction or another process. |
| Revocation and keys | Native [JWKS](https://github.com/keycloak/keycloak/blob/26.0.6/services/src/main/java/org/keycloak/protocol/oidc/OIDCLoginProtocolService.java) supplies signing keys, not a relationship revision. Current [IAM validation](../../../backend/agents/iam_agent/app/services/token_validator.py) verifies signature/issuer/claims; its introspection path preserves signed-token fallback when remote introspection is unavailable. It is not a fail-closed online generation check. No immediate revocation claim follows from a valid signature. |
| Grants and writer authority | [Grants](../../../infra/keycloak/keycloak_registration_connector/src/main/java/ai/sentinelgrid/keycloak/registration/Grants.java) has an operator version/hash, not a persistent issuer-wide association generation. Existing [IAM admin](../../../backend/agents/iam_agent/app/services/keycloak_admin_client.py) and [tenant-management](../../../backend/services/tenant_service/app/core/keycloak.py) paths include mutations, user delegation or provisioning. They cannot become read/acquisition authority by reusing credentials. |

Pinned [client](https://github.com/keycloak/keycloak/blob/26.0.6/model/jpa/src/main/java/org/keycloak/models/jpa/entities/ClientEntity.java)
and [user entities](https://github.com/keycloak/keycloak/blob/26.0.6/model/jpa/src/main/java/org/keycloak/models/jpa/entities/UserEntity.java)
do not expose the aggregate durable generation required here. Cache revision
counters, token `jti`, timestamps and `notBefore` are not interchangeable with it.
An [event listener](https://github.com/keycloak/keycloak/blob/26.0.6/server-spi-private/src/main/java/org/keycloak/events/EventListenerProvider.java)
can participate in an emitting transaction; that does not prove every mutation
emits a suitable event or acquires a common fence before changing state. A listener
or post-commit invalidation alone is insufficient.

## Precise proposed consistency contract

Let `S` be an immutable issuer observation and `G` its durable generation tuple.
`t_read` is a database snapshot point **inside the observation request** after
management authentication and before the first protected read. Every reported
association, enabled bit and policy component must belong to that same committed
snapshot. All mutations committed before `t_read` must be visible. An overlapping
mutation may be ordered after `t_read`; this contract does not promise the latest
state at response delivery. Errors, unsupported stores, ambiguous rows or failure
to establish that snapshot return unavailable without identity/configuration writes.

The snapshot covers exact issuer, realm identity/incarnation, internal client UUID,
public client ID, actual subject UUID and reciprocal link, enabled/service-account
states, federation status, owned tenant attribution and all issuance-relevant
client/realm policy, mapper, scope, group, role and management-grant dependencies.
Separate Admin GETs cannot be labeled a single snapshot. Policies outside this
coverage make conditional acquisition unavailable until covered.

`t_issue` is the successful durable conditional-issuance commit point. Native
authentication, current grant authority, exact association, enabled states and
effective policy must still match `S/G` under the common writer fence before any
account/mapper fallback, credential acquisition or token release. A changed,
deleted, recreated, disabled, revoked, missing or uncertain dependency denies.
Signing/encoding, if performed before commit, stays internal; release a response
only after successful commit. Commit failure must never release a usable token.
Proof of the transaction-to-HTTP boundary is an implementation prerequisite.

A mutation committed between `t_read` and `t_issue` invalidates the condition.
A disable after `t_issue` does not retroactively make that acquisition precede
the disable. Preventing use of already-issued tokens requires a separately
qualified fail-closed online revocation/generation boundary at data admission,
or an explicitly accepted bounded token lifetime. Current offline verification
and local lease checks remain unchanged and establish neither immediate issuer
revocation nor cancellation of an in-flight request. Any new receiver rule needs
its own compatibility review, outages policy and real tests before adoption.

This proposed point-in-time contract is a semantic decision requiring review.
The prior latest-state/revalidation witnesses **remain failed** under their
original criteria. Add a history-based snapshot/issuance oracle; never rename
the old expectations to produce passing counts. The direct-SQL witness remains
an adversarial invalidation-bypass test, not a supported deployment writer.

## Fresh snapshot design candidate

Use a short-lived, issuer-owned read transaction over the qualified local store,
with scalar/immutable projections and proven consistent-snapshot isolation.
Avoid request-managed realm/client objects, first-level entity reuse and query
cache results. Resolve exact IDs only; require one existing reciprocal relation.
Do not clear or flush the authentication session's entity manager to refresh a
read. Management and owned-grant validity must also be checked against the
snapshot/generation; authentication is never replaced by a projection.

Version-specific provider-local JPA access is a candidate, not a portable API
promise. Before changing source, document the actual supported session and
transaction lifecycle, read-isolation configuration, cache-bypass behavior,
projection mappings, supported database and non-mutation evidence. A normal
READ COMMITTED transaction with several SELECTs is insufficient. Repeated
reads, an application mutex, one locked row or a final refresh cannot cover
multiple objects, missing rows, phantoms and later acquisition.

All storage credentials and reads remain within the issuer. SentinelGrid never
gets vendor database access. No direct vendor SQL, new vendor table, lock,
transaction-isolation change or migration is adopted by this proposal. If a
supported provider facility cannot establish the snapshot, stop and review an
explicit issuer implementation change; do not approximate success with caches.

## Issuer generation and fencing design candidate

Prefer an issuer-maintained durable generation bound to a realm incarnation,
client/subject incarnation and monotonic revisions of every covered dependency,
including tenant/policy, credentials, management grants and revocation. A
provider-wide epoch may conservatively invalidate unrelated observations;
targeted dependency versions are an optimization requiring the same proof.
Deletion retains a tombstone or bumps a durable parent epoch. UUID/name reuse,
disable/re-enable and restore must not resurrect a condition (the ABA problem).
A content hash is useful for equality, but cannot detect change-and-return.

All participating mutation paths must serialize through that same durable fence
and update generations atomically with their changes. Inventory Admin REST/UI,
client registration, imports, bootstrap/seeding, SDKs, credentials, realm policy,
mapper/scope/role/group updates, user lifecycle, service-account creation/removal,
federation/storage maintenance, background jobs and operator recovery. Native
issuance must participate too. Enforce enrollment and grant revocation across
nodes; deny an unqualified path rather than claim it is covered by an event.
Privileged database/import/restore bypass requires issuer unavailability, an
epoch change and requalification before reopening. A direct database writer is
not made safe by a cache TTL. Root compromise is outside this mechanism's promise.

The condition is untrusted equality input, never authority. A proposed observation
v2 would add an opaque issuer condition, generation, policy digest and bounded
expiry to the minimal v1 identity fields. It remains protected by the distinct
scoped association management identity, exact target/tenant and owned TLS.
Do not cache observations or accept a caller-supplied identity/policy/URL.
Observation does not consume a nonce or create a ledger/identity record.

The future acquisition boundary would reside at the **native issuer token
endpoint**, retaining native client authentication and native signing. A narrowly
versioned extension grant is a candidate seam. It would accept only an opaque
condition and bounded attempt ID in addition to the fixed native client identity;
no requested tenant, subject, target, audience, claims, scope or delegation.
The issuer independently checks the fixed profile/grant and current generation.
It must use a reviewed non-creating issuance path: never invoke stock account or
mapper repair, even if the subject disappears or a default mapper is absent.
No application signer, generic token proxy or second identity authority is added.

**Stock acquisition must also be closed for enrolled clients.** Blocking only
the new grant leaves an ordinary `client_credentials` bypass. Prove that every
stock/exchange/refresh/password/browser/alternate client-auth path denies this
profile before creating/repairing effects. A late service-account policy callback
does not suffice. Do not replace a global grant provider and affect unrelated
clients casually. Choosing the entry guard, native issuance integration and
complete writer fence is the outstanding version-specific feasibility decision.

This design may require issuer-owned durable condition/attempt state. Its schema,
transaction coupling, native lifecycle and upgrade/restore mechanism require
an explicit reviewed issuer-storage decision; no schema is selected here.
Application Flyway migrations are not a way to modify vendor tables. Any future
application state still needs paired SQLAlchemy/Flyway changes and RLS review.
Do not use a second application's database or a distributed lease without
issuer-enforced fencing to simulate atomicity across two independent stores.

Use a canonical lock order and bounded transaction/request deadlines; prevent
deadlock, starvation and expiry while waiting. Losing a fence/transaction/node
must deny; a process-local lock or expiring lease cannot authorize a stale worker.
For a timed-out request, the caller must treat acquisition outcome as unknown
and perform no data dispatch. A bounded issuer attempt record binds the exact
principal/condition/operation and rejects duplicate or conflicting replay.
Do not store or replay bearer values. A new attempt requires fresh observation
and a bounded retry budget; duplicate prevention is not exactly-once HTTP delivery.
Crash after commit but before response may consume an attempt with no delivery.
Outages, partitions, rollback, failover and restart require explicit tests.

## Alternatives and reasons

| Option | Decision |
| --- | --- |
| Refresh or evict caches before returning v1 | Insufficient alone: no common snapshot or protection of later issuance; still useful to investigate cache behavior |
| Add `observed_at`, a TTL, signed response, policy hash or configured UUID | No durable change/ABA detection or enforcement at acquisition; authenticity is not freshness |
| Preflight then stock token endpoint, or mint first and check `sub` | Rejected: native fallback can create/repair; mint-first violates the before-acquisition boundary |
| Native `notBefore`, short JWT lifetime or JWKS refresh | Retain real native checks, but these do not provide the full association generation or immediate per-request revocation |
| Application mutex, one row lock, higher isolation only on observation | Does not serialize all objects/writers and later issuance; missing rows and alternate paths remain |
| Event-listener revision or post-commit cache invalidation | Incomplete writer coverage/order is unproved; transaction participation is not universal pre-mutation fencing |
| Application reads/locks in vendor DB or copied association registry | Rejected as application authority/storage coupling; a registry cannot attest current provider state |
| Immutable provisioning and an admin gateway | Possible only if every writer and stock issuance path is enforceably mediated; network convention alone is not that proof |
| Issuer-native conditional acquisition with complete generation/fence | Preferred design to investigate; requires explicit version/storage/compatibility decisions and qualification, not available in the current prototype |
| Weaken the pre-token requirement or use another issuer | Separate superseding architecture/product decision with evidence, not an implicit fallback in this task |

## Remediation sequence and exit criteria

These are ordered engineering units within the existing migration work. They
do not move existing IAM/service restoration into later product phases. Complete
one unit and record its evidence before proceeding; do not mark parent acceptance
complete from containment, a source decision or a local fixture.

| Unit | Work and required exit evidence |
| --- | --- |
| R1: SQL observer completeness | Extend only disposable-lab instrumentation; capture JDBC preparation/execution failures plus server parse/recompile/internal command attempts, with independent request/connection/transaction attribution. Calibrate the complete matrix below before reusing any no-write claim. This is the next bounded unit. |
| R2: Exact issuer feasibility | Select an exact maintained candidate for review separately from historical26.0.6 evidence. Map native auth/grants/non-creating issuance, all writer entrypoints, supported snapshot APIs, fence/storage/commit-to-response hooks and stock-path denial. Produce a go/no-go source/API matrix and explicit version/storage/compatibility decision. An absent hook blocks implementation; use no placeholder fence. |
| R3: Fresh snapshot prototype | After the source decision, implement the minimal isolated observation version. Prove coherent persistent state and disabled inspection with fresh IDs, metadata dependencies and read-only SQL evidence. Keep the v1/current client closed. Retain the old failures and add the new consistency oracle. |
| R4: Conditional issuance prototype | After the storage/writer decision, implement native-authenticated compare-and-issue and every required writer/stock-path guard together. Prove no account/mapper repair and atomic generation/attempt commit. A partial writer fence cannot pass this unit. |
| R5: Full provider qualification | Repeat all88native/SDK checks, all46baseline scenarios, all18controlled experiments with retained original outcomes and new histories; add missing mapper/account, mixed snapshot, ABA, credential/grant revocation, timeout/replay/crash and concurrent native issuance cases. Qualify PostgreSQL/distributed cache, federation/custom-store rejection, transport and operational matrices; review maintained version/SPI/security/license/image artifacts. |
| R6: Explicit caller compatibility | Review supersession of the stock user-response assumption and stock acquisition request separately, then add the scoped adapter. Require exact identity/tenant/policy/generation agreement across metadata/association/acquisition; preserve current IAM/receipt/receiver, management-profile separation, local lease, fixed GET and all negative tests. Unsupported/missing provider denies before acquisition/data effects. |
| R7: Custody, data and adoption | Qualify safe disabled provisioning and per-client metadata rights; protected grants/credential provisioning, distribution, rotation/revocation/CAS/recovery/audit; actual signed claims/JWKS/mappers/scopes/tenant mutation; ticket model/Flyway/read-role/RLS/existing-data/upgrade/restore and actual callers. Return to all retained IAM, gateway/MCP, service/action/infrastructure restoration work. Deployment needs its own authorized acceptance. |

R2 may reveal an infeasible platform choice. Record that finding and preserve
the requirements; do not automatically add vendor tables, widen management
rights, relax a test or introduce a different issuer. R1 independently closes
an evidence prerequisite and can proceed while architecture remains proposed.

## SQL instrumentation acceptance

The prior H2 callbacks and row triggers remain evidence. They detected zero-row
UPDATE, rolled-back row UPDATE and nested DDL, but missed a JDBC-rejected
parse-time failure. Native Admin SQL shares the unmarked channel: **observation
write attribution is not cleared for that experiment**. Preserve that ambiguity;
new attribution cannot retroactively assign the old records.

Instrument both sides of the JDBC boundary without changing credentials,
authentication, query text, parameters, query results or transaction outcomes.
Record attempts before delegating prepare/execute/batch calls, including failures
before a prepared command exists. Complement those with pinned server parser,
recompile, command, transaction and internal/deferred-effect hooks. A JDBC wrapper
alone misses internal commands; H2 prepared-command callbacks alone miss parser
failure. Lab-only instrumentation must remain outside the provider artifact.

Correlate server-owned request ID, process epoch, connection/session/transaction,
observer versus native Admin versus fixture origin, operation class and outcome.
Include pooled connection reuse, threads and async/background work. An origin
tag cannot suppress a record or come from arbitrary production request headers.
Unknown attribution/operation, dropped events, unbalanced entry/exit, logging
failure or sequence gaps fail the evidence gate. Exclude raw SQL/parameters,
secrets, bearer tokens and tenant profile data from published reports.

| Calibration or experiment | Required observable evidence |
| --- | --- |
| Valid SELECT and real provider observation | Entry/start/success/error correlation; genuine native auth and database results; no injected admission/result |
| Invalid syntax, bind/prepare failure, authorization/constraint failure | Attempt plus exact failure stage even with no prepared command; distinguish client-only rejection from server receipt |
| Zero-row UPDATE/DELETE and batch/merge | Mutating statement attempt even when no row trigger fires; partial batch failures retained |
| Row UPDATE followed by rollback/savepoint rollback | Both attempt and row evidence, terminal transaction outcome and unchanged committed fingerprint |
| CREATE/ALTER/DROP and nested/internal commands | Parse/prepare/execute and schema inventory, including implicit commit behavior; no assumption that rollback undoes DDL |
| Recompile/reprepare, failed commit, abrupt database/process loss | New attempt/stage correlation, incomplete tails, restart epoch and independently checked recovery state; missing logs cannot prove zero |
| Deferred trigger/flush/background effects | Cover all participating threads/connections through configured drain/quiescence and restart/recovery checks; publish the finite observation bound, not an unlimited absence claim |
| Native Admin writer interleaved with observation | Independent server-owned correlation and transaction mapping; observer and writer changes separately accounted, unknowns fail |

Retain protected row triggers and before/after fingerprints for all relevant
vendor identity/configuration/schema records, with session/event bookkeeping
classified separately. Statement attempts prove attempted effects even after
rollback; equal snapshots alone do not. Calibrate by deliberately introducing
known effects in fresh synthetic state and demonstrate detection. Prove the
instrumentation preserves the uninstrumented provider's behavior. H2 evidence
does not establish PostgreSQL, other driver, cluster or production coverage.

## Bounded R1 evidence update

The [lab-only attempt observer](../../../infra/keycloak/keycloak_registration_connector/qualification/attempts/README.md)
now supplies bounded JDBC/server/row/transaction calibration and native request
attribution through commit. Its [review](../../../infra/keycloak/keycloak_registration_connector/attempts-review.json)
records 17 fixture cases, all 14 detection checks and all 46 retained baseline
cases passing, plus 11 offline evidence fault controls. It resolves a shared CDI
proxy attribution collision by keying the backing request context. Deliberate
log loss/process death and unclassified startup/background/API scopes remain
uncleared whole-log evidence. An earlier unexplained valid-read 503 is retained.
The new native disable experiment still reports earlier enabled state; all nine
original failed gates and their original attribution ambiguity remain unchanged.
R2 source/API/version/writer/storage feasibility is next, carrying the remaining
R1 limits and every R3–R7 requirement. This adds instrumentation only; the proposed
consistency/issuance contract and current provider/caller behavior are unchanged.

## Safety, compatibility and operations gates

All future runtime work is confined to **new disposable synthetic loopback labs**
with fresh realms/accounts/clients/grants/secrets/data, bounded processes and
verified cleanup. Never use an existing/live issuer, realm, tenant, database,
secret store, volume or provider. No runtime experiment is required by this ADR.
No current code, application schema, dependency, configuration, workflow, provider
default or deployment changes as part of documenting it.

Before adoption, review exact server/Java/SPI/build/driver/image digests, supported
upgrade range, maintained security advisories and transitive licensing. Include
grant/secret owners, distribution and audit, per-client least privilege, condition
expiry/revocation, CAS/recovery and bounded retry/rate budgets. Prove root path,
proxy/hostname/TLS/CA/redirect/timeout/framing/cookie and native token-profile
boundaries. No broad admin/user/NHI/provider-action credential may substitute for
association, metadata or workload authority.

Require guarded disabled rollout, dependency/version mismatch denial, outage and
partition behavior, writer enrollment validation, rollback/backup/restore with a
new epoch, old-condition invalidation and independent effect verification. Audit
records identify build/profile/generation/attempt/outcome under retention/access
policy without bearer/secret values. Missing required durable audit must stop
release; audit reconstruction makes no issuer/model calls. Keep accepted,
executed and verified outcomes distinct. None of this document establishes
runtime adoption, immediate revocation, full call-graph coverage or feature parity.
