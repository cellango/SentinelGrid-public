# ADR 0002: Non-creating issuer association readback

Date: October 18, 2026.
Status: **proposed for isolated prototype qualification**. No runtime adoption,
provider installation, dependency or caller change is approved by this document.

## Context and evidence

The [current fixed-ticket client and registration reader](../gateway-identity.md#issuer-registration-readback-and-local-credential-lifecycle)
require fresh authenticated readback before workload token acquisition. They
remain disabled by default. A configured subject UUID, service-account name,
fragment, local registry row or synthetic HTTP response cannot prove the actual
provider's client-to-subject relationship.

Repository manifests currently pin three different historical Keycloak versions:

| Manifest | Pin | Role in this review | Source finding |
| --- | --- | --- | --- |
| [Development](../../../docker-compose.dev.yml) | 24.0.5 | Existing development input | Association GET can create an absent account |
| [Minimal](../../../docker-compose.minimal.yml) | 25.0.6 | Existing minimal input | Same behavior |
| [Test](../../../docker-compose.test.yml) | 26.0.6 | First isolated compatibility candidate | Same behavior |

In the pinned [24.0.5](https://github.com/keycloak/keycloak/blob/24.0.5/services/src/main/java/org/keycloak/services/resources/admin/ClientResource.java),
[25.0.6](https://github.com/keycloak/keycloak/blob/25.0.6/services/src/main/java/org/keycloak/services/resources/admin/ClientResource.java)
and [26.0.6 client resources](https://github.com/keycloak/keycloak/blob/26.0.6/services/src/main/java/org/keycloak/services/resources/admin/ClientResource.java),
GET `clients/{client-uuid}/service-account-user` may enable/create the missing
account. It cannot satisfy a non-creating observation contract.

The reviewed user GET uses the user-profile representation. The pinned
[26.0.6 profile conversion](https://github.com/keycloak/keycloak/blob/26.0.6/server-spi-private/src/main/java/org/keycloak/userprofile/DefaultUserProfile.java)
and [model conversion](https://github.com/keycloak/keycloak/blob/26.0.6/server-spi-private/src/main/java/org/keycloak/models/utils/ModelToRepresentation.java)
do not expose the required association; the reviewed24/25 counterparts have the
same omission. `serviceAccountClientId` is populated in a separate
[export path](https://github.com/keycloak/keycloak/blob/26.0.6/model/storage-private/src/main/java/org/keycloak/exportimport/util/ExportUtils.java).
Its presence in a representation schema or export does not establish availability
from user GET. Current stock24/25/26 user GET therefore fails the existing guard.
This conclusion concerns these pinned paths, not every possible extension or API.

The internal [UserModel link](https://github.com/keycloak/keycloak/blob/26.0.6/server-spi/src/main/java/org/keycloak/models/UserModel.java)
can identify the service account's **internal client UUID**. The reviewed
[JPA service-account lookup](https://github.com/keycloak/keycloak/blob/26.0.6/model/jpa/src/main/java/org/keycloak/models/jpa/JpaUserProvider.java)
queries that relationship without the client-resource creation fallback. This
supports a source-feasible design, not runtime proof for every storage provider.
Keycloak documents [custom REST resources through provider interfaces](https://www.keycloak.org/docs/latest/server_development/index.html#_extensions_rest);
the [pinned provider interface](https://github.com/keycloak/keycloak/blob/26.0.6/server-spi-private/src/main/java/org/keycloak/services/resource/RealmResourceProvider.java)
is the compatibility input. Current documentation is guidance, not a guarantee
that packaging/authentication details match a historical version.

No provider was run for this review. The local Docker daemon was unavailable.
Version26.0.6 is selected only for the first reproducible compatibility prototype
because it already appears in the test manifest. It is **not** selected as a
production version or recommended upgrade. Before any deployment, separately
select a maintained release, review dependencies/security, pin image/build digests
and repeat the complete qualification. No manifest or version pin changes here.

## Proposed direction

Build a small deterministic **`keycloak_registration_connector`** provider prototype.
It is a provider integration, not a reasoning agent. Its sole proposed operation
is a protected, non-creating association read. It must inspect actual provider
models and must never call the account-creating Admin REST resource. No direct
application access to the Keycloak database, custom vendor table, token signer,
account provisioning, refresh or token-exchange path is added.

The proposed route, absent from the current source and runtime, is:

`GET /realms/{realm}/sentinelgrid-registration/v1/clients/{client_uuid}/association`

Only an exact canonical UUID route is admitted. No body, search, arbitrary URL,
caller tenant hint, subject selector, expansion or alternate method is supported.
The expected subject and tenant come from an owned provider grant, cross-checked
against the authenticated management token. A URL or realm/deployment name grants
no scope. Requests to unknown/disabled/unconfigured targets must not create state.

The provider must:

1. Authenticate through Keycloak's supported bearer-authentication path for the
   selected version. Do not decode an unverified token, accept a session cookie,
   use an anonymous resource, or implement a second signer. Verify issuer, lifetime,
   recipient, management client/subject and exact signed target before target-model access.
2. Require a distinct proposed association contract
   `keycloak-registration-association-v1`, permission
   `iam.read_workload_association`, and exactly the IAM verifier audience plus
   `urn:sentinelgrid:issuer-association`. Tenant/client/subject/target claims and
   at-most60-second lifetime follow the existing management-boundary discipline.
   The signed `sg_registration_target` contains exactly issuer, client_uuid,
   client_id, subject_id and tenant_id. Reject delegation, user/NHI/read-client
   proofs, broad admin tokens and unreviewed realm/client roles or scopes.
3. Independently authorize that management principal against an explicit server-owned,
   default-empty grant: issuer/realm, management client/subject, target client UUID,
   client ID, subject UUID, tenant UUID and permission. Protect grant configuration
   from API/model/user input and version/hash it. No broad realm-management role is
   required or treated as a substitute. Missing grant or conflicting token denies
   before target lookups. Grant distribution/lifecycle/audit still needs implementation.
4. Resolve the exact realm/client from provider context and the owned target.
   Load the existing subject by its owned UUID through the qualified local storage
   path and compare `getServiceAccountClientLink()` to the **internal client UUID**,
   not the public client ID. Also read the existing service account by client and
   require its subject UUID to agree. Missing, ambiguous, foreign or conflicting models deny. Report disabled state
   without enabling anything; the adapter must enforce its owned inspection/
   dispatch state policy. Names are consistency checks, never proof.
5. Use only qualified non-creating model reads. No `enableServiceAccount`, `addUser`,
   client/user setter, credential manager, export, repair, provisioning or lazy
   account-creation helper is permitted. Initially restrict the prototype to the
   reviewed local store; federation/import/custom storage/cache behavior needs
   separate evidence. Never assume every implementation of an interface is pure.
6. Return a minimal, bounded, strict JSON observation over owned TLS with no-store
   semantics. Proposed fields are contract, issuer, realm_id, client_uuid,
   client_id, subject_id, tenant_id, client_enabled, subject_enabled and observed_at.
   Realm ID is an exact owned provider identifier, not assumed to be a tenant UUID.
   Tenant is a checked owned attribution, not an inferred native provider relation.
   Exclude tokens, secrets, usernames, profile data, credentials and raw provider
   representations. Readback errors are redacted and cannot become empty success.

This response is an authenticated observation, not an authorization token, signed
attestation, consumed nonce or atomic snapshot of all issuer policy. Provider
build/version/digest must be verified through owned deployment evidence, not a
self-reported response. Reads can update normal telemetry/cache/audit machinery;
non-creating means no client, subject, credential, role, mapper, group or grant
record is provisioned, repaired or mutated by the observation.

## Compatibility with the current client

This proposal does **not** supersede the existing Python guard in executable code.
The current `IssuerRegistrationReader` still requires the stock user response's
association and fails closed when missing. Existing metadata-read management
contract/audiences and its Admin REST targets remain unchanged.

If the prototype passes, a separately reviewed adapter will combine fresh existing
metadata readback with this association observation. It will use a **separate scoped
association bearer**, verified through unchanged current IAM before calling the
owned route. Metadata-reader and association-provider credentials have distinct
contracts/recipients/grants; neither admits a workload data read. No extra audience
or role may be silently added to an existing token profile to make it work.

That integration must explicitly supersede only the assumption that stock user GET
supplies the association. It must require exact issuer/client UUID/client ID/subject/
tenant agreement across the owned registration, authenticated observation and
metadata, plus enabled state and bounded freshness. Every fetch must re-observe;
constructed/cached observations remain inadmissible. Preserve all mapper/scope/role/
tenant/client-policy drift checks, local credential version/expiry/revocation gates,
unchanged current-IAM signature/receipt and workload receiver, and fixed ticket GET.
A missing provider, unsupported version or inconsistent response remains unavailable
before workload token acquisition. No fallback to name lookup or mint-first proof.

Existing metadata-admin rights still require per-client provider qualification;
adding a narrow association provider does not repair those wider rights. Local
leases remain process-local. Safe disabled provisioning, management-token issuance,
protected custody/distribution/rotation/revocation/recovery, real token/JWKS/claim
proof, tenant tests, ticket SQL/RLS and deployed caller adoption remain required.

## Alternatives considered

| Option | Assessment |
| --- | --- |
| Stock service-account GET | Rejected for this contract: can create missing state in all three reviewed pins |
| Ordinary user GET or populated export/schema field | Does not expose the necessary relationship through the reviewed GET path; no compatibility inference |
| Username, configured UUID, copied fragment or local NHI registry | Does not observe the provider-owned relationship |
| Preflight user GET then service-account GET | A deletion between requests can trigger creation; presence checking does not remove the race |
| Read-only database access from SentinelGrid | Couples application credentials to vendor storage/schema; not selected |
| Mint a workload token first and use sub/azp as association proof | Changes the required before-token-acquisition boundary; not selected |
| Minimal provider model read | Preferred prototype: preserves the boundary and can return only scoped association fields; adds a versioned extension and qualification burden |

## Qualification and migration gates

Prototype work may proceed in an isolated source/test fixture. Acceptance for
production adoption or changing the caller remains pending all of these gates:

- Reproducible provider build with reviewed license/dependency provenance and pinned
  Keycloak/Java/SPI/JAR/image digests; no plugin auto-installation into existing realms.
- Real selected-version bearer authentication, exact audience/contract/target/tenant
  checks and default-empty provider grants. Forged/expired/foreign/replayed-for-another-
  target/ambiguous/user/admin/NHI/read-client credentials deny before target-model access.
- Existing disabled/enabled client association reads; missing/deleted subject or
  client, stale/rebound UUID/link, renamed client, conflicting grant and concurrent
  deletion/recreation do not create or repair any identity record.
- Database/model mutation instrumentation around the observation and before/after
  inventories of client/user/credential/mapper/role/group records, including failure,
  retry, redirect/outage and account-not-yet-created cases. Pure-function mocks alone
  cannot establish provider-side non-mutation.
- Exact UUID/issuer/tenant/version agreement, strict bounded JSON, TLS/CA/timeout/
  proxy/redirect/cookie limits and generic failures. No search/secret/export/write
  endpoints; no profile leakage, unbounded grants or mutable snapshot admission.
- Local-store/cache freshness and rollback/restart behavior; unsupported federation
  denies until separately qualified. Normal cache/audit activity is distinguished
  from identity/configuration writes in the evidence.
- A reviewed client adapter and explicit compatibility decision superseding only
  the stock-response assumption, with all current positive/negative caller tests
  retained. Missing or removed extension still stops before workload mint/data.
- Only after these gates: qualified disabled provisioning, protected credential
  lifecycle, tenant/token/JWKS/claim/drift tests, receiver/caller deployment and data/
  RLS/operations approval. The prototype alone enables nothing.

A failed gate keeps the capability disabled and records the unmet condition.
Temporal behind `case_runtime` and the engine ADR are unaffected. No existing
feature, IAM restoration requirement or unavailable operation is retired by this
association decision.
