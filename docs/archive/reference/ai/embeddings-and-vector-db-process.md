# Embeddings and Vector Database Process

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Overview

- Single vector backend: pgvector (no qdrant for security events).
- Single embedder service: shared by knowledge-base content and security events (SentinelGuard/SIEM Agent/IAM).
- Rationalizer: server-side selector determines which events/alerts are embedded to keep volume/cost bounded.

This document explains the complete process of taking raw cybersecurity knowledge (NIST, MITRE, OWASP, Playbooks) and loading it into the vector database with embeddings for RAG (Retrieval Augmented Generation). A security-events section below covers SentinelGuard/SIEM/IAM usage.

---

## Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Data Sources                                                 │
│    • NIST 800-53 Controls (JSON/embedded)                      │
│    • MITRE ATT&CK Techniques (JSON/embedded)                   │
│    • OWASP Content (JSON/embedded)                             │
│    • SOC Playbooks (JSON/embedded)                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Knowledge Base Loader                                        │
│    (KnowledgeBaseLoader.load_nist_controls())                   │
│    • Parses input data                                          │
│    • Formats content (title + description + guidance)           │
│    • Prepares metadata                                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. RAG Service - Store Knowledge                                │
│    (RAGService.store_knowledge())                               │
│    • Receives: category, title, content, metadata               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Embeddings Service                                           │
│    (EmbeddingsService.generate_embedding())                     │
│    • Input: "title\ncontent" (combined text)                    │
│    • Model: BGE-M3 (or all-MiniLM-L6-v2 fallback)              │
│    • Output: 1024-dimensional vector (normalized)               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Database Insert                                              │
│    (CybersecurityKnowledgeBase model)                           │
│    • Stores: title, content, metadata                           │
│    • Stores: embedding (vector(1024))                           │
│    • Stores: tenant_id (NULL for shared, UUID for tenant)      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. PostgreSQL + pgvector                                        │
│    • Table: cybersecurity_knowledge_base                        │
│    • Column: embedding vector(1024)                             │
│    • Index: IVFFlat for cosine similarity search                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Security events embedding flow (SentinelGuard, SIEM Agent, IAM)

```
SentinelGuard / SIEM Agent / IAM events
        │ (ECS-normalized with tenant_id, agent_id/host_id, @timestamp)
        ▼
Rationalizer (filters: severity/category, dedupe, size caps)
        │ emits summary fields + OpenSearch _id pointer
        ▼
Embedding Service (single model, same as KB)
        │
        ▼
pgvector (table with tenant_id, source, host/agent ids, alert_id/os_id_ref, @timestamp, summary, embedding)
```

**Summary fields (minimal PII):** rule.name/description, event.action/category/type, process.name/command_line (truncated), file.path, user.name (if needed), message/short text, host.id/name, plus tenant_id, agent_id/host_id, @timestamp, OpenSearch `_id` pointer, source (`sentinelguard`, `siem_agent`, `iam_agent`).

**Rationalizer rules (example starting point):**
- Severity filter: embed only medium/high/critical (configurable).
- Category filter: auth, malware, anomaly, lateral_movement, persistence.
- Deduplication: skip near-duplicate summaries within a time window per tenant/host.
- Size caps: truncate command_line/message to safe lengths before embedding.

**Tenancy:** every vector row carries `tenant_id`; queries must include tenant scope.

## Step-by-Step Process

### Step 1: Data Preparation

**Input Format:**
```python
{
    "id": "AC-2",
    "family": "Access Control",
    "description": "The organization manages information system accounts...",
    "guidance": "Account management addresses...",
    "version": "800-53r5"
}
```

**Processing:**
```python
# In KnowledgeBaseLoader.load_nist_controls()
content_parts = [
    control.get("description", ""),
    f"\n\nGuidance: {control.get('guidance')}",
    f"\n\nSupplemental Guidance: {control.get('supplemental_guidance')}"
]
content = "\n".join(content_parts)
```

**Result:** Structured text content ready for embedding.

---

### Step 2: Text Combination

**Format:** `"{title}\n{content}"`

