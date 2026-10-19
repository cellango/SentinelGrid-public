# Keycloak registration connector prototype

**Experimental, default-disabled source prototype.** This deterministic provider
integration is not a reasoning agent or a qualified deployment. Read the
[root preview scope](../../../RELEASE_SCOPE.md) and
[proposed association ADR](../../../docs/architecture/decisions/0002-issuer-association-readback.md)
and [consistency/conditional-issuance plan](../../../docs/architecture/decisions/0003-association-consistency-and-issuance.md).
The latter is design only: SQL observer calibration precedes issuer feasibility,
snapshot and conditional-issuance prototypes, full qualification and an explicit
caller compatibility decision. It clears none of the nine failed gates.
Default repository workflows install no provider; current Python clients and their
missing-association guard are unchanged. No application/Compose/Helm/CI path loads
this JAR. Keycloak 26.0.6 is a historical source-compatibility candidate from the
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
management client. Native service-account `client_id`, when present, must exactly
match signed `azp`; it supplies no alternate identity or additional authority. No custom signer or application JWT verification fork is added.

After authentication and grant checks, only the pinned local JPA user provider is
admitted. The target subject's actual internal-client link must match the exact
client UUID, and the reciprocal existing account must identify the same subject.
Names are not proof. Missing/deleted/rebound/foreign/federated/inconsistent state
or SDK failure returns generic503. Repeated exact lookups reject observed changes;
they do not establish an atomic or cache-fresh snapshot. The controlled experiments
below demonstrate committed changes that these repeated reads do not observe. Disabled client/subject
state can be reported without enabling it. The proposed later caller adapter must
apply its own expected inspection/dispatch state policy before token acquisition.

Responses contain only contract, issuer, realm_id, client_uuid, client_id,
subject_id, tenant_id, client_enabled, subject_enabled and observed_at, with
no-store/no-cache headers. Realm ID is an owned provider identifier; tenant UUID
is checked attribution from the owned grant, not inferred native tenancy. No
secret/token/username/profile/raw provider representation is returned. There are
no provision/repair/credential/write/schema/export helpers or name-search fallback.
The response-time `observed_at` clock is not a database snapshot timestamp,
revision or freshness/fencing proof. This observation grants no data read, action
or token-acquisition authority.

## Isolated source checks

The Maven module targets Java 21, pins Keycloak 26.0.6 and build/test inputs, disables
annotation processing, and builds a thin JAR containing original classes and
provider metadata only. SDK dependencies are provided, tests are test scoped;
upstream implementations are not bundled. These experimental commands compile
source and run synthetic fixtures; they do not start or install a Keycloak server:

```sh
mvn -f infra/keycloak/keycloak_registration_connector/pom.xml clean verify
```

Use a disposable Maven cache/settings and Java 21 toolchain for isolation. The
[build review](build-review.json) records the actual temporary toolchain, final
source-input and repeated clean-JAR hashes. [Dependency artifacts](dependency-artifacts.json)
record206provided/test artifacts plus build support hashes and inherited declared
license metadata. These declarations are not runtime advisory, bundle, licensing
or redistribution clearance. No JDK, Maven, SDK, provider JAR or other binary is
published with this source. Default preview CI and application dependency graphs
are unchanged; this command is separate experimental prototype qualification.

**88 checks** use the actual Keycloak native bearer verifier and RSA implementation
with owned synthetic keys, request/context and SDK storage doubles. There is no
injected authenticated result or replacement admission function. They cover good
and forged signatures, native revocation, missing/disabled management identity,
exact authority/target/tenant/audience/time, default-empty/disabled grants, malformed
or duplicate JSON/JWT claims, request/body ambiguity, foreign origins, missing or
rebound target links, unsupported storage, disabled-state observation and minimal
responses. Doubled SDK mutations/session cleanup/username fallback are forbidden.
A passing mocked local JPA object is **not** real database non-mutation evidence.

