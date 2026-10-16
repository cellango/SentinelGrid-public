# Tenant identifier guidance

- Programmatic calls must use tenant UUIDs to enforce hard isolation boundaries.
- Slugs are customer-friendly but should be translated to UUIDs at the gateway edge and only in rare, read-oriented cases; downstream services remain UUID-only.
- Reject any slug that does not map to the authenticated tenant/realm; never mix tenant scopes.

# Flyway migration naming and schema targeting

- Database schema changes must update both the SQLAlchemy model layer and a Flyway migration in the same change. Do not add tables, columns, indexes, constraints, or schema-affecting raw SQL without the matching model update.
- All database schema changes must be made through Flyway-managed migrations. Do not rely on runtime table creation, ad hoc SQL, service startup migration runners, or legacy/non-Flyway migration folders for new schema changes.
- Use `V###__<schema>_<short_action>.sql` (Flyway version, zero-padded 3 digits, double underscore, snake_case description). Example: `V008__security_ops_add_incident_tags.sql`.
- Versions increment globally across all schemas (Flyway orders by version, not description); do not reuse or reorder.
- Keep one migration per logical change and per schema; avoid mixing schemas in the same file.
- Set the search path at the top for the target schema (e.g., `SET search_path = security_ops, public;`) and avoid cross-schema dependencies; if unavoidable, add them in a follow-up migration and document clearly.
