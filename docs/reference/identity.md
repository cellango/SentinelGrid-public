# Identity and tenant review boundaries

Status: focused source and disposable-database review; deployment qualification remains pending. The [tenant UUID rule](../AGENTS.md) is a required
invariant, not evidence that all existing endpoints enforce it. Slugs are a
customer-facing convenience at the gateway edge; downstream programmatic traffic
must use the authenticated tenant UUID and reject mismatches.

| Boundary | Source to inspect |
| --- | --- |
| Browser/API proxy routes | [frontend API routes](../../frontend/src/app/api/), [gateway routes](../../backend/services/api_gateway/app/api/) |
| IAM token validation and public auth | [auth.py](../../backend/agents/iam_agent/app/api/auth.py), [IAM services](../../backend/agents/iam_agent/app/services/) |
| Shared service security helpers | [security.py](../../backend/libs/sg_core/security.py) |
| Tenant-aware persistence | [shared models](../../backend/libs/sg_core/models.py) and individual service queries |
| Regression evidence | [IAM auth tests](../../backend/agents/iam_agent/tests/test_auth_api.py) and [release review](../release/review.md) |

## IAM token validation source checks

The [IAM validator](../../backend/agents/iam_agent/app/services/token_validator.py)
now uses PyJWT's RS256 signature, exact issuer, audience and time validation, with
required subject and tenant UUID claims. It rejects unsigned/wrong-algorithm tokens,
untrusted issuer origins/realm paths, missing or incompatible signing keys and
invalid claim types. Identity comes from verified claims; email domains and realm
names cannot remap a tenant. Failed validation has no authenticated payload.

Signing keys come only from configured `KEYCLOAK_URL`, using
`KEYCLOAK_VERIFY_TLS`, bounded cache lifetime and no redirects. An external browser
issuer must be explicitly configured using `KEYCLOAK_ISSUER_BASE_URLS`, a JSON list
of trusted bases such as `["https://identity.example.test"]`. The base excludes
`/realms/...`; each token must match an exact base plus a valid realm segment.
Production also requires secure issuer-base URLs. Tokens must include
`KEYCLOAK_CLIENT_ID` in `aud`; configure the identity provider's audience mapper
rather than accepting `azp` or disabling audience validation. No automatic
localhost/public-host aliases are added.

Introspection validates the JWT boundary before using signed identity. Explicit
inactive results deny; unavailable introspection retains the existing local signed-
JWT fallback and therefore cannot prove immediate revocation. Keys newly rotated
into a cached realm become available after `JWKS_CACHE_TTL` expires; unknown keys
fail closed. Revocation and rotation behavior still require live provider qualification.

The [token tests](../../backend/agents/iam_agent/tests/test_token_validator.py) use
real ephemeral RSA keys/signatures with mocked key transport; configuration tests
also retain TLS/production guards. They run in `make preview-check` alongside the
existing mocked auth-route checks. This verifies the named source boundary, not
live Keycloak configuration, all callers, RLS or an operational IAM deployment.
Focused audit/session, ITDR proposal and local NHI controls are described below. SCIM/editor and full
IAM acceptance remain separate migration slices; live provider/runtime qualification
is pending.

The old direct-reset endpoint returns HTTP 410 in IAM and the frontend proxy;
that removes the bypass and does not implement account recovery. The mocked tests
prove the named route does not construct an identity-provider admin client.
They do not certify live Keycloak, SSO, MFA, realm provisioning, enrollment,
all internal callers, or a two-tenant end-to-end isolation boundary.

The agent runtime and AI Shield Go gateway retain the known missing-configuration
internal-token fallback described in [the credential review](../release/credentials.md).
Those runtimes are excluded from supported execution. Do not translate old
"resolved" tenant-attribute notes or production signoffs into a current security
claim. Use [SECURITY.md](../../SECURITY.md) for private findings; no product
credentials are needed to run the supported preview checks.

## IAM authorization and policy source checks

`/api/v1/authorize` and its batch route now require a current, active, unexpired
user entitlement matching the authenticated tenant, subject, resource and action,
plus an explicit applicable `access` or `authorization` policy `allow`. Missing
policies, no matching grant, lookup failures and unsupported definitions deny.
Only `*` is a resource wildcard; the complete remaining suffix must match.
Decision caching is disabled; the `use_cache` service argument and tenant-scoped
cache-clear endpoint remain compatible with existing callers and old entries.

