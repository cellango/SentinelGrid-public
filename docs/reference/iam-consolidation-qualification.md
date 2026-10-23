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

Consolidation permits a local transaction; it does not rewrite existing writers
to use one. In particular, `PolicyService.create_policy` commits its policy before
extracting child rules. That is an integration obligation, not fixed here. All
portal, seed/template, bulk, governance, role-sync and principal/credential writers
must participate before activation. Audit and principal/governance relationship
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
