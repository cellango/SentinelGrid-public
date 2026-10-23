# Evidence and run provenance storage

Status: **inactive storage extension**, paired SQLAlchemy metadata and Flyway
V019. There is no API, Activity, worker or production provisioning writer, no new
application grant, and no activation flag. Deployment alone does not enable writes.
This is a partial implementation of the [logical contracts](agentic-contracts.md),
not a completed case workflow or end-to-end SOC qualification.

## Storage contract

`evidence_references` retains bounded source type, locator, immutable source version,
content SHA-256 or explicit digest-unavailable reason, observation/collection times,
retention deadline, access classification and custody reference. It does not fetch
URLs or copy evidence blobs. Existing evidence stores remain source systems; never
put credentials or bearer URLs in locators. The writer must enforce access and
retention policy; these stored labels do not implement those controls.

`case_evidence_links` binds evidence to a case in the same tenant. `run_manifests`
retains a run UUID, tenant/case/request identity, initiating subject, mode,
trigger/content references and explicit playbook, selection, skill, model, prompt,
toolset, policy and runtime versions. Its versioned JSON-object payload retains
up to 256 KiB of exact UTF-8 bytes and a database-checked SHA-256. This is an exact
byte digest, not an RFC 8785 canonicalization claim. `evidence_ids` is a required
array with at most 256 entries. Deferred constraints require exactly the immutable
`run_evidence_links` set at commit; missing, additional, duplicate or non-UUID
entries cannot be committed. Empty sets can describe ungrounded/denied synthetic
records and do not establish eligibility to execute an action.

Composite foreign keys enforce tenant/case lineage. A unique tenant/case/request
key detects duplicate provisioning; it does not implement retry response semantics.
The future writer must compare the complete retained request before treating a
conflict as an idempotent replay. All four tables reject row UPDATE and DELETE,
including owner DML, and have forced tenant RLS. Application roles have no table
access. Schema owners/superusers can bypass or remove protections; this is not
cryptographic tamper-proof storage. Retention erasure/hold/recovery procedures need
separate qualification before activation; no purge job is added here.

Version strings and content references must identify retained immutable artifacts
when a writer is qualified. SQL cannot prove that a source version exists, that
content is trustworthy, or that a model produced an output. Future producers must
validate the full payload schema, reject ambiguous JSON (including duplicate keys),
resolve/pin artifacts and enforce provenance/version consistency before persistence.
Stored `live` mode is a record label, never live-execution authority. None of these
records replaces Temporal execution history or establishes provider effects.

## Provisioning authority: proposed, not enabled

The accepted boundary remains deterministic `case_runtime` authorization, verified
tenant UUIDs, exact action admission and separately qualified issuer/caller gates.
The [action authority](action-authority.md) and root [guardrails](../../AGENTS.md)
still apply. Database owner inserts in tests are fixture setup only.

A possible first synthetic qualification profile would use a verified user caller,
fresh entitlement and policy evaluation, and explicit provisioning permissions.
Names such as `case.create` and `case.grant.manage` are **proposed capabilities**,
not existing accepted permissions. A dedicated least-privilege provisioning login
would be distinct from the action application role. This change creates neither
that login nor its grants. The existing action role admission rejects extra table
privileges, including access to these new tables.

Before enabling any writer, the owner must approve the initial caller profile,
server-owned mapping from permissions to case ownership/grants, and the consistency
boundary for revocation between policy evaluation and database commit. A proposal:
creation must not implicitly confer approval/execution/verification rights; grant
administration is separate, expiring, audited and cannot self-escalate. Tenant,
caller and permitted mode come from verified server context, never model output,
headers or submitted evidence. Stale/revoked identity, mismatched tenant, unknown
capability, stale policy and ambiguous prior requests fail closed. These are
qualification requirements, not implemented authorization in V019.

A user-seeded synthetic case is not automated event admission. Automated workload
issuers, token exchange/delegation and caller lifecycle must pass their separate
accepted gates before an event can provision a case. No ADR acceptance, production
credential, permission change or provider authorization is inferred from this
storage work. Temporal remains the execution owner; no competing runtime is added.

## Native qualification and scope

Run `make preview-case-provenance-db` with reviewed `SG_TEST_PG_BINDIR` and
`SG_TEST_FLYWAY` paths. Missing tools fail; the test owns and destroys a temporary
cluster and cannot select an existing database. The restricted RLS probe and all
fixture roles exist only in that cluster. Never use these fixtures as provisioning
instructions for a deployed database.

The extension profile [case-provenance-profile.json](../../publication/case-provenance-profile.json)
pins V001–V019. The established application profile remains explicitly pinned to
V001–V018; it must not silently claim V019 coverage. New tests cover populated
V018 upgrade preservation, checksum failure, no-op migrate, physical/model shape,
invalid records, atomic evidence-set denial, cross-tenant/case edges, immutability,
request conflicts, application denial, RLS, restart and restored records with Flyway
validation. They do not qualify deployed data, production provisioning, Temporal
replay, provider effects or complete audit reconstruction. Local checks are not CI.
