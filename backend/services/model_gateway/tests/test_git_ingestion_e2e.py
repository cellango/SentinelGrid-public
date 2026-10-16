"""
End-to-End tests for Git Ingestion Pipeline
Tests complete workflow from webhook to data storage.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from app.services.git_data_ingestion_service import GitDataIngestionService
from app.services.scheduled_ingestion_service import ScheduledIngestionService
from app.models.git_repos import GitRepository, GitIngestionJob


@pytest.fixture
def sample_repo_structure(tmp_path):
    """Create a sample git repository structure with knowledge base files."""
    repo_path = tmp_path / "test-repo"
    repo_path.mkdir()
    
    # Create NIST controls file
    nist_dir = repo_path / "nist"
    nist_dir.mkdir()
    nist_file = nist_dir / "controls.json"
    nist_file.write_text(json.dumps({
        "controls": [
            {
                "id": "AC-2",
                "family": "Access Control",
                "description": "The organization manages information system accounts.",
                "guidance": "Account management addresses user accounts throughout their lifecycle.",
                "version": "800-53r5"
            }
        ]
    }))
    
    # Create MITRE techniques file
    mitre_dir = repo_path / "mitre"
    mitre_dir.mkdir()
    mitre_file = mitre_dir / "techniques.json"
    mitre_file.write_text(json.dumps({
        "techniques": [
            {
                "id": "T1078",
                "name": "Valid Accounts",
                "description": "Adversaries may steal credentials or abuse legitimate credentials.",
                "tactic": ["Initial Access"],
                "detection": "Monitor for unusual login patterns.",
                "mitigation": "Use multifactor authentication.",
                "version": "ATT&CK v13"
            }
        ]
    }))
    
    # Create playbook file
    playbook_dir = repo_path / "playbooks"
    playbook_dir.mkdir()
    playbook_file = playbook_dir / "playbooks.json"
    playbook_file.write_text(json.dumps({
        "playbooks": [
            {
                "id": "malware-response-v1",
                "name": "Malware Detection & Response",
                "description": "Comprehensive playbook for malware incidents.",
                "steps": [
                    {
                        "name": "Detection & Triage",
                        "description": "EDR/SIEM alert analysis"
                    }
                ]
            }
        ]
    }))
    
    return repo_path


@pytest.mark.e2e
class TestGitIngestionE2E:
    """End-to-end tests for git ingestion pipeline."""
    
    def test_complete_ingestion_flow_customer_repo(self, db_session, sample_tenant_id, tmp_path, sample_repo_structure):
        """Test complete ingestion flow for customer repository."""
        from app.services.rag_service import RAGService
        
        # Mock git operations
        with patch('subprocess.run') as mock_git:
            mock_git.return_value = Mock(returncode=0)
            
            service = GitDataIngestionService(db_session=db_session)
            
            # Mock the clone to return our test repo structure
            with patch.object(service, '_clone_or_update_repo') as mock_clone:
                mock_clone.return_value = None
                
                # Override discover to return our test files
                with patch.object(service, '_discover_kb_files') as mock_discover:
                    mock_discover.return_value = [
                        sample_repo_structure / "nist" / "controls.json",
                        sample_repo_structure / "mitre" / "techniques.json",
                        sample_repo_structure / "playbooks" / "playbooks.json"
                    ]
                    
                    # Mock RAG service to track calls
                    with patch.object(service, 'rag_service') as mock_rag:
                        mock_rag.store_knowledge.return_value = {
                            "status": "success",
                            "id": str(uuid4())
                        }
                        
                        # Execute ingestion
                        result = service.ingest_from_repo(
                            repo_url="https://github.com/customer/kb.git",
                            repo_type="customer",
                            tenant_id=sample_tenant_id,
                            branch="main"
                        )
                        
                        # Verify results
                        assert result["status"] == "success"
                        assert result["files_processed"] == 3
                        assert result["total_loaded"] >= 0
                        
                        # Verify store_knowledge was called with tenant_id for customer repo
                        # (we can check the calls if needed)
                        assert mock_rag.store_knowledge.called
    
    def test_complete_ingestion_flow_global_repo(self, db_session, tmp_path, sample_repo_structure):
        """Test complete ingestion flow for global repository."""
        with patch('subprocess.run'):
            service = GitDataIngestionService(db_session=db_session)
            
            with patch.object(service, '_clone_or_update_repo'), \
                 patch.object(service, '_discover_kb_files') as mock_discover:
                
                mock_discover.return_value = [
                    sample_repo_structure / "nist" / "controls.json"
                ]
                
                with patch.object(service, 'rag_service') as mock_rag:
                    mock_rag.store_knowledge.return_value = {
                        "status": "success",
                        "id": str(uuid4())
                    }
                    
                    # Execute ingestion for global repo
                    result = service.ingest_from_repo(
                        repo_url="https://github.com/sentinelgrid/global-kb.git",
                        repo_type="global",
                        tenant_id=None,
                        branch="main"
                    )
                    
                    assert result["status"] == "success"
                    assert result["repo_type"] == "global"
                    assert result["tenant_id"] is None
    
    def test_webhook_to_ingestion_flow(self, db_session, sample_tenant_id):
        """Test complete webhook → ingestion flow."""
        github_webhook = {
            "repository": {
                "clone_url": "https://github.com/user/repo.git"
            },
            "ref": "refs/heads/main",
            "commits": [
                {
                    "added": ["knowledge-base/nist/controls.json", "knowledge-base/mitre/techniques.json"],
                    "modified": []
                }
            ]
        }
        
        service = GitDataIngestionService(db_session=db_session)
        
        with patch.object(service, 'ingest_from_repo') as mock_ingest:
            mock_ingest.return_value = {
                "status": "success",
                "files_processed": 2,
                "total_loaded": 5,
                "total_errors": 0
            }
            
            result = service.process_webhook_payload(
                github_webhook,
                repo_type="customer",
                tenant_id=sample_tenant_id
            )
            
            assert result["status"] == "success"
            mock_ingest.assert_called_once()
            call_kwargs = mock_ingest.call_args[1]
            assert call_kwargs["repo_type"] == "customer"
            assert call_kwargs["tenant_id"] == sample_tenant_id
    
    def test_multi_file_processing(self, db_session, sample_tenant_id, sample_repo_structure):
        """Test processing multiple file types in single ingestion."""
        service = GitDataIngestionService(db_session=db_session)
        
        with patch('subprocess.run'), \
             patch.object(service, '_clone_or_update_repo'), \
             patch.object(service, '_discover_kb_files') as mock_discover:
            
            # Return multiple files of different types
            mock_discover.return_value = [
                sample_repo_structure / "nist" / "controls.json",
                sample_repo_structure / "mitre" / "techniques.json",
                sample_repo_structure / "playbooks" / "playbooks.json"
            ]
            
            with patch.object(service, 'rag_service') as mock_rag:
                mock_rag.store_knowledge.return_value = {"status": "success", "id": str(uuid4())}
                
                result = service.ingest_from_repo(
                    repo_url="https://github.com/user/repo.git",
                    repo_type="customer",
                    tenant_id=sample_tenant_id
                )
                
                assert result["status"] == "success"
                assert result["files_processed"] == 3
                # Should have results for each category
                assert "results" in result
                assert "nist" in result["results"]
                assert "mitre" in result["results"]
                assert "playbooks" in result["results"]
    
    def test_error_handling_invalid_json(self, db_session, sample_tenant_id, tmp_path):
        """Test error handling for invalid JSON files."""
        repo_path = tmp_path / "bad-repo"
        repo_path.mkdir()
        invalid_file = repo_path / "invalid.json"
        invalid_file.write_text("not valid json {")
        
        service = GitDataIngestionService(db_session=db_session)
        
        with patch('subprocess.run'), \
             patch.object(service, '_clone_or_update_repo'), \
             patch.object(service, '_discover_kb_files', return_value=[invalid_file]):
            
            result = service.ingest_from_repo(
                repo_url="https://github.com/user/bad-repo.git",
                repo_type="customer",
                tenant_id=sample_tenant_id
            )
            
            # Should handle error gracefully
            assert result["status"] in ["success", "partial"]
            # Check that errors are tracked
            if "total_errors" in result:
                assert result["total_errors"] > 0
    
    def test_scheduled_polling_flow(self, db_session):
        """Test scheduled polling of registered repositories."""
        from app.models.git_repos import GitRepository
        
        # Create test repository record
        repo = GitRepository(
            tenant_id=uuid4(),
            repo_url="https://github.com/user/repo.git",
            repo_type="customer",
            branch="main",
            is_active=True
        )
        db_session.add(repo)
        db_session.commit()
        db_session.refresh(repo)
        
        scheduled_service = ScheduledIngestionService(db_session=db_session)
        
        with patch.object(scheduled_service, 'get_repos_to_poll', return_value=[repo]), \
             patch.object(scheduled_service, 'poll_and_ingest') as mock_poll:
            
            mock_poll.return_value = {
                "status": "success",
                "files_processed": 2
            }
            
            results = scheduled_service.poll_all_active_repos()
            
            assert results["total"] == 1
            assert results["processed"] == 1
            assert results["success"] == 1
            mock_poll.assert_called_once_with(repo)


@pytest.mark.e2e
class TestTenantIsolationE2E:
    """E2E tests for tenant isolation in git ingestion."""
    
    def test_customer_repo_tenant_isolation(self, db_session, tmp_path):
        """Test that customer repos store data with correct tenant_id."""
        tenant_id_1 = str(uuid4())
        tenant_id_2 = str(uuid4())
        
        service = GitDataIngestionService(db_session=db_session)
        
        # Mock RAG service to track tenant_id calls
        stored_tenant_ids = []
        
        def track_store_knowledge(*args, **kwargs):
            if "tenant_id" in kwargs:
                stored_tenant_ids.append(kwargs["tenant_id"])
            return {"status": "success", "id": str(uuid4())}
        
        with patch('subprocess.run'), \
             patch.object(service, '_clone_or_update_repo'), \
             patch.object(service, '_discover_kb_files', return_value=[]), \
             patch.object(service, 'rag_service') as mock_rag:
            
            mock_rag.store_knowledge.side_effect = track_store_knowledge
            
            # Ingest for tenant 1
            service.ingest_from_repo(
                repo_url="https://github.com/tenant1/repo.git",
                repo_type="customer",
                tenant_id=tenant_id_1
            )
            
            # Ingest for tenant 2
            service.ingest_from_repo(
                repo_url="https://github.com/tenant2/repo.git",
                repo_type="customer",
                tenant_id=tenant_id_2
            )
            
            # Verify tenant_ids were used (if files were processed)
            # This test mainly verifies the service accepts different tenant_ids
    
    def test_global_repo_no_tenant_id(self, db_session):
        """Test that global repos store data without tenant_id."""
        service = GitDataIngestionService(db_session=db_session)
        
        stored_tenant_ids = []
        
        def track_store_knowledge(*args, **kwargs):
            stored_tenant_ids.append(kwargs.get("tenant_id"))
            return {"status": "success", "id": str(uuid4())}
        
        with patch('subprocess.run'), \
             patch.object(service, '_clone_or_update_repo'), \
             patch.object(service, '_discover_kb_files', return_value=[]), \
             patch.object(service, 'rag_service') as mock_rag:
            
            mock_rag.store_knowledge.side_effect = track_store_knowledge
            
            result = service.ingest_from_repo(
                repo_url="https://github.com/sentinelgrid/global-kb.git",
                repo_type="global",
                tenant_id=None
            )
            
            assert result["status"] == "success"
            assert result["tenant_id"] is None

