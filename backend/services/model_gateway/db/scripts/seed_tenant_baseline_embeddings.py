#!/usr/bin/env python3
"""
Seed baseline cybersecurity knowledge embeddings into each tenant's vector space.
Intended to be safe to re-run (upserts by tenant_id + source + os_id_ref).
"""

import sys
import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

script_dir = Path(__file__).resolve().parent
service_root = script_dir.parent.parent  # db -> model_gateway
sys.path.insert(0, str(service_root))

from app.core.config import settings  # noqa: E402
from app.services.embedding_seed_service import EmbeddingSeedService  # noqa: E402


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    engine = create_engine(settings.MODEL_GATEWAY_DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = SessionLocal()
    try:
        seeder = EmbeddingSeedService(db=db)
        result = seeder.seed_all_active_tenants()
        logger.info("Baseline seeding completed: %s", result)
        return 0
    except Exception as exc:
        logger.exception("Baseline seeding failed: %s", exc)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
