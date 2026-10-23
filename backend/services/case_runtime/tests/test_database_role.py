"""Actual full-catalog role/ACL denials and recovery; no mocked catalog results.

All DCL and helper DDL are disposable test provisioning. Application code only
reads catalogs; it never grants privileges or changes installed schema objects.
"""

from contextlib import contextmanager
import hashlib
import json
import os
import pytest
from fastapi import HTTPException
from psycopg2 import sql
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.authority.database_role import require_safe_database_role
from app.authority.models import Base
from test_action_database import lab as lab, flow as flow  # noqa:F401
from test_mcp_case_records_database import connected as connected  # noqa:F401
from test_action_boundary import proposal


@pytest.fixture(autouse=True)
def full_profile_required():
    assert os.environ.get("SG_ACTION_DB_PROFILE") == "shared_application", (
        "This separate role gate requires the full shared profile; no reduced substitute"
    )


def counts(lab):
    c = lab["connect"]()
    try:
        with c, c.cursor() as q:
            result = {}
            for table in Base.metadata.sorted_tables:
                q.execute(
                    sql.SQL(
                        "SELECT pg_catalog.row_to_json(t)::text FROM {}.{} t ORDER BY pg_catalog.row_to_json(t)::text"
                    ).format(sql.Identifier(table.schema), sql.Identifier(table.name))
                )
                result[table.name] = hashlib.sha256(
                    json.dumps(q.fetchall()).encode()
                ).hexdigest()
            q.execute(
                "SELECT pg_catalog.row_to_json(t)::text FROM public.flyway_schema_history t ORDER BY installed_rank"
            )
            result["migration_history"] = hashlib.sha256(
                json.dumps(q.fetchall()).encode()
            ).hexdigest()
            return result
    finally:
        c.close()


@contextmanager
def provisioning(lab, setup, cleanup):
    c = lab["connect"]()
    try:
        with c, c.cursor() as q:
            for statement in setup:
                q.execute(statement)
        try:
            yield
        finally:
            with c, c.cursor() as q:
                for statement in cleanup:
                    q.execute(statement)
    finally:
        c.close()


def grant_case(name, grant, undo=None):
    return pytest.param(
        [grant],
        [undo or grant.replace("GRANT ", "REVOKE ", 1).replace(" TO ", " FROM ", 1)],
        id=name,
    )


