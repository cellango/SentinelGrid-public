"""
RAG Service
Retrieval Augmented Generation service for cybersecurity knowledge base
"""

import logging
import os
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, text, cast, func
import sqlalchemy
from pgvector.sqlalchemy import Vector

from app.models.knowledge_base import CybersecurityKnowledgeBase
from app.services.embeddings_service import EmbeddingsService

logger = logging.getLogger(__name__)


class RAGService:
    """Service for RAG retrieval from cybersecurity knowledge base."""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session
        # Prefer a KB embedding model configurable via env; default to MiniLM (384-d)
        kb_model = os.getenv("KB_EMBEDDING_MODEL") or os.getenv("EMBEDDING_MODEL_NAME") or "all-MiniLM-L6-v2"
        self.embeddings_service = EmbeddingsService(model_name=kb_model)
    
    def search(
        self,
        query: str,
        tenant_id: Optional[str] = None,
        category: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search knowledge base using vector similarity.
        
        Args:
            query: Search query text
            tenant_id: Tenant ID (for tenant-specific + shared knowledge)
            category: Optional category filter (nist, mitre, owasp, etc.)
            top_k: Number of results to return
            
        Returns:
            List of relevant knowledge base entries
        """
        if not self.db:
            logger.warning("Database session not available for RAG search")
            return []

        if not tenant_id:
            logger.warning("RAG search blocked: tenant_id is required for isolation")
            return []
        
        try:
            # Generate embedding for query
            query_embedding = self.embeddings_service.generate_embedding(query)
            
            if not query_embedding or len(query_embedding) == 0:
                logger.warning("Failed to generate query embedding")
                return []
            
            embedding_str = '[' + ','.join(str(float(x)) for x in query_embedding) + ']'
            
            # Raw SQL for vector search to avoid SQLAlchemy/vector type quirks
            tenant_clause = "tenant_id IS NULL"
            params = {"query_vec": embedding_str, "top_k": top_k}
            
            if tenant_id:
                tenant_clause = "(tenant_id IS NULL OR tenant_id = :tenant_id)"
                params["tenant_id"] = tenant_id
            
            category_clause = ""
            if category:
                category_clause = " AND category = :category"
                params["category"] = category
            
            sql = text(f"""
                SELECT 
                    id, category, subcategory, title, content, "metadata", source_url, framework_version,
                    1 - (embedding <=> CAST(:query_vec AS vector)) AS similarity
                FROM cybersecurity_knowledge_base
                WHERE {tenant_clause}{category_clause}
                ORDER BY similarity DESC
                LIMIT :top_k
            """)
            
            results = self.db.execute(sql, params).mappings().all()
            
            # Format results
            formatted_results = []
            for row in results:
                formatted_results.append({
                    "id": str(row.get("id")),
                    "category": row.get("category"),
                    "subcategory": row.get("subcategory"),
                    "title": row.get("title"),
                    "content": row.get("content"),
                    "metadata": row.get("metadata"),
                    "source_url": row.get("source_url"),
                    "similarity": float(row.get("similarity") or 0.0),
                    "framework_version": row.get("framework_version")
                })
            
            logger.info(f"RAG search returned {len(formatted_results)} results for query: {query[:50]}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in RAG search: {e}", exc_info=True)
            return []
    
    def store_knowledge(
        self,
        category: str,
        title: str,
        content: str,
        tenant_id: Optional[str] = None,
        subcategory: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source_url: Optional[str] = None,
        framework_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Store knowledge base entry with embedding.
        
        Args:
            category: Knowledge category (nist, mitre, owasp, etc.)
            title: Entry title
            content: Entry content
            tenant_id: Tenant ID (None for shared knowledge)
            subcategory: Optional subcategory
            metadata: Optional metadata
            source_url: Optional source URL
            framework_version: Optional framework version
            
        Returns:
            Created entry ID
        """
        if not self.db:
            logger.warning("Database session not available for storing knowledge")
            return {"status": "error", "error": "Database not available"}
        
        try:
            # Generate embedding
            text_to_embed = f"{title}\n{content}"
            embedding = self.embeddings_service.generate_embedding(text_to_embed)
            
            if not embedding:
                return {"status": "error", "error": "Failed to generate embedding"}
            
            # Create knowledge base entry
            kb_entry = CybersecurityKnowledgeBase(
                tenant_id=tenant_id,
                category=category,
                subcategory=subcategory,
                title=title,
                content=content,
                embedding=embedding,
                metadata_json=metadata or {},
                source_url=source_url,
                framework_version=framework_version
            )
            
            self.db.add(kb_entry)
            self.db.commit()
            self.db.refresh(kb_entry)
            
            logger.info(f"Stored knowledge base entry: {kb_entry.id} (category: {category})")
            
            return {
                "status": "success",
                "id": str(kb_entry.id),
                "category": category
            }
            
        except Exception as e:
            logger.error(f"Error storing knowledge base entry: {e}")
            self.db.rollback()
            return {"status": "error", "error": str(e)}
    
    def bulk_store(
        self,
        entries: List[Dict[str, Any]],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bulk store knowledge base entries.
        
        Args:
            entries: List of dicts with category, title, content, etc.
            tenant_id: Optional tenant ID
            
        Returns:
            Summary of stored entries
        """
        stored = 0
        errors = 0
        
        for entry in entries:
            result = self.store_knowledge(
                category=entry.get("category"),
                title=entry.get("title"),
                content=entry.get("content"),
                tenant_id=tenant_id or entry.get("tenant_id"),
                subcategory=entry.get("subcategory"),
                metadata=entry.get("metadata"),
                source_url=entry.get("source_url"),
                framework_version=entry.get("framework_version")
            )
            
            if result.get("status") == "success":
                stored += 1
            else:
                errors += 1
        
        return {
            "total": len(entries),
            "stored": stored,
            "errors": errors
        }
