"""Embedding ingestion API for security events (pgvector)."""

import logging
import uuid
from uuid import UUID
from datetime import datetime
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_current_tenant, get_tenant_session
from app.services.embeddings_service import EmbeddingsService
from app.models.security_event_embedding import SecurityEventEmbedding
from concurrent.futures import ThreadPoolExecutor, TimeoutError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/embeddings", tags=["embeddings"])

_embedding_service: Optional[EmbeddingsService] = None
DB_VECTOR_DIM: Optional[int] = getattr(
    SecurityEventEmbedding.__table__.c.embedding.type, "dim", None
)


def _coerce_tenant_id(value: str | uuid.UUID | None) -> str | uuid.UUID | None:
    """Accept UUID strings from requests while keeping DB-bound values UUID-typed when possible."""
    if value is None or isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return value


def _enforce_same_tenant(requested_tenant_id: str | UUID, current_tenant_id: UUID) -> None:
    if str(requested_tenant_id) != str(current_tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access denied",
        )


def _enforce_summary_tenant_scope(
    summaries: List["SecurityEventSummary"],
    current_tenant_id: UUID,
) -> None:
    for summary in summaries:
        _enforce_same_tenant(summary.tenant_id, current_tenant_id)


def get_embedding_service() -> Optional[EmbeddingsService]:
    global _embedding_service
    if _embedding_service is None:
        try:
            logger.info("Loading embedding service/model...")
            _embedding_service = EmbeddingsService()
            logger.info("Embedding service ready with model %s", _embedding_service.model_name if hasattr(_embedding_service, "model_name") else "unknown")
        except Exception as exc:
            logger.exception("Failed to initialize EmbeddingsService: %s", exc)
            _embedding_service = None
    return _embedding_service


class SecurityEventSummary(BaseModel):
    tenant_id: str = Field(..., description="Tenant UUID")
    source: str = Field(..., description="sentinelguard|siem_agent|iam_agent|...")
    agent_id: Optional[str] = None
    host_id: Optional[str] = None
    os_id: str = Field(..., description="OpenSearch document id")
    timestamp: datetime
    summary: str
    fields: Optional[Dict[str, Any]] = None

    def redacted(self) -> "SecurityEventSummary":
        """Best-effort redaction for obvious secrets/PII before embedding."""
        import re

        def _redact_text(val: str) -> str:
            if not val:
                return val
            patterns = [
                r"(?i)(api[_-]?key|token|secret|password)[:=\\s]*[A-Za-z0-9\\-_/+=]{10,}",
                r"(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}",
            ]
            redacted = val
            for pat in patterns:
                redacted = re.sub(pat, "[REDACTED]", redacted, flags=re.IGNORECASE)
            return redacted

        redacted_summary = _redact_text(self.summary)
        redacted_fields = self.fields or {}
        if isinstance(redacted_fields, dict):
            for k, v in list(redacted_fields.items()):
                if isinstance(v, str):
                    redacted_fields[k] = _redact_text(v)
        return SecurityEventSummary(
            tenant_id=self.tenant_id,
            source=self.source,
            agent_id=self.agent_id,
            host_id=self.host_id,
            os_id=self.os_id,
            timestamp=self.timestamp,
            summary=redacted_summary,
            fields=redacted_fields,
        )


class EmbeddingIngestRequest(BaseModel):
    summaries: List[SecurityEventSummary]


class EmbeddingIngestResponse(BaseModel):
    ingested: int
    failed: int
    errors: List[str] = Field(default_factory=list)


class EmbeddingSearchRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant UUID")
    query: str = Field(..., description="Free-text query to search embeddings")
    limit: int = Field(5, ge=1, le=50, description="Max results")


class EmbeddingSearchResult(BaseModel):
    os_id: str
    source: str
    similarity: float
    summary: str
    fields: Dict[str, Any]
    timestamp: datetime


class EmbeddingSearchResponse(BaseModel):
    results: List[EmbeddingSearchResult]
    count: int