ROLE_CASES = [
    pytest.param(
        [f"ALTER ROLE sg_action_app {flag}"],
        [f"ALTER ROLE sg_action_app NO{flag}"],
        id=flag.lower(),
    )
    for flag in ["SUPERUSER", "BYPASSRLS", "CREATEROLE", "CREATEDB", "REPLICATION"]
] + [
    grant_case("predefined-read-all", "GRANT pg_read_all_data TO sg_action_app"),
    grant_case("predefined-monitor", "GRANT pg_monitor TO sg_action_app"),
    grant_case("owner-membership", "GRANT sg_migrator TO sg_action_app"),
    grant_case(
        "noninherited-owner-membership",
        "GRANT sg_migrator TO sg_action_app WITH INHERIT FALSE",
        "REVOKE sg_migrator FROM sg_action_app",
    ),
    grant_case("schema-create", "GRANT CREATE ON SCHEMA case_runtime TO sg_action_app"),
    grant_case("public-schema-create", "GRANT CREATE ON SCHEMA public TO PUBLIC"),
    grant_case(
        "database-create", "GRANT CREATE ON DATABASE sg_case_lab TO sg_action_app"
    ),
    grant_case("case-insert", "GRANT INSERT ON case_runtime.cases TO sg_action_app"),
    grant_case(
        "grant-insert",
        "GRANT INSERT ON case_runtime.case_access_grants TO sg_action_app",
    ),
    grant_case(
        "case-insert-column", "GRANT INSERT(id) ON case_runtime.cases TO sg_action_app"
    ),
    grant_case(
        "receipt-forgery",
        "GRANT INSERT ON case_runtime.action_receipts TO sg_action_app",
    ),
    grant_case(
        "verification-forgery",
        "GRANT INSERT ON case_runtime.action_verifications TO sg_action_app",
    ),
    grant_case(
        "case-wide-update",
        "GRANT UPDATE ON case_runtime.cases TO sg_action_app",
        "REVOKE UPDATE ON case_runtime.cases FROM sg_action_app; GRANT UPDATE(id) ON case_runtime.cases TO sg_action_app",
    ),
    grant_case(
        "proposal-wide-update",
        "GRANT UPDATE ON case_runtime.action_proposals TO sg_action_app",
    ),
    grant_case(
        "decision-wide-update",
        "GRANT UPDATE ON case_runtime.approval_decisions TO sg_action_app",
    ),
    grant_case(
        "case-status-update",
        "GRANT UPDATE(status) ON case_runtime.cases TO sg_action_app",
    ),
    grant_case(
        "grant-permission-update",
        "GRANT UPDATE(permission) ON case_runtime.case_access_grants TO sg_action_app",
    ),
    grant_case(
        "fence-target-update",
        "GRANT UPDATE(resource_key) ON case_runtime.resource_fences TO sg_action_app",
    ),
    grant_case(
        "delete", "GRANT DELETE ON case_runtime.action_proposals TO sg_action_app"
    ),
    grant_case(
        "truncate", "GRANT TRUNCATE ON case_runtime.case_access_grants TO sg_action_app"
    ),
    grant_case("trigger", "GRANT TRIGGER ON case_runtime.cases TO sg_action_app"),
    grant_case("references", "GRANT REFERENCES ON case_runtime.cases TO sg_action_app"),
    grant_case(
        "history-update",
        "GRANT UPDATE(checksum) ON public.flyway_schema_history TO sg_action_app",
    ),
    grant_case(
        "history-insert",
        "GRANT INSERT ON public.flyway_schema_history TO sg_action_app",
    ),
    grant_case(
        "history-truncate",
        "GRANT TRUNCATE ON public.flyway_schema_history TO sg_action_app",
    ),
    grant_case(
        "select-grant-option",
        "GRANT SELECT ON case_runtime.cases TO sg_action_app WITH GRANT OPTION",
        "REVOKE GRANT OPTION FOR SELECT ON case_runtime.cases FROM sg_action_app",
    ),
    grant_case(
        "column-grant-option",
        "GRANT UPDATE(id) ON case_runtime.cases TO sg_action_app WITH GRANT OPTION",
        "REVOKE GRANT OPTION FOR UPDATE(id) ON case_runtime.cases FROM sg_action_app",
    ),
    grant_case(
        "public-grant-forgery",
        "GRANT INSERT ON case_runtime.case_access_grants TO PUBLIC",
    ),
    grant_case("other-domain-read", "GRANT SELECT ON public.tenants TO sg_action_app"),
    grant_case("other-domain-write", "GRANT UPDATE ON public.tenants TO sg_action_app"),
    pytest.param(
        ["ALTER TABLE case_runtime.cases OWNER TO sg_action_app"],
        [
            "ALTER TABLE case_runtime.cases OWNER TO sg_migrator",
            "GRANT SELECT ON case_runtime.cases TO sg_action_app",
            "GRANT UPDATE(id) ON case_runtime.cases TO sg_action_app",
        ],
        id="table-owner",
    ),
    pytest.param(
        ["ALTER SCHEMA case_runtime OWNER TO sg_action_app"],
        [
            "ALTER SCHEMA case_runtime OWNER TO sg_migrator",
            "GRANT USAGE ON SCHEMA case_runtime TO sg_action_app",
        ],
        id="schema-owner",
    ),
    pytest.param(
        ["ALTER TABLE public.flyway_schema_history OWNER TO sg_action_app"],
        [
            "ALTER TABLE public.flyway_schema_history OWNER TO sg_migrator",
            "GRANT SELECT ON public.flyway_schema_history TO sg_action_app",
        ],
        id="history-owner",
    ),
    pytest.param(
        ["ALTER FUNCTION case_runtime.current_tenant_id() OWNER TO sg_action_app"],
        ["ALTER FUNCTION case_runtime.current_tenant_id() OWNER TO sg_migrator"],
        id="function-owner",
    ),
    pytest.param(
        ["ALTER FUNCTION case_runtime.current_tenant_id() SECURITY DEFINER"],
        ["ALTER FUNCTION case_runtime.current_tenant_id() SECURITY INVOKER"],
        id="executable-security-definer",
    ),
    pytest.param(
        ["ALTER TABLE case_runtime.cases DISABLE ROW LEVEL SECURITY"],
        ["ALTER TABLE case_runtime.cases ENABLE ROW LEVEL SECURITY"],
        id="RLS-disabled",
    ),
    pytest.param(
        ["ALTER TABLE case_runtime.cases NO FORCE ROW LEVEL SECURITY"],
        ["ALTER TABLE case_runtime.cases FORCE ROW LEVEL SECURITY"],
        id="RLS-not-forced",
    ),
    pytest.param(
        ["REVOKE SELECT ON case_runtime.cases FROM sg_action_app"],
        ["GRANT SELECT ON case_runtime.cases TO sg_action_app"],
        id="required-read-missing",
    ),
    pytest.param(
        ["REVOKE UPDATE(id) ON case_runtime.cases FROM sg_action_app"],
        ["GRANT UPDATE(id) ON case_runtime.cases TO sg_action_app"],
        id="required-lock-privilege-missing",
    ),
]