## Disposable local runtime qualification

The opt-in [runner](qualification/run_local.py) creates a new HTTPS Keycloak 26.0.6
process, local cache, persistent loopback-only H2 database and synthetic realm.
It accepts local artifact/tool paths, never an issuer URL, existing realm, database
or deployment configuration. It verifies the distribution, H2, thin-JAR and build
source hashes before use. Normal application, Compose, Helm and CI paths are
unchanged. This experiment is separate from the supported source-preview checks.

Use Java 21 and the Python source-review environment with `httpx` and `cryptography`.
First build the exact reviewed source above, then obtain the historical distribution
from the URL and digest in [runtime review](runtime-review.json). No download or
system install is performed by the runner. Choose a new private report directory
outside the checkout:

```sh
python infra/keycloak/keycloak_registration_connector/qualification/run_local.py \
  --disposable-local-only \
  --distribution-zip /path/to/keycloak-quarkus-dist-26.0.6.zip \
  --provider-jar infra/keycloak/keycloak_registration_connector/target/keycloak-registration-connector-0.1.0-prototype.jar \
  --java-home /path/to/jdk-21 \
  --report-dir /tmp/new-sg-private-report
```

The runner owns and removes its fresh lab state and stops its process groups on
normal completion/failure. Keep its reports private; they contain synthetic IDs,
local paths and table fingerprints. An externally forced process kill still needs
operator cleanup using the recorded lab path. No credentials,
keys, tokens or row values are deliberately logged or published. It does not use
shell expansion, inherited provider/cloud credentials, HTTP proxies or redirects.
Vendor H2 dev-file forces its fixed development database credential; the fresh
H2 listener binds only loopback and is never a deployable configuration. Bootstrap
and service-account secrets and the trusted self-signed TLS key are generated in
the lab and removed. Realm-bound Admin REST performs fixture provisioning outside
measured observations, avoiding a pinned vendor startup-import/cache bug.

The [runtime review](runtime-review.json) records 46 passing measured scenarios
against the final provider artifact. Actual native issuance/authentication, JAX-RS
routing, configured-origin and TLS verification, exact token claims and local JPA
relationships are exercised. H2 BEFORE-row triggers instrument all 87 vendor base
tables for INSERT/UPDATE/DELETE and log table/operation outside the DB transaction.
Sorted row fingerprints compare persistent state before/after each probe. A deliberate
fixture UPDATE followed by ROLLBACK proves attempted writes remain detectable.
Six explicit bookkeeping tables are counted separately; every other table,
including clients, users, credentials, mappers, roles, groups and component/grant
configuration, is protected by default. No protected write attempt or persistent
identity/configuration change was observed. A 12-request concurrent read/retry
window also passes. Fixture writes and server startup/shutdown are outside those
measurement windows; the evidence is not a claim that all Keycloak activity is pure.

Coverage includes valid and disabled-state inspection, forged/native-expired/
revoked/disabled-management/ungranted-workload tokens, signed wrong tenant/contract/
permission/target/session/username profiles, duplicate bearer, cookies, tenant and
query hints, bodies/chunking/encoded paths, wrong origin/TLS trust/hostname, closed
configuration, foreign link/federation marker denial, deletion/recreation with a
new subject UUID, explicit local cache clears, server restart and outage/recovery.
Both HEAD and POST are rejected by the actual server with 405; routed unavailable
observations return generic no-store 503. Same-name recreation is explicit fixture
provisioning, never an observation side effect. The rollback calibration tests the
observer; it is not a provider transaction-race or application recovery test.

[Runtime artifacts](runtime-artifacts.json) hash all 423 vendor JARs plus the archive
root license. That root license does not classify every dependency. No binary is
published; transitive-license, advisory, maintained-release, image and deployment
clearance remain open. The vendor reports that this extension SPI is internal.
The lab required explicit CDI veto for the factory-owned resource and normalization
of an empty root base path; authorization remains factory/grant owned.