**Example:**
```
AC-2 Account Management
The organization manages information system accounts, including establishing, activating, modifying, disabling, and removing accounts.

Guidance: Account management addresses the management of user, system, service, and application accounts...
```

**Why:** Combining title and content ensures embeddings capture both the concept (title) and details (content).

---

### Step 3: Embedding Generation

**Service:** `EmbeddingsService.generate_embedding()`

**Model:** BGE-M3 (`BAAI/bge-m3`)
- **Dimensions:** 1024
- **Features:** Multilingual, high quality
- **Fallback:** `all-MiniLM-L6-v2` (384 dimensions) if BGE-M3 unavailable

**Process:**
```python
# In EmbeddingsService.generate_embedding()
embeddings = self.model.encode(
    texts,
    convert_to_numpy=True,
    normalize_embeddings=True  # Normalize for cosine similarity
)

# Returns: List[float] of length 1024
# Example: [0.123, -0.456, 0.789, ...] (1024 values)
```

**Normalization:** Embeddings are normalized (L2 norm = 1) to enable efficient cosine similarity search.

---

### Step 4: Database Storage

**Model:** `CybersecurityKnowledgeBase`

**Fields Stored:**
- `id`: UUID (auto-generated)
- `tenant_id`: UUID or NULL (for shared knowledge)
- `category`: "nist", "mitre", "owasp", "playbook"
- `subcategory`: "control", "technique", "top10", etc.
- `title`: "AC-2 Account Management"
- `content`: Full text content
- `embedding`: `vector(1024)` - The embedding vector
- `metadata`: JSONB with additional info (control_id, framework_version, etc.)
- `source_url`: Optional URL to source
- `framework_version`: "800-53r5", "ATT&CK v13", etc.

**SQL Insert (conceptual):**
```sql
INSERT INTO cybersecurity_knowledge_base (
    tenant_id,
    category,
    subcategory,
    title,
    content,
    embedding,
    metadata,
    framework_version
) VALUES (
    NULL,  -- Shared knowledge
    'nist',
    'control',
    'AC-2 Account Management',
    'The organization manages...',
    '[0.123, -0.456, 0.789, ...]'::vector(1024),  -- Embedding
    '{"control_id": "AC-2", "family": "Access Control"}'::jsonb,
    '800-53r5'
);
```

---

### Step 5: Vector Index Creation

**Index Type:** IVFFlat (Inverted File Index with Flat lists)

**Purpose:** Fast approximate nearest neighbor search

**Creation:**
```sql
CREATE INDEX idx_cyber_kb_embedding ON cybersecurity_knowledge_base 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**Note:** IVFFlat index requires data to exist. It's created after initial data load or may need recreation after large data changes.

---

## Code Flow Example

### Complete Example: Loading a NIST Control

```python
# 1. Initialize services
loader = KnowledgeBaseLoader(db_session=db)
rag_service = RAGService(db_session=db)

# 2. Prepare data
control_data = {
    "id": "AC-2",
    "description": "Account management...",
    "guidance": "Account management addresses..."
}

# 3. Store via RAG service (handles embedding internally)
result = rag_service.store_knowledge(
    category="nist",
    title="AC-2 Account Management",
    content="Account management...\n\nGuidance: ...",
    subcategory="control",
    metadata={"control_id": "AC-2"},
    framework_version="800-53r5"
)

# 4. Inside RAGService.store_knowledge():
#    a. Combines title + content
text_to_embed = f"{title}\n{content}"

#    b. Generates embedding
embedding = embeddings_service.generate_embedding(text_to_embed)
#    Returns: [0.123, -0.456, ...] (1024 floats)

#    c. Creates database record
kb_entry = CybersecurityKnowledgeBase(
    category="nist",
    title="AC-2 Account Management",
    content=content,
    embedding=embedding,  # Vector stored here
    metadata=metadata
)

