"""
Training Worker
RQ worker for processing adapter training jobs
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rq import Worker, Queue, Connection
import redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_training_worker():
    """Create and return a training worker."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    try:
        redis_conn = redis.from_url(redis_url)
        redis_conn.ping()
        
        # Create training queue
        training_queue = Queue("training", connection=redis_conn)
        
        logger.info(f"Training worker initialized with Redis: {redis_url}")
        return Worker([training_queue], connection=redis_conn)
    except Exception as e:
        logger.error(f"Failed to create training worker: {e}")
        raise


if __name__ == "__main__":
    """Run the worker (for command-line execution)."""
    worker = create_training_worker()
    logger.info("Starting training worker...")
    worker.work(with_scheduler=False)

