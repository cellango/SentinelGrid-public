"""
Integration tests for Git Ingestion API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from app.main import app
from app.core.database import get_db, get_superadmin_db, get_tenant_session


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return Mock()


@pytest.fixture
def client(mock_db_session):
    """FastAPI test client with mocked database."""
    def override_tenant_db():
        yield mock_db_session

    def override_superadmin_db():
        yield mock_db_session

    def unexpected_db():
        raise AssertionError("Unexpected plain DB dependency used")
        yield  # pragma: no cover
    
    app.dependency_overrides[get_db] = unexpected_db
    app.dependency_overrides[get_tenant_session] = override_tenant_db
    app.dependency_overrides[get_superadmin_db] = override_superadmin_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sample_tenant_id():
    """Sample tenant ID."""
    return str(uuid4())


class TestGitIngestionAPI:
    """Test suite for Git Ingestion API endpoints."""

    @staticmethod
    def _customer_headers(sample_tenant_id):
        return {"X-Tenant-ID": sample_tenant_id}

    @staticmethod
    def _global_headers(sample_tenant_id):
        return {
            "X-Tenant-ID": sample_tenant_id,
            "X-Platform-Operation": "true",
        }
    
    def test_ingest_from_repo_success(self, client, mock_db_session, sample_tenant_id):
        """Test successful manual repository ingestion."""
        with patch('app.api.git_ingestion.GitDataIngestionService') as mock_service_class:
            mock_service = Mock()
            mock_service.ingest_from_repo.return_value = {
                "status": "success",
                "files_processed": 5,
                "total_loaded": 10,
                "total_errors": 0
            }
            mock_service_class.return_value = mock_service
            
            response = client.post(
                "/internal/llm/git-ingestion/ingest",
                headers=self._customer_headers(sample_tenant_id),
                json={
                    "repo_url": "https://github.com/user/repo.git",
                    "repo_type": "customer",
                    "tenant_id": sample_tenant_id,
                    "branch": "main"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["files_processed"] == 5
    
    def test_ingest_from_repo_defaults_to_authenticated_tenant(self, client, mock_db_session, sample_tenant_id):
        """Customer repo ingestion defaults to the authenticated tenant header."""
        with patch('app.api.git_ingestion.GitDataIngestionService') as mock_service_class:
            mock_service = Mock()
            mock_service.ingest_from_repo.return_value = {
                "status": "success",
                "files_processed": 1
            }
            mock_service_class.return_value = mock_service

            response = client.post(
                "/internal/llm/git-ingestion/ingest",
                headers=self._customer_headers(sample_tenant_id),
                json={
                    "repo_url": "https://github.com/user/repo.git",
                    "repo_type": "customer",
                    "branch": "main"
                }
            )

        assert response.status_code == 200
        assert mock_service.ingest_from_repo.call_args.kwargs["tenant_id"] == sample_tenant_id

    def test_ingest_from_repo_global_requires_platform_header(self, client, mock_db_session, sample_tenant_id):
        """Test global repo ingestion doesn't require tenant_id."""
        response = client.post(
            "/internal/llm/git-ingestion/ingest",
            headers=self._customer_headers(sample_tenant_id),
            json={
                "repo_url": "https://github.com/global/repo.git",
                "repo_type": "global",
                "branch": "main"
            }
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Global repository operations require X-Platform-Operation: true"

    def test_ingest_from_repo_global_with_platform_header(self, client, mock_db_session, sample_tenant_id):
        """Test global repo ingestion uses explicit platform-operation context."""
        with patch('app.api.git_ingestion.GitDataIngestionService') as mock_service_class:
            mock_service = Mock()
            mock_service.ingest_from_repo.return_value = {
                "status": "success",
                "files_processed": 0
            }
            mock_service_class.return_value = mock_service
            
            response = client.post(
                "/internal/llm/git-ingestion/ingest",
                headers=self._global_headers(sample_tenant_id),
                json={
                    "repo_url": "https://github.com/global/repo.git",
                    "repo_type": "global",
                    "branch": "main"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
    
    def test_ingest_from_repo_error(self, client, mock_db_session, sample_tenant_id):
        """Test ingestion error handling."""
        with patch('app.api.git_ingestion.GitDataIngestionService') as mock_service_class:
            mock_service = Mock()
            mock_service.ingest_from_repo.return_value = {
                "status": "error",
                "error": "Repository not found"
            }
            mock_service_class.return_value = mock_service
            
            response = client.post(
                "/internal/llm/git-ingestion/ingest",
                headers=self._customer_headers(sample_tenant_id),
                json={
                    "repo_url": "https://github.com/invalid/repo.git",
                    "repo_type": "customer",
                    "tenant_id": sample_tenant_id
                }
            )
            
            assert response.status_code == 500
            assert response.json()["detail"] == "Repository not found"
    
    @pytest.mark.asyncio
    async def test_github_webhook_success(self, client, mock_db_session, sample_tenant_id):
        """Test GitHub webhook endpoint."""
        webhook_payload = {
            "repository": {
                "clone_url": "https://github.com/user/repo.git"
            },
            "ref": "refs/heads/main",
            "commits": [
                {
                    "added": ["knowledge-base/nist/controls.json"],
                    "modified": []
                }
            ]
        }
        
        with patch('app.api.git_ingestion.GitDataIngestionService') as mock_service_class:
            mock_service = Mock()
            mock_service.process_webhook_payload.return_value = {
                "status": "success",
                "files_processed": 1
            }
            mock_service_class.return_value = mock_service
            
            response = client.post(
                f"/internal/llm/git-ingestion/webhook/github?tenant_id={sample_tenant_id}&repo_type=customer",
                headers={**self._customer_headers(sample_tenant_id), "X-GitHub-Event": "push"},
                json=webhook_payload,
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_github_webhook_wrong_event(self, client, mock_db_session):
        """Test GitHub webhook with non-push event."""
        response = client.post(
            "/internal/llm/git-ingestion/webhook/github",
            headers={**self._customer_headers(str(uuid4())), "X-GitHub-Event": "pull_request"},
            json={"action": "opened"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"
    
    @pytest.mark.asyncio
    async def test_gitlab_webhook_success(self, client, mock_db_session):
        """Test GitLab webhook endpoint."""
        webhook_payload = {
            "project": {
                "git_http_url": "https://gitlab.com/user/repo.git"
            },
            "ref": "main",
            "commits": [
                {
                    "added": ["kb/mitre.json"],
                    "modified": []
                }
            ]
        }
        
        with patch('app.api.git_ingestion.GitDataIngestionService') as mock_service_class:
            mock_service = Mock()
            mock_service.process_webhook_payload.return_value = {
                "status": "success"
            }
            mock_service_class.return_value = mock_service
            
            response = client.post(
                "/internal/llm/git-ingestion/webhook/gitlab?repo_type=global",
                headers={**self._global_headers(str(uuid4())), "X-GitLab-Event": "Push Hook"},
                json=webhook_payload,
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
    
    def test_list_registered_repos_empty(self, client, mock_db_session, sample_tenant_id):
        """Test listing repositories when none exist."""
        from sqlalchemy import select
        mock_stmt = Mock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result
        
        response = client.get(
            "/internal/llm/git-ingestion/repos",
            headers=self._customer_headers(sample_tenant_id),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_list_registered_repos_filtered(self, client, mock_db_session, sample_tenant_id):
        """Test listing repositories with tenant filter."""
        from app.models.git_repos import GitRepository
        from sqlalchemy import select
        
        mock_repo = Mock(spec=GitRepository)
        mock_repo.id = uuid4()
        mock_repo.tenant_id = uuid4()
        mock_repo.url = "https://github.com/user/repo.git"
        mock_repo.branch = "main"
        mock_repo.status = "active"
        mock_repo.metadata_json = {
            "repo_type": "customer",
            "last_ingestion_status": None,
        }
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_repo]
        mock_db_session.execute.return_value = mock_result
        
        response = client.get(
            f"/internal/llm/git-ingestion/repos?tenant_id={sample_tenant_id}",
            headers=self._customer_headers(sample_tenant_id),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data[0]["repo_url"] == "https://github.com/user/repo.git"
        assert data[0]["repo_type"] == "customer"
    
    def test_register_repo_customer(self, client, mock_db_session, sample_tenant_id):
        """Test registering a customer repository."""
        from app.models.git_repos import GitRepository
        from sqlalchemy import select
        
        # Mock no existing repo
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        # Mock new repo creation
        mock_repo = Mock(spec=GitRepository)
        mock_repo.id = uuid4()
        mock_db_session.add = Mock()
        mock_db_session.commit = Mock()
        mock_db_session.refresh = Mock()
        
        response = client.post(
            "/internal/llm/git-ingestion/repos/register",
            headers=self._customer_headers(sample_tenant_id),
            params={
                "repo_url": "https://github.com/user/repo.git",
                "repo_type": "customer",
                "tenant_id": sample_tenant_id,
                "branch": "main",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "registered"
        assert data["repo_type"] == "customer"
    
    def test_register_repo_customer_defaults_to_authenticated_tenant(self, client, mock_db_session, sample_tenant_id):
        """Customer repo registration defaults to the authenticated tenant header."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        mock_db_session.add = Mock()
        mock_db_session.commit = Mock()
        mock_db_session.refresh = Mock()

        response = client.post(
            "/internal/llm/git-ingestion/repos/register",
            headers=self._customer_headers(sample_tenant_id),
            params={
                "repo_url": "https://github.com/user/repo.git",
                "repo_type": "customer"
            }
        )

        assert response.status_code == 200
        assert response.json()["repo_type"] == "customer"

    def test_register_repo_global(self, client, mock_db_session, sample_tenant_id):
        """Test registering a global repository."""
        from sqlalchemy import select
        
        # Mock no existing repo
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        # Mock new repo creation
        mock_repo = Mock()
        mock_repo.id = uuid4()
        mock_db_session.add = Mock()
        mock_db_session.commit = Mock()
        mock_db_session.refresh = Mock()
        
        response = client.post(
            "/internal/llm/git-ingestion/repos/register",
            headers=self._global_headers(sample_tenant_id),
            params={
                "repo_url": "https://github.com/global/repo.git",
                "repo_type": "global",
                "branch": "main"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "registered"
        assert data["repo_type"] == "global"
    
    def test_poll_all_repos(self, client, mock_db_session, sample_tenant_id):
        """Test polling all active repositories."""
        with patch('app.api.git_ingestion.ScheduledIngestionService') as mock_service_class:
            mock_service = Mock()
            mock_service.poll_all_active_repos.return_value = {
                "total": 2,
                "processed": 2,
                "success": 2,
                "failed": 0,
                "skipped": 0
            }
            mock_service_class.return_value = mock_service
            
            response = client.post(
                "/internal/llm/git-ingestion/poll",
                headers=self._customer_headers(sample_tenant_id),
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert data["success"] == 2
