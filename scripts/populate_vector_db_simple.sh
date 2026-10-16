#!/bin/bash
# Simple script to populate vector database
# Uses a minimal Python environment to avoid heavy dependencies

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MODEL_GATEWAY_DIR="$PROJECT_ROOT/backend/services/model_gateway"

echo "📚 Populating Vector Database with Knowledge Bases"
echo "=================================================="
echo ""

# Check if postgres is running
if ! docker-compose -f "$PROJECT_ROOT/docker-compose.dev.yml" ps postgres 2>/dev/null | grep -q "Up"; then
    echo "❌ PostgreSQL is not running. Please start it first:"
    echo "   cd $PROJECT_ROOT"
    echo "   docker-compose -f docker-compose.dev.yml up -d postgres"
    exit 1
fi

echo "✅ PostgreSQL is running"
echo ""

# Ensure table exists (from previous step, it should)
echo "📋 Verifying database schema..."
docker-compose -f "$PROJECT_ROOT/docker-compose.dev.yml" exec -T postgres psql -U sg -d sg -c "
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
" > /dev/null 2>&1

echo "✅ Database schema verified"
echo ""

# Use Python with minimal install approach
echo "🔧 Setting up Python environment..."
cd "$MODEL_GATEWAY_DIR"

# Try to use python3 with pip install
if command -v python3 &> /dev/null; then
    echo "Installing minimal dependencies..."
    python3 -m pip install --quiet --user sqlalchemy psycopg2-binary sentence-transformers pgvector 2>&1 | tail -3 || {
        echo "⚠️  Could not install dependencies. Trying Docker approach..."
        
        # Fallback to Docker
        echo ""
        echo "🐳 Running in Docker container (this may take a moment)..."
        echo ""
        
        docker-compose -f "$PROJECT_ROOT/docker-compose.dev.yml" run --rm \
            -e MODEL_GATEWAY_DATABASE_URL=postgresql://sg:sg@postgres:5432/sg \
            -e PYTHONPATH=/app \
            -v "$MODEL_GATEWAY_DIR:/app" \
            --entrypoint python \
            model_gateway \
            scripts/load_knowledge_base.py --all --database-url postgresql://sg:sg@postgres:5432/sg 2>&1 | tail -30
        
        exit $?
    }
    
    echo "✅ Dependencies installed"
    echo ""
    echo "📚 Loading knowledge bases..."
    echo ""
    
    # Set database URL
    export MODEL_GATEWAY_DATABASE_URL="postgresql://sg:sg@localhost:5432/sg"
    export DATABASE_URL="postgresql://sg:sg@localhost:5432/sg"
    
    # Run the loader
    python3 scripts/load_knowledge_base.py --all --database-url postgresql://sg:sg@localhost:5432/sg
    
else
    echo "❌ Python3 not found. Please install Python 3.8+ or use Docker approach."
    exit 1
fi

echo ""
echo "✅ Knowledge base population complete!"
echo ""
echo "📊 Summary:"
docker-compose -f "$PROJECT_ROOT/docker-compose.dev.yml" exec -T postgres psql -U sg -d sg -c "
SELECT 
    category, 
    COUNT(*) as count 
FROM cybersecurity_knowledge_base 
GROUP BY category 
ORDER BY category;
"

