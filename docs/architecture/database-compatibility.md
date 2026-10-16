# Database compatibility and case storage plan

Reviewed October 16, 2026. Status: accepted platform planning baseline; **full
database/runtime qualification remains pending**. The focused IAM audit/session
implementation and synthetic qualification are recorded below. This page defines storage boundaries and migration gates for
the [runtime decision](decisions/0001-case-runtime.md) and
[logical contracts](../reference/agentic-contracts.md). The planning sections add no schema or execution dependencies; the focused IAM
implementation below pairs its model and additive migration without deployment
provisioning or a general runtime qualification.

## Preserve the public lineage

The application migration authority is
[backend/migrations_consolidated](../../backend/migrations_consolidated/).
Retain the exact V001–V013 files and their checksums. New application changes pair
explicit-schema SQLAlchemy models and new Flyway migrations in the same review,
under [the contributor rules](../AGENTS.md). Allocate the next globally available
version when implementing each change; this plan reserves no numbers.

| Public versions | Existing schema intent | Compatibility requirement |
| --- | --- | --- |
| V001 | Initial dump: `public`, `security_ops`, `orchestration`, `audit`, `reporting`, `llm_training`; extensions and owner declarations | Preserve baseline bytes; qualify its extension, owner, privilege and schema prerequisites before calling it a fresh-install path |
| V002 | Scan type | Preserve `orchestration.scans` behavior |
| V003 | Tenant backfills, tenant helper, RLS and policies | Retain this RLS lineage; never substitute another branch's different V003 |
| V004 | Shared report-template reads | Preserve narrowly scoped shared visibility while denying tenant-private cross-reads |
| V005–V007 | Evidence requirements, tenant framework selections, control coverage | Preserve compliance model and tenant coverage data |
| V008–V009 | Evidence lifecycle/links/reviews/exports and idempotency | Reuse existing evidence references; preserve deduplication and lifecycle |
| V010 | Compliance recommendations | Keep these distinct from a generic cross-domain recommendation or execution task |
| V011–V012 | Integrity, retention and tenant compliance preferences | Preserve legal retention, integrity and launch controls |
| V013 | `public.infrastructure_change_requests` | Preserve cloud change review fields and matching model/index/default contract |

V001 statically declares 147 tables; the consolidated files through V013 declare
157 distinct table names. These are source inventory counts, not a verified live
catalog or proof of complete model coverage. Only the
[V013 offline contract](../../backend/tests/test_infrastructure_change_schema.py)
is currently checked against its paired model. PostgreSQL execution, baseline
installation, historical upgrades and RLS remain unqualified.

