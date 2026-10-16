"""
Unit tests for Embeddings Service
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from app.services.embeddings_service import EmbeddingsService, SENTENCE_TRANSFORMERS_AVAILABLE


class TestEmbeddingsService:
    """Test suite for EmbeddingsService."""
    
    def test_init_with_bge_m3(self):
        """Test service initialization with BGE-M3 model."""
        with patch('app.services.embeddings_service.SentenceTransformer') as mock_transformer:
            mock_model = Mock()
            mock_transformer.return_value = mock_model
            
            service = EmbeddingsService(model_name="BAAI/bge-m3")
            
            assert service.model_name == "BAAI/bge-m3"
            assert service.dimension == 1024
            mock_transformer.assert_called_once_with("BAAI/bge-m3")
    
    def test_init_with_minilm(self):
        """Test service initialization with all-MiniLM-L6-v2 model."""
        with patch('app.services.embeddings_service.SentenceTransformer') as mock_transformer:
            mock_model = Mock()
            mock_transformer.return_value = mock_model
            
            service = EmbeddingsService(model_name="all-MiniLM-L6-v2")
            
            assert service.model_name == "all-MiniLM-L6-v2"
            assert service.dimension == 384
            mock_transformer.assert_called_once_with("all-MiniLM-L6-v2")
    
    @patch('app.services.embeddings_service.SENTENCE_TRANSFORMERS_AVAILABLE', False)
    def test_init_without_sentence_transformers(self):
        """Test service initialization when sentence-transformers not available."""
        service = EmbeddingsService()
        
        assert service.model is None
        assert service.dimension == 1024  # Default dimension
    
    @patch('app.services.embeddings_service.SentenceTransformer')
    def test_load_model_success(self, mock_transformer):
        """Test successful model loading."""
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        
        service = EmbeddingsService()
        
        assert service.model == mock_model
        mock_transformer.assert_called_once()
    
    @patch('app.services.embeddings_service.SentenceTransformer')
    def test_load_model_failure(self, mock_transformer):
        """Test model loading failure."""
        mock_transformer.side_effect = Exception("Model not found")
        
        with pytest.raises(Exception):
            EmbeddingsService()
    
    @patch('app.services.embeddings_service.SentenceTransformer')
    def test_generate_embedding_single_text(self, mock_transformer):
        """Test generating embedding for single text."""
        mock_model = Mock()
        # Mock numpy array for embedding
        mock_embedding = np.array([0.1] * 1024)
        mock_model.encode.return_value = mock_embedding
        mock_transformer.return_value = mock_model
        
        service = EmbeddingsService()
        result = service.generate_embedding("This is a test sentence.")
        
        assert isinstance(result, list)
        assert len(result) == 1024
        assert all(isinstance(x, float) for x in result)
        mock_model.encode.assert_called_once()
    
    @patch('app.services.embeddings_service.SentenceTransformer')
    def test_generate_embedding_batch_texts(self, mock_transformer):
        """Test generating embeddings for batch of texts."""
        mock_model = Mock()
        # Mock batch embeddings
        mock_embeddings = np.array([[0.1] * 1024, [0.2] * 1024])
        mock_model.encode.return_value = mock_embeddings
        mock_transformer.return_value = mock_model
        
        service = EmbeddingsService()
        texts = ["First sentence.", "Second sentence."]
        result = service.generate_embedding(texts)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert len(result[0]) == 1024
        assert len(result[1]) == 1024
    
    @patch('app.services.embeddings_service.SentenceTransformer')
    def test_generate_embedding_normalized(self, mock_transformer):
        """Test that embeddings are normalized."""
        mock_model = Mock()
        # Create unnormalized embedding
        mock_embedding = np.array([1.0, 2.0, 3.0] * 341 + [1.0])[:1024]
        mock_model.encode.return_value = mock_embedding
        mock_transformer.return_value = mock_model
        
        service = EmbeddingsService()
        result = service.generate_embedding("Test")
        
        # Verify normalize_embeddings=True was passed
        call_kwargs = mock_model.encode.call_args[1]
        assert call_kwargs.get("normalize_embeddings") is True
    
    @patch('app.services.embeddings_service.SentenceTransformer')
    def test_generate_embedding_convert_to_numpy(self, mock_transformer):
        """Test that embeddings are converted to numpy."""
        mock_model = Mock()
        mock_embedding = np.array([0.1] * 1024)
        mock_model.encode.return_value = mock_embedding
        mock_transformer.return_value = mock_model
        
        service = EmbeddingsService()
        service.generate_embedding("Test")
        
        # Verify convert_to_numpy=True was passed
        call_kwargs = mock_model.encode.call_args[1]
        assert call_kwargs.get("convert_to_numpy") is True
    
    @patch('app.services.embeddings_service.SENTENCE_TRANSFORMERS_AVAILABLE', False)
    def test_generate_embedding_without_model(self):
        """Test embedding generation when model not available."""
        service = EmbeddingsService()
        
        result = service.generate_embedding("Test")
        
        assert result == []
    
    @patch('app.services.embeddings_service.SentenceTransformer')
    def test_generate_embedding_exception_handling(self, mock_transformer):
        """Test error handling during embedding generation."""
        mock_model = Mock()
        mock_model.encode.side_effect = Exception("Encoding failed")
        mock_transformer.return_value = mock_model
        
        service = EmbeddingsService()
        result = service.generate_embedding("Test")
        
        assert result == []
    
    @patch('app.services.embeddings_service.SentenceTransformer')
    def test_generate_embedding_batch_exception(self, mock_transformer):
        """Test error handling for batch embedding generation."""
        mock_model = Mock()
        mock_model.encode.side_effect = Exception("Batch encoding failed")
        mock_transformer.return_value = mock_model
        
        service = EmbeddingsService()
        result = service.generate_embedding(["Text 1", "Text 2"])
        
        assert result == [[]]
    
    def test_embedding_dimension_property(self):
        """Test embedding_dimension property."""
        with patch('app.services.embeddings_service.SentenceTransformer'):
            service = EmbeddingsService(model_name="BAAI/bge-m3")
            assert service.embedding_dimension == 1024
            
            service2 = EmbeddingsService(model_name="all-MiniLM-L6-v2")
            assert service2.embedding_dimension == 384
    
    @patch('app.services.embeddings_service.SentenceTransformer')
    def test_generate_embedding_empty_string(self, mock_transformer):
        """Test embedding generation for empty string."""
        mock_model = Mock()
        mock_embedding = np.array([0.0] * 1024)
        mock_model.encode.return_value = mock_embedding
        mock_transformer.return_value = mock_model
        
        service = EmbeddingsService()
        result = service.generate_embedding("")
        
        assert isinstance(result, list)
        assert len(result) == 1024
    
    @patch('app.services.embeddings_service.SentenceTransformer')
    def test_generate_embedding_long_text(self, mock_transformer):
        """Test embedding generation for long text."""
        mock_model = Mock()
        mock_embedding = np.array([0.1] * 1024)
        mock_model.encode.return_value = mock_embedding
        mock_transformer.return_value = mock_model
        
        service = EmbeddingsService()
        long_text = "This is a very long text. " * 100
        result = service.generate_embedding(long_text)
        
        assert isinstance(result, list)
        assert len(result) == 1024
        mock_model.encode.assert_called_once()

