"""
Report Q&A Service
Allows users to query compliance reports using natural language with STRICT tenant isolation
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from dataclasses import dataclass

from app.services.audit_client import AuditClient

logger = logging.getLogger(__name__)


@dataclass
class UserContext:
    """User context for tenant isolation."""
    user_id: str
    tenant_id: UUID
    realm: str
    email: Optional[str] = None


class ReportQAService:
    """
    Report Q&A service placeholder. Vector search is disabled until pgvector
    integration is wired through the embedding service.
    """
    
    def __init__(
        self,
        embedding_model=None,
        llm_client=None
    ):
        """
        Initialize Report Q&A service.
        """
        self.qdrant_client = None
        # Initialize embedding model
        if embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            except ImportError:
                logger.warning("sentence-transformers not available")
                self.embedding_model = None
        else:
            self.embedding_model = embedding_model
        
        # LLM client (placeholder - should be actual LLM service)
        self.llm_client = llm_client
        self.audit_client = AuditClient()
    
    def query_reports(
        self,
        user_context: UserContext,
        query: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Query compliance reports using natural language.

        Returns a “service unavailable” payload until pgvector integration is available.
        """
        result = {
            "answer": "Report Q&A service is currently unavailable (pgvector path pending).",
            "sources": [],
            "error": "Service unavailable"
        }
        try:
            payload = {
                "tenant_id": str(user_context.tenant_id),
                "realm_name": user_context.realm,
                "action": "report_qa",
                "action_category": "ai",
                "actor_user_id": user_context.user_id,
                "actor_email": user_context.email,
                "metadata": {
                    "query": query[:500],
                    "sources": [],
                },
            }
            import asyncio
            asyncio.create_task(self.audit_client.log_ai_event(payload))
        except Exception as e:
            logger.warning(f"Failed to enqueue AI audit log: {e}")
        return result
    
    def _generate_answer(self, query: str, context_chunks: List[str]) -> str:
        """
        Generate answer using LLM based on context.
        
        Args:
            query: User query
            context_chunks: Relevant report chunks
            
        Returns:
            Generated answer
        """
        # Build prompt
        context = "\n\n".join([
            f"[Source {i+1}]\n{chunk}"
            for i, chunk in enumerate(context_chunks)
        ])
        
        prompt = f"""You are a compliance analyst assistant. Answer the user's question based ONLY on the following compliance report excerpts.

Context from compliance reports:
{context}

User question: {query}

Instructions:
- Answer based ONLY on the provided context
- If the information is not in the context, say "I don't have that information in the reports."
- Be specific and cite relevant metrics or findings
- Use professional language appropriate for compliance reporting

Answer:"""
        
        # Generate answer using LLM
        if self.llm_client:
            try:
                answer = self.llm_client.generate(prompt, max_tokens=500)
                return answer
            except Exception as e:
                logger.error(f"LLM generation failed: {e}")
                return "Unable to generate answer. Please try rephrasing your question."
        else:
            # Fallback: simple keyword-based response
            return self._simple_answer(query, context_chunks)
    
    def _simple_answer(self, query: str, context_chunks: List[str]) -> str:
        """
        Simple fallback answer when LLM not available.
        
        Args:
            query: User query
            context_chunks: Context chunks
            
        Returns:
            Simple extracted answer
        """
        # Find most relevant chunk (already sorted by relevance)
        if not context_chunks:
            return "No relevant information found."
        
        # Return first chunk as context
        answer = f"Based on your compliance reports:\n\n{context_chunks[0]}"
        
        if len(context_chunks) > 1:
            answer += f"\n\n(Found {len(context_chunks)} relevant sections in your reports)"
        
        return answer
    
    
    def get_available_reports(self, user_context: UserContext) -> List[Dict[str, Any]]:
        """
        Get list of reports available for querying (tenant-scoped).
        
        Args:
            user_context: User context with tenant_id and realm
            
        Returns:
            List of available reports
        """
        if not self.qdrant_client:
            return []
        
        try:
            # This would query the database for reports with llm_ingested=true
            # For now, return empty list as placeholder
            return []
            
        except Exception as e:
            logger.error(f"Failed to get available reports: {e}")
            return []


# Singleton
_report_qa_service: Optional[ReportQAService] = None


def get_report_qa_service() -> ReportQAService:
    """Get or create the global Report Q&A service instance."""
    global _report_qa_service
    if _report_qa_service is None:
        _report_qa_service = ReportQAService()
    return _report_qa_service
