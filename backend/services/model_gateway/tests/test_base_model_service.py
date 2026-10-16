"""
Tests for Base Model Service.
"""

import pytest
import os
import sys
import types
from unittest.mock import Mock, patch, MagicMock
from app.services.base_model_service import BaseModelService


def test_base_model_service_initialization():
    """Test BaseModelService initialization."""
    service = BaseModelService()
    
    assert service.base_model_name is not None
    assert service.model_path is not None
    assert service.model_loaded is False
    assert service.model is None


def test_load_base_model_llama_cpp_not_installed():
    """Test model loading when llama.cpp is not installed."""
    service = BaseModelService()
    
    with patch.dict(os.environ, {"LLM_RUNTIME": "llama_cpp"}):
        with patch.dict(sys.modules, {"llama_cpp": None}):
            service.load_base_model()
            
            # Should fall back to mock
            assert service.model_loaded is True
            assert service.model is None  # Mock model


def test_load_base_model_file_not_found():
    """Test model loading when file doesn't exist."""
    service = BaseModelService()
    fake_llama_module = types.ModuleType("llama_cpp")
    fake_llama_module.Llama = Mock()
    
    with patch.dict(os.environ, {"LLM_RUNTIME": "llama_cpp", "BASE_MODEL_PATH": "/nonexistent"}):
        with patch.dict(sys.modules, {"llama_cpp": fake_llama_module}):
            from pathlib import Path
            with patch.object(Path, "exists", return_value=False):
                service.load_base_model()
                
                # Should fall back to mock
                assert service.model_loaded is True


def test_generate_with_mock_model():
    """Test text generation with mock model."""
    service = BaseModelService()
    service.model_loaded = True
    service.model = None  # Mock model

    with patch.dict(os.environ, {"LLM_RUNTIME": "llama_cpp"}):
        result = service.generate("What is cybersecurity?")
    
    assert "text" in result
    assert "tokens" in result
    assert "finish_reason" in result
    assert "Mock" in result["text"] or "placeholder" in result["text"].lower()


def test_generate_with_llama_cpp():
    """Test text generation with llama.cpp."""
    # Mock Llama instance
    mock_llama = MagicMock()
    mock_llama.return_value = {
        "choices": [{"text": "Cybersecurity is...", "finish_reason": "stop"}],
        "usage": {"completion_tokens": 10}
    }
    fake_llama_module = types.ModuleType("llama_cpp")
    fake_llama_module.Llama = MagicMock(return_value=mock_llama)
    
    service = BaseModelService()
    
    with patch.dict(os.environ, {"LLM_RUNTIME": "llama_cpp"}):
        with patch.dict(sys.modules, {"llama_cpp": fake_llama_module}):
            with patch("pathlib.Path.exists", return_value=True):
                service.load_base_model()
                service.model = mock_llama

                result = service.generate("What is cybersecurity?")

                assert result["text"] == "Cybersecurity is..."
                assert result["tokens"] == 10
                assert result["finish_reason"] == "stop"


def test_model_service_error_handling():
    """Test error handling in model service."""
    service = BaseModelService()
    service.model_loaded = True
    service.model = None
    
    # Generate should not raise exception
    result = service.generate("Test prompt")
    assert "text" in result


@pytest.mark.skip(reason="Requires actual model file")
def test_load_real_model():
    """Test loading a real model file."""
    model_path = os.getenv("TEST_MODEL_PATH")
    if not model_path:
        pytest.skip("TEST_MODEL_PATH not set")
    
    service = BaseModelService()
    service.model_path = model_path
    
    service.load_base_model()
    
    assert service.model_loaded is True
