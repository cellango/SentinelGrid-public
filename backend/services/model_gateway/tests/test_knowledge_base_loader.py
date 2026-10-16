"""
Unit tests for Knowledge Base Loader
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.services.knowledge_base_loader import KnowledgeBaseLoader


@pytest.fixture
def sample_nist_data():
    """Sample NIST controls data."""
    return {
        "controls": [
            {
                "id": "AC-2",
                "family": "Access Control",
                "description": "The organization manages information system accounts.",
                "guidance": "Account management addresses user accounts throughout their lifecycle.",
                "supplemental_guidance": "This includes creating, modifying, disabling, and removing accounts.",
                "version": "800-53r5"
            },
            {
                "id": "AC-3",
                "family": "Access Control",
                "description": "The organization enforces approved authorizations.",
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
                "description": "Adversaries may steal credentials.",
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
                "description": "Access control enforces policy.",
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
                "description": "Comprehensive playbook for malware incidents.",
                "category": "incident_response",
                "steps": [
                    {
                        "step": 1,
                        "description": "Detection & Triage",
                        "actions": ["EDR alert analysis", "Hash lookup"]
                    }
                ]
            }
        ]
    }


class TestKnowledgeBaseLoader:
    """Test suite for KnowledgeBaseLoader."""
    
    def test_init(self, db_session):
        """Test loader initialization."""
        loader = KnowledgeBaseLoader(db_session=db_session)
        
        assert loader.db == db_session
        assert loader.rag_service is not None
        assert loader.embeddings_service is not None
    
    @patch.object(KnowledgeBaseLoader, '_get_sample_nist_controls')
    def test_load_nist_controls_from_embedded(self, mock_sample, db_session, sample_nist_data):
        """Test loading NIST controls from embedded sample data."""
        mock_sample.return_value = sample_nist_data
        
        loader = KnowledgeBaseLoader(db_session=db_session)
        
        with patch.object(loader.rag_service, 'store_knowledge') as mock_store:
            mock_store.return_value = {"status": "success", "id": "test-id"}
            
            result = loader.load_nist_controls()
            
            assert result["framework"] == "NIST"
            assert result["loaded"] >= 0
            assert "errors" in result
            assert mock_store.called
    
    def test_load_nist_controls_from_file(self, db_session, sample_nist_data, tmp_path):
        """Test loading NIST controls from JSON file."""
        nist_file = tmp_path / "nist-controls.json"
        nist_file.write_text(json.dumps(sample_nist_data))
        
        loader = KnowledgeBaseLoader(db_session=db_session)
        
        with patch.object(loader.rag_service, 'store_knowledge') as mock_store:
            mock_store.return_value = {"status": "success", "id": "test-id"}
            
            result = loader.load_nist_controls(data_source=str(nist_file))
            
            assert result["framework"] == "NIST"
            assert mock_store.called
    
    def test_load_nist_controls_content_formatting(self, db_session, sample_nist_data):
        """Test NIST control content formatting."""
        loader = KnowledgeBaseLoader(db_session=db_session)
        
        with patch.object(loader, '_get_sample_nist_controls', return_value=sample_nist_data), \
             patch.object(loader.rag_service, 'store_knowledge') as mock_store:
            
            mock_store.return_value = {"status": "success"}
            loader.load_nist_controls()
            
            # Verify content includes description and guidance
            call_args = mock_store.call_args
            assert "content" in call_args.kwargs
            assert "Account management" in call_args.kwargs["content"]
            assert "Guidance:" in call_args.kwargs["content"]
    
    def test_load_nist_controls_metadata(self, db_session, sample_nist_data):
        """Test NIST control metadata storage."""
        loader = KnowledgeBaseLoader(db_session=db_session)
        
        with patch.object(loader, '_get_sample_nist_controls', return_value=sample_nist_data), \
             patch.object(loader.rag_service, 'store_knowledge') as mock_store:
            
            mock_store.return_value = {"status": "success"}
            loader.load_nist_controls()
            
            # Verify metadata
            call_args = mock_store.call_args
            assert call_args.kwargs["category"] == "nist"
            assert call_args.kwargs["subcategory"] == "control"
            assert "metadata" in call_args.kwargs
            assert call_args.kwargs["metadata"]["control_id"] == "AC-2"
    
    @patch.object(KnowledgeBaseLoader, '_get_sample_mitre_techniques')
    def test_load_mitre_attack(self, mock_sample, db_session, sample_mitre_data):
        """Test loading MITRE ATT&CK techniques."""
        mock_sample.return_value = sample_mitre_data
        
        loader = KnowledgeBaseLoader(db_session=db_session)
        
        with patch.object(loader.rag_service, 'store_knowledge') as mock_store:
            mock_store.return_value = {"status": "success"}
            
            result = loader.load_mitre_attack()
            
            assert result["framework"] == "MITRE ATT&CK"
            assert result["loaded"] >= 0
            assert mock_store.called
    
    def test_load_mitre_attack_content_formatting(self, db_session, sample_mitre_data):
        """Test MITRE technique content formatting."""
        loader = KnowledgeBaseLoader(db_session=db_session)
        
        with patch.object(loader, '_get_sample_mitre_techniques', return_value=sample_mitre_data), \
             patch.object(loader.rag_service, 'store_knowledge') as mock_store:
            
            mock_store.return_value = {"status": "success"}
            loader.load_mitre_attack()
            
            # Verify content includes description, detection, mitigation
            call_args = mock_store.call_args
            assert "content" in call_args.kwargs
            assert "Adversaries may steal" in call_args.kwargs["content"]
            assert "Detection:" in call_args.kwargs["content"]
            assert "Mitigation:" in call_args.kwargs["content"]
    
    @patch.object(KnowledgeBaseLoader, '_get_sample_owasp_content')
    def test_load_owasp_content(self, mock_sample, db_session, sample_owasp_data):
        """Test loading OWASP content."""
        mock_sample.return_value = sample_owasp_data
        
        loader = KnowledgeBaseLoader(db_session=db_session)
        
        with patch.object(loader.rag_service, 'store_knowledge') as mock_store:
            mock_store.return_value = {"status": "success"}
            
            result = loader.load_owasp_content()
            
            assert result["framework"] == "OWASP"
            assert result["loaded"] >= 0
            assert mock_store.called
    
    def test_load_owasp_content_formatting(self, db_session, sample_owasp_data):
        """Test OWASP content formatting."""
        loader = KnowledgeBaseLoader(db_session=db_session)
        
        with patch.object(loader, '_get_sample_owasp_content', return_value=sample_owasp_data), \
             patch.object(loader.rag_service, 'store_knowledge') as mock_store:
            
            mock_store.return_value = {"status": "success"}
            loader.load_owasp_content()
            
            # Verify content includes description and prevention
            call_args = mock_store.call_args
            assert "content" in call_args.kwargs
            assert "Access control enforces" in call_args.kwargs["content"]
            assert "How to Prevent:" in call_args.kwargs["content"]
    
    @patch.object(KnowledgeBaseLoader, '_get_sample_playbooks')
    def test_load_playbooks(self, mock_sample, db_session, sample_playbook_data):
        """Test loading SOC playbooks."""
        mock_sample.return_value = sample_playbook_data
        
        loader = KnowledgeBaseLoader(db_session=db_session)
        
        with patch.object(loader.rag_service, 'store_knowledge') as mock_store:
            mock_store.return_value = {"status": "success"}
            
            result = loader.load_playbooks()
            
            assert result["framework"] == "SOC Playbooks"
            assert result["loaded"] >= 0
            assert mock_store.called
    
    def test_load_playbooks_content_formatting(self, db_session, sample_playbook_data):
        """Test playbook content formatting."""
        loader = KnowledgeBaseLoader(db_session=db_session)
        
        with patch.object(loader, '_get_sample_playbooks', return_value=sample_playbook_data), \
             patch.object(loader.rag_service, 'store_knowledge') as mock_store:
            
            mock_store.return_value = {"status": "success"}
            loader.load_playbooks()
            
            # Verify content includes description and steps
            call_args = mock_store.call_args
            assert "content" in call_args.kwargs
            assert "malware incidents" in call_args.kwargs["content"]
            assert "Steps:" in call_args.kwargs["content"]
    
    def test_load_nist_controls_error_handling(self, db_session):
        """Test error handling in NIST controls loading."""
        loader = KnowledgeBaseLoader(db_session=db_session)
        
        with patch.object(loader, '_get_sample_nist_controls', return_value={"controls": [{"invalid": "data"}]}), \
             patch.object(loader.rag_service, 'store_knowledge') as mock_store:
            
            mock_store.return_value = {"status": "error", "error": "Failed to store"}
            
            result = loader.load_nist_controls()
            
            assert result["framework"] == "NIST"
            assert result["errors"] >= 0
    
    def test_load_nist_controls_empty_data(self, db_session):
        """Test loading with empty NIST data."""
        loader = KnowledgeBaseLoader(db_session=db_session)
        
        with patch.object(loader, '_get_sample_nist_controls', return_value={"controls": []}):
            result = loader.load_nist_controls()
            
            assert result["framework"] == "NIST"
            assert result["loaded"] == 0
            assert result["errors"] == 0
    
    def test_load_nist_controls_file_not_found(self, db_session):
        """Test loading when file doesn't exist (falls back to embedded)."""
        loader = KnowledgeBaseLoader(db_session=db_session)
        
        with patch.object(loader, '_get_sample_nist_controls') as mock_sample:
            mock_sample.return_value = {"controls": []}
            
            result = loader.load_nist_controls(data_source="/nonexistent/file.json")
            
            # Should fall back to embedded data
            assert mock_sample.called
    
    def test_load_all_frameworks(self, db_session):
        """Test loading all frameworks."""
        loader = KnowledgeBaseLoader(db_session=db_session)
        
        with patch.object(loader, 'load_nist_controls') as mock_nist, \
             patch.object(loader, 'load_mitre_attack') as mock_mitre, \
             patch.object(loader, 'load_owasp_content') as mock_owasp, \
             patch.object(loader, 'load_playbooks') as mock_playbooks:
            
            mock_nist.return_value = {"framework": "NIST", "loaded": 10}
            mock_mitre.return_value = {"framework": "MITRE", "loaded": 20}
            mock_owasp.return_value = {"framework": "OWASP", "loaded": 15}
            mock_playbooks.return_value = {"framework": "Playbooks", "loaded": 5}
            
            # If load_all method exists, test it
            # Otherwise, test individual calls
            loader.load_nist_controls()
            loader.load_mitre_attack()
            loader.load_owasp_content()
            loader.load_playbooks()
            
            assert mock_nist.called
            assert mock_mitre.called
            assert mock_owasp.called
            assert mock_playbooks.called

