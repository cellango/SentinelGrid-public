# Domain-owned storage foundation

Direction accepted; implementation remains partial and inactive. Inspected source
base: `26e88082859a87c0dece422fd33cde0b1d1555d7`. No deployed database audit.
This foundation does not supersede the Temporal ADR or enable provisioning.

## Ownership and transaction contract

Domain ownership means one authoritative writer and explicit invariants, not one
database per agent. A modest shared PostgreSQL cluster may initially host domain
databases. Separate databases still require cross-store coordination. Schemas can
share transactions but not independent physical failure/recovery boundaries.

| Data / source identity | Target owner | Transaction and reader boundary |
| --- | --- | --- |
| Catalog `public.policies` and `public.policy_rules` | IAM effective authority | Policy activation, deny changes, grants, principal bindings and authorization generation must be coherent; other domains request decisions |
| IAM `public.entitlements`, role bindings, governance and local decision audit | IAM | Subject grants are not catalog permission definitions; preserve IDs, status, expiry and audit relations |
| Catalog `public.entitlements` | Catalog | Permission definitions only; never import as subject grants |
| Catalog `public.policy_templates` | Catalog reusable definitions | Current rows are mutable, **not already immutable versions**. Publish version/digest-pinned immutable definitions before IAM activation references them |
| `case_runtime` cases, approvals, action grants, attempts and outbox | Case/response | Case writer holds its local transaction/locks; IAM does not own case lifecycle |
| Case evidence links/run manifests; compliance custody records | Case linkage / evidence custody respectively | Preserve immutable references and retention/hold authority. No arbitrary cross-domain writes |
| Temporal persistence and visibility | Temporal | Vendor lifecycle; application facts remain in owner stores; no second scheduler |
| Reporting, retrieval, OpenSearch | Projection owners | Lag-aware read models; cannot authorize actions. Existing pgvector retained |

This is a first-boundary inventory, not a complete table ownership certification.
`publication/domain-store-foundation.json` records source identities, writer
families and migration paths. Unlisted tables/writers remain unqualified.

Current evidence: IAM `app/core/database.py` requires a separate grant database;
`app/api/request_context.py` provides distinct policy/grant sessions;
`app/services/evaluation_engine.py` combines their reads. Consolidating mutable
effective policy with grants removes that internal split. It does **not** make
the final case commit atomic with IAM revocation. External issuer freshness is a
separate contract; local locks cannot order unknown remote revocations.

Keep the admission-fence experiment and its tests. Compare a scoped split-store
fence with a narrow same-database admission interface using equal create-first /
revoke-first guarantees. Neither whole-tenant closure nor a consistency island is
enabled by this foundation. New broad deny policies must invalidate prior
decisions even when absent from their earlier matched-rule list.

## DBF-01: offline foundation checkpoint

The pure Python rehearsal copies **synthetic** row envelopes into logical target
groups, preserves opaque payloads/status/expiry/IDs, separates same-named
entitlement meanings, checks rule ancestry, detects conflicting identities and
reconciles canonical counts/digests. It rejects mixed policy/template rows and
unknown source profiles. The actual migration bytes are checked against the two
pinned profiles. The output is explicitly non-executable.

Run `make preview-domain-foundation` (standard library only). No database,
network, environment credentials or application imports are used. These tests do
not qualify SQL installation, the evaluator, RLS, live data, restore, concurrency
or end-to-end containment. A synthetic flag is a fixture convention, not a
security control capable of detecting real data. There is no CLI accepting data.

The target names in the rehearsal are logical labels, **not new SQL tables**.
No schema change, ORM change, Flyway migration or writer switch is in DBF-01.
All inactive/denied/expired rows remain unchanged; no decision engine is added.

## Migration path correction plan

The qualified application profile selects V001–V018; inactive provenance selects
V001–V019. IAM uses its legacy V0–V3 lineage plus V014–V017. Their histories cannot
be merged by matching version numbers. Shared catalog entitlements have a
different schema and meaning from IAM entitlements.

Development Compose's core runner mounts `backend/migrations` plus model gateway
migrations, uses `flyway_schema_history_core`, enables automatic baseline and
ignore-missing and disables validation. Additional model-gateway and SOAR runners
have separate histories. Minimal Compose also baselines. These configurations
are not the pinned qualification profile; no runner is corrected or executed
here. IAM's separate URL must also be explicitly reconciled in deployment config.

Before changing a runner: inventory each actual database's history, schemas,
ownership and checksums through separately authorized read-only inspection;
classify fresh / recognized upgrade / unknown. Reject unknown or drifted lineage.
Create an explicit profile and paired ORM/Flyway change for the intended target,
then test fresh install, supported upgrade, interrupted migration, restart and
logical restore. Never use repair, ignore-missing or automatic baseline to adopt
an unknown populated store. Do not rewrite published migration bytes.

## Bounded checkpoint sequence

| Checkpoint | Entry and deliverable | Exit tests / documentation |
| --- | --- | --- |
| DBF-01 ownership/preflight | Reviewed source profiles; ownership ledger, synthetic transfer planner | Deterministic reconciliation and negative tests; no SQL or runtime edits; this page plus contract inventory |
| DBF-02 native IAM rehearsal | DBF-01 reviewed; explicit paired model/Flyway target, full table/foreign-key and writer inventory | Disposable databases only; preserve policy/grant/audit IDs; existing evaluator before/after gives identical allow/deny/challenge; newly inserted deny, expiry, tenants, nonowner RLS; atomic policy+grant rollback; fresh/upgrade/restore comparison |
| DBF-03 runner alignment | Recognized lineage and successful native rehearsal | Correct development bundle/config without executing live; no baseline fallback; wrong histories fail; install/upgrade/restore checks; operator runbook |
| DBF-04 strict admission comparison | Coherent IAM authority; all invalidation paths accounted for | Reuse fence cases: both commit orderings, stale decisions, duplicate recovery, timeouts/deadlocks, uncertain outcomes, restart, restored generation non-reuse. Document placement choice before writer integration |
| DBF-05 synthetic workflow | Admission contract qualified; separately approved implementation | Actual Temporal plus case/evidence/approval/action persistence and simulated provider boundary; replay/outbox/inbox reconciliation; no real containment claim |

Every checkpoint includes implementation, meaningful automated tests, matching
docs and contract impact review, then stops for commit/push approval. CI remains
paused. Do not wait for extracting every projection before the first workflow.

## Cutover, rollback and restore gates

DBF-01 has no data effects; discard its generated plan to roll back. DBF-02 must
demonstrate owner-preserving logical dump/restore with synthetic data. Real
cutover is later: freeze all relevant writers in a bounded window, export under
a coherent snapshot, validate counts/digests/relations/evaluation, then switch
one authority. Never run two writable masters. Before new writes, rollback can
return to the intact old authority; after new writes, rollback requires a
qualified reverse/delta reconciliation or remains closed. Simply switching a URL
back would lose decisions and revocations.

Restore acceptance spans IAM, case/evidence references and Temporal retried
Activities. An independently controlled incarnation must prevent restored old
generations from reopening admission; restoring its authority alongside the old
database is insufficient. Preserve ambiguous effects for reconciliation, not
automatic replay. Define RPO/RTO and recovery custody before production; no
throughput, downtime or freshness guarantees have been measured here.

Writer inventory must cover policy CRUD, portal imports/updates, seed/template
paths, grants and bulk operations, access requests, governance, role sync and
service-account/principal lifecycle. The current list is a review queue, not
proof of exhaustive participation. Unknown policy DSL or template semantics must
be reconciled, not silently dropped to make a migration pass.
