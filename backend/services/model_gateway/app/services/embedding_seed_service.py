"""Seed and backfill embeddings for tenants (baseline knowledge + safety guardrails)."""

import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.knowledge_base import CybersecurityKnowledgeBase
from app.models.security_event_embedding import SecurityEventEmbedding
from app.services.embeddings_service import EmbeddingsService

logger = logging.getLogger(__name__)


def _coerce_tenant_id(value: str | uuid.UUID | None) -> str | uuid.UUID | None:
    """Accept UUID strings from APIs/tests while keeping UUID objects for DB-backed writes."""
    if value is None or isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return value


class EmbeddingSeedService:
    """Populate vector store with baseline knowledge per tenant without duplicating work."""

    def __init__(
        self,
        db: Session,
        embedder: Optional[EmbeddingsService] = None,
        target_dim: Optional[int] = None,
    ):
        self.db = db
        self.embedder = embedder or EmbeddingsService()
        self.target_dim = (
            target_dim
            or getattr(SecurityEventEmbedding.__table__.c.embedding.type, "dim", None)
            or getattr(self.embedder, "embedding_dimension", None)
        )
        bind = self.db.get_bind() if hasattr(self.db, "get_bind") else getattr(self.db, "bind", None)
        self._supports_on_conflict = bool(getattr(bind, "dialect", None) and bind.dialect.name == "postgresql")

    def seed_all_active_tenants(
        self,
        categories: Optional[List[str]] = None,
        max_entries: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Seed baseline embeddings for all active tenants."""
        tenant_ids = self.db.execute(text("SELECT id FROM tenants WHERE status = 'active'")).scalars().all()
        return self.seed_baseline_for_tenants([str(tid) for tid in tenant_ids], categories, max_entries)

    def seed_baseline_for_tenants(
        self,
        tenant_ids: List[str],
        categories: Optional[List[str]] = None,
        max_entries: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Seed baseline CIS/NIST/MITRE/SOC content into security_event_embeddings per tenant."""
        kb_entries = self._load_baseline_entries(categories=categories, limit=max_entries)
        if not kb_entries:
            return {"tenants": len(tenant_ids), "ingested": {}, "skipped": {}, "entries": 0}

        result = {"tenants": len(tenant_ids), "ingested": {}, "skipped": {}, "entries": len(kb_entries)}

        for tenant_id in tenant_ids:
            ingested = 0
            skipped = 0
            for kb_entry in kb_entries:
                record = self._prepare_record(tenant_id, kb_entry)
                if not record:
                    skipped += 1
                    continue
                try:
                    self._upsert_embedding(record)
                    ingested += 1
                except Exception as exc:
                    logger.error("Failed to seed baseline embedding tenant=%s kb=%s: %s", tenant_id, kb_entry.id, exc)
                    self.db.rollback()
                    skipped += 1
            self.db.commit()
            result["ingested"][tenant_id] = ingested
            result["skipped"][tenant_id] = skipped

        return result

    def _load_baseline_entries(
        self,
        categories: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[CybersecurityKnowledgeBase]:
        """Fetch shared knowledge base entries (tenant_id is NULL)."""
        stmt = select(CybersecurityKnowledgeBase).where(CybersecurityKnowledgeBase.tenant_id.is_(None))
        if categories:
            stmt = stmt.where(CybersecurityKnowledgeBase.category.in_(categories))
        if limit:
            stmt = stmt.limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def _prepare_record(self, tenant_id: str, kb_entry: CybersecurityKnowledgeBase) -> Optional[Dict[str, Any]]:
        """Build a security_event_embeddings record from a KB entry."""
        if not self.embedder:
            logger.warning("Embedding model not available; skipping seed")
            return None

        content_snippet = (kb_entry.content or "")[:800]
        summary = f"[{kb_entry.category}] {kb_entry.title}: {content_snippet}"

        embedding = self.embedder.generate_embedding(summary)
        if not embedding:
            return None
        embedding = self._normalize_embedding_length(embedding)

        timestamp = kb_entry.updated_at or kb_entry.created_at or datetime.utcnow()
        return {
            "tenant_id": _coerce_tenant_id(tenant_id),
            "source": "baseline",
            "agent_id": None,
            "host_id": None,
            "os_id_ref": f"kb-{kb_entry.id}",
            "timestamp": timestamp,
            "summary": summary,
            "fields": {
                "category": kb_entry.category,
                "subcategory": kb_entry.subcategory,
                "title": kb_entry.title,
                "framework_version": kb_entry.framework_version,
                "source_url": kb_entry.source_url,
            },
            "embedding": embedding,
        }

    def _normalize_embedding_length(self, embedding: List[float]) -> List[float]:
        """Pad or truncate embedding vectors to the configured dimension."""
        if not self.target_dim or not isinstance(embedding, list):
            return embedding
        current = len(embedding)
        if current == self.target_dim:
            return embedding
        if current < self.target_dim:
            return embedding + [0.0] * (self.target_dim - current)
        return embedding[: self.target_dim]

    def _upsert_embedding(self, record: Dict[str, Any]) -> None:
        """Upsert embedding using a unique key (tenant_id, source, os_id_ref)."""
        if self._supports_on_conflict:
            stmt = (
                pg_insert(SecurityEventEmbedding)
                .values(**record)
                .on_conflict_do_update(
                    index_elements=[
                        SecurityEventEmbedding.tenant_id,
                        SecurityEventEmbedding.source,
                        SecurityEventEmbedding.os_id_ref,
                    ],
                    set_={
                        "timestamp": record["timestamp"],
                        "summary": record["summary"],
                        "fields": record["fields"],
                        "embedding": record["embedding"],
                        "host_id": record.get("host_id"),
                        "agent_id": record.get("agent_id"),
                    },
                )
            )
            self.db.execute(stmt)
        else:
            existing = (
                self.db.query(SecurityEventEmbedding)
                .filter_by(
                    tenant_id=record["tenant_id"],
                    source=record["source"],
                    os_id_ref=record["os_id_ref"],
                )
                .one_or_none()
            )
            if existing:
                existing.timestamp = record["timestamp"]
                existing.summary = record["summary"]
                existing.fields = record["fields"]
                existing.embedding = record["embedding"]
                existing.host_id = record.get("host_id")
                existing.agent_id = record.get("agent_id")
            else:
                self.db.add(SecurityEventEmbedding(**record))
