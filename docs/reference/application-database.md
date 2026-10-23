# Shared application database qualification

Reviewed October 22, 2026. **Isolated source qualification; no deployment or
existing-database adoption.** The [shared profile](../../publication/application-database-profile.json)
selects all eighteen unchanged consolidated migrations, V001–V018. The separate
[IAM profile](../../publication/iam-database-profile.json) remains a different
physical database/history; its local V0–V3 files are excluded here.

## Reproduce the native gate

Provide reviewed native PostgreSQL binaries, its required extension libraries,
Flyway and the preview Python environment. This command does not install tools:

```sh
PYTHONDONTWRITEBYTECODE=1 \
SG_TEST_PG_BINDIR=/path/to/reviewed/postgresql/bin \
SG_TEST_FLYWAY=/path/to/reviewed/flyway \
make preview-application-db PYTHON=.venv/bin/python
```

The [gate](../../scripts/qualify_application_database.py) accepts no connection
arguments, existing data directory or database URL. It creates a new private
temporary cluster with a loopback listener, SCRAM host authentication and generated
credentials. Local trust authentication is confined to its private socket directory.
It stops and removes the lab on exit. Missing tools or extensions fail this separate
gate; they are never skipped or replaced with SQLite or startup DDL.

The bundle helper checks SHA-256 before copying migrations. Its configuration uses
one `public.flyway_schema_history`, schema creation disabled, validation enabled,
no automatic baseline, clean disabled and an empty `ignoreMigrationPatterns`.
Clearing that value disables Flyway's default future-version ignore, so a missing
highest applied version also fails validation. See the
[Flyway setting](https://documentation.red-gate.com/fd/flyway-ignore-migration-patterns-setting-277579002.html).
The JSON result must explicitly report success; a zero process exit alone cannot
establish validation success.

## Observed scope

The owned macOS arm64 lab used PostgreSQL **17.5**, Flyway **11.20.2**, `pgcrypto`
**1.3**, `uuid-ossp` **1.1**, pgvector **0.8.1** and the installed OpenSSL **3.6.2**.
These are test tool versions, not a production version decision. PostgreSQL was
built with OpenSSL and UUID support; the pgvector source was pinned to official
tag commit `778dacf20c07caf904557a88705142631818d8cb`.
[PostgreSQL](https://www.postgresql.org/docs/17/pgcrypto.html) documents pgcrypto's
OpenSSL build requirement, and [pgvector](https://github.com/pgvector/pgvector/tree/v0.8.1)
documents its separate build and extension installation.

The gate checks:

- A fresh full V001–V018 migration, eighteen successful non-NULL checksummed
  history entries, validation, and a second migration executing zero files.
- An independently installed V013 database with a synthetic tenant row upgraded
  through V018; the complete row remains byte-identical.
- Changed SQL and a missing highest applied version rejected without repair;
  restoring only the disposable bundle restores valid history.
- An unversioned populated database refused without baseline/history creation or
  loss of its synthetic witness.
- Immediate PostgreSQL crash/restart preserving catalogs, histories and the
  tenant witness, followed by successful validation.
- A native logical dump and restore into another new database, preserving the
  catalog table/extension inventory, history entries and tenant witness, followed
  by successful validation.

This general gate intentionally uses a privileged lab migrator to distinguish SQL
execution from deployment privilege design. Its catalog checks are table names,
extension versions and applied history, not a complete constraint/policy diff or
proof of every domain's data and RLS behavior. The populated witness covers one
synthetic tenant row, not all historic data shapes, production backups or PITR.

## Action and MCP records in the full shared catalog

The existing native action/MCP tests can also select the complete shared profile:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend/libs:backend/services/case_runtime \
SG_ACTION_DB_PROFILE=shared_application \
SG_TEST_PG_BINDIR=/path/to/reviewed/postgresql/bin \
SG_TEST_FLYWAY=/path/to/reviewed/flyway \
make preview-action-db PYTHON=.venv/bin/python
```

The fixture bootstraps extensions under the dump's `sg` owner in the new lab,
then removes that role's temporary superuser privilege **before** Flyway connects.
It grants `sg` USAGE/CREATE on `public` and grants owner membership only to the
non-superuser migration role with BYPASSRLS. Preinstalling extensions under an unrelated
administrator fails V001's extension comments; omitting the owner's schema CREATE
privilege fails its ownership changes. Those are explicit provisioning prerequisites,
not reasons to change baseline SQL or keep a runtime role privileged.
A non-BYPASSRLS migrator then fails V008 FK validation over a FORCE RLS table
under V001's `row_security=off`. The full-profile test therefore grants BYPASSRLS
only to its migration role and revokes it immediately after migration, before
application tests; this is an explicit privileged lab boundary, not
least-privilege production provisioning. The owner role remains non-superuser
and non-BYPASSRLS after extension bootstrap.

The action application role has no owner membership, superuser or BYPASSRLS and
keeps its existing narrow grants. The 27 native checks exercise action authority,
tenant RLS, immutable records, approvals, atomic outbox failure, concurrency,
ambiguous retries and crash recovery, including actual MCP SDK calls through the
receiving ASGI API. The IAM HTTP link is synthetic and the API transport is in
process. The default fixture remains V018-only; unknown profile names fail.

These checks qualify only this local profile. Production extension custody,
roles, TLS, capacity, backup/PITR, populated legacy reconciliation, every domain's
physical contract/RLS, hosted CI, Temporal infrastructure and live issuer/provider
effects remain open. The authority remains disabled by default. See the
[compatibility plan](../architecture/database-compatibility.md) and
[action boundary](action-authority.md).

The [action role-admission gate](action-database-role.md) adds actual catalog/ACL
denial and recovery checks to this full profile; it does not provision deployment
privileges or certify every PostgreSQL security surface.