class FixGroupSearchResult(BaseModel):
    fix_group_id: str
    scanner_id: Optional[str]
    target_ref: Optional[str]
    ticket_id: Optional[str] = None
    similarity: float
    summary: str
    guidance: Optional[Dict[str, Any]] = None
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FixGroupSearchResponse(BaseModel):
    results: List[FixGroupSearchResult]
    count: int


@router.post("/security-events/search-stub")
def search_stub():
    """Simple stub to verify POST routing without dependencies."""
    return EmbeddingSearchResponse(
        results=[
            EmbeddingSearchResult(
                os_id="stub-os-id",
                source="stub",
                similarity=1.0,
                summary="stub result",
                fields={},
                timestamp=datetime.utcnow(),
            )
        ],
        count=1,
    )

@router.get("/security-events/search/ping")
def search_ping():
    """Lightweight ping to verify search route wiring."""
    return {"status": "ok"}

@router.get("/health")
def embeddings_health(db: Session = Depends(get_tenant_session)):
    """
    Health probe for embedding path: checks model availability and vector store reachability.
    """
    try:
        embedder = get_embedding_service()
        model_ready = embedder is not None
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Embedding model health check failed: %s", exc)
        model_ready = False

    vector_store_ok = True
    vector_count = None
    try:
        vector_count = db.execute(text("SELECT COUNT(*) FROM security_event_embeddings")).scalar()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Vector store health query failed: %s", exc)
        vector_store_ok = False

    status_label = "ok" if model_ready and vector_store_ok else "degraded"
    return {
        "status": status_label,
        "model_ready": model_ready,
        "vector_store": vector_store_ok,
        "vectors": vector_count,
    }


@router.post("/security-events", response_model=EmbeddingIngestResponse)
def ingest_security_event_embeddings(
    payload: EmbeddingIngestRequest,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
    embedder: Optional[EmbeddingsService] = Depends(get_embedding_service),
):
    """Ingest security event summaries and store embeddings in pgvector."""
    logger.info("Embedding ingest request: %d summaries", len(payload.summaries) if payload.summaries else 0)
    if not payload.summaries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No summaries provided"
        )
    if embedder is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding model not available",
        )
    _enforce_summary_tenant_scope(payload.summaries, current_tenant_id)

    ingested = 0
    errors: List[str] = []
    bind = db.get_bind()
    supports_on_conflict = bool(getattr(bind, "dialect", None) and bind.dialect.name == "postgresql")

    for summary in payload.summaries:
        try:
            redacted = summary.redacted()
            logger.info("Generating embedding for os_id=%s tenant=%s", redacted.os_id, redacted.tenant_id)
            embedding = embedder.generate_embedding(redacted.summary)
            if not embedding:
                errors.append(f"Embedding generation failed for os_id={redacted.os_id}")
                continue
            logger.info("Embedding generated for os_id=%s len=%d", redacted.os_id, len(embedding))

            target_dim = DB_VECTOR_DIM or len(embedding)
            current_dim = len(embedding)
            if current_dim != target_dim:
                if current_dim < target_dim:
                    embedding = embedding + [0.0] * (target_dim - current_dim)
                else:
                    embedding = embedding[:target_dim]
                logger.warning(
                    "Adjusted embedding dimension from %d to %d for os_id=%s",
                    current_dim,
                    target_dim,
                    summary.os_id,
                )

            record_data = {
                "tenant_id": _coerce_tenant_id(redacted.tenant_id),
                "source": redacted.source,
                "agent_id": redacted.agent_id,
                "host_id": redacted.host_id,
                "os_id_ref": redacted.os_id,
                "timestamp": redacted.timestamp,
                "summary": redacted.summary,
                "fields": redacted.fields or {},
                "embedding": embedding,
            }

            if supports_on_conflict:
                from sqlalchemy.dialects.postgresql import insert as pg_insert

                stmt = (
                    pg_insert(SecurityEventEmbedding)
                    .values(**record_data)
                    .on_conflict_do_update(
                        index_elements=[
                            SecurityEventEmbedding.tenant_id,
                            SecurityEventEmbedding.source,
                            SecurityEventEmbedding.os_id_ref,
                        ],
                        set_={
                            "timestamp": record_data["timestamp"],
                            "summary": record_data["summary"],
                            "fields": record_data["fields"],
                            "embedding": record_data["embedding"],
                            "agent_id": record_data["agent_id"],
                            "host_id": record_data["host_id"],
                        },
                    )
                )
                db.execute(stmt)
            else:
                existing = (
                    db.query(SecurityEventEmbedding)
                    .filter_by(
                        tenant_id=record_data["tenant_id"],
                        source=record_data["source"],
                        os_id_ref=record_data["os_id_ref"],
                    )
                    .one_or_none()
                )
                if existing:
                    existing.timestamp = record_data["timestamp"]
                    existing.summary = record_data["summary"]
                    existing.fields = record_data["fields"]
                    existing.embedding = record_data["embedding"]
                    existing.agent_id = record_data["agent_id"]
                    existing.host_id = record_data["host_id"]
                else:
                    db.add(SecurityEventEmbedding(**record_data))
            ingested += 1
            logger.info("Embedding stored for os_id=%s", summary.os_id)
        except Exception as e:
            logger.error(f"Failed to ingest summary os_id={summary.os_id}: {e}")
            db.rollback()
            errors.append(f"{summary.os_id}: {e}")
        else:
            db.commit()

    return EmbeddingIngestResponse(
        ingested=ingested,
        failed=len(errors),
        errors=errors[:10],
    )


