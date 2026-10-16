import uuid

from app.models.knowledge_base import CybersecurityKnowledgeBase
from app.models.security_event_embedding import SecurityEventEmbedding
from app.services.embedding_seed_service import EmbeddingSeedService


class _StubEmbedder:
    """Lightweight embedder stub for tests."""

    def __init__(self, dim: int = 384):
        self.embedding_dimension = dim
        self.model_name = "stub-model"

    def generate_embedding(self, text):
        # Return a small vector and let the seeder pad to the configured dimension
        return [0.1, 0.2]


def test_seed_baseline_for_tenant(db_session):
    kb_entry = CybersecurityKnowledgeBase(
        tenant_id=None,
        category="nist",
        subcategory="control",
        title="AC-2 Account Management",
        content="Manage accounts and review access regularly.",
        embedding=None,
    )
    db_session.add(kb_entry)
    db_session.commit()

    tenant_id = str(uuid.uuid4())
    tenant_uuid = uuid.UUID(tenant_id)
    target_dim = getattr(SecurityEventEmbedding.__table__.c.embedding.type, "dim", 1024)
    seeder = EmbeddingSeedService(
        db_session,
        embedder=_StubEmbedder(dim=target_dim),
        target_dim=target_dim,
    )
    # Avoid ON CONFLICT path because test tables lack a matching unique constraint
    seeder._supports_on_conflict = False

    result = seeder.seed_baseline_for_tenants([tenant_id])
    assert result["ingested"][tenant_id] == 1

    stored = (
        db_session.query(SecurityEventEmbedding)
        .filter_by(tenant_id=tenant_uuid, source="baseline")
        .all()
    )
    assert len(stored) == 1
    assert stored[0].os_id_ref.startswith("kb-")
    assert len(stored[0].embedding) == target_dim

    # Re-run to verify idempotent upsert does not duplicate rows
    result_repeat = seeder.seed_baseline_for_tenants([tenant_id])
    assert result_repeat["ingested"][tenant_id] == 1
    assert (
        db_session.query(SecurityEventEmbedding)
        .filter_by(tenant_id=tenant_uuid, source="baseline")
        .count()
        == 1
    )


def test_embeddings_health_endpoint(client, monkeypatch):
    # Avoid loading a real model; stub the embedder for health check
    from app.api import embeddings as embeddings_api

    embeddings_api._embedding_service = _StubEmbedder()

    resp = client.get("/api/v1/embeddings/health", headers={"X-Tenant-ID": "test-tenant"})
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    assert "model_ready" in body
    assert "vector_store" in body
