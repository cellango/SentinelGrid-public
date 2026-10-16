"""Database configuration for Model Gateway."""

from typing import Generator
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Database URL from resolved service settings
DATABASE_URL = settings.MODEL_GATEWAY_DATABASE_URL

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


@event.listens_for(engine, "connect")
def _reset_tenant_on_connect(dbapi_connection, connection_record):
    """Clear tenant RLS state when a new physical connection is created."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SET app.current_tenant_id = ''")
        cursor.execute("SET app.is_superadmin = 'false'")
    finally:
        cursor.close()


def get_db() -> Session:
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_tenant(
    x_tenant_id: str = Header(..., alias="X-Tenant-ID", description="Tenant UUID"),
) -> UUID:
    """Extract and validate the tenant UUID from internal service headers."""
    try:
        return UUID(str(x_tenant_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Tenant-ID header",
        ) from exc


def get_tenant_db(tenant_id: UUID | str) -> Generator[Session, None, None]:
    """Yield a DB session with tenant-scoped RLS context applied."""
    resolved_tenant = str(tenant_id)
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.current_tenant_id = :tid"), {"tid": resolved_tenant})
        db.execute(text("SET LOCAL app.is_superadmin = 'false'"))
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        try:
            db.execute(text("RESET app.current_tenant_id"))
            db.execute(text("RESET app.is_superadmin"))
        except Exception:
            pass
        db.close()


def get_superadmin_db() -> Generator[Session, None, None]:
    """Yield a DB session with superadmin RLS bypass for shared platform content."""
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.is_superadmin = 'true'"))
        db.execute(text("SET LOCAL app.current_tenant_id = ''"))
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        try:
            db.execute(text("RESET app.is_superadmin"))
            db.execute(text("RESET app.current_tenant_id"))
        except Exception:
            pass
        db.close()


def get_tenant_session(
    tenant_id: UUID = Depends(get_current_tenant),
) -> Generator[Session, None, None]:
    """FastAPI dependency that returns a tenant-scoped DB session."""
    yield from get_tenant_db(tenant_id)


def init_db():
    """Initialize database tables."""
    from app.models.database import (
        TenantTrainingData,
        TenantModelAdapter,
        AdapterVersionHistory,
        AdapterTrainingJob,
        TrainingDataSnapshot
    )
    from app.models.knowledge_base import CybersecurityKnowledgeBase
    from app.models.git_repos import GitRepository, GitIngestionJob
    
    # Enable pgvector extension
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        logger.info("pgvector extension enabled")
    except Exception as e:
        logger.warning(f"Could not enable pgvector extension: {e}")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")


def set_tenant_context(db: Session, tenant_id: str):
    """Set tenant context for RLS policies."""
    # This sets the session variable that RLS policies use
    # Note: In production, validate tenant_id is a valid UUID
    try:
        db.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
        # Use SET LOCAL so it only affects this transaction
    except Exception as e:
        logger.warning(f"Error setting tenant context: {e}. RLS may not work correctly.")