## Controlled consistency and failure experiments — adoption blocked

**18 experiments completed; 9 adoption gates failed.** The same thin provider
artifact then passed the 46 baseline runtime scenarios again. The
[controlled review](controlled-failures-review.json) distinguishes experiment
completion from gate success. Add `--controlled-failures` to the command above
for this mode. The current result exits **2** after cleanup because gates remain
unmet; an unexpected harness failure also writes a separate failure record.
Default source-preview CI does not run this experimental lab.

This mode adds a pinned H2 statement listener, private-file query barriers and
connection-local fixture attribution. It pauses actual service-account SELECTs
before the first or after the second query while a separate connection commits
an owned synthetic mutation. It changes neither bearer admission nor query results.
A native Admin REST mutation is also tested. The listener logs process/sequence,
operation category, channel and query shape, with no SQL text or parameters.
A health function checks observer I/O failures and per-process sequence gaps.
The connection marker uses the pinned H2 thread-local session through reflection;
this internal test API is not an application or deployment dependency.

| Experiment | Recorded result | Meaning |
| --- | --- | --- |
| Disable client directly in the lab DB before a warm request | 200 with `client_enabled: true` | Adversarial cache-bypass witness; direct DB writes are not a supported production writer |
| Disable client through native Admin REST during the first association query | 200 with `client_enabled: true` after the admin commit | Repeated lookups do not guarantee revalidation of the committed state |
| Disable subject or rename client during the read | Earlier successful observation can survive | Latest-state/freshness gate fails |
| Rebind, delete or recreate subject before the first query | 503 | These early changes are detected |
| Rebind, delete or recreate after the second query | Earlier association can be returned | No latest-state-at-response or final-revalidation guarantee |
| Kill this lab's H2 process during the query, then recover it | Generic no-store 503; protected fingerprints unchanged after recovery; native retry 200 | Real persistence failure is unavailable, with bounded recovery evidence |

The late-mutation experiments challenge latest-state-at-response/revalidation
claims. They do not alone settle every possible linearizable point-in-time
contract. No such consistency contract or issuer-side fence is established here.
A new decision must define the snapshot/version/fencing boundary across observation
and later token acquisition, preserve non-creation and disabled-state requirements,
and qualify its implementation. Refreshing one cached object or relaxing these
failed gates is insufficient. The current Python missing-association guard remains
closed; no adapter, caller or production installation is enabled.

Statement calibration detects prepared zero-row UPDATEs, a rolled-back row UPDATE
and nested CREATE/ALTER/DROP work, all separated from observation requests. A
client-rejected parse-time failure produces **no corresponding H2 callback**.
Pre-command/recompile failures, abrupt-death callbacks and broader delayed effects
therefore remain coverage gaps. A leading-comment truncation behavior was also
found during calibration; fixture SQL is trimmed and attributed through a session
variable instead of comments. These are pinned callback observations, not complete
SQL audit or absence-of-attempts proof.

Tagged JDBC observation windows show zero unmarked protected row attempts and
zero unmarked mutating/unknown prepared-command starts. Intentional fixture
writes are recorded separately. Native Admin REST SQL shares the unmarked channel,
so that experiment measures freshness and does **not** clear observation write
attribution. The baseline 46 windows again have zero protected row changes/attempts.
Bookkeeping activity, fixture mutation and a failure of observation consistency
are distinct results; none is hidden behind a single passing test count.

Controlled mode deliberately terminates only its newly created H2 process. A
private temporary backup of the fixed synthetic subject and direct FK rows allows
fixture restoration for deletion/recreation tests. That file, all new realms,
secrets, databases and process groups are removed on normal completion/failure;
all nine processes exited in the recorded run. Keep reports private. The earlier
cleanup limitation for externally killed harness processes still applies.

## Remaining qualification