#    d. Inserts into database
db.add(kb_entry)
db.commit()
#    pgvector handles vector storage automatically
```

---

## Embedding Model Details

### BGE-M3 Model

**Model Card:** `BAAI/bge-m3`  
**Dimensions:** 1024  
**Normalization:** Yes (L2 normalized)  
**First Use:** Downloads model (~1.5GB) on first call, then cached  
**Performance:** High quality embeddings for semantic search

**Why BGE-M3?**
- Excellent for semantic similarity
- Supports long text (up to 8192 tokens)
- Multilingual support
- Good for cybersecurity domain

### Fallback Model

**Model:** `sentence-transformers/all-MiniLM-L6-v2`  
**Dimensions:** 384  
**Use:** If BGE-M3 unavailable or as fallback

**Note:** If using fallback, must update database schema to `vector(384)` instead of `vector(1024)`.

---

## Vector Database Operations

### Inserting with Embeddings

```python
from app.models.knowledge_base import CybersecurityKnowledgeBase
from app.services.embeddings_service import EmbeddingsService

embeddings_service = EmbeddingsService()

# Generate embedding
text = "AC-2 Account Management\nDescription..."
embedding = embeddings_service.generate_embedding(text)
# Returns: List[float] of length 1024

# Store in database
kb_entry = CybersecurityKnowledgeBase(
    category="nist",
    title="AC-2",
    content=text,
    embedding=embedding  # pgvector handles conversion
)

db.add(kb_entry)
db.commit()
```

**pgvector Conversion:** The `Vector(1024)` column type automatically converts the Python list to pgvector format.

### Searching with Embeddings

```python
from app.services.rag_service import RAGService

rag_service = RAGService(db_session=db)

# Search query
query = "How do I manage user accounts?"

# 1. Generate query embedding
query_embedding = embeddings_service.generate_embedding(query)

# 2. Vector similarity search
results = rag_service.search(
    query=query,
    tenant_id="tenant-123",
    top_k=5
)

# 3. Results ordered by similarity (cosine distance)
for result in results:
    print(f"{result['title']}: {result['similarity']:.3f}")
```

**SQL Query (conceptual):**
```sql
SELECT 
    title,
    content,
    1 - (embedding <=> :query_vec::vector) AS similarity
FROM cybersecurity_knowledge_base
WHERE tenant_id IS NULL OR tenant_id = :tenant_id
ORDER BY similarity DESC
LIMIT 5;
```

---

## Migration Process (Flyway)

### Schema Migration (V1.1)

```sql
-- Creates marker for data migration
INSERT INTO data_migration_history (migration_version, migration_name, status)
VALUES ('V1.1', 'Load initial cybersecurity knowledge base data', 'pending');
```

### Data Migration (Python Script)

**File:** `db/scripts/load_knowledge_base_data.py`

**Process:**
1. **Check Status:**
   ```python
   status = check_migration_status(db, "V1.1")
   if status == "completed":
       return  # Already loaded
   ```

2. **Mark Started:**
   ```python
   mark_migration_started(db, "V1.1")
   ```

3. **Load Data:**
   ```python
   loader = KnowledgeBaseLoader(db_session=db)
   results = loader.load_all()
   # This calls:
   #   - load_nist_controls()
   #   - load_mitre_techniques()
   #   - load_owasp_content()
   #   - load_playbooks()
   ```

4. **For Each Entry:**
   - Formats content
   - Generates embedding
   - Stores in database

5. **Mark Completed:**
   ```python
   mark_migration_completed(db, "V1.1", total_loaded)
   ```

---

## Running the Process

### Option 1: Via Flyway Migrations (Recommended)

```bash
# Run schema + data migrations
docker-compose -f docker-compose.dev.yml up \
    model_gateway_migrations \
    model_gateway_data_migrations
```

**What Happens:**
1. Flyway runs SQL migrations (V1.0, V1.1)
2. Creates `data_migration_history` table
3. Inserts marker: V1.1, status='pending'
4. Python script runs
5. Checks marker
6. Loads data with embeddings
7. Updates marker: status='completed'

### Option 2: Direct Python Script

```bash
cd backend/services/model_gateway

# Install dependencies
pip install -r requirements-loader.txt

