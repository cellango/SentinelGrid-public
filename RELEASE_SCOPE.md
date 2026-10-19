# Developer source preview scope

Status: **developer source review only**. Reviewed October 15, 2026. The full
commit and checks for the frozen candidate are recorded in its prepared release
manifest; see [candidate verification](docs/release/candidate.md). The
[pre-publication review](docs/release/review.md) records earlier preparation and
the remaining public-activation gates; it is not a live repository-status API.
The [selected contents](docs/release/contents.md) and
[exact path inventory](publication/source-files.json) record the reviewed selection,
including owner-approved experimental cloud-provider source.

Original SentinelGrid code is licensed under [Apache-2.0](LICENSE). Existing
third-party terms and component notices are preserved; see [LICENSING.md](LICENSING.md).

| Surface | Included verification | Runtime support |
| --- | --- | --- |
| Main frontend | Focused auth/recovery tests | Full build and backend integration remain separate gates |
| IAM auth | Isolated HTTP regressions with mocked dependencies; direct-reset requests return 410 without account mutation | Other identity, token, realm, and admin paths need further review |
| Backend/shared libraries | Source compilation, undefined-name checks, and offline V013 model/DDL contract | Fresh installation, migration execution, tenant isolation, and startup not certified |
| SentinelGuard | Go source for review | Live enrollment, telemetry, and packaging excluded |
| AI Shield | Existing component source and license | No new bundled-snapshot security clearance |
| Posture/cloud providers | Experimental source, including work in progress | Customer accounts, provisioning, and remediation excluded |
| Pentest | Experimental source | Active scans, autonomous tools, and exploitation excluded |
| Infrastructure/Packer/packaging | Historical designs; AMIs private by default; publication workflows disabled | Cloud apply, image builds, repackaging, and publication excluded |

No UI, API, job, or background worker is advertised as a supported runtime in this
preview. Supported commands run local source checks and mocked tests only. Legacy
Compose files and deployment scripts remain inspectable; invoking them manually
runs experimental code outside this scope. Disabling workflows does not repair
experimental services' authorization or execution boundaries.

## Review environment

- Git and Python 3.13 for inventory, compilation, and targeted IAM auth tests.
- Ruff 0.15.7 for undefined names and Python syntax.
- Node.js 22 with `frontend/package-lock.json` and `npm ci --ignore-scripts` for focused frontend tests.
- Gitleaks 8.30.1 for candidate source and all locally available Git refs.
- GitHub-hosted Ubuntu for public CI; no cloud credentials or OIDC.

Source checks need no Docker, database, identity provider, model, or cloud account.
IAM tests use FastAPI's HTTP client with mocks; they do not establish end-to-end
identity or tenant safety. Historical completion, audit, hardening, and compliance
claims are development records rather than verification of this snapshot.

The [Task 8 dependency review](docs/release/dependencies.md) covers the hashed Python
review environment and locked main frontend installation. It records two scoped,
dated exceptions for unpatched development tooling and the separate third-party
license terms. Other runtime dependency graphs remain unresolved.

## Future runnable beta

The intended demonstration is synthetic event → detection → incident → reviewed
non-destructive response → evidence/report. This preparation does not claim it
passes end to end. Before supporting it, select the exact services, disable other
routes/jobs in that runtime, prove clean-clone installation and Flyway upgrades,
verify two-tenant denials and approval replay protection, and inject model/service
failures without downstream mutations. Bind results to an exact commit before
changing this scope.


## Current IAM source selection

