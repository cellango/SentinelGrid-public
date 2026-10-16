"""
Database configuration for IAM Agent.
Includes pgvector extension support for vector storage.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.declarative import declarative_base as db_base
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Database URL (can be separate DB for IAM or use main DB)
DATABASE_URL = getattr(settings, 'IAM_DB_URL', settings.DB_URL) or 'postgresql://sg:sg@postgres:5432/SentinelGridIAM'

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = db_base()


def init_db():
    """Initialize database and enable pgvector extension."""
    try:
        with engine.connect() as conn:
            # Enable pgvector extension
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            logger.info("pgvector extension enabled")
    except Exception as e:
        logger.warning(f"Could not enable pgvector extension: {e}")
        logger.warning("pgvector may not be installed. Install with: apt-get install postgresql-16-pgvector")


def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize on import
init_db()

