# Keycloak registration connector prototype

**Experimental, default-disabled source prototype.** This deterministic provider
integration is not a reasoning agent or a qualified deployment. Read the
[root preview scope](../../../RELEASE_SCOPE.md) and
[proposed association ADR](../../../docs/architecture/decisions/0002-issuer-association-readback.md).
No provider is installed by this repository; current Python clients and their
missing-association guard are unchanged. No application/Compose/Helm/CI path loads
this JAR. Keycloak26.0.6 is a historical source-compatibility candidate from the
existing test manifest, not a production-version recommendation.

## Implemented source boundary

The provider factory discovers a single resource:
GET `/realms/{realm}/sentinelgrid-registration/v1/clients/{client_uuid}/association`.
Trusted factory `Config.Scope` supplies `enabled` (false by default) and
`grants-json` (version1 with an empty list by default). Missing/disabled/empty
configuration admits nothing. No HTTP request changes configuration. The
[empty example](grants.example.json) contains no operative grant.

Each immutable grant names issuer, realm_id, iam_audience, management_client_id,
management_subject_id, client_uuid, client_id, subject_id and tenant_id. The
registry has a positive integer revision, a SHA256 of its input, at most128grants,
strict duplicate/trailing-token rejection and a64KiB input limit. Unknown fields,
conflicting duplicate owners, ambiguous identifiers, noncanonical UUIDs, a shared
management/read identity or non-HTTPS issuer deny configuration. These are
operator-owned target grants, not proof that a provider registration exists.

The resource requires an exact HTTPS origin/raw path, GET, no query/cookies/body/
transfer encoding or tenant/user/internal-auth hints, and one bounded canonical
RS256 bearer. Strict parsing is used only to reject ambiguity and select an owned
candidate; it does not authenticate. Actual native Keycloak
`AppAuthManager.BearerTokenAuthenticator`, `TokenVerifier` and issuer signature/
revocation/active-user/client checks authenticate the submitted bytes. Session
claims and username fallback hints are rejected before that path; the resource
must not invoke native session cleanup while observing an association.

The management token must use `keycloak-registration-association-v1`, permission
`iam.read_workload_association`, workload kind, exact owned issuer/client/subject/
tenant/target, canonical UUIDjti, lifetime/age at most60seconds and exactly the IAM
verifier audience plus `urn:sentinelgrid:issuer-association`. Delegation, broad
roles, scopes and alternate user/NHI/workload profiles cannot replace this grant.
The native management subject must itself be the local service account of its
management client. No custom signer or application JWT verification fork is added.

After authentication and grant checks, only the pinned local JPA user provider is
admitted. The target subject's actual internal-client link must match the exact
client UUID, and the reciprocal existing account must identify the same subject.
Names are not proof. Missing/deleted/rebound/foreign/federated/inconsistent state
or SDK failure returns generic503. Repeated exact lookups reject observed changes;
they do not establish an atomic or cache-fresh snapshot. Disabled client/subject
state can be reported without enabling it. The proposed later caller adapter must
apply its own expected inspection/dispatch state policy before token acquisition.

Responses contain only contract, issuer, realm_id, client_uuid, client_id,
subject_id, tenant_id, client_enabled, subject_enabled and observed_at, with
no-store/no-cache headers. Realm ID is an owned provider identifier; tenant UUID
is checked attribution from the owned grant, not inferred native tenancy. No
secret/token/username/profile/raw provider representation is returned. There are
no provision/repair/credential/write/schema/export helpers or name-search fallback.
This observation grants no data read, action or token-acquisition authority.

## Isolated source checks

The Maven module targets Java21, pins Keycloak26.0.6 and build/test inputs, disables
annotation processing, and builds a thin JAR containing original classes and
provider metadata only. SDK dependencies are provided, tests are test scoped;
upstream implementations are not bundled. These experimental commands compile
source and run synthetic fixtures; they do not start or install a Keycloak server:

```sh
mvn -f infra/keycloak/keycloak_registration_connector/pom.xml clean verify
```

Use a disposable Maven cache/settings and Java21 toolchain for isolation. The
[build review](build-review.json) records the actual temporary toolchain, final
source-input and repeated clean-JAR hashes. [Dependency artifacts](dependency-artifacts.json)
record206provided/test artifacts plus build support hashes and inherited declared
license metadata. These declarations are not runtime advisory, bundle, licensing
or redistribution clearance. No JDK, Maven, SDK, provider JAR or other binary is
published with this source. Default preview CI and application dependency graphs
are unchanged; this command is separate experimental prototype qualification.

**86 checks** use the actual Keycloak native bearer verifier and RSA implementation
with owned synthetic keys, request/context and SDK storage doubles. There is no
injected authenticated result or replacement admission function. They cover good
and forged signatures, native revocation, missing/disabled management identity,
exact authority/target/tenant/audience/time, default-empty/disabled grants, malformed
or duplicate JSON/JWT claims, request/body ambiguity, foreign origins, missing or
rebound target links, unsupported storage, disabled-state observation and minimal
responses. Doubled SDK mutations/session cleanup/username fallback are forbidden.
A passing mocked local JPA object is **not** real database non-mutation evidence.

## Remaining qualification

Before any installation or client adoption: select a maintained deployment release;
review exact Java/SPI/SDK/JAR/image dependencies/advisories/licenses; demonstrate real
server discovery/routing, TLS/hostname/header/body bounds and native authorization;
use new isolated synthetic state with database/model write instrumentation and
before/after identity inventories; test absent/deleted/recreated/rebound/concurrent
accounts, local-store/cache freshness, restart/rollback and unsupported federation;
qualify management grants/token provisioning/custody/distribution/lifecycle/audit;
and review the caller adapter. Metadata-admin per-client rights, protected provider
rotation/revocation/recovery, real token/JWKS/mappers/drift/tenant proof and ticket
SQL/RLS/data/caller deployment remain open. Only then may a separate compatibility
decision replace the stock-response assumption. The current guard stays intact.
