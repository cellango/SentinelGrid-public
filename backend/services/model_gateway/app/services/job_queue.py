"""
Job Queue Service
Redis Queue (RQ) integration for background tasks
"""

import logging
from typing import Dict, Any, Optional, Callable
import os
import redis
from rq import Queue
from rq.job import Job, JobStatus

logger = logging.getLogger(__name__)


class JobQueueService:
    """Service for managing background jobs using Redis Queue (RQ)."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize job queue service.
        
        Args:
            redis_url: Redis connection URL (defaults to env var)
        """
        redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        
        try:
            self.redis_conn = redis.from_url(redis_url, decode_responses=False)
            # Test connection
            self.redis_conn.ping()
            
            # Create queues
            self.training_queue = Queue("training", connection=self.redis_conn)
            self.default_queue = Queue("default", connection=self.redis_conn)
            
            logger.info(f"Job queue service initialized with Redis: {redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_conn = None
            self.training_queue = None
            self.default_queue = None
    
    def enqueue_training_job(
        self,
        job_id: str,
        tenant_id: str,
        training_func: Callable,
        *args,
        **kwargs
    ) -> Optional[Job]:
        """
        Enqueue a training job.
        
        Args:
            job_id: Unique job identifier
            tenant_id: Tenant ID
            training_func: Function to execute (adapter training)
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            RQ Job object or None if queue unavailable
        """
        if not self.training_queue:
            logger.error("Training queue not available. Redis connection failed.")
            return None
        
        try:
            # Add job_id and tenant_id to kwargs
            job_kwargs = {
                "job_id": job_id,
                "tenant_id": tenant_id,
                **kwargs
            }
            
            # Enqueue job with timeout (training can take hours)
            job = self.training_queue.enqueue(
                training_func,
                *args,
                **job_kwargs,
                job_id=job_id,
                job_timeout="24h",  # 24 hour timeout for training
                result_ttl=86400,  # Keep results for 24 hours
                failure_ttl=86400,  # Keep failures for 24 hours
                meta={"tenant_id": tenant_id, "job_type": "training"}
            )
            
            logger.info(f"Enqueued training job {job_id} for tenant {tenant_id}")
            return job
            
        except Exception as e:
            logger.error(f"Error enqueueing training job {job_id}: {e}")
            return None
    
    def enqueue_job(
        self,
        job_id: str,
        func: Callable,
        queue_name: str = "default",
        *args,
        **kwargs
    ) -> Optional[Job]:
        """
        Enqueue a job to a specific queue.
        
        Args:
            job_id: Unique job identifier
            func: Function to execute
            queue_name: Queue name (default, training, etc.)
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            RQ Job object or None
        """
        queue = self.get_queue(queue_name)
        if not queue:
            logger.error(f"Queue {queue_name} not available")
            return None
        
        try:
            job = queue.enqueue(
                func,
                *args,
                **kwargs,
                job_id=job_id,
                result_ttl=3600,  # 1 hour default
                failure_ttl=3600
            )
            logger.info(f"Enqueued job {job_id} to queue {queue_name}")
            return job
        except Exception as e:
            logger.error(f"Error enqueueing job {job_id}: {e}")
            return None
    
    def get_queue(self, queue_name: str) -> Optional[Queue]:
        """Get a queue by name."""
        if not self.redis_conn:
            return None
        
        try:
            if queue_name == "training":
                return self.training_queue
            else:
                return Queue(queue_name, connection=self.redis_conn)
        except Exception as e:
            logger.error(f"Error getting queue {queue_name}: {e}")
            return None
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dictionary with job status, result, error, etc.
        """
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            
            status_info = {
                "job_id": job.id,
                "status": job.get_status(),
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "ended_at": job.ended_at.isoformat() if job.ended_at else None,
                "meta": job.meta,
            }
            
            # Add result or error
            if job.is_finished:
                status_info["result"] = job.result
            elif job.is_failed:
                status_info["error"] = str(job.exc_info) if job.exc_info else "Unknown error"
            
            return status_info
            
        except Exception as e:
            logger.error(f"Error getting job status for {job_id}: {e}")
            return None
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if cancelled, False otherwise
        """
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            job.cancel()
            logger.info(f"Cancelled job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return False
    
    def get_queue_stats(self, queue_name: str = "training") -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Args:
            queue_name: Queue name
            
        Returns:
            Dictionary with queue stats
        """
        queue = self.get_queue(queue_name)
        if not queue:
            return {"error": "Queue not available"}
        
        try:
            return {
                "queue_name": queue_name,
                "queued_jobs": len(queue),
                "started_jobs": queue.started_job_registry.count,
                "finished_jobs": queue.finished_job_registry.count,
                "failed_jobs": queue.failed_job_registry.count,
            }
        except Exception as e:
            logger.error(f"Error getting queue stats for {queue_name}: {e}")
            return {"error": str(e)}


# Global job queue service instance
_job_queue_service: Optional[JobQueueService] = None


def get_job_queue_service() -> JobQueueService:
    """Get or create global job queue service instance."""
    global _job_queue_service
    if _job_queue_service is None:
        _job_queue_service = JobQueueService()
    return _job_queue_service
