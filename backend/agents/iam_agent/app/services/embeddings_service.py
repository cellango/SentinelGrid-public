"""
Embeddings Service for IAM RAG
Generates embeddings for IAM data to enable RAG queries
"""

import logging
from typing import List, Dict, Any, Optional
import numpy as np
# Optional import - sentence-transformers has dependency conflicts
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """Service for generating embeddings for RAG."""
    
    def __init__(self):
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning("sentence-transformers not available, embeddings will be disabled")
            self.model = None
            self.embedding_dim = 384  # Default for all-MiniLM-L6-v2
            return
        
        # Use lightweight model by default (all-MiniLM-L6-v2)
        # Can be upgraded to BGE-M3 later for better quality
        model_name = getattr(settings, 'EMBEDDINGS_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
        
        try:
            self.model = SentenceTransformer(model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Loaded embeddings model: {model_name} (dim={self.embedding_dim})")
        except Exception as e:
            logger.error(f"Failed to load embeddings model: {e}")
            self.model = None
            self.embedding_dim = 384  # Default for all-MiniLM-L6-v2
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text."""
        if not self.model or not text:
            return None
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts (more efficient)."""
        if not self.model or not texts:
            return [None] * len(texts)
        
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            return [None] * len(texts)
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings."""
        return self.embedding_dim

