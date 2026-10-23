# Database source changes

The authoritative contributor rules are in [AGENTS.md](../../AGENTS.md). A schema
change must pair SQLAlchemy model changes with a Flyway-managed migration in the
same review. Do not use runtime table creation, startup scripts, or ad hoc SQL as
a replacement migration mechanism.

The [database compatibility plan](../architecture/database-compatibility.md) is the
canonical target for physical case storage, existing-history reconciliation, tenant
roles/session handling and install/upgrade/restore qualification. It is planning
only; its proposed tables and migration slices are not implemented.

## Source locations

- [Shared ORM](../../backend/libs/sg_core/models.py)
- [Consolidated Flyway migrations](../../backend/migrations_consolidated/)
- [Flyway configuration references](../../backend/migrations/)
- [Offline V013 model/DDL contract](../../backend/tests/test_infrastructure_change_schema.py)

Use `V###__<schema>_<short_action>.sql`, with a globally unique version across all
schemas and an explicit target schema/search path. Keep each logical migration
within one schema where possible. Preserve already numbered migration history;
do not rewrite a baseline because an old setup note suggests refreshing it.
Older migration folders and application-local migration helpers are legacy source
references, not the path for new schema changes.

V013 currently describes the public infrastructure-change-request table. Its
matching model, JSONB fields, server defaults, and four indexes are checked offline.
That test does not execute SQL or certify database connectivity, historical upgrade
paths, fresh installs, restores, or tenant isolation. A future runnable beta needs
separate disposable-database migration/upgrade/restore verification before any
operation on shared data. The source preview requires no database.