Every active applicable policy is evaluated, including configured `sod` rules.
Priority, policy order and action order cannot make an allow or challenge override
a denial. Deny takes precedence, followed by approval, step-up and explicit allow.
`log` and `notify` are auxiliary declarations; this evaluator does not send
notifications or treat them as grants. Unsupported actions, including
`auto_approve`, deny until a separately reviewed implementation exists. The
binary authorization endpoint denies step-up/approval requirements: request-body
`mfa_verified`, `approved` or similar flags cannot fulfill them.

Tenant policies apply to every requested target. App-scoped policies match an
exact `resource_type="app"` and resource UUID; entitlement-scoped policies match
current matching entitlement UUIDs. Scoped policies require a UUID. The stored
policy type/scope must agree with its DSL. No implicit app membership, resource
hierarchy, group inheritance or automatic provider action is implemented.

Policy rules AND their conditions; an empty condition list matches. The supported
facts are `role`, `group`, `department`, `ip`, `country`, `device_known`,
`time_of_day`, `day_of_week`, `risk_level`, `risk_score`, `user_id`, `username`,
`email`, `resource`, `resource_type` and `action`. Operators are `equals`,
`not_equals`, `includes`/`contains`, `in`/`not_in`, `greater_than` and `less_than`.
Operands must have compatible types; ordered comparisons are numeric. Missing
facts and unsupported fields/operators fail closed, including in a condition
following a false condition. Model-generated/custom attributes are not authority.

For authorization, subject roles come from the verified caller's token for
self-requests. Only verified `TENANT_ADMIN`, `IAM_ADMIN`, `PLATFORM_ADMIN` or
`INTERNAL_SERVICE` callers can request another subject in the same tenant; their
own roles are never substituted for that subject's roles. Such delegated requests
have unavailable subject roles and therefore deny any role-dependent policy until
an authoritative subject lookup is implemented. The peer IP comes from the server
request, without trusting forwarded headers. Time is current server UTC, formatted
as `HH:MM` and a lowercase weekday. Groups, risk, device, location and directory
attributes remain unavailable to authorization until trusted providers are added;
policies requiring them deny. Caller metadata cannot supply trusted facts.

Policy create/update/delete/activate/reject, seed cloning, template instantiation
and `/policies/evaluate` require verified `TENANT_ADMIN`, `IAM_ADMIN` or
`PLATFORM_ADMIN` roles within the authenticated tenant. The evaluation endpoint
and the duplicate legacy IAM Portal policy routes use the same guard and evaluator.
Evaluation is an administrator simulation using supplied hypothetical facts; its response
cannot authorize an action. A SoD policy can deny conflicting verified role
combinations without hardcoded role pairs, and a SoD-only allow cannot grant access.

The [policy regressions](../../backend/agents/iam_agent/tests/test_policy_enforcement.py)
and tenant-route checks run in `make preview-check` with synthetic storage and
blocked database initialization. They test default deny, ordering, SoD conflicts,
context spoofing, stale grants, scoped targets, expiry and write failures. These are focused source checks. The durable audit and database tests below extend
that boundary; live identity provisioning and all downstream enforcement remain open.


## Persistent audit and tenant database checks

The shared `DB_URL` holds app-catalog entitlements, policies and directory/catalog
records. `IAM_DB_URL` explicitly selects a **separate PostgreSQL database** for
fine-grained access grants, governance and grant audit; it is never inferred from
`DB_URL`. Missing grant-store configuration returns HTTP 503. Selecting the same
configured host/port/database for both stores is rejected. Catalog `app_id`/`name`
rows and grant `resource_type`/`resource_id`/`action` rows are incompatible contracts.
The session split preserves them; it moves no existing data. Authorization reads
policy state in the shared tenant session and commits grant usage and its audit in
the IAM session. These reads across databases are not a distributed transaction or
an exact provider-action authorization/approval mechanism.

New [V014](../../backend/migrations_consolidated/V014__public_iam_audit_and_tenant_guards.sql)
and [IAMAuditEvent](../../backend/agents/iam_agent/app/models/audit_event.py) add
`public.iam_audit_events` without altering or backfilling legacy `entitlement_audit_log`.
The new table records tenant, actual actor/type, subject, decision, resource/action,
reason and bounded redacted context/change snapshots. IDs have no cascading foreign
keys, so deleting a live grant cannot erase the new event. Legacy history retains
its existing shape and retention limitations; it is not silently relabelled or copied.
Credential-like payload keys are redacted; this is not a complete arbitrary-PII
classification or external tamper-evidence system.

