"""
Tests for Job Queue Service.
"""

import pytest
from unittest.mock import Mock, patch
from app.services.job_queue import JobQueueService


def test_job_queue_initialization():
    """Test job queue service initialization."""
    with patch("app.services.job_queue.redis.from_url") as mock_redis:
        mock_conn = Mock()
        mock_conn.ping.return_value = True
        mock_redis.return_value = mock_conn
        
        with patch("app.services.job_queue.Queue") as mock_queue:
            service = JobQueueService(redis_url="redis://localhost:6379")
            
            assert service.redis_conn is not None
            assert service.training_queue is not None


def test_enqueue_training_job(mock_job_queue):
    """Test enqueueing a training job."""
    service = JobQueueService()
    service.training_queue = mock_job_queue
    
    def dummy_training_func(job_id, tenant_id, config):
        pass
    
    job = service.enqueue_training_job(
        job_id="test-job-123",
        tenant_id="tenant-456",
        training_func=dummy_training_func,
        training_config={"epochs": 3}
    )
    
    assert job is not None
    mock_job_queue.enqueue.assert_called_once()


def test_get_job_status(mock_job_queue):
    """Test getting job status."""
    service = JobQueueService()
    
    with patch("app.services.job_queue.Job") as mock_job_class:
        mock_job = Mock()
        mock_job.id = "test-job-123"
        mock_job.get_status.return_value = "started"
        mock_job.is_finished = False
        mock_job.is_failed = False
        mock_job.created_at = None
        mock_job.started_at = None
        mock_job.ended_at = None
        mock_job.meta = {"tenant_id": "tenant-456"}
        
        mock_job_class.fetch.return_value = mock_job
        service.redis_conn = Mock()
        
        status = service.get_job_status("test-job-123")
        
        assert status is not None
        assert status["job_id"] == "test-job-123"
        assert status["status"] == "started"


def test_cancel_job(mock_job_queue):
    """Test cancelling a job."""
    service = JobQueueService()
    
    with patch("app.services.job_queue.Job") as mock_job_class:
        mock_job = Mock()
        mock_job.cancel.return_value = True
        mock_job_class.fetch.return_value = mock_job
        service.redis_conn = Mock()
        
        result = service.cancel_job("test-job-123")
        
        assert result is True
        mock_job.cancel.assert_called_once()


def test_get_queue_stats(mock_job_queue):
    """Test getting queue statistics."""
    service = JobQueueService()
    service.training_queue = mock_job_queue
    
    mock_job_queue.__len__.return_value = 5
    mock_job_queue.started_job_registry.count = 2
    mock_job_queue.finished_job_registry.count = 10
    mock_job_queue.failed_job_registry.count = 1
    
    stats = service.get_queue_stats("training")
    
    assert stats["queue_name"] == "training"
    assert stats["queued_jobs"] == 5
    assert stats["started_jobs"] == 2
    assert stats["finished_jobs"] == 10
    assert stats["failed_jobs"] == 1