@router.post("/security-events/search", response_model=EmbeddingSearchResponse)
def search_security_event_embeddings(
    payload: EmbeddingSearchRequest,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """
    Tenant-scoped vector search over security_event_embeddings.
    Uses pgvector cosine similarity; requires tenant_id.
    """
    try:
        _enforce_same_tenant(payload.tenant_id, current_tenant_id)
        if payload.query == "__stub__":
            logger.warning("Embedding search stub hit tenant=%s", payload.tenant_id)
            return EmbeddingSearchResponse(
                results=[
                    EmbeddingSearchResult(
                        os_id="stub-os-id",
                        source="stub",
                        similarity=1.0,
                        summary="stub result",
                        fields={},
                        timestamp=datetime.utcnow(),
                    )
                ],
                count=1,
            )
        logger.warning(
            "Embedding search start tenant=%s limit=%s query_len=%s",
            payload.tenant_id,
            payload.limit,
            len(payload.query or ""),
        )
        embedder = get_embedding_service()
        if embedder is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Embedding model not available",
            )
        logger.debug("Embedding service present? %s", bool(embedder))
        logger.debug("Embedding model loaded, generating query embedding")
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(embedder.generate_embedding, payload.query)
            try:
                query_embedding = future.result(timeout=10)
            except TimeoutError:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Embedding generation timed out",
                )
        logger.debug("Embedding generation complete")
        if not query_embedding:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to generate embedding for query",
            )
        logger.debug("Generated query embedding len=%s", len(query_embedding))
        target_dim = DB_VECTOR_DIM or len(query_embedding)
        current_dim = len(query_embedding)
        if current_dim != target_dim:
            if current_dim < target_dim:
                query_embedding = query_embedding + [0.0] * (target_dim - current_dim)
            else:
                query_embedding = query_embedding[:target_dim]
        logger.debug("Adjusted embedding dimension to %s", len(query_embedding))
        # Build vector literal for pgvector
        vec_literal = "[" + ",".join(f"{v:.6f}" for v in query_embedding) + "]"
        logger.debug("Vector literal built len=%s", len(vec_literal))

        sql = text(
            """
            SELECT os_id_ref, source, summary, fields, "timestamp",
                   1 - (embedding <=> (:query_vec)::vector) AS similarity
            FROM security_event_embeddings
            WHERE tenant_id = :tenant_id
            ORDER BY embedding <=> (:query_vec)::vector
            LIMIT :limit
            """
        )

        # Apply a short statement timeout to avoid hanging
        db.execute(text("SET LOCAL statement_timeout = 5000"))
        logger.debug("Executing vector search SQL")
        rows = db.execute(
            sql,
            {"tenant_id": payload.tenant_id, "query_vec": vec_literal, "limit": payload.limit},
        ).mappings()
        logger.debug("Vector search returned rows")

        results: List[EmbeddingSearchResult] = []
        for r in rows:
            results.append(
                EmbeddingSearchResult(
                    os_id=r["os_id_ref"],
                    source=r["source"],
                    similarity=float(r["similarity"]),
                    summary=r["summary"],
                    fields=r["fields"] or {},
                    timestamp=r["timestamp"],
                )
            )
        logger.warning(
            "Embedding search done tenant=%s results=%d",
            payload.tenant_id,
            len(results),
        )
        return EmbeddingSearchResponse(results=results, count=len(results))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Embedding search unhandled error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {exc}",
        )