Each allow/deny made by the evaluation engine, including lookup errors, attempts an
event. Authentication/admission rejections before evaluation are outside this stream. Allow requires
an audit commit in the same IAM transaction as usage. Audit failure rolls back usage,
returns a deny marked unaudited internally, and the HTTP authorization adapter returns
503. It does not claim that an unavailable database recorded the failed attempt.
The individual and bulk grant-create/update/revoke paths couple changes and events
in one transaction; bulk items use savepoints and report success only after the
outer commit. Grant mutations require a verified tenant administrator and user UUID;
a body `granted_by` value or a previous grantor cannot impersonate the current actor.
Other role/editor/provider writers still need their feature acceptance. Governance checks follow below.

The [shared transaction helper](../../backend/libs/sg_core/tenant_session.py) validates
a UUID before opening a session and binds parameterized transaction-local `set_config`
on every SQLAlchemy transaction, including savepoints and transactions after commit/
rollback. A session cannot be rebound to another tenant. Pool checkout clears old
session-level tenant/admin settings outside a transaction. IAM ownership helpers
require an explicit authenticated tenant; a resource merely having a tenant or a
user UUID is insufficient. Importing IAM database configuration no longer runs DDL.

V014 forces RLS for the named existing IAM tenant tables and parent-bound child rows.
Restrictive guards intersect older permissive policies, preventing the
`app.is_superadmin` flag from widening those tables. New audit events permit scoped
read/append and prohibit application update/delete. The application must be a
nonowner, nonsuperuser, `NOBYPASSRLS` role without policy-alter, role-membership or
truncate privileges. The old shared superadmin helper fails closed; the IAM helper's
legacy name retains platform-role checks and tenant scope. Cross-tenant maintenance
requires a separately provisioned operational identity, not an application flag.
Custom tenant settings remain trusted middleware input, not protection from a
compromised service that can execute arbitrary SQL.

Run `make preview-check` for unit/source checks and `make preview-iam-db` for the
[real database suite](../../backend/agents/iam_agent/tests/test_iam_database.py).
The latter requires PostgreSQL server tools (`SG_TEST_PG_BINDIR` can select them)
and starts/removes its own private Unix-socket cluster, ignoring existing DB URLs.
Missing tools fail the gate. It tests two tenants using a nonowner application role,
commit/rollback/savepoint/pool reuse, stale session flags, invalid context, cross-tenant
writes/child links, model/DDL parity, immutable audit writes, retained legacy rows,
allow/deny events and atomic failure handling. Local qualification used PostgreSQL
17.5, SQLAlchemy 2.0.39 and psycopg2 2.9.10. The separate CI job targets PostgreSQL 16
on Ubuntu; its hosted result must be checked after publication of this change.