# Run script
python db/scripts/load_knowledge_base_data.py
```

### Option 3: API Endpoint

```bash
# Load all knowledge bases
curl -X POST http://localhost:8002/internal/llm/knowledge-base/load \
  -H "Content-Type: application/json" \
  -d '{"frameworks": ["nist", "mitre", "owasp", "playbooks"]}'
```

---

## Verification

### Check Data Loaded

```sql
-- Count by category
SELECT category, COUNT(*) as count 
FROM cybersecurity_knowledge_base 
GROUP BY category;

-- Check embeddings exist
SELECT 
    category,
    title,
    CASE 
        WHEN embedding IS NULL THEN 'No embedding'
        ELSE 'Has embedding'
    END as embedding_status
FROM cybersecurity_knowledge_base
LIMIT 5;
```

### Check Migration Status

```sql
SELECT 
    migration_version,
    migration_name,
    status,
    records_loaded,
    completed_at
FROM data_migration_history;
```

### Test Vector Search

```python
from app.services.rag_service import RAGService

rag_service = RAGService(db_session=db)
results = rag_service.search("account management", top_k=3)

for r in results:
    print(f"{r['title']}: similarity={r['similarity']:.3f}")
```

---

## Performance Considerations

### Embedding Generation

**First Load:**
- Model download: ~1.5GB (one-time)
- Model loading: ~2-5 seconds
- Embedding generation: ~0.1-0.5 seconds per entry

**Subsequent Loads:**
- Model already cached
- Embedding generation: ~0.1-0.5 seconds per entry

**Batch Processing:**
- Can generate embeddings in batches
- Current implementation: One at a time
- Future optimization: Batch encoding

### Database Insert

**Single Insert:** ~10-50ms per entry  
**Bulk Insert:** Use `bulk_store()` method for better performance

### Vector Index

**IVFFlat Index:**
- Created after initial data load
- Requires ~100+ vectors for optimal performance
- May need recreation after large data changes

---

## Troubleshooting

### Embeddings Not Generated

**Symptoms:**
- `embedding IS NULL` in database
- `"Failed to generate embedding"` in logs

**Solutions:**
1. Check sentence-transformers installed: `pip install sentence-transformers`
2. Check model downloads: First run downloads model
3. Check embedding service initialization

### Wrong Embedding Dimensions

**Symptoms:**
- Database error: "vector dimension mismatch"

**Solutions:**
1. Verify model dimension matches schema:
   - BGE-M3: 1024
   - all-MiniLM-L6-v2: 384
2. Update schema if needed:
   ```sql
   ALTER TABLE cybersecurity_knowledge_base 
   ALTER COLUMN embedding TYPE vector(384);
   ```

### Slow Embedding Generation

**Solutions:**
1. Use GPU if available
2. Batch processing (future enhancement)
3. Cache embeddings for repeated content

---

## Future Enhancements

1. **Batch Embedding Generation:**
   ```python
   texts = [entry1, entry2, ...]
   embeddings = model.encode(texts, batch_size=32)
   ```

2. **Embedding Caching:**
   - Cache embeddings for identical content
   - Avoid regenerating for duplicate entries

3. **Incremental Updates:**
   - Only generate embeddings for new/changed entries
   - Update existing entries on content change

4. **Parallel Processing:**
   - Process multiple categories in parallel
   - Use multiprocessing for large datasets

---

## Summary

**The Complete Process:**
1. **Data Source** → Raw cybersecurity knowledge (JSON/embedded)
2. **Format Content** → Combine title + description + guidance
3. **Generate Embedding** → BGE-M3 model (1024-dim vector)
4. **Store in Database** → PostgreSQL + pgvector
5. **Index for Search** → IVFFlat index for fast similarity search
6. **Retrieve via RAG** → Vector similarity search for context

**Key Components:**
- `KnowledgeBaseLoader` - Formats and prepares data
- `EmbeddingsService` - Generates embeddings
- `RAGService` - Stores and retrieves knowledge
- `CybersecurityKnowledgeBase` - Database model with vector column

**Migration Flow:**
- Flyway SQL → Creates schema and markers
- Python Script → Loads data with embeddings
- Status Tracking → Prevents duplicate loads
