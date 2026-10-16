#!/usr/bin/env python3
"""
Data Migration Script for Knowledge Base
This script loads cybersecurity knowledge base data with embeddings.

Run after Flyway migration V1.1 has been applied.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add parent directories to path
script_dir = Path(__file__).parent
service_root = script_dir.parent.parent  # db -> model_gateway
sys.path.insert(0, str(service_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.services.knowledge_base_loader import KnowledgeBaseLoader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_migration_status(db_session, migration_version: str) -> dict:
    """Check if data migration should run."""
    result = db_session.execute(
        text("SELECT status, records_loaded FROM data_migration_history WHERE migration_version = :version"),
        {"version": migration_version}
    ).fetchone()
    
    if not result:
        logger.warning(f"Migration marker {migration_version} not found. Creating it...")
        db_session.execute(
            text("""
                INSERT INTO data_migration_history (migration_version, migration_name, status)
                VALUES (:version, 'Load initial cybersecurity knowledge base data', 'pending')
                ON CONFLICT (migration_version) DO NOTHING
            """),
            {"version": migration_version}
        )
        db_session.commit()
        return {"status": "pending", "records_loaded": 0}
    
    return {"status": result[0], "records_loaded": result[1] or 0}


def mark_migration_started(db_session, migration_version: str):
    """Mark migration as started."""
    db_session.execute(
        text("""
            UPDATE data_migration_history
            SET status = 'running', started_at = NOW(), updated_at = NOW()
            WHERE migration_version = :version
        """),
        {"version": migration_version}
    )
    db_session.commit()


def mark_migration_completed(db_session, migration_version: str, records_loaded: int):
    """Mark migration as completed."""
    db_session.execute(
        text("""
            UPDATE data_migration_history
            SET status = 'completed',
                completed_at = NOW(),
                records_loaded = :records,
                updated_at = NOW()
            WHERE migration_version = :version
        """),
        {"version": migration_version, "records": records_loaded}
    )
    db_session.commit()


def mark_migration_failed(db_session, migration_version: str, error: str):
    """Mark migration as failed."""
    db_session.execute(
        text("""
            UPDATE data_migration_history
            SET status = 'failed',
                completed_at = NOW(),
                error_message = :error,
                updated_at = NOW()
            WHERE migration_version = :version
        """),
        {"version": migration_version, "error": str(error)[:500]}
    )
    db_session.commit()


def main():
    migration_version = "V1.1"
    
    # Database connection
    db_url = os.getenv(
        "MODEL_GATEWAY_DATABASE_URL",
        os.getenv("DATABASE_URL", "postgresql://sg:sg@localhost:5432/sg")
    )
    
    logger.info(f"Connecting to database: {db_url}")
    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    try:
        # Check migration status
        status = check_migration_status(db, migration_version)
        
        if status["status"] == "completed":
            logger.info(f"Migration {migration_version} already completed ({status['records_loaded']} records loaded). Skipping.")
            return 0
        
        if status["status"] == "running":
            logger.warning(f"Migration {migration_version} is marked as running. It may have failed previously.")
            logger.info("Marking as pending to retry...")
            db.execute(
                text("UPDATE data_migration_history SET status = 'pending' WHERE migration_version = :version"),
                {"version": migration_version}
            )
            db.commit()
        
        # Mark as started
        mark_migration_started(db, migration_version)
        logger.info(f"Starting data migration {migration_version}...")
        
        # Load knowledge bases
        loader = KnowledgeBaseLoader(db_session=db)
        load_result = loader.load_all()
        kb_results = load_result.get("results", {})
        summary = load_result.get("summary", {})
        
        # Count total loaded
        total_loaded = summary.get("total_loaded", 0)
        total_errors = summary.get("total_errors", 0)
        
        if total_errors > 0:
            error_msg = f"Migration completed with {total_errors} errors. {total_loaded} records loaded."
            logger.error(error_msg)
            mark_migration_failed(db, migration_version, error_msg)
            return 1
        
        # Mark as completed
        mark_migration_completed(db, migration_version, total_loaded)
        
        logger.info(f"✅ Data migration {migration_version} completed successfully!")
        logger.info(f"   Loaded {total_loaded} knowledge base entries")
        
        for framework, result in kb_results.items():
            logger.info(f"   - {result.get('framework', framework)}: {result.get('loaded', 0)} items")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error in data migration {migration_version}: {e}", exc_info=True)
        mark_migration_failed(db, migration_version, str(e))
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
