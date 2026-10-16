"""
Embeddings Service
Generates embeddings using BGE-M3 model
"""

import logging
from typing import List, Union
import os
import signal

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available. Install with: pip install sentence-transformers")


class EmbeddingsService:
    """Service for generating embeddings using sentence-transformers."""
    
    def __init__(self, model_name: str | None = None):
        """
        Initialize embeddings service.
        
        Args:
            model_name: Model name (default from EMBEDDING_MODEL_NAME env or BAAI/bge-m3)
        """
        env_model = os.getenv("EMBEDDING_MODEL_NAME") or os.getenv("EMBEDDINGS_MODEL")
        self.model_name = model_name or env_model or "all-MiniLM-L6-v2"
        self.model = None
        name_lower = (self.model_name or "").lower()
        self.dimension = 1024 if "bge-m3" in name_lower else 384
        self._load_model()
    
    def _load_model(self):
        """Loads the sentence transformer model."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning("sentence-transformers not available. Embeddings will not work.")
            return
        
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Successfully loaded embedding model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model {self.model_name}: {e}")
            raise
    
    def generate_embedding(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generates embeddings for text or list of texts.
        
        Args:
            text: Single text string or list of text strings
            
        Returns:
            For single text: List of floats (embedding vector)
            For list of texts: List of embedding vectors
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE or not self.model:
            logger.error("Embedding model not available")
            return [] if isinstance(text, str) else [[]]

        try:
            # Handle single string or list
            is_single = isinstance(text, str)
            texts = [text] if is_single else text
            
            # Generate embeddings
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True  # Normalize for cosine similarity
            )
            
            # Convert to list
            if is_single:
                return embeddings[0].tolist()
            else:
                return embeddings.tolist()
                
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return [] if isinstance(text, str) else [[]]
    
    @property
    def embedding_dimension(self) -> int:
        """Return the dimension of embeddings."""
        return self.dimension
