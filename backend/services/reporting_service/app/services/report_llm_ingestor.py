"""
Report LLM Ingestor
Ingests compliance reports into vector DB for Q&A with strict tenant isolation
"""

import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import re

logger = logging.getLogger(__name__)

# Try importing PDF text extraction
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    logger.warning("PyPDF2 not available")
    PYPDF2_AVAILABLE = False


class ReportLLMIngestor:
    """Placeholder for report ingestion into the embedding service/pgvector."""
    
    def __init__(self, embedding_model=None):
        """
        Initialize LLM ingestor (vector path intentionally disabled until pgvector wiring is added).
        """
        self.embedding_model = embedding_model
        logger.info("ReportLLMIngestor initialized without vector DB client (pgvector path pending)")
    
    def ingest_report(
        self,
        report_id: UUID,
        tenant_id: UUID,
        realm_name: str,
        report_type: str,
        pdf_path: str,
        generated_at: datetime,
        db_session
    ) -> bool:
        """
        Ingest report into vector DB.
        
        Args:
            report_id: Report ID
            tenant_id: Tenant ID (for isolation)
            realm_name: Realm name (for isolation)
            report_type: Type of report
            pdf_path: Path to PDF file
            generated_at: Report generation timestamp
            db_session: Database session for storing references
        
        Returns:
            True if successful
        """
        logger.warning(
            "ReportLLMIngestor.ingest_report called but vector path is disabled. "
            "Implement embedding service + pgvector integration before enabling."
        )
        return False
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF file."""
        if not PYPDF2_AVAILABLE:
            logger.warning("PyPDF2 not available, cannot extract PDF text")
            return ""
        
        try:
            text = []
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text.append(page.extract_text())
            
            return "\n\n".join(text)
            
        except Exception as e:
            logger.error(f"Failed to extract PDF text: {e}")
            return ""
    
    def _chunk_report(self, text: str, max_chunk_size: int = 1000) -> List[str]:
        """
        Chunk report text into smaller pieces.
        
        Args:
            text: Full report text
            max_chunk_size: Maximum characters per chunk
            
        Returns:
            List of text chunks
        """
        # Split by sections (look for headers)
        sections = re.split(r'\n\n+', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for section in sections:
            section_length = len(section)
            
            # If adding this section would exceed max size, finalize current chunk
            if current_length + section_length > max_chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            
            # If single section is too large, split it by sentences
            if section_length > max_chunk_size:
                sentences = re.split(r'[.!?]\s+', section)
                for sentence in sentences:
                    if current_length + len(sentence) > max_chunk_size and current_chunk:
                        chunks.append("\n\n".join(current_chunk))
                        current_chunk = []
                        current_length = 0
                    current_chunk.append(sentence)
                    current_length += len(sentence)
            else:
                current_chunk.append(section)
                current_length += section_length
        
        # Add final chunk
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
        
        return chunks
    
    def delete_report(self, report_id: UUID, db_session):
        """
        Delete report from vector DB.
        
        Args:
            report_id: Report ID
            db_session: Database session
        """
        logger.info(
            "ReportLLMIngestor.delete_report called but vector path is disabled; nothing to delete."
        )


# Singleton
_llm_ingestor: Optional[ReportLLMIngestor] = None


def get_llm_ingestor() -> ReportLLMIngestor:
    """Get or create the global LLM ingestor instance."""
    global _llm_ingestor
    if _llm_ingestor is None:
        _llm_ingestor = ReportLLMIngestor()
    return _llm_ingestor
