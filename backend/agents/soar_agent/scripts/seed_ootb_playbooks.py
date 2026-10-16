#!/usr/bin/env python3
"""
Standalone script to seed Out-of-the-Box playbooks.

Usage:
    python -m backend.agents.soar_agent.scripts.seed_ootb_playbooks
    OR
    cd backend/agents/soar_agent && python scripts/seed_ootb_playbooks.py
"""

import sys
import os
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.services.playbook_seeder import seed_all_ootb_playbooks
from app.core.database import get_db, init_db
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for seeding OOTB playbooks."""
    logger.info("Initializing database...")
    init_db()
    
    logger.info("Seeding OOTB playbooks...")
    db = next(get_db())
    try:
        seeded = seed_all_ootb_playbooks(db)
        logger.info(f"Successfully seeded {len(seeded)} OOTB playbooks")
        
        for pb in seeded:
            logger.info(f"  - {pb.playbook_key}: {pb.name}")
    except Exception as e:
        logger.error(f"Error seeding playbooks: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