Flyway versions identify a sequence, not a merge strategy. For a database that
actually applied a conflicting V003, stop and preserve its history, schema and
data first. Do not rename its history entry, run `repair`, disable validation, or
pretend it applied the public RLS migration. Plan a separately reviewed export into
a qualified public-lineage database, with tenant mapping and row reconciliation;
allow an in-place bridge only after a specific catalog/history comparison proves
it safe. Different history-table names do not prove that tables are independent.
[Flyway's versioned migration guidance](https://documentation.red-gate.com/flyway/flyway-concepts/migrations/versioned-migrations)
explains checksum tracking and unique ordered versions.

## Existing source gaps and ownership

| Source family | Finding / required disposition | Implementation owner |
| --- | --- | --- |
| [Core configuration](../../backend/migrations/flyway-schema-only.conf) and [development Compose](../../docker-compose.dev.yml) | Configuration names the consolidated folder, but its commented command overrides it with the old folder. Compose core runner mounts the old folder plus model-gateway SQL, uses a separate core history table, disables validation and ignores missing migrations. Replace with one explicit qualified application runner before runtime enablement | CI/infrastructure migration, with every affected schema owner |
| [Minimal Compose](../../docker-compose.minimal.yml) | SOAR mount references a different old service path; runners and history-table defaults differ from development Compose | CI/infrastructure migration |
| [Shared ORM](../../backend/libs/sg_core/models.py) | Some models are unqualified; `alert_playbook_triggers` needs comparison with its `security_ops` DDL. `playbooks` and phishing tables have same-name representations in different schemas. Bind each mapper/query to its intended table before moving data | Runtime/domain migration |
| [SOAR local SQL](../../backend/agents/soar_agent/db/migrations/), [model-gateway SQL](../../backend/services/model_gateway/db/migrations/), [legacy SQL](../../backend/migrations_legacy/) | Separate local numbering and histories; some tables overlap V001. Historical intent only. Compare columns, constraints, data and callers; port missing accepted changes to fresh consolidated versions rather than enabling another application migrator | Runtime/model and domain migration |
| [IAM local SQL](../../backend/agents/iam_agent/migrations/), scanner and observables SQL | Identify the actual database and history for each consumer. A separately provisioned IAM database and the shared database can have same-name tables with different contracts. Keep a documented physical database/schema/table identity; do not merge them by name | IAM and domain migration |
| [Session helper](../../backend/libs/sg_core/db.py) | Plain sessions coexist with tenant sessions; transaction-local tenant setup is present, but binding syntax, transaction boundaries and pool reuse are not database-tested. The session-controlled superadmin policy requires separate privilege design | IAM migration and each caller |
| V013 and later tenant tables | V003 has a fixed table list and cannot cover tables created later. V013 does not add RLS; inventory later tables and add tested policies in new migrations | IAM and domain migration |
| Existing `create_all`, raw DDL and startup helpers | These remain source in experimental modules. They cannot be the migration authority for admitted features. Move schema intent into paired model/Flyway changes and prevent startup creation on the qualified path | Each component's migration task |
| New approval, checkpoint, registry, memory and posture/compliance candidates | Require explicit schema/type/tenant mapping, data preservation and paired models. Checkpoint JSON is historical input, not a second live case scheduler. Translate accepted non-Flyway revisions; do not run a second migration system | Runtime/model, prototype and domain migration |

This is a porting gate, not a claim that existing deployments used any one layout.
Capture each database's effective URL destination (without credentials), PostgreSQL
and extension versions, roles, schemas, search paths, all history tables, checksums,
row counts and constraint/policy definitions before deciding its path. New
application Flyway execution must use only the consolidated location, one documented
history table in the application database, validation enabled, and no automatic
baseline/ignore-missing workaround. Adoption of a populated legacy database needs
an explicit reviewed reconciliation. Database/role provisioning is a separately
reviewed infrastructure step; application DDL still belongs to Flyway.

If an unchanged historical migration cannot execute with reviewed prerequisites,
D0 fails. Record the exact error and seek a separate explicit baseline/compatibility
decision; do not hide it by changing published checksums, skipping a version or
claiming that a later corrective migration repairs an earlier execution failure.

## Physical target and boundaries

Use a new **`case_runtime` schema in the application PostgreSQL database** for the
general case and action records below. Keep existing domain tables in their current
schemas; a case can reference incidents, tickets, assets, findings and compliance
evidence without renaming them or copying their raw records. A new case gets its own
UUID; an incident UUID is not automatically the general case UUID. Only the
authorized facade and deterministic domain APIs write business authority.

| Storage boundary | Authority and access | Migration / recovery boundary |
| --- | --- | --- |
| Application DB: current domain schemas plus proposed `case_runtime` | Cases, access, plan revisions, definition versions, proposals, decisions, evidence refs, receipts and outbox | Project Flyway with paired ORM; application backup and reconciliation |
| Separate Temporal persistence and visibility databases | Engine history, scheduling/timers, replay and visibility | Vendor schema tooling pinned to the selected server release; dedicated infrastructure credentials and recovery process |
| Existing evidence/source stores and tenant-scoped retrieval | Source records, artifacts and derived searchable representations | Their documented domain lifecycle; references/digests and authorized retrieval |
| Redis | Target cache/notifications only | Rebuildable; never authority for approval, effect completion or case scheduling |

The separate Temporal databases are a project isolation decision. Workers use the
engine API, not SQL access to its tables; the application role cannot read or modify
vendor storage and the Temporal role cannot modify application records. Do not put
vendor DDL in the application Flyway history or add SQLAlchemy business models for
vendor-owned tables. An operator runs the reviewed vendor migration step; service
startup is not the application migration mechanism. Temporal documents its
[schema upgrade tooling](https://github.com/temporalio/temporal/blob/main/tools/sql/README.md)
and [visibility storage](https://docs.temporal.io/self-hosted-guide/visibility).
Server/SDK/database/extension versions, privileges and resource requirements are
qualification decisions for the implementation tasks, not selected pins here.

### Proposed application tables

The [adaptive Playbook refinement](adaptive-playbooks.md) supersedes the earlier
independent `workflow_definitions` proposal with immutable versions of the existing
Playbook identity and a coverage catalog. It also makes the manifest/event/artifact
audit records explicit. No physical table or migration has changed.

These are physical planning names, **all absent until implemented**. Every
tenant-owned row has `tenant_id UUID NOT NULL`. Unless shown otherwise, use a UUID
primary key plus a unique `(tenant_id, id)` target for composite child references.
Existing domain links carry the source schema/type and tenant-bound source UUID.

| Tables in `case_runtime` | Key relationships and required content |
| --- | --- |
| `cases`, `case_access_grants`, `case_entity_links` | Independent case identity, revision, kind, goal, business status, accountable owner, classification, timestamps; scoped principal grants and canonical entity/service references. Unique `(tenant_id, case_id, source_type, source_id)` links |
| `case_source_links` | Legacy incident/ticket/execution mapping with source system/schema/key and provenance; unique source identity per tenant and link kind. Explicit mapping, never an authorization alias |
| `case_plan_revisions` | Immutable `(tenant_id, case_id, plan_revision)` with plan UUID, validated bounded graph, definition digests, constraints and author. One active revision pointer on the case, updated by compare-and-swap |
| `workflow_run_requests`, `trigger_receipts` | Run UUID, existing Playbook/version and case/plan, coverage refs, immutable selection binding, compiler/runtime build, trusted initiator/scope, trigger identity, parent run, correlation, submission status and engine identity. Unique tenant/source/event/dedup identity rejects a conflicting reused key rather than accepting new content |
| `workflow_run_projections`, `task_projections` | Engine run/task IDs, parent/dependency references, monotonic projection revision, observed state/time. Rebuildable display/query projections, never an independent runnable queue |
| `manual_tasks`, `manual_task_events` | Authoritative human assignment, permitted decision, required evidence, deadline and append-only authenticated completion/cancellation/escalation events. Engine owns wake-up timing; application records prove what the person actually did |
| `evidence_references`, `case_evidence_links` | Tenant/case, scoped source locator/version, digest where applicable, collection/observation/freshness times, provenance and access/retention classification. Immutable versions; reuse existing compliance evidence rather than duplicating artifacts |
| `agent_invocations`, `agent_results` | Separate definition/run/task IDs, pinned prompt/model/tool versions, bounded input refs, typed result/evidence, uncertainty, usage and outcome. No credentials or hidden reasoning traces |
| `action_proposals`, `policy_decisions` | Stable logical action ID, separate immutable proposal ID/revision with unique `(tenant_id, action_id, proposal_revision)`, exact target/parameters/tool/effect/constraints/revisions/expiry plus canonical proposal hash; policy version, caller capabilities and decision. New content creates a new proposal; never mutate an approved payload |
| `approval_requests`, `approval_decisions` | Request/decision UUIDs tied to exact action/hash, tenant/case/plan/policy revisions, approver/role, separation of duties, expiry and revocation. Append decisions; enforce one effective decision under locking and current policy |
| `action_claims`, `resource_fences`, `action_attempts`, `action_receipts` | One logical effect identity per tenant; stable idempotency key, scoped resource key/fencing generation, lease/attempt, provider request/effect identity, typed ambiguous/failed/executed result and immutable redacted receipt refs. Unique attempt numbers; no duplicate live claim for the same effect |
| `action_verifications`, `case_closure_decisions` | Independent verifier/method/version, authoritative postconditions, health/freshness window, pass/fail/inconclusive, missing evidence and accountable closure/risk decision. Closure is a business decision, not a projected workflow status |
| `outbox_events`, `consumer_receipts` | Atomic business-event UUID, tenant, aggregate/revision, event schema/version and bounded reference payload; delivery attempts/lease/next-attempt/dead-letter state. Unique consumer/event receipt and aggregate-event identity for idempotent processing |
| `playbook_content_packages`, `use_case_catalog`, `agent_definitions`, `tool_definitions` | Platform-controlled immutable content packages, WF-* outcome coverage and agent/tool definitions. Full canonical payloads/digests, schemas, owner, compatibility and lifecycle. Runtime role reads global packages; no independent executable workflow registry |
| `playbook_versions`, `use_case_playbook_bindings`, `tenant_playbook_enablements` | Tenant-owned immutable version snapshots extending existing Playbook identity; optional reviewed base package; full source/compiled content, compiler/runtime versions, planning contract, coverage links and separate authorized enablement. Preserve tenant customizations and source IDs |
| `run_manifests`, `execution_events`, `task_attempts`, `decision_records`, `runtime_history_links` | Full run/selection/version/context manifest; append-only per-run event sequence/integrity refs, task/attempt and originating plan revision, typed decisions/input/output/authority links, engine history pointer. Unique `(tenant_id, run_id, sequence)` with serialized sequence allocation; event/outbox and authoritative writes commit together |
| `evidence_artifacts`, `artifact_access_events` | Protected source/approved bytes, digests/location, redaction links, source/event/collection times, custody/access events, retention/hold; connect existing evidence stores and audit rather than copy raw data into history |

In `security_ops`, plan immutable `detection_playbook_binding_versions` extending
the existing rule/mapping identity. Bind tenant/rule/query version, exact Playbook
version, conditions/precedence, fallback and publication decision; add cross-schema
references in explicit follow-up migrations. Keep legacy mapping reads through a
scoped compatibility projection/adapter, not a second active selection authority.
The full history/catalog audit must precede any constraint change or data backfill.

Tenant-owned customization must live in separate tenant-scoped version rows; it
cannot write global definitions or use `tenant_id = NULL` as implicit shared access.
Global definition publication uses a separate narrowly privileged role. Add
tenant-specific indexes for case/status/time, source identity, active manual work,
evidence expiry, pending approvals, resource ownership and outbox delivery. Use
partial indexes for active rows where needed; verify query plans and lock behavior
on representative synthetic volume before choosing additional indexes.

Keep constrained identifiers, status, revision, timestamps, expiry, hashes and
relationships as typed columns. Use bounded, versioned JSONB for graphs, typed
parameters, schemas, redacted results and provenance extensions; validate it at the
contract boundary. Do not bury tenant identity, authorization or all relations in
one mutable JSON blob. Match ORM and DDL nullability, server defaults, time zones,
JSONB types, checks, indexes and foreign keys in the same change.

Internal foreign keys include tenant UUID, so a valid object UUID cannot attach a
child to another tenant's parent. Add cross-schema tenant/domain constraints in
explicit follow-up migrations after both sides exist and invalid/orphan rows have
been resolved. For external service/database references, validate ownership through
the authorized domain API and record provenance; do not invent a cross-database FK.
Apply retention/legal holds explicitly; avoid cascade-deleting audit/approval/effect
history. Restrict updates to immutable rows and audit privileged corrections.

### Transaction and authority rules

1. Atomically persist case/run intake, dedup receipt and outbox before returning
   accepted. A unique-key conflict must return the same bound request or reject a
   content mismatch. No acknowledgement after a rolled-back or uncertain commit.
2. A leased dispatcher starts/signals the stable engine identity, then records
   delivery. Crash between those steps must be safe on redelivery. Consumer receipts
   and monotonic projection revisions reject duplicate or older updates.
3. Persist an exact approval decision and outbox event together. Resume re-reads
   current authority; notification or projected status alone cannot approve.
4. Claim an action with current case/plan revisions, policy, valid approval and a
   resource fence in a short transaction. Do not keep a database transaction open
   across an LLM/provider call or human wait. Recheck cancellation/expiry/authority
   immediately before dispatch; use provider preconditions/fencing where supported.
   Revocation after an effect is dispatched requires reconciliation, not a promise
   that a local lock can undo it.
5. Store receipts and verification separately. Preserve uncertainty after provider
   timeout or uncertain commit. Reconcile authoritative state before retrying a
   possible write; block and assign a human when safe reconciliation is unavailable.
   Local idempotency cannot promise exactly-once effects at arbitrary providers.

Application outbox retry state concerns message delivery, not case orchestration.
Temporal remains the sole scheduling owner. Keep sensitive evidence and credentials
out of both outbox payloads and engine history; use authorized references, scoped
credential lookup, redaction and explicit retention/access policies.

## Tenant sessions and least privilege

Use verified server/workload context, validated as UUID, for every application
transaction including background work, approval, retrieval, resume and outbox
delivery. Apply `app.current_tenant_id` transaction-locally with a parameterized
`set_config(..., true)` call before the first scoped query. Reapply after every
commit/rollback and new transaction; a previous transaction's setup is insufficient.
Missing, empty or malformed context must deny rather than widen access. Test the
actual SQLAlchemy driver binding, nested transactions and pool checkout paths.
[PostgreSQL documents transaction-local settings](https://www.postgresql.org/docs/16/functions-admin.html).

The target application role is neither table owner, superuser nor `BYPASSRLS` and
cannot inherit the migration role, alter policies or truncate tables. Enable and
force RLS on tenant tables, with scoped read predicates and write checks. Use a
separate audited operational role for authorized cross-tenant maintenance. Remove
the ordinary application's ability to turn a session flag into superadmin access
through a new reviewed migration; leave V003's bytes intact. A custom tenant setting
is trusted middleware context, not proof against a compromised SQL-capable service.
Retain endpoint authorization and prevent arbitrary SQL/model control of settings.

Policy review must include shared rows, views, functions, joined child tables,
foreign keys, direct SQL and all permissive policies. PostgreSQL documents owner/
superuser bypass, `FORCE`, policy composition and integrity-check behavior in its
[RLS guidance](https://www.postgresql.org/docs/16/ddl-rowsecurity.html).
Workers must select explicit authorized tenant work, then open tenant-scoped
transactions; do not give every worker a bypass role to poll across tenants.
Case classification and per-case grants further restrict reads within a tenant.

## Porting domain data and embeddings

Keep current IAM, scans, findings, incident/ticket, reporting, compliance/evidence
and V013 cloud records authoritative until each reviewed adapter and migration
passes parity tests. Existing operator approvals and infrastructure change reviews
remain historical records; they are not sufficient proof for a new exact action
unless all required binding fields can be verified. Otherwise require a fresh
approval. Never backfill fabricated approvers, hashes or verified success.

Legacy Redis task/memory payloads and checkpoint JSON need a tenant-bound inventory,
recorded versions and a drain/import disposition. Finished work can be imported as
history with provenance. Pending writes require explicit reconciliation and renewed
authority; opaque checkpoints cannot be replayed as trusted Temporal history.
Pause/drain competing schedulers at cutover, map active IDs and test rollback
ownership. Two runtimes must never execute the same pending effect.

Current source mixes 384-dimensional knowledge-base embeddings and 1024-dimensional
security-event embeddings. Future model/knowledge/memory ports must reconcile the
producer, ORM, SQL type and index for each collection. No blanket dimension switch,
drop/recreate, truncation, zero-padding or assumption that equal dimensions mean
compatible embedding spaces. Store model/version, dimension, preprocessing version,
source digest, tenant/access scope and freshness with each derived representation.

For an accepted new embedding model, add a parallel versioned representation and
index, backfill from authorized original content in bounded restartable batches,
then compare coverage, quality, privacy and latency before switching reads. Keep
old representations through the rollback window. Public/shared knowledge must have
an explicit ingestion authority and cannot expose private tenant material; caches,
query vectors and memory retrieval need tenant/model version isolation too.
[pgvector's primary documentation](https://github.com/pgvector/pgvector) describes
dimension-specific vectors and indexes; the safe migration above is a project choice.

Accepted posture/compliance prototypes must translate non-Flyway revisions into new
paired model/Flyway changes, resolve divergent revision heads, and convert text tenant
IDs through verified tenant mappings. Unknown/demo slugs and malformed IDs are
quarantined for a decision; never cast or assign them to a default tenant. Reuse
existing asset/service/evidence ownership before creating overlapping data stores.

## Ordered implementation slices

| Slice | Work and prerequisite | Exit evidence |
| --- | --- | --- |
| D0 — inventory and runner | Record effective histories/catalogs; preserve checksums; fix location/validation/role/extension prerequisites in a reviewed change | Qualified public-lineage fresh baseline plus a recorded reconciliation route for each older database |
| D1 — IAM and domain compatibility | Pair explicit-schema model fixes and additive IAM/RLS changes; preserve current domain/public-only features; normalize tenant IDs with verified mappings | Real least-privilege two-tenant and pooled-transaction tests; preserved domain data and APIs |
| D2 — accepted source ports | Immutable Playbook versions/bindings/compiler, qualified detection subset with all catalog rows dispositioned, approval intent, domain additions, model routing/knowledge/memory and accepted prototype changes; globally new versions, no local-history imports | Each source migration has exact column/constraint/data mapping and feature parity; no competing execution authority |
| D3 — shared case foundation | `case_runtime` models/migrations, Playbook versions/coverage, run manifests/events/artifacts, evidence/access/legacy links, intake/run/outbox; qualify Temporal vendor storage separately | Atomic acceptance/redelivery and application/vendor privilege boundaries, contract tests and replay/restore evidence |
| D4 — action and human authority | Immutable proposals/policy/approval decisions, manual tasks, claims/fences/receipts/verification; pair all callers with exact contracts | Changed/stale/forged approvals denied, ambiguous effects reconciled, no duplicate supported effects after worker death |
| D5 — cutover and retirement | Backfill/projection reconciliation, active-run drain and single-owner cutover; keep rollback compatibility | Data/count/digest reconciliation, recovery rehearsal, current documentation and explicit old-path disposition |

D0–D2 accompany the repository's existing IAM, runtime/model, prototype, domain and
CI migration tasks. D3–D5 implement the later shared-platform foundation as needed;
this planning task does not authorize their code, database operations or enablement.
Repository retirement needs every accepted existing feature accounted for; it does
not wait for every proposed future workflow to be built.

## Required qualification matrix

Run only against disposable synthetic databases in the implementation tasks. Pin
the tested PostgreSQL/extension/Flyway/driver/engine versions and capture effective
configuration, checksums, catalogs and results privately without credentials.

| Test route | Required assertions |
| --- | --- |
| Empty application DB | Provision reviewed prerequisites, execute exact public V001–V013 then new migrations, validate history, compare every admitted ORM table/column/type/default/index/constraint/policy; no startup DDL required |
| Upgrade from public baseline | Seed two tenants at V013 with domain/evidence/cloud/shared fixtures; migrate incrementally; preserve IDs, counts, non-derived data digests, retention and approved access |
| Earlier public versions | Exercise supported V001/V002 pre-RLS and V012 boundaries through V013 and new versions; validate child backfills, missing/orphan-row decisions, shared-template visibility and RLS |
| Conflicting/legacy/service histories | Inventory actual history tables, schema/data drift and divergent checksums; reject an unreviewed path; rehearse the chosen export/import or proved bridge and reconcile every row |
| Least-privilege tenancy | Tenant A cannot read/change/link/resume/approve tenant B; missing/empty/malformed context denies; inserts and tenant-ID updates cannot cross scope; session admin flag cannot bypass; test direct and joined reads, shared definitions and FK error handling |
| Connection/transaction lifecycle | Reuse one pooled connection A→B→unset, with commit, rollback, exceptions, nested transactions and retries; tenant context never leaks or silently disappears before a scoped query |
| Durability/concurrency | Duplicate intake, outbox crash before/after engine start, out-of-order projections, duplicate approvals, competing workers, lease expiry, stale fences, cancellation, uncertain commits/provider timeout; no authority lost or extra supported effects |
| Embedding transition | Match exact producer/model/preprocessing/dimension/index; interrupted backfill resumes, coverage/quality/privacy checks pass; old reads work during rollback |
| Failure and recovery | Interrupt additive backfill/index/migration steps; verify history and safe retry. Restore application plus vendor persistence/visibility and evidence refs to documented recovery points; reconcile outbox/projections/receipts without reissuing uncertain writes |
| Evidence reconstruction | Export full pinned content, selection, manifest, every plan/attempt/decision/approval/receipt/verification and permitted artifacts; reconstruct offline with zero model/provider calls. Verify custody, integrity anchors, redaction/retention/hold and protected history after definition retirement |
| Rolling compatibility and cutover | Old/new readers coexist during expansion; active definitions replay under qualified workers; drain old owner; rollback software without destructive schema downgrade or two schedulers |

Use expand → backfill → validate → switch → retain → separately review contraction.
Set lock/statement budgets, migration privileges, backup/recovery points and the
rollback window in each implementation change. Prefer forward corrective migrations
or application rollback while additive schema remains compatible. A restored
database does not undo a provider effect; reconcile external state before resuming.
No cleanup or destructive downgrade is included here. Passing offline preview
checks verifies this documentation change, not any row in the qualification matrix.


## IAM audit and session implementation

The focused IAM migration keeps two physical database contracts separate:

| Store | Table identity and caller | Migration history |
| --- | --- | --- |
| Shared application `DB_URL` | `public.entitlements` is the app catalog; `public.policies` is policy DSL. Catalog/Portal/policy sessions and the authorization policy reader use this store. | Exact consolidated V001–V013 plus new V014; the full extension/owner/runner baseline remains a D0 gate. |
| Separate `IAM_DB_URL` | `public.entitlements` is fine-grained grants; grant, role-mapping, access-request/governance session adapters and `public.iam_audit_events` use this store. | Historical IAM V0–V3 retained byte for byte, plus new consolidated V014 in the explicitly selected IAM profile. No shared V001 is imported. |

The [reviewed profile](../../publication/iam-database-profile.json) pins selected
source paths and SHA-256 values. `python scripts/prepare_iam_flyway.py --output
<new-directory>` assembles an IAM-only `sql/` location and `flyway.conf`, with
validation enabled, cleaning disabled and automatic baselining disabled. The tool
only copies reviewed bytes; it neither connects nor runs Flyway. Run an operator-
reviewed Flyway distribution from that bundle directory, supply credentials through
the deployment secret configuration and use the existing IAM history table. Never
point the IAM runner at the whole shared application location or run the shared
baseline against an IAM grant database. New application DDL remains solely in
`backend/migrations_consolidated`; the bundle is a reviewed selection, not another
migration source or startup runner.

For an existing IAM database, inventory its actual history table, checksums,
columns/constraints/policies, owner/privileges, rows and backup first. Exact historical
lineage can validate then advance to V014. Missing/drifted history, a private V126
variant, an unreviewed earlier shape or an unknown populated database must stop for
explicit reconciliation; do not repair checksums, auto-baseline, ignore missing
versions or manufacture history. Fresh synthetic tests execute exact V1–V3 SQL and
V014; V0 contains only provisioning comments. The shared-policy fixture uses the
exact named table declarations from V001. This verifies SQL behavior, **not** an
end-to-end Flyway execution or the complete shared baseline. D0 and hosted runner
qualification remain required before enabling a deployment.

V014 creates a new audit table/model without replacing legacy audit data or adding
cascading audit foreign keys. It adds restrictive tenant guards on the named IAM
parent/child tables present in either profile; missing unrelated tables are left
alone, and unexpected tenant-column types fail migration. It does not expand the
fixed V003 table list to every later domain table: V013 and other domain-wide RLS
acceptance remain in their owning migration tasks. App-controlled superadmin flags
cannot bypass the named IAM guards. Legacy shared/global IAM definitions gain no
implicit cross-tenant authority; their read/clone contracts require feature review.

Provision roles separately: a migration owner; a nonowner application role with
`NOSUPERUSER NOBYPASSRLS`, no migration/operational role membership, no schema-create/
policy-alter/truncate rights; domain-specific DML; and SELECT/INSERT only for the new
audit events. No credentials or roles are created by V014. Retention/cross-tenant
maintenance needs a separate accountable operational identity. Both database URLs,
server/driver versions, history validation, grants, backups and rollback window must
be reviewed for a real environment. An application rollback keeps the additive table;
never drop audit history as a schema downgrade.

The current checks use a new private socket-only PostgreSQL cluster and synthetic
records. They prove the named audit, grant and tenant transaction paths with a
least-privilege role. Current grant CRUD/authorization is covered; older campaign,
certification, role-pattern and editor ORM/API differences are not thereby qualified.
The [identity reference](../reference/identity.md#persistent-audit-and-tenant-database-checks)
describes semantics, tested versions and limits. These focused results do not close
D0, all domain compatibility, runtime/engine qualification or overall IAM acceptance.