The [database profile notes](../architecture/database-compatibility.md#iam-audit-and-session-implementation)
explain history selection and adoption gates. These tests qualify the named boundary
and synthetic upgrade. They do not certify the complete V001–V013 application
baseline/Flyway runner, arbitrary populated legacy databases, all views/functions,
all downstream endpoints or live identity configuration. Shared/global grant patterns
and seed clones receive no cross-tenant exception in the new guards; their authorized
sharing path remains feature reconciliation work before runtime enablement. The
governance compatibility boundary is described below.


## Access request source and database checks

The [access request API](../../backend/agents/iam_agent/app/api/access_requests.py)
retains its routes and response fields, with these admission rules:

- Creation uses the verified caller as requester and beneficiary. `requested_for`
  remains a compatible field for that same UUID; another UUID returns 403, including
  for administrators. On-behalf-of requests need a trusted directory membership path
  before admission. Existing delegated rows can still be read, denied or cancelled
  by authorized callers, but cannot be approved (409).
- Only verified `TENANT_ADMIN`, `SOC_MANAGER` or `PLATFORM_ADMIN` roles can review,
  preserving the existing reviewer-role set. An approver must differ from both
  requester and beneficiary (403); these roles cannot bypass that check. Only the
  requester can cancel. Read/history visibility remains tenant- and participant-
  scoped, with the existing administrator exception inside the authenticated tenant.
- Targets must be nonblank. An optional new expiration must include a timezone
  and be in the future (422). Approval rechecks expiration and existing active grants
  (409), using persisted request data rather than a replacement target in the review.
- Review and cancellation lock and reload the tenant-scoped request row. Competing
  transitions serialize; a request that is no longer pending returns 400. This
  prevents two successful reviews of one request. It does not establish global
  uniqueness across different requests or other grant writers.
- Creation, approval, denial and cancellation commit the request, its history,
  any created grant and audit events together. Failures attempt rollback and return
  503. Audit/flush or pre-commit failures leave no transition. A lost acknowledgement
  after the database commits is indeterminate to the caller: inspect the request
  before retrying. A completed request cannot be approved again. Each committed transition records the actual
  caller, beneficiary, target and old/new status; approval also records grant
  creation. Responses are validated and detached from ORM loading before commit.
  Admission rejections do not claim a durable transition event.

The [ORM mappings](../../backend/agents/iam_agent/app/models/access_request.py)
now match the **existing, unchanged IAM V3** columns, JSONB history metadata,
defaults, checks and named indexes. There is no new database schema or migration
in this change. The nullable legacy `requested_for` means the requester in API
responses and approval; rows are not rewritten. Historical IAM V0–V3 and consolidated
V001–V014 bytes remain unchanged. The IAM-only profile and separate-store rules above
still apply; deploying against a different historical shape requires reconciliation.

Required unit checks include admission and existing tenant-route regressions. The
owned PostgreSQL suite also covers real V3/ORM compatibility, transitions, rejected
cross-tenant IDs, audit and commit failures (including a lost commit acknowledgement),
stale ORM state, legacy rows, simultaneous
reviews and approval/cancellation contention. These are synthetic source/database
results. Governance/certification/role synchronization, shared-definition admission,
SCIM/editor ports, provider effects, full Flyway adoption and hosted CI remain
outside this qualification. A grant request approval is not the proposed exact
provider-action approval protocol in the future case runtime.


## Governance campaign and certification checks

The [governance API](../../backend/agents/iam_agent/app/api/governance.py) uses a
[deterministic service](../../backend/agents/iam_agent/app/services/governance_service.py)
and [typed DTOs](../../backend/agents/iam_agent/app/schemas/governance.py) over the
separate IAM grant store. No model output supplies reviewer or tenant authority.
The campaign, certification, history and schedule ORM mappings now match historical
IAM V1 storage. The schedule mapping does not start a scheduler.

| API field or state | Existing IAM storage and compatibility |
| --- | --- |
| Campaign dates, reviewer type, grace days and entitlement patterns | Explicit versioned `scope`, `review_config` and `schedule` JSON; patterns persist and constrain selection |
| Campaign `pending` / `in_progress` | Database `draft` / `active`; start/complete endpoints own those transitions |
| Certification `user_id` | Beneficiary of the joined tenant-scoped **user** grant; role/group UUIDs are not treated as users |
| `reviewer_id`, `review_date`, `comments` | Existing `certifier_id`, `decision_date`, `justification` |
| `approved` / `retained` | Database status `approved`, decision `approve`; metadata preserves the API's distinct review outcome |
| `revoked` | Database status `revoked`, decision `revoke`, with an audited grant-status change when needed |

Only verified `TENANT_ADMIN`, `IAM_ADMIN` or `PLATFORM_ADMIN` users can create,
read or manage campaigns. All operations remain inside the authenticated tenant.
Certification lists restrict ordinary callers to their own beneficiary/reviewer
records. Pending queues use the assigned reviewer and active campaigns; supplying
another reviewer UUID requires a current administrator role. Filtering cannot grant
decision authority. Certification requires the exact persisted reviewer UUID.

Self mode is an explicit attestation of an existing user grant by its beneficiary;
it creates no access. Admin mode assigns the verified administrator who starts the
campaign, requires independence from every selected beneficiary, and rechecks the
current administrator role when deciding. Manager assignment returns 409 until a
trusted directory mapping is implemented. There is no fallback to self review.
Campaign patterns use `resource_type:resource_id:action`, with `*` only as a complete
field. Selection includes active, unexpired user grants, with at most 500 records;
role/group certification is unsupported. Up to 100 bounded patterns and bulk IDs
between 1 and 500 are accepted; bulk IDs must be distinct.

Dates require timezones and an increasing interval. Start requires the current
time inside that interval. Draft configuration can be edited; starting freezes it.
General PUT cannot start or complete a campaign, and active configuration edits
return 409. Cancellation closes review admission. Certification approval/retention
cannot retain inactive, expired or overdue access and cannot recreate a revoked
grant. Changes to the grant target or membership fields after assignment require
reconciliation before decision or completion. Completion rejects missing/extra
certifications and unresolved legacy statuses.

The explicit completion call may revoke pending grants only when configured grace
days (0–3650) have elapsed after the campaign end. It does not launch a background
job. Without eligible revocation, all certifications must be resolved first.
Locks follow campaign → certification → grant order, with refreshed ORM state, so
review and completion cannot race to contradictory outcomes. Bulk decisions share
one transaction and never report a committed subset on failure.

Campaign changes, certification history, grant revocations and actual-actor audit
events commit together. Failures attempt rollback and return 503. A lost commit
acknowledgement can leave a durable decision; inspect state before retry. Confirmed
revocations invalidate existing read caches after commit; cache invalidation remains
best effort. Authorization itself reads current grants, independent of that cache.
Validated responses do not reload ORM rows after commit. Legacy certification
history retains its cascading retention limits; the separate append-only IAM audit
has no cascading grant/campaign foreign keys.

[V015](../../backend/migrations_consolidated/V015__public_governance_contract.sql)
adds only campaign `updated_at` and its trigger, plus a restrictive history-link
guard requiring the certification's exact entitlement. Historical campaign timestamps
start at migration time. V001–V014 and IAM V0–V3 are unchanged; existing JSON,
statuses, decisions and IDs are not converted or backfilled. Current selected files
are pinned by the [IAM profile](../../publication/iam-database-profile.json). In the shared catalog profile V015 makes no
change when `audit_campaigns` is absent; it never merges the two stores.

Only campaigns/certifications explicitly created by this adapter carry its contract
marker. Lists select that contract; access by an unreconciled legacy campaign ID
returns 409. Unsupported continuous/scheduled/delegated configurations remain in
storage and need explicit adoption; a marker is a compatibility discriminator,
not an authorization credential. No legacy row is silently enabled by migration.

Unit checks cover admission and body/filter bypasses. The owned PostgreSQL suite
checks populated-row preservation, model/DDL contracts, pattern/reviewer selection,
scope and stale-target rejection, grace periods, missing/unresolved records, history
and audit outages, atomic bulk rollback, uncertain commits and review/completion
contention. This is focused synthetic qualification. Full shared D0/Flyway execution,
unknown populated histories, hosted CI, live directory/provider effects and shared
definitions require their separate gates. Current role synchronization, ITDR proposal
and local NHI admission are described below; SCIM/editor admission remains open.


## Role patterns, directory synchronization and sharing

The [role API](../../backend/agents/iam_agent/app/api/role_mappings.py) and
[role reconciliation service](../../backend/agents/iam_agent/app/services/role_sync_service.py)
require verified `TENANT_ADMIN`, `IAM_ADMIN` or `PLATFORM_ADMIN` context and a user
UUID. Body `created_by`/`granted_by` fields remain compatible inputs but provide no
authority. Tenant UUIDs come from that context; an omitted pattern tenant means the
current tenant. It never creates a global definition. Reads, writes and deletes stay
tenant scoped, and definition changes share their audit transaction.

Role/pattern storage matches IAM V1's lengths, priority, enabled flag, indexes and
uniqueness. [V016](../../backend/migrations_consolidated/V016__public_role_grant_provenance.sql)
adds explicit `auto_grant` (false for historical rows) and nullable `created_by` (no
invented historical actor). New definitions record the actual caller. Whole-field `*`
is supported in `resource_type:resource_id:action`; embedded globs, empty fields and
unresolved tenant placeholders are rejected. Definitions are explicit user-grant
rules. Editing/disabling/deleting a definition does not itself run reconciliation.

The [directory reader](../../backend/agents/iam_agent/app/services/role_directory_service.py)
is disabled until deployment-owned `IAM_ROLE_SYNC_REALMS` maps tenant UUID strings
to realm names. This JSON setting has an empty default; there is no fallback to the
generic realm or request-supplied realm. Configure it through environment/secret
configuration without committing credentials. The existing Keycloak URL, TLS and
admin authentication settings apply. Production requires the existing HTTPS/TLS and
service-account controls, plus a least-privilege directory-read account and an
administrator-controlled, non-user-editable tenant attribute. Those real provider
permissions/profile settings still need deployment qualification.

Directory observations require an exact user UUID, one matching `tenant_id`
attribute, a boolean enabled flag and valid effective realm-role names. Disabled
users yield no roles. Transport errors, redirects, malformed/missing membership,
oversized responses and expired observations fail; they never become empty-role
success. Redirects and environment proxies are disabled on these directory requests.
Each response is capped at 1 MiB; reads use a 10-second timeout. Realm enumeration
continues through an empty page and rejects duplicates or more than 100 accounts.
Valid foreign-tenant accounts in a shared realm are excluded, never relabelled.
Role observations are bounded at 100 realm roles per user and checked within 30
seconds before mutation and commit. They are observations, not a distributed lock
on Keycloak state. Client-role and group/composite behavior require live provider
qualification; no instantaneous revocation guarantee follows from these tests.

Single-user synchronization reconciles all observed realm roles against enabled,
explicitly opted-in tenant patterns. Bulk role synchronization enumerates the bounded
realm, selects present and previously managed members, and commits one operation.
An unverified former member blocks bulk reconciliation. Limits are 500 patterns,
500 stored user grants and 500 grant creates/revocations per operation. Over-limit
work fails without a committed subset; inventories do not silently truncate.

[Service-owned provenance](../../backend/agents/iam_agent/app/models/role_grant_binding.py)
in `public.iam_role_grants` distinguishes managed grants from manual or legacy ones.
Request metadata cannot establish that ownership. Overlapping role sources share
one grant; losing one source preserves another. Losing the last applicable source
revokes an active managed grant. Revoked, expired or suspended rows are not silently
reactivated when a role returns. Manual grants and old `source=role_sync` metadata
are not adopted or revoked automatically. Existing legacy ownership requires explicit
reconciliation before it can be managed by this service.

V016 forces RLS and intersects tenant, user-subject and entitlement links for the
new provenance table. Its grant trigger prevents a managed target/beneficiary/expiry/
grantor from being repurposed through a generic writer; ownership transfer is not
an admitted API. Status/usage changes remain possible under their existing authority.
Tenant/user transaction locks serialize competing syncs; grant/provenance/actual-
actor audit writes commit together. Audit, provenance or pre-commit failure rolls
back the operation. An acknowledgement lost after commit requires state inspection;
retries reuse the durable ownership instead of creating another grant. Confirmed
changes invalidate read caches after commit; authorization still reads current DB
grants. Directory realm, roles and observation time are retained in scoped audit.
These operations write the IAM database; they do not assign/remove Keycloak roles.

Global patterns remain inaccessible under the restrictive tenant guards. Both policy
bundle services explicitly return 503 for seed listing/cloning until an authorized
shared-publication contract is implemented. An `sg_admin` slug is not that contract,
and no bypass identity or tenant flag is introduced. Policy-template reads now select
only the authenticated tenant, excluding NULL/global and other tenants. This verifies
the named service query, not universal `policy_templates` table RLS or all template
writers; those broader database/caller gates remain open.

Unit and owned PostgreSQL checks cover directory transport and membership failures,
legacy opt-out/preservation, model/DDL parity, verified actors, two tenants, exact
ownership links, metadata forgery, role overlap/removal, sticky denials, audit and
provenance outages, bulk rollback, uncertain commits and concurrent syncs. Synthetic
HTTP transport supplies directory data; no live Keycloak or Redis instance is used.
Full shared baseline/Flyway/history/privilege adoption, hosted CI, live identity
permissions/profile configuration, every other grant writer and overall IAM
acceptance remain separate gates.


## ITDR response proposal admission

The [ITDR intake](../../backend/agents/iam_agent/app/api/itdr.py) retains
`POST /internal/iam/itdr/enforce` and `/enforce/batch` as compatibility paths.
They **record proposals only**. A successful response means the IAM audit commit
was acknowledged; it never means an account, session, MFA policy, notification,
review queue, WAF rule or SOAR incident changed. `actions_executed` stays empty,
`auto_response_enabled` stays false and `soar_incident_id` stays null. No environment
flag or body approval field enables effects. New callers should check `status`,
`actions_recorded`, each action's outcome and `proposal_id`.

The deterministic threat catalog contains ten proposal categories. Its severities
and suggested actions are response recommendations, not validated detection facts
or authority to execute. Caller-supplied threat/context data is retained as an
unverified assertion. LOG_ALERT means an audit record only; SOC/user notification,
human-review queuing and every enforcement action return **blocked**. No external
message or incident is sent, and no automatic detection-to-effect path is admitted.

Verified tenant/IAM/platform administrators with a user UUID may submit. The shared
internal token has no user actor and cannot submit. Tenant UUIDs come from verified
server context. Optional legacy body tenant/realm values must match that tenant and
its server-owned `IAM_ROLE_SYNC_REALMS` mapping. The existing bounded directory
reader must observe the exact subject UUID and tenant membership within 30 seconds,
including immediately before audit commit. Missing maps, outages, redirects,
foreign membership, malformed or stale observations cannot become success. These
are read-only directory observations with the provider qualification limits above.

Unknown threats, non-UUID subjects, extra authority/approval fields and unbounded
batches are rejected. Batches contain 1–10 signals; each context allows at most
2,048 encoded JSON bytes, six levels and 256 values. The body context cannot choose
operations or credentials. Credential-like keys are redacted by the existing audit
logger; callers must still avoid secrets in arbitrary free-text values. Context is
not echoed in the response or written to application logs by this intake.

[The service](../../backend/agents/iam_agent/app/services/itdr_service.py) commits
all proposal records together using the existing separate IAM database and its
append-only, forced-tenant audit table. Each receipt identifies the actual caller,
subject, directory observation and response-map version. A provider verification
failure commits rejection events only, then returns a generic 403/503; no proposal
subset is committed. Input/authentication mismatches are rejected before provider
access. Audit/commit failure returns 503 and attempts rollback. An acknowledgement
lost after commit may leave durable records: inspect audit state before retry.
Repeated submissions can create additional proposal records; no effect idempotency,
approval workflow, incident tracking or distributed provider transaction is claimed.

Overlapping legacy response executors in `automated_response`, `automated_responses`,
`auto_remediation` and `workflow_integration` now return explicit 503 from their
response methods and helpers, including old dry-run/placeholder paths. Those paths
lack the admitted action ownership, tenant-bound provider contract or truthful
receipt semantics. The anomaly API now derives tenant/actor from the verified request-context dependency.
Anomaly detection can still return findings, with empty
`actions_taken` and `response_status=blocked`; it does not call the old response
executor. Detection/query/analytics paths outside this intake retain their separate
experimental qualification limits. Existing clients of blocked methods need to
handle 503 and submit proposals explicitly; no transparent execution fallback exists.

Real provider effects require the planned shared action boundary: exact server-owned
policy/approval, scoped provider credentials and target membership, durable action
intent/reconciliation, independently verified effect receipts and failure/retry
qualification. Temporal remains the selected future runtime behind `case_runtime`;
this slice neither implements it nor reopens the deferred engine decision.

Unit checks cover all ten categories, authority/size/scope negatives, synthetic HTTP
provider errors and legacy bypass helpers. The owned PostgreSQL suite checks durable
receipts, redaction, two-tenant visibility, forced RLS, batch rollback, audit permission
outages and uncertain commit acknowledgement. No schema or dependency changes,
existing database migration, live provider mutation, hosted CI or deployment is
implied by this source qualification.


## Non-human identity: local registry and credential lifecycle

The [NHI API](../../backend/agents/iam_agent/app/api/nhi.py) implements a bounded
**IAM-local registry**, disabled by default. `IAM_ENABLE_SERVICE_ACCOUNTS=true`
opts into these local operations only. It does not create Keycloak/OAuth/cloud
clients, enable machine login, assign permissions or integrate certificate identity.
Responses explicitly carry `credential_scope=local_registry_only` and
`provider_status=not_integrated`. This is partial NHI source qualification.

`/api/v1/nhi/service-accounts` supports create/list/get and an expiring-credential
view. Its existing `/{id}/rotate`, `/deactivate`, `/activate` and DELETE paths now
require JSON `expected_version` (the current `credential_version`) and accept an
optional bounded reason. Callers of the earlier candidate interface must adopt that
version contract. UUID paths, typed status/expiry filters, 1–365 rotation days and
bounded names/descriptions/reasons are enforced. Lists fail 409 above 100 matching
accounts rather than silently truncating; expiry windows accept 0–365 days and
include already-expired active records.

Verified `TENANT_ADMIN`, `IAM_ADMIN` or `PLATFORM_ADMIN` users with a user UUID manage
the current tenant's registry. A platform role remains tenant scoped. Owner and
creator are the actual verified caller on creation; request bodies cannot choose
tenant, owner, actor, roles, provider or metadata. Other authorized administrators
in that same tenant can manage lifecycle. Ownership/definition transfers are not
admitted. The shared internal token cannot create or manage these identities.
Disabled access returns 501 before storage; database errors return 503, never a
fabricated empty inventory or not-found result.

Creation, rotation and reactivation generate a fresh local secret using 48 random
bytes from [Python secrets](https://docs.python.org/3.13/library/secrets.html).
Only its SHA-256 digest is stored; these are generated high-entropy credentials,
not user-chosen passwords. Plaintext appears only in the acknowledged issuance
response. Read/list/audit responses omit both plaintext and digest. Issuance/read
responses set `Cache-Control: no-store` and `Pragma: no-cache`. Generated secrets
never enter audit snapshots or application logs. Avoid secrets in free-text inputs;
there is no general secret detector for arbitrary description/reason text.

The [local service](../../backend/agents/iam_agent/app/services/nhi_service.py)
has an administrator-side credential-proof method using constant-time digest
comparison, current database state and aware expiry checks. This method is not a
public endpoint, token exchange or permission decision. It audits its local proof
result under the verified administrator's identity and grants no roles, JWTs,
entitlements or API scopes. Current authentication still rejects these opaque
secrets as bearer JWTs. A future machine-authentication consumer must qualify its
own authority, rate limits, credential handling and operation scope before adoption.

Rotation replaces the digest and invalidates the previous local proof. Deactivation
clears the digest/expiry. Reactivation requires an inactive record and issues a new
secret, so it cannot revive old credentials. Soft deletion clears credentials,
retains history/name reservation and is terminal. These changes affect this local
registry only: they do not revoke an external provider token or terminate sessions.
Expiry is checked on each local proof; no background scheduler is introduced.

Row locks reload current state and require the exact expected version. One of two
competing rotations succeeds; the stale request returns 409. Account, version,
credential and actual-actor audit updates commit together. Audit/storage failure
rolls back and returns 503 without a credential receipt. If commit acknowledgement
is lost, a credential may have changed without its plaintext reaching the caller.
Inspect the registry's current version and explicitly rotate at that version; the
lost plaintext cannot be recovered. Repeating the old version cannot rotate again.
Creation has the same uncertainty; find the retained name/ID before recovery.

[V017](../../backend/migrations_consolidated/V017__public_service_account_registry.sql)
and its [ORM](../../backend/agents/iam_agent/app/models/service_account.py) add
`public.iam_service_accounts` in the separate IAM store. Forced restrictive tenant
RLS, lifecycle/credential constraints, an immutable-ownership/version trigger and
blocked hard deletion guard that contract. Operational roles still need explicit
least privileges; RLS is not protection against a privileged database owner or
superuser. The migration does not adopt or change a private runtime-created
`nhi_service_accounts` table, and it leaves shared catalog `api_keys` untouched.
Unknown legacy ownership/data/history needs explicit reconciliation. No startup
or request path creates tables. The IAM profile now selects eight files through
V017; the shared catalog profile makes no change when the IAM grant domain is absent.

The legacy `/api/v1/api-keys` create/list/rotate/revoke operations now return 503
under verified context. Their old implementation minted strings, returned an empty
list and claimed revocation without persistence/authentication. Neither an environment
flag nor the NHI registry makes those API keys valid. Scope/rate-limit storage and
actual authentication remain blocked pending their own implementation and acceptance.
The bootstrap seeder also stops retrieving a client secret merely to print it.
Its other provider privileges/bootstrap operations remain separate deployment gates.

Unit and owned PostgreSQL tests cover the disabled default, actor/tenant input
forgery, secret response boundaries, complete local lifecycle, expiry, old/stale
credentials, two tenants, populated legacy preservation, ORM/DDL parity, restrictive
RLS/immutable ownership, inventory bounds, audit rollback, uncertain commits and
competing rotations. All SQL runs in a disposable owned cluster. Existing database
migration, full Flyway/shared-baseline history, live identity/provider configuration,
bootstrap privileges, hosted CI and whole-IAM migration acceptance remain open.
