"""
Unit tests for Scheduled Ingestion Service
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.scheduled_ingestion_service import ScheduledIngestionService
from app.models.git_repos import GitRepository, GitIngestionJob


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return Mock()


@pytest.fixture
def scheduled_service(mock_db_session):
    """Create ScheduledIngestionService instance."""
    return ScheduledIngestionService(db_session=mock_db_session)


@pytest.fixture
def sample_repo():
    """Sample GitRepository instance."""
    repo = Mock(spec=GitRepository)
    repo.id = uuid4()
    repo.tenant_id = uuid4()
    repo.repo_url = "https://github.com/user/repo.git"
    repo.repo_type = "customer"
    repo.branch = "main"
    repo.paths = None
    repo.is_active = True
    repo.last_ingested_at = None
    return repo


class TestScheduledIngestionService:
    """Test suite for ScheduledIngestionService."""
    
    def test_init(self, scheduled_service):
        """Test service initialization."""
        assert scheduled_service.db is not None
        assert scheduled_service.poll_interval_minutes == 60
    
    @patch('app.services.scheduled_ingestion_service.select')
    def test_get_repos_to_poll(self, mock_select, scheduled_service, sample_repo):
        """Test getting active repositories to poll."""
        mock_stmt = Mock()
        mock_select.return_value = mock_stmt
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_repo]
        scheduled_service.db.execute.return_value = mock_result
        
        repos = scheduled_service.get_repos_to_poll()
        
        assert len(repos) == 1
        assert repos[0] == sample_repo
    
    def test_should_poll_repo_never_ingested(self, scheduled_service, sample_repo):
        """Test repo should be polled if never ingested."""
        sample_repo.last_ingested_at = None
        
        assert scheduled_service.should_poll_repo(sample_repo) is True
    
    def test_should_poll_repo_old_ingestion(self, scheduled_service, sample_repo):
        """Test repo should be polled if last ingestion is old."""
        sample_repo.last_ingested_at = datetime.utcnow() - timedelta(hours=2)
        scheduled_service.poll_interval_minutes = 60
        
        assert scheduled_service.should_poll_repo(sample_repo) is True
    
    def test_should_poll_repo_recent_ingestion(self, scheduled_service, sample_repo):
        """Test repo should not be polled if recently ingested."""
        sample_repo.last_ingested_at = datetime.utcnow() - timedelta(minutes=30)
        scheduled_service.poll_interval_minutes = 60
        
        assert scheduled_service.should_poll_repo(sample_repo) is False
    
    @patch('app.services.scheduled_ingestion_service.GitIngestionJob')
    @patch.object(ScheduledIngestionService, 'git_service')
    def test_poll_and_ingest_success(self, mock_git_service, mock_job_class, scheduled_service, sample_repo):
        """Test successful polling and ingestion."""
        # Setup mocks
        mock_job = Mock(spec=GitIngestionJob)
        mock_job_class.return_value = mock_job
        scheduled_service.db.add = Mock()
        scheduled_service.db.commit = Mock()
        scheduled_service.db.refresh = Mock()
        
        mock_git_service.ingest_from_repo.return_value = {
            "status": "success",
            "files_processed": 5,
            "total_loaded": 10,
            "total_errors": 0,
            "results": {
                "nist": {"loaded": 10, "errors": 0}
            }
        }
        
        result = scheduled_service.poll_and_ingest(sample_repo)
        
        assert result["status"] == "success"
        assert mock_job.status == "success"
        assert mock_job.files_processed == 5
        assert mock_job.records_loaded == 10
        assert sample_repo.last_ingested_at is not None
        assert sample_repo.last_ingestion_status == "success"
    
    @patch.object(ScheduledIngestionService, 'git_service')
    def test_poll_and_ingest_skipped(self, mock_git_service, scheduled_service, sample_repo):
        """Test polling skipped when recently ingested."""
        sample_repo.last_ingested_at = datetime.utcnow() - timedelta(minutes=30)
        scheduled_service.poll_interval_minutes = 60
        
        result = scheduled_service.poll_and_ingest(sample_repo)
        
        assert result["status"] == "skipped"
        mock_git_service.ingest_from_repo.assert_not_called()
    
    @patch('app.services.scheduled_ingestion_service.GitIngestionJob')
    @patch.object(ScheduledIngestionService, 'git_service')
    def test_poll_and_ingest_failure(self, mock_git_service, mock_job_class, scheduled_service, sample_repo):
        """Test polling with ingestion failure."""
        mock_job = Mock(spec=GitIngestionJob)
        mock_job_class.return_value = mock_job
        scheduled_service.db.add = Mock()
        scheduled_service.db.commit = Mock()
        scheduled_service.db.refresh = Mock()
        
        mock_git_service.ingest_from_repo.side_effect = Exception("Ingestion failed")
        
        result = scheduled_service.poll_and_ingest(sample_repo)
        
        assert result["status"] == "error"
        assert mock_job.status == "failed"
        assert mock_job.error_message == "Ingestion failed"
    
    @patch.object(ScheduledIngestionService, 'get_repos_to_poll')
    @patch.object(ScheduledIngestionService, 'poll_and_ingest')
    def test_poll_all_active_repos(self, mock_poll, mock_get_repos, scheduled_service, sample_repo):
        """Test polling all active repositories."""
        # Create multiple repos
        repo2 = Mock(spec=GitRepository)
        repo2.id = uuid4()
        repo2.is_active = True
        
        mock_get_repos.return_value = [sample_repo, repo2]
        mock_poll.side_effect = [
            {"status": "success"},
            {"status": "success"}
        ]
        
        results = scheduled_service.poll_all_active_repos()
        
        assert results["total"] == 2
        assert results["processed"] == 2
        assert results["success"] == 2
        assert mock_poll.call_count == 2
    
    @patch.object(ScheduledIngestionService, 'get_repos_to_poll')
    @patch.object(ScheduledIngestionService, 'poll_and_ingest')
    def test_poll_all_active_repos_mixed_results(self, mock_poll, mock_get_repos, scheduled_service):
        """Test polling with mixed success/failure results."""
        repo1 = Mock(spec=GitRepository)
        repo1.is_active = True
        repo2 = Mock(spec=GitRepository)
        repo2.is_active = True
        
        mock_get_repos.return_value = [repo1, repo2]
        mock_poll.side_effect = [
            {"status": "success"},
            {"status": "error", "error": "Failed"}
        ]
        
        results = scheduled_service.poll_all_active_repos()
        
        assert results["total"] == 2
        assert results["processed"] == 2
        assert results["success"] == 1
        assert results["failed"] == 1
    
    @patch.object(ScheduledIngestionService, 'get_repos_to_poll')
    @patch.object(ScheduledIngestionService, 'poll_and_ingest')
    def test_poll_all_active_repos_with_skipped(self, mock_poll, mock_get_repos, scheduled_service):
        """Test polling with some repos skipped."""
        repo1 = Mock(spec=GitRepository)
        repo1.is_active = True
        repo2 = Mock(spec=GitRepository)
        repo2.is_active = True
        
        mock_get_repos.return_value = [repo1, repo2]
        mock_poll.side_effect = [
            {"status": "success"},
            {"status": "skipped"}
        ]
        
        results = scheduled_service.poll_all_active_repos()
        
        assert results["total"] == 2
        assert results["processed"] == 2
        assert results["success"] == 1
        assert results["skipped"] == 1