@pytest.mark.parametrize("setup,cleanup", ROLE_CASES)
def test_privilege_expansion_denies_all_record_entrypoints_without_writes(
    flow, setup, cleanup
):
    p = flow["submit"]().json()
    assert p["status"] == "pending_approval"
    before = counts(flow["lab"])
    with provisioning(flow["lab"], setup, cleanup):
        results = [
            flow["submit"](),
            flow["decide"](p),
            flow["api"].client.get(
                flow["path"] + "/" + p["proposal_id"],
                headers=flow["api"].headers(flow["users"][0]),
            ),
        ]
        for response in results:
            assert response.status_code == 503, response.text
            assert response.json() == {"detail": "Action database role is unsafe"}
        assert counts(flow["lab"]) == before
    # No successful startup cache: catalog changes are checked on this same store/pool.
    assert flow["submit"]().status_code == 201


@pytest.mark.parametrize(
    "mode", ["transitive-owner", "admin-option", "noninherited-forbidden-grant"]
)
def test_indirect_or_latent_role_privileges_are_not_a_bypass(flow, mode):
    setup = ["CREATE ROLE sg_role_bridge NOLOGIN NOSUPERUSER NOBYPASSRLS"]
    cleanup = ["REVOKE sg_role_bridge FROM sg_action_app"]
    if mode == "transitive-owner":
        setup += [
            "GRANT sg_migrator TO sg_role_bridge",
            "GRANT sg_role_bridge TO sg_action_app",
        ]
        cleanup += ["REVOKE sg_migrator FROM sg_role_bridge"]
    elif mode == "admin-option":
        setup += ["GRANT sg_role_bridge TO sg_action_app WITH ADMIN OPTION"]
    else:
        setup += [
            "GRANT INSERT ON case_runtime.case_access_grants TO sg_role_bridge",
            "GRANT sg_role_bridge TO sg_action_app WITH INHERIT FALSE",
        ]
        cleanup += [
            "REVOKE INSERT ON case_runtime.case_access_grants FROM sg_role_bridge"
        ]
    cleanup += ["DROP ROLE sg_role_bridge"]
    before = counts(flow["lab"])
    with provisioning(flow["lab"], setup, cleanup):
        assert flow["submit"]().status_code == 503
        assert counts(flow["lab"]) == before
    assert flow["submit"]().status_code == 201


def test_narrow_group_membership_is_accepted(flow):
    with provisioning(
        flow["lab"],
        [
            "CREATE ROLE sg_role_reader NOLOGIN NOSUPERUSER NOBYPASSRLS",
            "GRANT SELECT ON case_runtime.cases TO sg_role_reader",
            "GRANT sg_role_reader TO sg_action_app WITH SET FALSE",
        ],
        [
            "REVOKE sg_role_reader FROM sg_action_app",
            "REVOKE SELECT ON case_runtime.cases FROM sg_role_reader",
            "DROP ROLE sg_role_reader",
        ],
    ):
        assert flow["submit"]().status_code == 201


def test_switched_role_and_privileged_session_user_are_rejected(lab):
    with Session(lab["owner"]) as s, s.begin():
        s.execute(text("SET LOCAL ROLE sg_action_app"))
        with pytest.raises(HTTPException) as error:
            require_safe_database_role(s)
        assert error.value.status_code == 503


def test_search_path_is_local_and_catalog_only(lab):
    with lab["engine"].connect() as c:
        before = c.execute(text("SHOW search_path")).scalar_one()
        c.rollback()
        with c.begin():
            c.execute(text("SET LOCAL search_path=public,pg_catalog"))
            require_safe_database_role(c)
            assert c.execute(text("SHOW search_path")).scalar_one() == "pg_catalog"
        assert c.execute(text("SHOW search_path")).scalar_one() == before


def test_mcp_observes_receiver_privilege_denial_without_a_record(connected):
    state = connected
    before = counts(state.flow["lab"])
    with provisioning(
        state.flow["lab"],
        ["GRANT INSERT ON case_runtime.case_access_grants TO sg_action_app"],
        ["REVOKE INSERT ON case_runtime.case_access_grants FROM sg_action_app"],
    ):
        result = state.call(
            "case_propose_action",
            {
                "case_id": state.flow["case_id"],
                "request_key": "11111111-1111-4111-8111-111111111111",
                "proposal": proposal(),
            },
        )
        assert result.json()["result"]["isError"] is True
        assert counts(state.flow["lab"]) == before
