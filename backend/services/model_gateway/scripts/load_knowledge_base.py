#!/usr/bin/env python3
"""
Load cybersecurity knowledge bases into vector database.

Usage:
    python scripts/load_knowledge_base.py --all
    python scripts/load_knowledge_base.py --nist
    python scripts/load_knowledge_base.py --mitre --owasp
    python scripts/load_knowledge_base.py --nist-source /path/to/nist.json
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import init_db
from app.services.knowledge_base_loader import KnowledgeBaseLoader

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Load cybersecurity knowledge bases into vector database")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Load all knowledge bases"
    )
    parser.add_argument(
        "--nist",
        action="store_true",
        help="Load NIST 800-53 controls"
    )
    parser.add_argument(
        "--mitre",
        action="store_true",
        help="Load MITRE ATT&CK techniques"
    )
    parser.add_argument(
        "--owasp",
        action="store_true",
        help="Load OWASP content"
    )
    parser.add_argument(
        "--playbooks",
        action="store_true",
        help="Load SOC playbooks"
    )
    parser.add_argument(
        "--nist-source",
        default=None,
        help="Path to NIST controls JSON file"
    )
    parser.add_argument(
        "--mitre-source",
        default=None,
        help="Path to MITRE techniques JSON file"
    )
    parser.add_argument(
        "--owasp-source",
        default=None,
        help="Path to OWASP content JSON file"
    )
    parser.add_argument(
        "--playbooks-source",
        default=None,
        help="Path to playbooks JSON file"
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("MODEL_GATEWAY_DATABASE_URL", "postgresql://sg:sg@localhost:5432/sg"),
        help="Database connection URL"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run (validate data without loading)"
    )
    
    args = parser.parse_args()
    
    # Determine what to load
    load_all = args.all
    load_nist = args.nist or load_all
    load_mitre = args.mitre or load_all
    load_owasp = args.owasp or load_all
    load_playbooks = args.playbooks or load_all
    
    if not (load_nist or load_mitre or load_owasp or load_playbooks):
        logger.error("No knowledge bases specified. Use --all or specify individual bases.")
        sys.exit(1)
    
    # Connect to database
    logger.info(f"Connecting to database: {args.database_url}")
    engine = create_engine(args.database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Initialize database (create tables, enable extensions)
    logger.info("Initializing database...")
    init_db()
    
    # Create session and loader
    db = SessionLocal()
    try:
        loader = KnowledgeBaseLoader(db_session=db)
        
        if args.dry_run:
            logger.info("DRY RUN MODE - No data will be loaded")
            # TODO: Add validation logic
            logger.info("Dry run complete")
            return
        
        results = {}
        
        # Load knowledge bases
        if load_nist:
            logger.info("Loading NIST 800-53 controls...")
            results["nist"] = loader.load_nist_controls(args.nist_source)
        
        if load_mitre:
            logger.info("Loading MITRE ATT&CK techniques...")
            results["mitre"] = loader.load_mitre_techniques(args.mitre_source)
        
        if load_owasp:
            logger.info("Loading OWASP content...")
            results["owasp"] = loader.load_owasp_content(args.owasp_source)
        
        if load_playbooks:
            logger.info("Loading SOC playbooks...")
            results["playbooks"] = loader.load_playbooks(args.playbooks_source)
        
        # Print summary
        print("\n" + "="*60)
        print("KNOWLEDGE BASE LOADING SUMMARY")
        print("="*60)
        
        total_loaded = 0
        total_errors = 0
        
        for framework, result in results.items():
            print(f"\n{result['framework']}:")
            print(f"  Loaded: {result['loaded']}")
            print(f"  Errors: {result['errors']}")
            print(f"  Total:  {result['total']}")
            total_loaded += result['loaded']
            total_errors += result['errors']
        
        print("\n" + "="*60)
        print(f"TOTAL: {total_loaded} items loaded, {total_errors} errors")
        print("="*60 + "\n")
        
        if total_errors > 0:
            logger.warning(f"Some items failed to load. Check logs for details.")
            sys.exit(1)
        else:
            logger.info("✅ All knowledge bases loaded successfully!")
            
    except Exception as e:
        logger.error(f"Error loading knowledge bases: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

