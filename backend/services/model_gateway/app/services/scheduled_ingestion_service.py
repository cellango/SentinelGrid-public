"""
Scheduled Ingestion Service
Polls registered git repositories for updates and triggers ingestion.
"""

import logging
import os
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, select
from uuid import UUID

from app.models.git_repos import GitRepository, GitIngestionJob
from app.services.git_data_ingestion_service import GitDataIngestionService

logger = logging.getLogger(__name__)


class ScheduledIngestionService:
    """Service for scheduled/polling-based git repository ingestion."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.git_service = GitDataIngestionService(db_session=db_session)
        self.poll_interval_minutes = int(os.getenv("GIT_POLL_INTERVAL_MINUTES", "60"))
    
    def get_repos_to_poll(self, tenant_id: Optional[str] = None) -> List[GitRepository]:
        """Get active repositories that need polling."""
        stmt = select(GitRepository).where(
            GitRepository.is_active == True
        )

        if tenant_id:
            tenant_uuid = UUID(str(tenant_id))
            stmt = stmt.where(
                or_(GitRepository.tenant_id == tenant_uuid, GitRepository.tenant_id.is_(None))
            )
        
        repos = self.db.execute(stmt).scalars().all()
        return repos
    
    def should_poll_repo(self, repo: GitRepository) -> bool:
        """Determine if repository should be polled based on last ingestion time."""
        if not repo.last_ingested_at:
            return True
        
        time_since_last = datetime.utcnow() - repo.last_ingested_at
        return time_since_last >= timedelta(minutes=self.poll_interval_minutes)
    
    def poll_and_ingest(self, repo: GitRepository) -> Dict[str, Any]:
        """Poll a repository and ingest if changes detected."""
        job = None
        try:
            # Check if we should poll
            if not self.should_poll_repo(repo):
                return {
                    "status": "skipped",
                    "message": f"Recently ingested at {repo.last_ingested_at}"
                }
            
            # Create ingestion job
            job = GitIngestionJob(
                repository_id=repo.id,
                tenant_id=repo.tenant_id,
                trigger_type="scheduled",
                status="running",
                started_at=datetime.utcnow()
            )
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)
            
            # Ingest from repository
            result = self.git_service.ingest_from_repo(
                repo_url=repo.repo_url,
                repo_type=repo.repo_type,
                tenant_id=str(repo.tenant_id) if repo.tenant_id else None,
                branch=repo.branch,
                paths=repo.paths
            )
            
            # Update job status
            job.status = result.get("status", "completed")
            job.files_processed = result.get("files_processed", 0)
            job.records_loaded = result.get("total_loaded", 0)
            job.errors = result.get("total_errors", 0)
            job.results = result.get("results")
            job.completed_at = datetime.utcnow()
            
            if result.get("status") == "error":
                job.error_message = result.get("error")
            
            # Update repository
            repo.last_ingested_at = datetime.utcnow()
            repo.last_ingestion_status = result.get("status", "completed")
            repo.last_ingestion_error = result.get("error")
            
            self.db.commit()
            
            return result
            
        except Exception as e:
            logger.error(f"Error polling repository {repo.repo_url}: {e}", exc_info=True)
            
            if job:
                job.status = "failed"
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                self.db.commit()
            
            return {
                "status": "error",
                "error": str(e)
            }
    
    def poll_all_active_repos(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Poll all active repositories."""
        repos = self.get_repos_to_poll(tenant_id=tenant_id)
        
        results = {
            "total": len(repos),
            "processed": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0
        }
        
        for repo in repos:
            result = self.poll_and_ingest(repo)
            
            results["processed"] += 1
            if result.get("status") == "success":
                results["success"] += 1
            elif result.get("status") == "error":
                results["failed"] += 1
            elif result.get("status") == "skipped":
                results["skipped"] += 1
        
        return results