@router.post("/fix-groups/search", response_model=FixGroupSearchResponse)
def search_fix_group_embeddings(
    payload: EmbeddingSearchRequest,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """
    Tenant-scoped vector search over remediation embeddings (fix_group and ticket sources).
    """
    try:
        _enforce_same_tenant(payload.tenant_id, current_tenant_id)
        logger.warning(
            "FixGroup search start tenant=%s limit=%s query_len=%s",
            payload.tenant_id,
            payload.limit,
            len(payload.query or ""),
        )
        embedder = get_embedding_service()
        if embedder is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Embedding model not available",
            )
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(embedder.generate_embedding, payload.query)
            try:
                query_embedding = future.result(timeout=10)
            except TimeoutError:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Embedding generation timed out",
                )
        if not query_embedding:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to generate embedding for query",
            )

        target_dim = DB_VECTOR_DIM or len(query_embedding)
        current_dim = len(query_embedding)
        if current_dim != target_dim:
            if current_dim < target_dim:
                query_embedding = query_embedding + [0.0] * (target_dim - current_dim)
            else:
                query_embedding = query_embedding[:target_dim]
        vec_literal = "[" + ",".join(f"{v:.6f}" for v in query_embedding) + "]"

        sql = text(
            """
            SELECT os_id_ref, summary, fields, "timestamp",
                   source,
                   1 - (embedding <=> (:query_vec)::vector) AS similarity
            FROM security_event_embeddings
            WHERE tenant_id = :tenant_id
              AND source IN ('fix_group','ticket')
            ORDER BY embedding <=> (:query_vec)::vector
            LIMIT :limit
            """
        )

        db.execute(text("SET LOCAL statement_timeout = 5000"))
        rows = db.execute(
            sql,
            {"tenant_id": payload.tenant_id, "query_vec": vec_literal, "limit": payload.limit},
        ).mappings()

        results: List[FixGroupSearchResult] = []
        for r in rows:
            fields = r["fields"] or {}
            results.append(
                FixGroupSearchResult(
                    fix_group_id=fields.get("fix_group_id") or r["os_id_ref"],
                    scanner_id=fields.get("scanner_id"),
                    target_ref=fields.get("target_ref"),
                    ticket_id=fields.get("ticket_id") if r["source"] == "ticket" else None,
                    similarity=float(r["similarity"]),
                    summary=r["summary"],
                    guidance=None,
                    created_at=r["timestamp"],
                    metadata={
                        "resource_type": fields.get("resource_type"),
                        "scan_id": fields.get("scan_id"),
                        "severity": fields.get("severity"),
                        "source": r["source"],
                        "ticket_id": fields.get("ticket_id"),
                    },
                )
            )
        logger.warning(
            "FixGroup search done tenant=%s results=%d",
            payload.tenant_id,
            len(results),
        )
        return FixGroupSearchResponse(results=results, count=len(results))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("FixGroup search unhandled error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {exc}",
        )
import math
