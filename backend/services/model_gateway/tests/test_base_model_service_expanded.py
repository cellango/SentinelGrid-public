"""
Expanded tests for Base Model Service
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os


@pytest.fixture
def base_model_service():
    """Create BaseModelService instance."""
    from app.services.base_model_service import BaseModelService
    return BaseModelService()


class TestBaseModelServiceExpanded:
    """Expanded test suite for BaseModelService."""
    
    def test_load_model_llama_cpp(self, base_model_service):
        """Test loading model with llama.cpp runtime."""
        with patch.dict(os.environ, {"LLM_RUNTIME": "llama_cpp"}), \
             patch('app.services.base_model_service.Llama') as mock_llama:
            
            mock_model = Mock()
            mock_llama.return_value = mock_model
            
            model = base_model_service.load_model(
                model_path="/path/to/model.gguf",
                runtime="llama_cpp"
            )
            
            assert model is not None
            mock_llama.assert_called_once()
    
    def test_load_model_transformers(self, base_model_service):
        """Test loading model with transformers runtime."""
        with patch.dict(os.environ, {"LLM_RUNTIME": "transformers"}), \
             patch('app.services.base_model_service.AutoModelForCausalLM') as mock_model_class, \
             patch('app.services.base_model_service.AutoTokenizer') as mock_tokenizer_class:
            
            mock_model = Mock()
            mock_tokenizer = Mock()
            mock_model_class.from_pretrained.return_value = mock_model
            mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
            
            result = base_model_service.load_model(
                model_path="BAAI/cybergpt-7b",
                runtime="transformers"
            )
            
            assert result is not None
            mock_model_class.from_pretrained.assert_called_once()
    
    def test_generate_text(self, base_model_service):
        """Test text generation with base model."""
        mock_model = Mock()
        mock_model.return_value = {
            "choices": [{"text": "Generated text"}]
        }
        
        with patch.object(base_model_service, 'model', mock_model):
            result = base_model_service.generate("Test prompt", max_tokens=100)
            
            assert result is not None
            assert isinstance(result, (str, dict))
    
    def test_model_not_loaded_error(self, base_model_service):
        """Test error handling when model not loaded."""
        base_model_service.model = None
        
        with pytest.raises(Exception) or base_model_service.generate("test") == None:
            result = base_model_service.generate("test")
            # Should handle gracefully
            assert result is None or "error" in str(result).lower()
    
    def test_model_loading_error_handling(self, base_model_service):
        """Test error handling during model loading."""
        with patch('app.services.base_model_service.Llama', side_effect=Exception("Model not found")):
            with pytest.raises(Exception):
                base_model_service.load_model(
                    model_path="/invalid/path",
                    runtime="llama_cpp"
                )
    
    def test_model_caching(self, base_model_service):
        """Test that model is cached after loading."""
        with patch('app.services.base_model_service.Llama') as mock_llama:
            mock_model = Mock()
            mock_llama.return_value = mock_model
            
            # Load model
            model1 = base_model_service.load_model("/path/to/model", "llama_cpp")
            
            # Load again (should return cached)
            model2 = base_model_service.load_model("/path/to/model", "llama_cpp")
            
            # Should only call Llama once (cached)
            assert mock_llama.call_count == 1
            assert model1 == model2

