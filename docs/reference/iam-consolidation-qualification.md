# IAM consolidation qualification candidate

Status: **locally qualified synthetic checkpoint; production integration pending**.
Base `26e88082859a87c0dece422fd33cde0b1d1555d7`. This isolated checkpoint
continues the accepted domain ownership direction without changing runtime
connections, deployed privileges or production migration profiles.

## Boundary and implementation

`tests/consolidation_qualification/V022__public_qualification_effective_policies.sql`
adds effective `public.policies` and `public.policy_rules` only in the disposable
IAM target. Their paired SQLAlchemy models live beside that fixture; no runtime
Base metadata is changed. V022 is a qualification-only version following the
V020/V021 fence fixtures, not an allocated production migration. Existing pinned
IAM V0–V3/V014–V017 bytes are verified and applied using actual Flyway before
the fixture. Production migrations require a separately reviewed profile/version.

The source arrangement reuses `test_iam_database` synthetic fixtures: separate
catalog policies and IAM grants. The target uses the unchanged `EvaluationEngine`
and `PolicyService` with a single nonowner tenant-bound session. No new permission
engine is introduced. The fixture copies full policy, rule and subject-grant rows
under a target transaction and compares them before evaluation usage counters
change. Catalog permission definitions and template candidates are not copied.
Existing mutable templates are not misrepresented as immutable published versions.

The disposable cluster uses an owned temporary directory, Unix socket and random
loopback port. Temporary owner authentication is generated locally for Flyway;
the nonowner test role uses the existing socket-only fixture arrangement and has
no superuser/BYPASSRLS/role-creation/database-creation rights. Grants exist only
inside this disposable cluster. No real DB_URL/IAM_DB_URL is used, and no
credentials or access survive successful teardown. This is not production-role
or credential-lifecycle qualification.

## Intended native tests

Run `make preview-iam-consolidation-db` with the already installed PostgreSQL
tools in `SG_TEST_PG_BINDIR`, Flyway executable in `SG_TEST_FLYWAY`, and the
existing Python environment. Missing tools fail instead of silently skipping.

The 18 native cases cover:

- actual split-versus-consolidated evaluator parity for allow, deny, MFA,
  approval challenge and unknown actions; durable decision audit;
- policy-level MFA challenge retained, with final action admission denied;
- expired/revoked grants and missing subjects;
- insertion of a new deny policy after an earlier allow, with another tenant
  still unaffected;
- nonowner rights, absent tenant context, tenant visibility, cross-tenant updates
  and child-rule ancestry;
- one explicit transaction committing or rolling back policy/grant changes;
- exact row transfer, duplicate-copy rollback, exclusion of catalog templates;
- native model/schema checks, fresh install, recognized IAM upgrade, repeated
  Flyway migration and validation;
- real pg_dump/pg_restore of policies, grants and audit, followed by validation
  and actual evaluator denial against the restored target.

## Execution evidence and limit

Native qualification passed: all 18 cases ran against an owned PostgreSQL cluster
with actual Flyway, the existing evaluator, nonowner tenant-bound sessions and
pg_dump/pg_restore. The recognized IAM upgrade retained its existing grant;
repeat migration applied no changes and validation succeeded. Disposable cluster
teardown completed. No real data, runtime wiring or production privilege changed.

Earlier evidence is retained separately: the sandbox bind failed before cluster
creation, an elevated launch was initially rejected, then explicit approval
permitted the native run. Its first run had 16 failures and 2 passes because the
unit-test connection guard recognized only the older native suite. The guard now
also recognizes this specific owned-cluster file; other tests remain blocked from
unintended SQL connections. The corrected 18-case run passed. Source collection
was never reported as native qualification.

## Remaining design and migration gates

Consolidation permits a local transaction; it does not automatically rewrite all
writers. The atomic mutation checkpoint below corrects the existing PolicyService
create/update and its tenant-template clone path. All alternate portal,
seed/template, bulk, governance, role-sync and principal/credential writers must
still be reviewed before activation. Audit and principal/governance relationship
transfer is not covered by this selected row-copy rehearsal.

This does not establish a stable authorization generation, order revocation
against a separate case commit, solve external issuer revocation propagation,
or qualify complete workload authorization. Preserve the fence tests and compare
the same admission semantics before selecting final placement. No fence is
enabled by adding policy tables to an IAM test database.

Rollback before activation means discarding the disposable target; live source
authority is unchanged. A future real cutover needs a bounded writer freeze,
coherent snapshot and complete relation/count/digest/evaluation reconciliation.
Do not dual-write authorization masters. After accepting new writes, rollback
requires reverse/delta reconciliation, not a URL switch. Logical dump/restore
tests do not establish PITR, RPO/RTO, independent incarnation custody or safe
reopening alongside restored cases and Temporal Activities.

Crash/restart during migration, lock contention/deadlocks, unknown populated
history, production-role admission, template version publication and full writer
coverage remain explicit later qualification gates. CI stays paused; publication
requires a tested checkpoint and separate commit/push approval.

## Atomic policy/rule mutation checkpoint

The existing PolicyService now commits a created policy and its extracted rules
once, after validating the response object. Updates acquire a tenant-filtered
parent row lock before replacing rules and updating the parent. This serializes
competing service updates so they cannot leave a parent from one revision with
children from another. The extraction helper validates the DSL and parent tenant,
uses explicit JSONB serialization, never commits/rolls back independently, and
propagates failure to the caller's rollback. Tenant-template cloning delegates to
the same create path. Shared seed cloning remains disabled.

This changes no database routing, schema, role grants, authorization policy or
HTTP request/response shape. Existing service failure conventions remain
`None`/`False`, mapped by the API to HTTP 400. One deliberate compatibility change:
update/activate/deactivate for missing or foreign-tenant IDs now returns failure
(HTTP 400) before attempting child writes, instead of an apparent successful
update followed by HTTP 404 on the subsequent read. Neither response exposes
another tenant's object. Empty updates succeed only for an existing own-tenant
policy. Existing delete semantics are outside this checkpoint.

Native tests exercise both current catalog policy storage and the consolidated
IAM fixture: successful create/update; failure before extraction, after rule
delete/insert, after parent update and before commit; invalid DSL; absent/foreign
parents; clone success/failure; API success/failure mapping; caller-controlled
helper rollback; and two concurrent writers with PostgreSQL blocking evidence.
Templates in the clone-specific test are supplied synthetic objects: that test
qualifies delegation and atomicity, not immutable publication or template lookup.
Existing native tenant-template tests remain the visibility regression gate.

Failure tests cover errors before a successful commit. A lost commit acknowledgement
can have an uncertain durable outcome and is not solved by rollback alone; this
checkpoint does not introduce idempotent create keys or claim exactly-once writes.
Parent locks protect cooperating PolicyService writers; they do not prove that
all alternate SQL writers follow the protocol. Full writer coverage, IAM
admission generations, cross-store case ordering and external issuer freshness
remain separate gates. No automatic activation follows local test success.
