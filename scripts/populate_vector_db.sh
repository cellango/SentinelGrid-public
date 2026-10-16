#!/bin/bash
# Script to populate vector database with knowledge bases
# This script runs the load_knowledge_base.py script in the model_gateway container

set -e

echo "🔍 Checking prerequisites..."

# Check if postgres is running
if ! docker-compose -f docker-compose.dev.yml ps postgres | grep -q "Up"; then
    echo "❌ PostgreSQL is not running. Please start it first:"
    echo "   docker-compose -f docker-compose.dev.yml up -d postgres"
    exit 1
fi

echo "✅ PostgreSQL is running"

# Check if pgvector extension is enabled
if ! docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -c "SELECT extname FROM pg_extension WHERE extname = 'vector';" | grep -q "vector"; then
    echo "📦 Enabling pgvector extension..."
    docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -c "CREATE EXTENSION IF NOT EXISTS vector;"
fi

echo "✅ pgvector extension enabled"

# Check if table exists, create if not
if ! docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -c "\dt cybersecurity_knowledge_base" 2>&1 | grep -q "cybersecurity_knowledge_base"; then
    echo "📦 Creating cybersecurity_knowledge_base table..."
    docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg <<'SQL'
CREATE TABLE IF NOT EXISTS cybersecurity_knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(50),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1024),
    metadata JSONB DEFAULT '{}',
    source_url TEXT,
    framework_version VARCHAR(20),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_tenant ON cybersecurity_knowledge_base(tenant_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_category ON cybersecurity_knowledge_base(category);
SQL
fi

echo "✅ Database schema ready"

# Build model_gateway if needed
echo "🔨 Building model_gateway service (if needed)..."
docker-compose -f docker-compose.dev.yml build model_gateway --no-cache 2>&1 | tail -5 || true

echo ""
echo "📚 Loading knowledge bases..."
echo "   This will load sample data for NIST, MITRE, OWASP, and Playbooks"
echo ""

# Run the load script in the container
docker-compose -f docker-compose.dev.yml run --rm \
    -e MODEL_GATEWAY_DATABASE_URL=postgresql://sg:sg@postgres:5432/sg \
    -e PYTHONPATH=/app \
    model_gateway \
    python scripts/load_knowledge_base.py --all --database-url postgresql://sg:sg@postgres:5432/sg

echo ""
echo "✅ Knowledge base population complete!"
echo ""
echo "You can verify by running:"
echo "  docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -c \"SELECT category, COUNT(*) FROM cybersecurity_knowledge_base GROUP BY category;\""

