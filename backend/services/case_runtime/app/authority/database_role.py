"""Read-only admission of the dedicated application role, not role provisioning.

Check each transaction against current PostgreSQL catalogs. Never cache success,
repair ACLs, switch roles or grant privileges. Trusted operators still control
concurrent DCL, system routines and the database; this is not a hostile-DBA fence.
"""

import json

from fastapi import HTTPException
from sqlalchemy import text

from app.authority.models import Base

INSERT_TABLES = frozenset(
    {
        "action_proposals",
        "approval_requests",
        "approval_decisions",
        "policy_decisions",
        "action_claims",
        "resource_fences",
        "action_attempts",
        "outbox_events",
    }
)
UPDATE_COLUMNS = {
    "cases": ["id"],
    "case_access_grants": ["id"],
    "resource_fences": ["generation"],
}

# This is server-owned policy. No names/privileges come from an HTTP/model input.
TABLE_POLICY = json.dumps(
    [
        {
            "schema_name": table.schema,
            "table_name": table.name,
            "insert_allowed": table.name in INSERT_TABLES,
            "update_columns": UPDATE_COLUMNS.get(table.name, []),
        }
        for table in Base.metadata.sorted_tables
    ]
    + [
        {
            "schema_name": "public",
            "table_name": "flyway_schema_history",
            "insert_allowed": False,
            "update_columns": [],
        }
    ]
)

ROLE_QUERY = text("""
WITH login AS (
  SELECT oid FROM pg_catalog.pg_roles WHERE rolname=session_user
), roles AS MATERIALIZED (
  SELECT r.oid,r.rolname,r.rolsuper,r.rolbypassrls,r.rolcreaterole,r.rolcreatedb,r.rolreplication
  FROM pg_catalog.pg_roles r, login u
  WHERE pg_catalog.pg_has_role(u.oid,r.oid,'MEMBER')
), policy AS (
  SELECT * FROM pg_catalog.jsonb_to_recordset(CAST(:policy AS jsonb))
    AS p(schema_name text, table_name text, insert_allowed boolean, update_columns text[])
), namespaces AS MATERIALIZED (
  SELECT * FROM pg_catalog.pg_namespace
  WHERE nspname NOT IN ('pg_catalog','information_schema')
    AND pg_catalog.left(nspname,3) <> 'pg_'
), relations AS MATERIALIZED (
  SELECT c.*,p.table_name AS allowed_name,p.insert_allowed,p.update_columns
  FROM pg_catalog.pg_class c JOIN namespaces n ON n.oid=c.relnamespace
  LEFT JOIN policy p ON p.schema_name=n.nspname AND p.table_name=c.relname
  WHERE c.relkind IN ('r','p','v','m','f','S')
), table_acl AS (
  SELECT c.*,a.grantee,a.privilege_type,a.is_grantable
  FROM relations c CROSS JOIN LATERAL pg_catalog.aclexplode(
    COALESCE(c.relacl,pg_catalog.acldefault(
      CASE WHEN c.relkind='S' THEN 's'::"char" ELSE 'r'::"char" END,c.relowner))) a
  WHERE a.grantee=0 OR a.grantee IN (SELECT oid FROM roles)
), column_acl AS (
  SELECT c.allowed_name,c.insert_allowed,c.update_columns,b.attname,a.*
  FROM relations c JOIN pg_catalog.pg_attribute b ON b.attrelid=c.oid
  CROSS JOIN LATERAL pg_catalog.aclexplode(b.attacl) a
  WHERE b.attnum>0 AND NOT b.attisdropped
    AND (a.grantee=0 OR a.grantee IN (SELECT oid FROM roles))
)
SELECT (
 current_user <> session_user
 OR NOT EXISTS(SELECT 1 FROM login)
 OR EXISTS(SELECT 1 FROM roles WHERE rolsuper OR rolbypassrls OR rolcreaterole
           OR rolcreatedb OR rolreplication OR pg_catalog.left(rolname,3)='pg_')
 OR EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members
           WHERE admin_option AND member IN (SELECT oid FROM roles))
 OR EXISTS(SELECT 1 FROM pg_catalog.pg_database d WHERE d.datdba IN (SELECT oid FROM roles))
 OR EXISTS(SELECT 1 FROM roles r WHERE pg_catalog.has_database_privilege(
           r.oid,pg_catalog.current_database(),'CREATE'))
 OR EXISTS(SELECT 1 FROM pg_catalog.pg_namespace n,roles r
           WHERE n.nspowner=r.oid OR pg_catalog.has_schema_privilege(r.oid,n.oid,'CREATE'))
 OR EXISTS(SELECT 1 FROM pg_catalog.pg_class WHERE relowner IN (SELECT oid FROM roles))
 OR EXISTS(SELECT 1 FROM pg_catalog.pg_proc WHERE proowner IN (SELECT oid FROM roles))
 OR EXISTS(SELECT 1 FROM pg_catalog.pg_type WHERE typowner IN (SELECT oid FROM roles))
 OR EXISTS(SELECT 1 FROM pg_catalog.pg_extension WHERE extowner IN (SELECT oid FROM roles))
 OR EXISTS(SELECT 1 FROM pg_catalog.pg_proc f JOIN namespaces n ON n.oid=f.pronamespace,roles r
           WHERE f.prosecdef AND pg_catalog.has_function_privilege(r.oid,f.oid,'EXECUTE'))
 OR EXISTS(SELECT 1 FROM table_acl
           WHERE is_grantable OR allowed_name IS NULL
              OR NOT (privilege_type='SELECT' OR (privilege_type='INSERT' AND insert_allowed)))
 OR EXISTS(SELECT 1 FROM column_acl
           WHERE is_grantable OR allowed_name IS NULL
              OR NOT (privilege_type='SELECT' OR (privilege_type='INSERT' AND insert_allowed)
                      OR (privilege_type='UPDATE' AND attname=ANY(update_columns))))
 OR EXISTS(SELECT 1 FROM policy p LEFT JOIN pg_catalog.pg_namespace n ON n.nspname=p.schema_name
           LEFT JOIN pg_catalog.pg_class c ON c.relnamespace=n.oid AND c.relname=p.table_name
           WHERE c.oid IS NULL OR c.relkind NOT IN ('r','p')
              OR (p.schema_name='case_runtime' AND (NOT c.relrowsecurity OR NOT c.relforcerowsecurity))
              OR NOT pg_catalog.has_schema_privilege(current_user,n.oid,'USAGE')
              OR NOT pg_catalog.has_table_privilege(current_user,c.oid,'SELECT')
              OR (p.insert_allowed AND NOT pg_catalog.has_table_privilege(current_user,c.oid,'INSERT'))
              OR EXISTS(SELECT 1 FROM pg_catalog.unnest(p.update_columns) u(column_name)
                        WHERE NOT pg_catalog.has_column_privilege(current_user,c.oid,u.column_name,'UPDATE')))
) AS unsafe
""")


def require_safe_database_role(session):
    # Schema-qualified catalog names and a transaction-local search path prevent
    # application/temporary names from shadowing the guard or subsequent queries.
    session.execute(text("SET LOCAL search_path = pg_catalog"))
    if session.execute(ROLE_QUERY, {"policy": TABLE_POLICY}).scalar_one() is not False:
        raise HTTPException(503, "Action database role is unsafe")
