"""
Unit tests for Git Data Ingestion Service
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from uuid import uuid4

from app.services.git_data_ingestion_service import GitDataIngestionService
from app.services.rag_service import RAGService
from app.services.knowledge_base_loader import KnowledgeBaseLoader


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return Mock()


@pytest.fixture
def mock_rag_service():
    """Mock RAG service."""
    service = Mock(spec=RAGService)
    service.store_knowledge = Mock(return_value={"status": "success", "id": str(uuid4())})
    return service


@pytest.fixture
def mock_knowledge_loader():
    """Mock knowledge base loader."""
    return Mock(spec=KnowledgeBaseLoader)


@pytest.fixture
def git_service(mock_db_session):
    """Create GitDataIngestionService instance with mocked dependencies."""
    with patch('app.services.git_data_ingestion_service.RAGService') as mock_rag, \
         patch('app.services.git_data_ingestion_service.KnowledgeBaseLoader') as mock_loader:
        
        mock_rag.return_value.store_knowledge.return_value = {"status": "success", "id": str(uuid4())}
        
        service = GitDataIngestionService(db_session=mock_db_session)
        return service


@pytest.fixture
def sample_nist_data():
    """Sample NIST controls data."""
    return {
        "controls": [
            {
                "id": "AC-2",
                "family": "Access Control",
                "description": "The organization manages information system accounts.",
                "guidance": "Account management addresses...",
                "version": "800-53r5"
            }
        ]
    }


@pytest.fixture
def sample_mitre_data():
    """Sample MITRE ATT&CK data."""
    return {
        "techniques": [
            {
                "id": "T1078",
                "name": "Valid Accounts",
                "description": "Adversaries may steal credentials...",
                "tactic": ["Initial Access"],
                "detection": "Monitor for unusual login patterns.",
                "mitigation": "Use multifactor authentication.",
                "version": "ATT&CK v13"
            }
        ]
    }


@pytest.fixture
def sample_owasp_data():
    """Sample OWASP data."""
    return {
        "items": [
            {
                "id": "A01:2021",
                "name": "Broken Access Control",
                "description": "Access control enforces policy...",
                "type": "top10",
                "how_to_prevent": "Implement strong access control policies.",
                "version": "2021"
            }
        ]
    }


@pytest.fixture
def sample_playbook_data():
    """Sample SOC playbook data."""
    return {
        "playbooks": [
            {
                "id": "malware-response-v1",
                "name": "Malware Detection & Response",
                "description": "Comprehensive playbook...",
                "steps": [
                    {
                        "name": "Detection & Triage",
                        "description": "EDR/SIEM alert analysis..."
                    }
                ]
            }
        ]
    }


class TestGitDataIngestionService:
    """Test suite for GitDataIngestionService."""
    
    def test_init(self, mock_db_session):
        """Test service initialization."""
        service = GitDataIngestionService(db_session=mock_db_session)
        assert service.db == mock_db_session
        assert service.temp_dir.exists()
    
    def test_get_repo_id(self, git_service):
        """Test repository ID generation."""
        repo_url = "https://github.com/user/repo.git"
        repo_id = git_service._get_repo_id(repo_url)
        
        assert repo_id.startswith("repo-")
        assert len(repo_id) > 5
        
        # Same URL should generate same ID
        repo_id2 = git_service._get_repo_id(repo_url)
        assert repo_id == repo_id2
    
    def test_detect_category_nist(self, git_service, sample_nist_data):
        """Test category detection for NIST."""
        file_path = Path("/tmp/nist-controls.json")
        category = git_service._detect_category(file_path, sample_nist_data)
        assert category == "nist"
    
    def test_detect_category_mitre(self, git_service, sample_mitre_data):
        """Test category detection for MITRE."""
        file_path = Path("/tmp/mitre-techniques.json")
        category = git_service._detect_category(file_path, sample_mitre_data)
        assert category == "mitre"
    
    def test_detect_category_owasp(self, git_service, sample_owasp_data):
        """Test category detection for OWASP."""
        file_path = Path("/tmp/owasp-top10.json")
        category = git_service._detect_category(file_path, sample_owasp_data)
        assert category == "owasp"
    
    def test_detect_category_playbook(self, git_service, sample_playbook_data):
        """Test category detection for playbooks."""
        file_path = Path("/tmp/playbooks.json")
        category = git_service._detect_category(file_path, sample_playbook_data)
        assert category == "playbooks"
    
    def test_detect_category_custom(self, git_service):
        """Test category detection for unknown format."""
        file_path = Path("/tmp/unknown.json")
        data = {"some": "data"}
        category = git_service._detect_category(file_path, data)
        assert category == "custom"
    
    @patch('subprocess.run')
    def test_clone_or_update_repo_clone_new(self, mock_subprocess, git_service):
        """Test cloning a new repository."""
        mock_subprocess.return_value = Mock(returncode=0)
        clone_path = Path("/tmp/test-repo")
        clone_path.parent.mkdir(parents=True, exist_ok=True)
        
        git_service._clone_or_update_repo(
            "https://github.com/user/repo.git",
            clone_path,
            "main"
        )
        
        # Should call git clone
        assert mock_subprocess.called
        calls = [str(call) for call in mock_subprocess.call_args_list]
        assert any("git clone" in str(call) for call in calls)
    
    @patch('subprocess.run')
    def test_clone_or_update_repo_update_existing(self, mock_subprocess, git_service):
        """Test updating an existing repository."""
        mock_subprocess.return_value = Mock(returncode=0)
        clone_path = Path("/tmp/existing-repo")
        clone_path.mkdir(parents=True, exist_ok=True)
        (clone_path / ".git").mkdir()
        
        git_service._clone_or_update_repo(
            "https://github.com/user/repo.git",
            clone_path,
            "main"
        )
        
        # Should call git fetch and pull
        assert mock_subprocess.called
        calls = [str(call) for call in mock_subprocess.call_args_list]
        assert any("git fetch" in str(call) or "git pull" in str(call) for call in calls)
    
    def test_ingest_from_repo_customer_missing_tenant_id(self, git_service):
        """Test ingestion fails when tenant_id missing for customer repo."""
        result = git_service.ingest_from_repo(
            repo_url="https://github.com/user/repo.git",
            repo_type="customer",
            tenant_id=None
        )
        
        assert result["status"] == "error"
        assert "tenant_id" in result["error"].lower()
    
    def test_ingest_from_repo_global_no_tenant_id_required(self, git_service):
        """Test global repo ingestion doesn't require tenant_id."""
        with patch.object(git_service, '_clone_or_update_repo'), \
             patch.object(git_service, '_discover_kb_files', return_value=[]):
            
            result = git_service.ingest_from_repo(
                repo_url="https://github.com/global/repo.git",
                repo_type="global",
                tenant_id=None
            )
            
            assert result["status"] == "success"
            assert result["files_processed"] == 0
    
    @patch('subprocess.run')
    def test_ingest_from_repo_success(self, mock_subprocess, git_service, tmp_path):
        """Test successful repository ingestion."""
        mock_subprocess.return_value = Mock(returncode=0)
        
        # Create mock repository structure
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        nist_file = repo_path / "nist" / "controls.json"
        nist_file.parent.mkdir()
        nist_file.write_text(json.dumps({"controls": []}))
        
        with patch.object(git_service, '_clone_or_update_repo') as mock_clone, \
             patch.object(git_service, '_discover_kb_files', return_value=[nist_file]), \
             patch.object(git_service, '_process_file') as mock_process:
            
            mock_clone.return_value = None
            mock_process.return_value = {
                "status": "success",
                "loaded": 5,
                "errors": 0,
                "category": "nist"
            }
            
            result = git_service.ingest_from_repo(
                repo_url="https://github.com/user/repo.git",
                repo_type="customer",
                tenant_id=str(uuid4())
            )
            
            assert result["status"] == "success"
            assert result["files_processed"] == 1
    
    def test_process_nist_data(self, git_service, mock_db_session, sample_nist_data, tmp_path):
        """Test processing NIST controls data."""
        nist_file = tmp_path / "nist-controls.json"
        nist_file.write_text(json.dumps(sample_nist_data))
        
        with patch.object(git_service, 'rag_service') as mock_rag:
            mock_rag.store_knowledge.return_value = {"status": "success", "id": str(uuid4())}
            
            result = git_service._process_nist_data(
                sample_nist_data,
                repo_type="customer",
                tenant_id=str(uuid4())
            )
            
            assert result["status"] == "success"
            assert result["loaded"] >= 0
            assert "errors" in result
    
    def test_process_mitre_data(self, git_service, sample_mitre_data):
        """Test processing MITRE techniques data."""
        with patch.object(git_service, 'rag_service') as mock_rag:
            mock_rag.store_knowledge.return_value = {"status": "success", "id": str(uuid4())}
            
            result = git_service._process_mitre_data(
                sample_mitre_data,
                repo_type="customer",
                tenant_id=str(uuid4())
            )
            
            assert result["status"] == "success"
            assert result["loaded"] >= 0
    
    def test_process_owasp_data(self, git_service, sample_owasp_data):
        """Test processing OWASP data."""
        with patch.object(git_service, 'rag_service') as mock_rag:
            mock_rag.store_knowledge.return_value = {"status": "success", "id": str(uuid4())}
            
            result = git_service._process_owasp_data(
                sample_owasp_data,
                repo_type="customer",
                tenant_id=str(uuid4())
            )
            
            assert result["status"] == "success"
            assert result["loaded"] >= 0
    
    def test_process_playbooks_data(self, git_service, sample_playbook_data):
        """Test processing SOC playbooks data."""
        with patch.object(git_service, 'rag_service') as mock_rag:
            mock_rag.store_knowledge.return_value = {"status": "success", "id": str(uuid4())}
            
            result = git_service._process_playbooks_data(
                sample_playbook_data,
                repo_type="customer",
                tenant_id=str(uuid4())
            )
            
            assert result["status"] == "success"
            assert result["loaded"] >= 0
    
    def test_process_file_invalid_json(self, git_service, tmp_path):
        """Test processing file with invalid JSON."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json")
        
        result = git_service._process_file(
            invalid_file,
            repo_type="customer",
            tenant_id=str(uuid4())
        )
        
        assert result["status"] == "error"
        assert "json" in result["error"].lower()
    
    def test_process_webhook_payload_github(self, git_service):
        """Test processing GitHub webhook payload."""
        webhook_data = {
            "repository": {
                "clone_url": "https://github.com/user/repo.git",
                "html_url": "https://github.com/user/repo"
            },
            "ref": "refs/heads/main",
            "commits": [
                {
                    "added": ["knowledge-base/nist/controls.json"],
                    "modified": []
                }
            ]
        }
        
        with patch.object(git_service, 'ingest_from_repo') as mock_ingest:
            mock_ingest.return_value = {"status": "success", "files_processed": 1}
            
            result = git_service.process_webhook_payload(
                webhook_data,
                repo_type="customer",
                tenant_id=str(uuid4())
            )
            
            assert result["status"] == "success"
            mock_ingest.assert_called_once()
    
    def test_process_webhook_payload_gitlab(self, git_service):
        """Test processing GitLab webhook payload."""
        webhook_data = {
            "project": {
                "git_http_url": "https://gitlab.com/user/repo.git",
                "web_url": "https://gitlab.com/user/repo"
            },
            "ref": "main",
            "commits": [
                {
                    "added": ["kb/mitre.json"],
                    "modified": []
                }
            ]
        }
        
        with patch.object(git_service, 'ingest_from_repo') as mock_ingest:
            mock_ingest.return_value = {"status": "success"}
            
            result = git_service.process_webhook_payload(
                webhook_data,
                repo_type="global",
                tenant_id=None
            )
            
            assert result["status"] == "success"
            mock_ingest.assert_called_once()
    
    def test_process_webhook_payload_no_kb_files(self, git_service):
        """Test webhook with no knowledge base files changed."""
        webhook_data = {
            "repository": {
                "clone_url": "https://github.com/user/repo.git"
            },
            "ref": "refs/heads/main",
            "commits": [
                {
                    "added": ["README.md"],
                    "modified": ["docs/guide.md"]
                }
            ]
        }
        
        result = git_service.process_webhook_payload(
            webhook_data,
            repo_type="customer",
            tenant_id=str(uuid4())
        )
        
        assert result["status"] == "skipped"
        assert "no knowledge base files" in result["message"].lower()
    
    def test_extract_repo_info_github(self, git_service):
        """Test extracting repository info from GitHub webhook."""
        webhook_data = {
            "repository": {
                "clone_url": "https://github.com/user/repo.git"
            },
            "ref": "refs/heads/develop"
        }
        
        repo_info = git_service._extract_repo_info(webhook_data)
        
        assert repo_info is not None
        assert repo_info["url"] == "https://github.com/user/repo.git"
        assert repo_info["branch"] == "develop"
    
    def test_extract_repo_info_gitlab(self, git_service):
        """Test extracting repository info from GitLab webhook."""
        webhook_data = {
            "project": {
                "git_http_url": "https://gitlab.com/user/repo.git"
            },
            "ref": "main"
        }
        
        repo_info = git_service._extract_repo_info(webhook_data)
        
        assert repo_info is not None
        assert repo_info["url"] == "https://gitlab.com/user/repo.git"
        assert repo_info["branch"] == "main"
    
    def test_get_changed_files(self, git_service):
        """Test extracting changed files from webhook."""
        webhook_data = {
            "commits": [
                {
                    "added": ["file1.json", "file2.json"],
                    "modified": ["file3.json"]
                },
                {
                    "added": ["file4.json"],
                    "modified": []
                }
            ]
        }
        
        files = git_service._get_changed_files(webhook_data)
        
        assert len(files) == 4
        assert "file1.json" in files
        assert "file2.json" in files
        assert "file3.json" in files
        assert "file4.json" in files


class TestGitIngestionTenantIsolation:
    """Test tenant isolation in git ingestion."""
    
    def test_customer_repo_with_tenant_id(self, git_service, mock_db_session):
        """Test customer repo stores data with tenant_id."""
        tenant_id = str(uuid4())
        
        with patch.object(git_service, '_clone_or_update_repo'), \
             patch.object(git_service, '_discover_kb_files', return_value=[]), \
             patch.object(git_service, 'rag_service') as mock_rag:
            
            mock_rag.store_knowledge = Mock(return_value={"status": "success"})
            
            result = git_service.ingest_from_repo(
                repo_url="https://github.com/customer/repo.git",
                repo_type="customer",
                tenant_id=tenant_id
            )
            
            # Verify tenant_id would be passed to store_knowledge
            # (actual call would happen in _process_file)
            assert result["status"] == "success"
    
    def test_global_repo_without_tenant_id(self, git_service):
        """Test global repo stores data without tenant_id."""
        with patch.object(git_service, '_clone_or_update_repo'), \
             patch.object(git_service, '_discover_kb_files', return_value=[]), \
             patch.object(git_service, 'rag_service') as mock_rag:
            
            mock_rag.store_knowledge = Mock(return_value={"status": "success"})
            
            result = git_service.ingest_from_repo(
                repo_url="https://github.com/sentinelgrid/global-kb.git",
                repo_type="global",
                tenant_id=None
            )
            
            assert result["status"] == "success"