The current main IAM assembly uses an explicit method/path/endpoint selection;
unreviewed legacy routes are unavailable before handler dependencies, and startup
does not seed Keycloak or launch identity jobs. Canonical policy routes take
precedence over legacy aliases. See the
[identity source-admission contract](docs/reference/identity.md#main-application-source-admission).
This adds source controls, not a supported login, onboarding, billing, identity
provider, worker or full-stack runtime. Existing component tests do not imply an
operation is enabled in that assembly.

Eleven IAM ORM column/type/nullability/primary-key mappings are checked against the
owned physical profile. An owned PostgreSQL17.5/Flyway11.20.2 probe now verifies the
unchanged eight-file separate IAM profile, real checksummed history, repeat migration,
drift/missing-version rejection and refusal to baseline a populated database. See
the [exact qualification scope](docs/architecture/database-compatibility.md#separate-iam-profile-actual-flyway-verification).
Full shared baseline/install/restore, deployment and live provider qualification
remain open: the local installation lacks `pgcrypto`/`vector`. The source-review
environment cannot import the full app; a temporary bcrypt overlay next stops at
missing `redis`, with no project dependency or environment changes.
The legacy migration launcher refuses execution and cannot fabricate Flyway history.
Existing installations also need explicit provider-grant expiry/reconciliation before
adopting disabled legacy jobs. No schema/history/data adoption or feature-equivalence
claim follows from passing source tests. The published preview tag remains its frozen
snapshot; current branch checks do not rewrite that release's evidence.


## Current MCP source boundary

The core MCP stdio server permits initialization/ping/discovery of twelve existing
tool names/input schemas, while every tool call returns an explicit error. Legacy
environment identities, arbitrary UUIDs/tenant headers, shared service tokens and
approval/audit flags do not authorize reads or writes. Direct legacy helpers/raw
clients also reject before downstream client setup. No tool arguments are rewritten
into a caller identity. See the [current MCP source contract](backend/agents/mcp_server/README.md).

Required MCP capabilities remain migration work. This source containment does not
qualify verified transport identity/capabilities, data ownership, provider effects,
durable audit, HTTP/OAuth, distributed limits, full gateway/caller compatibility or
complete runtime/feature equivalence. The additional hash-pinned MCP1.x protocol
test graph belongs to the source-review environment; no deployment graph or SDK2
compatibility is cleared. The frozen preview release remains unchanged.

## Current shared identity verification

The [delegated IAM client and gateway identity gate](docs/architecture/gateway-identity.md)
check a bounded, input-bound verification receipt, raw browser credential conflicts
and an explicit user-client/tenant contract. The actual gateway rejects missing,
ambiguous, workload or foreign identity before business dependencies. Its user
bindings are empty by default. Shared-token ingestion and global ingest diagnostics
remain blocked pending owned delegation. Offline positive data paths use spies;
full proxy/action authorization, direct-service callers, live provider registration,
SQL and runtime/feature equivalence remain open. A wider legacy gateway suite has
existing failures and is not claimed passing. Core MCP remains unavailable.


The same [identity source contract](docs/architecture/gateway-identity.md#direct-service-workload-reads)
now includes request-bound, short-lived workload reads for three ticketing GET
operations. Explicit owned issuer/client/subject/tenant/service/permission bindings
default to empty. The old shared header-only tenant helper returns 503; ticketing,
scanner and SOAR import sites use service-selected adapters. Writes, scanner
artifact reads and SOAR's shared catalog remain unavailable pending their contracts.
Existing gateway ticket callers cannot use these reads until signed workload
issuance and forwarding migrate. These capabilities remain required restoration
work. Offline tests mount the actual ticket router with current IAM verification
and data/session spies; no real SQL, token issuer, deployed provider/caller,
one-time replay protection or end-user action delegation is qualified.


IAM's [shared user context](docs/architecture/gateway-identity.md#iam-in-process-user-identity)
also applies that owned user contract directly after the current in-process RSA
validator, with no self-verification RPC. Static internal credentials plus tenant
headers no longer create IAM authority. Policy user-info and scoped sessions share
one immutable identity; direct cookie-only/session-marker authentication is not
added. Actual policy/access-request router checks use key, session/data and existing
unit-harness Redis doubles. Other IAM/service callers, workload issuance, provider
registration, SQL/RLS, action authorization and full runtime remain unqualified;
blocked capabilities stay required restoration work.


The [orchestrator HTTP gate](docs/architecture/gateway-identity.md#orchestrator-http-source-boundary)
also covers its actual assembly and six standalone routers. Only local root/health
metadata is public. Stored posture history has one bounded source read requiring an
exact owned user/reader grant; its legacy physical table, Flyway/model ownership,
SQL/RLS and runtime adoption remain unqualified. Store failures are unavailable,
not empty success. The other twenty operations, including global readiness/metrics,
model-backed GETs and response actions, remain unavailable and required restoration
work. RSA/actual-assembly checks use key/HTTP/storage doubles. Component metric/probe
checks are separate from route admission; no workload issuer or provider effect is
qualified and the frozen published release remains unchanged.


The [SOAR source gate](docs/architecture/gateway-identity.md#soar-owned-definition-reads-and-source-admission)
also covers its actual app and five routers. Two tenant-owned definition reads
require an exact registered reader and use tenant-only queries; installed webhook
URLs are withheld. The other 26 unique operations, shared catalog, webhooks and
execution remain unavailable and required restoration work. Raw tenant/query/API-
or shared-token identity and runtime table initialization cannot enable them.
Read-session failure cannot report success. Current-RSA/actual-assembly tests use
key/HTTP/session/storage doubles; physical schema/Flyway/read-role/RLS, saved workflow
redaction, live provider/caller and execution qualifications remain open. No engine
replacement, supported runtime or change to the frozen published release is implied.


The [ingestion source boundary](docs/architecture/gateway-identity.md#ingestion-runtime-reader-and-source-admission)
preserves seven method/path pairs. Only root metadata is public; the two metrics
GETs require an exact registered service-wide runtime reader. Ingest/flush and
global health/readiness remain unavailable and required restoration work. Headers,
debug tokens and body tenants cannot confer authority. Internal body hints cannot
override canonical tenant context. Actual-assembly/current-IAM checks use key/HTTP
doubles and the real local metrics renderer, with no admission override. Workload
issuance, source/body/replay binding, trusted scrape/probe clients, queue/delivery/
OpenSearch/model effects, deployment and full runtime qualification remain open.


The [connector source boundary](docs/architecture/gateway-identity.md#connector-owned-metadata-reads-and-source-admission)
preserves 12 method/path declarations. Two tenant-owned metadata reads require exact
registered reader grants and select no credential, sync-setting or provider-error
columns. Eight write/sync/provider-test/OAuth operations remain unavailable and
required restoration work. Import-time DDL is removed; raw tenant/state helpers and
shared-token ingestion forwarding deny. Actual-assembly/current-IAM checks use key/
HTTP/session/result doubles without admission or provider-SDK substitutes. Managed
schema/Flyway/RLS/data/encryption, real SDK/provider/OAuth/workload/delivery and full
runtime qualification remain open.


The [detection source boundary](docs/architecture/gateway-identity.md#detection-scheduler-runtime-read-and-source-admission)
preserves 14 declarations. Only root metadata is public; scheduler status requires an
exact registered service-wide reader and an already initialized runtime object.
Uninitialized state returns 503. Twelve rule/health/lifecycle operations stay
unavailable and required restoration. Import-time DDL and automatic scheduling are
removed; direct lifecycle helpers cannot fabricate started/completed work. The
tracked legacy model conflicts with the consolidated rule catalog shape; neither
is changed. Current-IAM/actual-assembly checks use key/HTTP and runtime-state doubles,
without identity/admission or scheduler-SDK replacements. Actual APScheduler,
backing stores, model/Flyway/RLS/data, rule evaluation, downstream credentials/effects
and full runtime remain unqualified; broader legacy fixture errors remain open.

## Experimental association-provider lab

The [Keycloak connector](infra/keycloak/keycloak_registration_connector/README.md)
adds an opt-in qualification runner for a new disposable synthetic Keycloak/H2
instance. It is outside the supported preview commands and production scope. Its
recorded local results do not enable the current caller or supersede the proposed
association ADR's remaining adoption gates. Existing environments are never targets.

The optional controlled-failure mode deliberately terminates its own new H2
process and records unresolved consistency and statement-coverage gates. Completing
those experiments is not an adoption pass; current callers and guards remain
unchanged. See the component's controlled review before considering integration.

The [association consistency and conditional-issuance proposal](docs/architecture/decisions/0003-association-consistency-and-issuance.md)
adds an ordered remediation plan only. Its snapshot, durable generation, complete
writer fence and native non-creating acquisition are unimplemented. All nine
controlled-study gates remain failed; no caller, schema, configuration or
production version is changed by this documentation.

The opt-in [SQL attempt observer](infra/keycloak/keycloak_registration_connector/qualification/attempts/README.md)
is confined to new disposable synthetic labs. It calibrates JDBC/server parsing,
recompile, errors, transactions, row attempts, attribution and deliberately failed
log/crash evidence. Its scoped controls and 46 baseline cases pass; whole-runtime
coverage and all nine earlier provider gates remain open. No application or
provider implementation, schema, dependency, default or deployment changes.

The [maintained issuer feasibility review](docs/architecture/keycloak-issuer-feasibility.md)
is source/design only. Keycloak 26.8.1 improves stock missing-account denial, but
provides no qualified complete snapshot/writer-fence contract for this prototype.
Issuer-core/storage/compatibility ownership must be decided before further
prototypes. No production version, application behavior or schema is adopted;
all historical failed gates and caller-adoption restrictions remain.

The [issuer-core/storage architecture proposal](docs/architecture/decisions/0004-issuer-core-storage-and-compatibility.md)
records owner-approved bounded prototype research. It specifies required core
writer, transaction and native migration boundaries; complete closure remains
unproved. No production issuer fork, new authority, schema, grant or caller
compatibility is adopted.
