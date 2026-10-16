"""Explicit shared catalog and separate IAM access-grant session factories.

Schema changes are Flyway-only; importing this module never executes DDL or connects.
"""
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker
from sg_core.db import engine as shared_engine
from sg_core.tenant_session import install_tenant_pool_reset
from app.core.config import settings

def _catalog_engine():
    target = make_url(settings.DB_URL) if settings.DB_URL else shared_engine.url
    if target.get_backend_name() != "postgresql":
        raise ValueError("DB_URL must select PostgreSQL")
    if target == shared_engine.url:
        return shared_engine
    result = create_engine(target, pool_pre_ping=True, pool_size=5, max_overflow=10)
    install_tenant_pool_reset(result)
    return result


engine = _catalog_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()
DATABASE_URL = str(engine.url)


def _iam_engine():
    if not settings.IAM_DB_URL:
        return None
    target = make_url(settings.IAM_DB_URL)
    source = engine.url
    if target.get_backend_name() != "postgresql":
        raise ValueError("IAM_DB_URL must select PostgreSQL")
    def location(url):
        return (url.host, url.port or 5432, url.database, url.query.get("host"))
    if location(target) == location(source):
        raise ValueError("IAM_DB_URL must select a database separate from the shared catalog")
    result = create_engine(target, pool_pre_ping=True, pool_size=5, max_overflow=10)
    install_tenant_pool_reset(result)
    return result


iam_engine = _iam_engine()
_IAMSessionLocal = sessionmaker(bind=iam_engine, autocommit=False, autoflush=False) if iam_engine is not None else None


class IAMDatabaseNotConfigured(RuntimeError):
    pass


def IAMSessionLocal():
    if _IAMSessionLocal is None:
        raise IAMDatabaseNotConfigured("IAM_DB_URL is required for the separate access-grant store")
    return _IAMSessionLocal()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
