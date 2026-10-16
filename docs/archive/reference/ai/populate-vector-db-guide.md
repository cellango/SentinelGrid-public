# Populate Vector Database - Quick Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Prerequisites

1. **PostgreSQL is running** (with pgvector extension)
2. **Database table exists** (`cybersecurity_knowledge_base`)
3. **Python dependencies** OR **Docker**

## ✅ Quick Start (Recommended)

### Option 1: Using Docker (Easiest)

```bash
cd /path/to/SentinelGrid

# Make sure postgres is running
docker-compose -f docker-compose.dev.yml up -d postgres

# Run the population script
./scripts/populate_vector_db_simple.sh
```

### Option 2: Using Python Directly

```bash
cd /path/to/SentinelGrid/backend/services/model_gateway

# Install minimal dependencies
pip3 install sqlalchemy psycopg2-binary sentence-transformers pgvector

# Run the loader
python3 scripts/load_knowledge_base.py --all --database-url postgresql://sg:sg@localhost:5432/sg
```

### Option 3: Manual Docker Run

```bash
cd /path/to/SentinelGrid

# Build model_gateway (skip llama-cpp if needed)
docker-compose -f docker-compose.dev.yml build model_gateway

# Run the loader
docker-compose -f docker-compose.dev.yml run --rm \
    -e MODEL_GATEWAY_DATABASE_URL=postgresql://sg:sg@postgres:5432/sg \
    -e PYTHONPATH=/app \
    model_gateway \
    python scripts/load_knowledge_base.py --all --database-url postgresql://sg:sg@postgres:5432/sg
```

## What Gets Loaded

The script will load sample data for:

- **NIST 800-53 Controls**: AC-2, AC-3, IR-4 (3 controls)
- **MITRE ATT&CK Techniques**: T1078, T1059 (2 techniques)
- **OWASP Top 10**: A01:2021, A07:2021 (2 items)
- **SOC Playbooks**: Malware Response, Phishing Response (2 playbooks)

**Total**: ~9 knowledge base entries with embeddings

## Verify Load

```bash
# Check counts by category
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -c "
SELECT category, COUNT(*) as count 
FROM cybersecurity_knowledge_base 
GROUP BY category 
ORDER BY category;
"

# Check a sample entry
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -c "
SELECT category, title, LEFT(content, 100) as content_preview 
FROM cybersecurity_knowledge_base 
LIMIT 3;
"
```

## Troubleshooting

### "Module not found" errors
Install dependencies:
```bash
pip3 install sqlalchemy psycopg2-binary sentence-transformers pgvector
```

### "Table does not exist"
The table should be created automatically. If not:
```bash
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -c "
CREATE EXTENSION IF NOT EXISTS vector;
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
"
```

### "Connection refused"
Make sure PostgreSQL is running:
```bash
docker-compose -f docker-compose.dev.yml up -d postgres
docker-compose -f docker-compose.dev.yml ps postgres
```

## Next Steps

After populating:
1. Test RAG search: `POST /internal/llm/rag/search?query=account management`
2. Test unified chat with RAG context
3. Add more knowledge bases using external JSON files

