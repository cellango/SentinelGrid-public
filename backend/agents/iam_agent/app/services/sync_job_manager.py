"""
Sync Job Manager Service
Manages sync job scheduling, execution, monitoring, and retry logic
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import uuid

from app.services.connector_framework import (
    ConnectorFactory,
    SyncJob,
    SyncDirection,
    SyncStatus
)
from app.services.integration_manager import IntegrationManager

logger = logging.getLogger(__name__)


class JobSchedule(str, Enum):
    """Sync job schedule types."""
    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class SyncJobManager:
    """Service for managing sync job execution and scheduling."""
    
    def __init__(self, integration_manager: IntegrationManager):
        self.integration_manager = integration_manager
        self.jobs: Dict[str, SyncJob] = {}  # In-memory storage (would use DB in production)
        self.schedules: Dict[str, Dict[str, Any]] = {}  # Scheduled jobs

    def _get_job(self, job_id: str, tenant_id: Optional[str] = None) -> SyncJob:
        job = self.jobs.get(job_id)
        if not job:
            raise LookupError(f"Job {job_id} not found")
        if tenant_id and getattr(job, "tenant_id", None) != tenant_id:
            raise LookupError(f"Job {job_id} not found")
        return job

    def _get_schedule_record(
        self,
        schedule_id: str,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            raise LookupError(f"Schedule {schedule_id} not found")
        if tenant_id and schedule.get("tenant_id") != tenant_id:
            raise LookupError(f"Schedule {schedule_id} not found")
        return schedule
    
    def create_sync_job(
        self,
        integration_id: str,
        sync_type: str,
        direction: SyncDirection = SyncDirection.IMPORT,
        filters: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new sync job.
        
        Args:
            integration_id: Integration to sync
            sync_type: Type of sync ('users', 'groups', 'full')
            direction: Sync direction
            filters: Optional filters
            tenant_id: Tenant ID for multi-tenancy
            
        Returns:
            Job information
        """
        # Get integration
        integration = self.integration_manager.get_integration(integration_id, tenant_id)
        if not integration:
            raise ValueError(f"Integration {integration_id} not found")
        
        # Create connector
        connector_type = integration["type"]
        connector = ConnectorFactory.create(connector_type, integration)
        
        # Create sync job
        job_id = str(uuid.uuid4())
        job = SyncJob(
            job_id=job_id,
            connector=connector,
            sync_type=sync_type,
            direction=direction,
            filters=filters
        )
        job.integration_id = integration_id
        job.tenant_id = tenant_id
        
        self.jobs[job_id] = job
        
        return {
            "job_id": job_id,
            "integration_id": integration_id,
            "sync_type": sync_type,
            "direction": direction.value,
            "status": job.status.value,
            "created_at": job.created_at.isoformat(),
            "tenant_id": tenant_id
        }
    
    def execute_sync_job(
        self,
        job_id: str,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a sync job."""
        job = self._get_job(job_id, tenant_id)
        
        if job.status == SyncStatus.RUNNING:
            raise ValueError(f"Job {job_id} is already running")
        
        result = job.execute()
        return result
    
    def schedule_sync_job(
        self,
        integration_id: str,
        schedule_type: JobSchedule,
        sync_type: str,
        direction: SyncDirection = SyncDirection.IMPORT,
        cron_expression: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Schedule a recurring sync job.
        
        Args:
            integration_id: Integration to sync
            schedule_type: Schedule type
            sync_type: Type of sync
            direction: Sync direction
            cron_expression: Custom cron expression (if schedule_type is CUSTOM)
            filters: Optional filters
            tenant_id: Tenant ID
            
        Returns:
            Schedule information
        """
        integration = self.integration_manager.get_integration(integration_id, tenant_id)
        if not integration:
            raise ValueError(f"Integration {integration_id} not found")

        schedule_id = str(uuid.uuid4())
        
        schedule = {
            "schedule_id": schedule_id,
            "integration_id": integration_id,
            "schedule_type": schedule_type.value,
            "sync_type": sync_type,
            "direction": direction.value,
            "cron_expression": cron_expression,
            "filters": filters or {},
            "enabled": True,
            "tenant_id": tenant_id,
            "last_run": None,
            "next_run": self._calculate_next_run(schedule_type, cron_expression),
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.schedules[schedule_id] = schedule
        
        return schedule
    
    def get_job_status(
        self,
        job_id: str,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get status of a sync job."""
        job = self._get_job(job_id, tenant_id)
        
        return {
            "job_id": job_id,
            "status": job.status.value,
            "sync_type": job.sync_type,
            "direction": job.direction.value,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "result": job.result,
            "error": job.error,
            "duration_seconds": (
                (job.completed_at - job.started_at).total_seconds()
                if job.completed_at and job.started_at else None
            )
        }
    
    def list_jobs(
        self,
        integration_id: Optional[str] = None,
        status: Optional[SyncStatus] = None,
        tenant_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List sync jobs with optional filtering."""
        jobs_list = []
        
        for job_id, job in self.jobs.items():
            # Apply filters
            if integration_id and hasattr(job, 'integration_id') and job.integration_id != integration_id:
                continue
            if tenant_id and getattr(job, "tenant_id", None) != tenant_id:
                continue
            if status and job.status != status:
                continue
            
            jobs_list.append(self.get_job_status(job_id))
        
        # Sort by created_at (newest first)
        jobs_list.sort(key=lambda x: x["created_at"], reverse=True)
        
        return jobs_list[:limit]
    
    def list_schedules(
        self,
        integration_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List scheduled sync jobs."""
        schedules_list = []
        
        for schedule in self.schedules.values():
            if integration_id and schedule["integration_id"] != integration_id:
                continue
            if tenant_id and schedule.get("tenant_id") != tenant_id:
                continue
            
            schedules_list.append(schedule)
        
        return schedules_list
    
    def get_schedule(
        self,
        schedule_id: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get a specific schedule."""
        return self._get_schedule_record(schedule_id, tenant_id)
    
    def update_schedule(
        self,
        schedule_id: str,
        updates: Dict[str, Any],
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a schedule."""
        schedule = self._get_schedule_record(schedule_id, tenant_id)
        
        schedule.update(updates)
        if "schedule_type" in updates or "cron_expression" in updates:
            schedule["next_run"] = self._calculate_next_run(
                JobSchedule(schedule["schedule_type"]),
                schedule.get("cron_expression")
            )
        
        return schedule
    
    def delete_schedule(
        self,
        schedule_id: str,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delete a schedule."""
        self._get_schedule_record(schedule_id, tenant_id)
        
        del self.schedules[schedule_id]
        
        return {
            "schedule_id": schedule_id,
            "status": "deleted",
            "deleted_at": datetime.utcnow().isoformat()
        }
    
    def get_sync_statistics(
        self,
        integration_id: Optional[str] = None,
        days: int = 30,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get sync statistics for integrations."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Filter jobs by date and integration
        recent_jobs = [
            job for job in self.jobs.values()
            if job.created_at >= cutoff_date and
            (not tenant_id or getattr(job, "tenant_id", None) == tenant_id) and
            (not integration_id or (hasattr(job, 'integration_id') and job.integration_id == integration_id))
        ]
        
        # Calculate statistics
        total_jobs = len(recent_jobs)
        successful_jobs = sum(1 for job in recent_jobs if job.status == SyncStatus.SUCCESS)
        failed_jobs = sum(1 for job in recent_jobs if job.status == SyncStatus.FAILED)
        
        # Calculate average duration
        completed_jobs = [job for job in recent_jobs if job.completed_at and job.started_at]
        avg_duration = None
        if completed_jobs:
            durations = [
                (job.completed_at - job.started_at).total_seconds()
                for job in completed_jobs
            ]
            avg_duration = sum(durations) / len(durations) if durations else None
        
        return {
            "period_days": days,
            "total_jobs": total_jobs,
            "successful_jobs": successful_jobs,
            "failed_jobs": failed_jobs,
            "success_rate": round((successful_jobs / total_jobs * 100) if total_jobs > 0 else 0, 2),
            "average_duration_seconds": round(avg_duration, 2) if avg_duration else None,
            "integration_id": integration_id,
            "tenant_id": tenant_id,
        }
    
    def retry_failed_job(
        self,
        job_id: str,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retry a failed sync job."""
        job = self._get_job(job_id, tenant_id)
        
        if job.status != SyncStatus.FAILED:
            raise ValueError(f"Job {job_id} is not in failed status")
        
        # Reset job status
        job.status = SyncStatus.PENDING
        job.error = None
        
        # Execute again
        return self.execute_sync_job(job_id, tenant_id=tenant_id)
    
    def _calculate_next_run(
        self,
        schedule_type: JobSchedule,
        cron_expression: Optional[str] = None
    ) -> str:
        """Calculate next run time for a schedule."""
        now = datetime.utcnow()
        
        if schedule_type == JobSchedule.ONCE:
            return now.isoformat()
        elif schedule_type == JobSchedule.HOURLY:
            next_run = now + timedelta(hours=1)
        elif schedule_type == JobSchedule.DAILY:
            next_run = now + timedelta(days=1)
        elif schedule_type == JobSchedule.WEEKLY:
            next_run = now + timedelta(weeks=1)
        elif schedule_type == JobSchedule.MONTHLY:
            next_run = now + timedelta(days=30)
        elif schedule_type == JobSchedule.CUSTOM and cron_expression:
            # Would use a cron library to calculate next run
            # For now, default to daily
            next_run = now + timedelta(days=1)
        else:
            next_run = now + timedelta(days=1)
        
        return next_run.isoformat()
