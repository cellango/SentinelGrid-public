# Action database role admission

Status: implemented and qualified in disposable native PostgreSQL17.5 full-catalog
tests. This guards the current proposal/approval/internal-reservation role. It does
not provision production roles, admit provider execution or replace case permissions.

## Enforced boundary

Every [action-authority transaction](../../backend/services/case_runtime/app/authority/store.py)
checks the current database catalogs through the
[role guard](../../backend/services/case_runtime/app/authority/database_role.py).
There is no successful-startup cache or automatic GRANT/REVOKE/ownership repair.
Unsafe roles return HTTP503 before tenant business reads/writes. Missing tables,
catalog access or required privileges also stop admission. MCP receives a bounded
unavailable error from the same receiving API.

The dedicated connection must use its actual login role, without `SET ROLE`.
Direct or indirect role memberships are inspected conservatively, including
memberships whose privileges are not currently inherited. A harmless narrow group
is allowed; owner, predefined `pg_*`, superuser, BYPASSRLS, CREATEROLE, CREATEDB,
REPLICATION and role ADMIN-option paths are rejected. The guard rejects ownership
of databases, schemas, relations, routines, types or extensions and effective
database/schema CREATE privileges. PostgreSQL's
[membership rules](https://www.postgresql.org/docs/17/role-membership.html) distinguish
membership, inheritance and the ability to switch roles; checking only current
superuser/BYPASSRLS flags cannot establish this boundary.

The server-owned table policy permits:

- SELECT on the twelve `case_runtime` tables and `public.flyway_schema_history`.
- INSERT on proposal, approval request/decision, policy decision, claim, resource
  fence, attempt and outbox tables.
- UPDATE(id) on cases/access grants for row locking, and UPDATE(generation) on
  resource fences. No other UPDATE columns are admitted.

Table and column ACLs are evaluated for the login, its role-membership closure and
PUBLIC, including grant options. Other non-system relation access is rejected.
This blocks case/grant creation, receipt/verification insertion, history mutation,
table-wide updates, DELETE/TRUNCATE/TRIGGER/REFERENCES and delegated grant options
through the application's database account. Column-only grants cannot hide behind
an apparently safe table ACL. Catalog
[privilege and ACL functions](https://www.postgresql.org/docs/17/functions-info.html#FUNCTIONS-INFO-ACCESS-TABLE)
provide the underlying information; runtime requests never supply policy names.

Required tables must retain enabled and forced RLS. Executable SECURITY DEFINER
routines in non-system schemas are rejected. The transaction sets its search path
to `pg_catalog` and uses schema-qualified catalog/business objects; the setting
ends with the transaction. The existing verified identity, current tenant/case
grants, separation of duties and immutable proposal/approval checks still apply.

## Native verification

With the [reviewed full shared tools/extensions](application-database.md), run:

```sh
PYTHONDONTWRITEBYTECODE=1 \
SG_TEST_PG_BINDIR=/path/to/reviewed/postgresql/bin \
SG_TEST_FLYWAY=/path/to/reviewed/flyway \
make preview-action-role-db PYTHON=.venv/bin/python
```

This separate gate requires the complete unchanged V001–V018 profile and fails on
missing tools. It creates only new disposable clusters. Test provisioning uses the
documented migration-owner extension custody and temporary migration BYPASSRLS,
revoked before application checks. The application remains nonowner/NOBYPASSRLS.

The 51 added checks use actual catalog/DCL changes, not mocked privilege answers.
They prove every record API denies an unsafe role without changing action-row
fingerprints; migration history is retained. Restoring the reviewed privileges allows
the same store/pool to admit valid work. The matrix covers direct/transitive and
noninherited owner grants, role administration, broad and column-only writes,
PUBLIC privileges, grant options, other-domain access, ownership, SECURITY DEFINER,
missing required permissions, RLS flags, switched sessions and search-path scope.
The actual MCP SDK also observes receiver denial without creating a proposal.
The existing native action/MCP tests continue to cover valid proposal, approval,
reservation, retries, atomic failures, tenant isolation and crash recovery.

## Qualification limits

This is a runtime check of the declared account/object/ACL boundary, not a lock on
concurrent administrator DCL or protection from a hostile database owner. Operators
must coordinate privilege changes with running transactions. It does not verify
every policy expression, trigger/function body, system-routine grant, extension,
language, FDW, large object or default-privilege configuration. Default TEMP access
is not revoked or certified; this path creates no temporary objects and pins its
query search path. A complete production privilege audit is still required.

The role guard cannot establish target ownership, authorize a provider effect,
qualify every domain's data/RLS or adopt an existing database. Production custody,
TLS, capacity, backup/PITR, concurrency with operational changes and rollout remain
separate gates. The service remains disabled by default and readiness remains503.
See the [action contract](action-authority.md) and
[database compatibility plan](../architecture/database-compatibility.md).