This is one node, one historical version, H2 and local cache. Sequential cache
clears/restarts and concurrent reads do not prove an atomic association snapshot,
concurrent deletion/rebinding safety, distributed cache freshness or PostgreSQL/
cluster compatibility. A non-null federation marker is rejected; an actual custom/
federated storage provider has not been exercised. Resolution and requalification
of the failed controlled consistency gates,
provider transaction/cache/rollback guarantees, complete statement/parse/recompile/
delayed-effect coverage, full HTTP framing/proxy/root-path/redirect/timeout boundaries, additional issuer/profile
failure cases and a maintained deployment/version/security/license review remain
required. Unsupported state stays unavailable. Do not enable an adapter from this
local result alone.

Then separately review the compatibility decision and caller adapter, management
grants/token provisioning/custody/distribution/lifecycle/audit, per-client metadata
rights, protected provider rotation/revocation/CAS/recovery, actual workload token/
JWKS/mappers/drift/tenant proof and ticket SQL/RLS/data/caller adoption. The current
Python reader/default-disabled/missing-association guard, IAM, receiver, reference
client, lease, metadata profile and production deployments remain unchanged.

## SQL attempt calibration

The opt-in [attempt observer](qualification/attempts/README.md) adds JDBC and
server parse/recompile/error/row/transaction tracing in a new disposable lab.
Its [review](attempts-review.json) records 17 fixture cases, 14 passing detection
checks, 11 offline fault controls and all 46 retained native baseline scenarios
passing. Native request-context identity and exact TCP frame correlation separate
observations from supported Admin writes through commit. The deliberate logger
failure/crash tails and unresolved startup/background scopes retain their failed
whole-log evidence gate. All nine earlier provider gates remain open; the new
interleaved native disable still returns earlier enabled state. The provider JAR
and existing application/guard/defaults remain unchanged. ADR 0003 R2 source/API/
writer/storage/conditional-issuance feasibility is next, with every prior gate
retained. No provider/caller deployment is enabled.

## Maintained-candidate issuer feasibility

The [26.8.1 source review](../../../docs/architecture/keycloak-issuer-feasibility.md)
and [review matrix](issuer-feasibility-review.json) select no deployment version.
Stock missing-account acquisition now denies, but a qualified aggregate snapshot,
all-writer generation/fence and native conditional commit are not supplied. The
existing extension is NO-GO for R3/R4 until an issuer-core ownership/storage/
compatibility decision is reviewed. Historical artifacts and all runtime failures,
current guards, empty grants and defaults are unchanged.

The [issuer-core decision proposal](../../../docs/architecture/decisions/0004-issuer-core-storage-and-compatibility.md)
records the core patch/storage/compatibility options and owner-approved bounded
prototype research. Writer closure is unproved, so R3/R4 remain NO-GO. No provider, artifact,
application, schema, dependency or default changes are supplied.

The first P1 component is the [compiler-assisted core audit](qualification/core_audit/README.md).
Its 15 controls and two deterministic source parses pass. It inventories native
entry/mutation syntax, including Admin API v2/SCIM paths; complete transitive
coverage and issuer enforcement remain unproved. It starts no issuer or database.

The paired [native token-entry experiment](qualification/entry_guard/README.md)
compiles an exact-source endpoint overlay with one early denial hook: 34 native
control tests, 34 guarded tests and eight input controls pass. It preserves actual
native client-secret authentication denials in an unmanaged fixture. This is a
method-body research result; front-door/constructor/alternate entry and all
writer/storage gates remain unqualified. Its isolated test POM never changes the
provider build or current issuer authority.

The [native admission design review](../../../docs/architecture/keycloak-native-admission.md)
traces the earlier request/realm/event and alternate/internal/error/worker paths.
Its proposed three core layers remain unimplemented; no full entry/writer closure
or R2 implementation/R3/R4 gate is cleared. The review supplies pinned source
references and the next denial-only experiment boundary.
