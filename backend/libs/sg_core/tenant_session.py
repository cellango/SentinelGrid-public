"""PostgreSQL tenant context for each SQLAlchemy transaction, including savepoints."""
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import event, text


def tenant_uuid(value) -> UUID:
    if not isinstance(value, (str, UUID)):
        raise ValueError("A tenant UUID is required")
    return UUID(str(value))


def install_tenant_pool_reset(engine) -> None:
    """Reset session-level residue outside a transaction at every pool checkout."""
    if not event.contains(engine, "checkout", _reset_checkout):
        event.listen(engine, "checkout", _reset_checkout)


def _reset_checkout(dbapi_connection, _record, _proxy):
    previous = dbapi_connection.autocommit
    dbapi_connection.autocommit = True
    try:
        with dbapi_connection.cursor() as cursor:
            cursor.execute("RESET app.current_tenant_id")
            cursor.execute("RESET app.is_superadmin")
    finally:
        dbapi_connection.autocommit = previous


def bind_tenant(session, tenant_id) -> None:
    """Bind once, before use. A Session cannot be switched to a different tenant."""
    tenant = tenant_uuid(tenant_id)
    if session.in_transaction() or "sg_tenant_id" in session.info:
        raise ValueError("Bind a fresh session before beginning a transaction")
    session.info["sg_tenant_id"] = tenant

    def after_begin(_session, _transaction, connection):
        connection.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true), "
                 "set_config('app.is_superadmin', 'false', true)"),
            {"tenant_id": str(tenant)},
        )

    event.listen(session, "after_begin", after_begin)


@contextmanager
def tenant_session(session_factory, tenant_id):
    tenant = tenant_uuid(tenant_id)
    session = session_factory()
    try:
        bind_tenant(session, tenant)
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()
