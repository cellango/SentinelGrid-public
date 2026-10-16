# Git-Based Data Ingestion Pipeline

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Overview

Automated pipeline for ingesting cybersecurity knowledge base data from git repositories without human intervention. Supports both customer-specific and global/shared repositories.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Git Repositories                          │
├──────────────────────────────┬──────────────────────────────┤
│  Customer Repos              │  Global Repos                │
│  tenant_id = UUID            │  tenant_id = NULL            │
│  - Private per customer      │  - Shared across all         │
│  - Customer-owned            │  - SentinelGrid-owned        │
└──────────────┬───────────────┴──────────────┬───────────────┘
               │                              │
               ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Webhook/Polling                           │
│  • GitHub webhooks                                          │
│  • GitLab webhooks                                          │
│  • Scheduled polling (fallback)                             │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              Git Data Ingestion Service                     │
│  1. Clone/update repository                                 │
│  2. Discover knowledge base files                           │
│  3. Parse JSON data                                         │
│  4. Detect category (NIST, MITRE, OWASP, Playbooks)        │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              Knowledge Base Loader                          │
│  • Format content                                           │
│  • Prepare metadata                                         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              Embeddings Service                             │
│  • Generate embeddings (BGE-M3)                            │
│  • 1024-dimensional vectors                                 │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              Vector Database                                │
│  • Store with tenant_id (customer) or NULL (global)        │
│  • Indexed for similarity search                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Repository Types

### Customer-Specific Repositories

**Purpose:** Tenant-specific knowledge base data  
**Tenant ID:** Customer UUID (from tenant table)  
**Access:** Only accessible to that tenant  
**Example:** `https://github.com/customer-xyz/knowledge-base`

**Configuration:**
```json
{
  "repo_url": "https://github.com/customer-xyz/kb",
  "repo_type": "customer",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch": "main",
  "paths": ["knowledge-base/", "data/"]
}
```

### Global/Shared Repositories

**Purpose:** Shared knowledge available to all tenants  
**Tenant ID:** NULL  
**Access:** All tenants can access via RAG  
**Example:** `https://github.com/sentinelgrid/global-kb`

**Configuration:**
```json
{
  "repo_url": "https://github.com/sentinelgrid/global-kb",
  "repo_type": "global",
  "tenant_id": null,
  "branch": "main",
  "paths": ["frameworks/"]
}
```

---

## Triggering Ingestion

### Option 1: Webhooks (Recommended)

#### GitHub Webhook Setup

1. **Go to Repository Settings → Webhooks**
2. **Add webhook:**
   - URL: `https://your-domain/internal/llm/git-ingestion/webhook/github?tenant_id={tenant_id}`
   - Content type: `application/json`
   - Events: `Push`
   - Secret: (optional, for verification)

3. **On push, webhook triggers:**
   - Checks for knowledge base file changes
   - If changed, triggers ingestion
   - Processes new/modified files
   - Generates embeddings
   - Stores in vector database

#### GitLab Webhook Setup

1. **Go to Project Settings → Webhooks**
2. **Add webhook:**
   - URL: `https://your-domain/internal/llm/git-ingestion/webhook/gitlab?tenant_id={tenant_id}`
   - Trigger: `Push events`
   - Secret token: (optional)

### Option 2: Scheduled Polling (Fallback)

Automatically polls registered repositories at intervals:

```bash
# Set polling interval (default: 60 minutes)
export GIT_POLL_INTERVAL_MINUTES=60

# Run scheduled ingestion
POST /internal/llm/git-ingestion/poll
```

**Use Cases:**
- Repositories without webhook support
- Backup for missed webhooks
- Manual triggering

### Option 3: Manual Trigger

```bash
# Ingest specific repository
POST /internal/llm/git-ingestion/ingest
{
  "repo_url": "https://github.com/customer-xyz/kb",
  "repo_type": "customer",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch": "main"
}
```

---

## Data File Formats

### Supported Formats

#### NIST Controls (`nist/controls.json`)
```json
{
  "controls": [
    {
      "id": "AC-2",
      "family": "Access Control",
      "description": "The organization manages...",
      "guidance": "Account management addresses...",
      "version": "800-53r5"
    }
  ]
}
```

#### MITRE Techniques (`mitre/techniques.json`)
```json
{
  "techniques": [
    {
      "id": "T1078",
      "name": "Valid Accounts",
      "description": "Adversaries may steal...",
      "tactic": ["Initial Access"],
      "detection": "Monitor for...",
      "mitigation": "Use multifactor...",
      "version": "ATT&CK v13"
    }
  ]
}
```

#### OWASP Content (`owasp/content.json`)
```json
{
  "items": [
    {
      "id": "A01:2021",
      "name": "Broken Access Control",
      "description": "Access control enforces...",
      "type": "top10",
      "how_to_prevent": "Implement access control...",
      "version": "2021"
    }
  ]
}
```

#### SOC Playbooks (`playbooks/playbooks.json`)
```json
{
  "playbooks": [
    {
      "id": "malware-response-v1",
      "name": "Malware Detection & Response",
      "description": "Comprehensive playbook...",
      "steps": [
        {
          "name": "Detection & Triage",
          "description": "EDR/SIEM alert analysis..."
        }
      ]
    }
  ]
}
```

### File Discovery

The service automatically discovers files matching these patterns:
- `**/*nist*.json`
- `**/*mitre*.json`
- `**/*owasp*.json`
- `**/*playbook*.json`
- `**/knowledge*.json`
- `**/kb-*.json`

Or structured paths:
- `nist/controls.json`
- `mitre/techniques.json`
- `owasp/content.json`
- `playbooks/playbooks.json`

---

## Repository Registration

### Register a Repository

```bash
POST /internal/llm/git-ingestion/repos/register
{
  "repo_url": "https://github.com/customer-xyz/kb",
  "repo_type": "customer",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch": "main",
  "paths": ["knowledge-base/"],
  "webhook_secret": "optional-secret"
}
```

**Response:**
```json
{
  "status": "registered",
  "id": "repo-uuid",
  "repo_url": "https://github.com/customer-xyz/kb",
  "repo_type": "customer",
  "webhook_url": "/internal/llm/git-ingestion/webhook/generic?tenant_id=..."
}
```

### List Registered Repositories

```bash
GET /internal/llm/git-ingestion/repos?tenant_id={tenant_id}
GET /internal/llm/git-ingestion/repos?repo_type=global
```

---

## Complete Workflow

### Customer Onboarding

1. **Create Tenant:**
   ```sql
   INSERT INTO tenants (id, name, slug) 
   VALUES (uuid_generate_v4(), 'Customer XYZ', 'customer-xyz');
   ```

2. **Customer Creates Repository:**
   - Creates private repo: `customer-xyz/knowledge-base`
   - Adds knowledge base files (NIST, MITRE, etc.)

3. **Register Repository:**
   ```bash
   POST /internal/llm/git-ingestion/repos/register
   {
     "repo_url": "https://github.com/customer-xyz/knowledge-base",
     "repo_type": "customer",
     "tenant_id": "tenant-uuid",
     "branch": "main"
   }
   ```

4. **Set Up Webhook:**
   - Customer adds webhook in GitHub/GitLab
   - URL: `/internal/llm/git-ingestion/webhook/github?tenant_id={tenant_id}`
   - Events: Push

5. **Initial Ingestion:**
   ```bash
   POST /internal/llm/git-ingestion/ingest
   {
     "repo_url": "https://github.com/customer-xyz/knowledge-base",
     "repo_type": "customer",
     "tenant_id": "tenant-uuid"
   }
   ```

6. **Automated Updates:**
   - Customer pushes changes → Webhook triggers
   - Pipeline processes → Generates embeddings → Stores in DB
   - Data available via RAG with tenant isolation

### Global Repository Setup

1. **Create Global Repository:**
   - SentinelGrid maintains: `sentinelgrid/global-knowledge-base`
   - Contains: Standard NIST, MITRE, OWASP content

2. **Register as Global:**
   ```bash
   POST /internal/llm/git-ingestion/repos/register
   {
     "repo_url": "https://github.com/sentinelgrid/global-knowledge-base",
     "repo_type": "global",
     "tenant_id": null,
     "branch": "main"
   }
   ```

3. **Set Up Webhook:**
   - Webhook URL: `/internal/llm/git-ingestion/webhook/github` (no tenant_id)

4. **Data Available to All:**
   - All tenants can access via RAG
   - `tenant_id IS NULL` in vector database

---

## Tenant Isolation

### How It Works

**Customer Data:**
```python
# Stored with tenant_id
rag_service.store_knowledge(
    category="nist",
    title="AC-2",
    content="...",
    tenant_id="customer-uuid"  # Customer-specific
)
```

**Global Data:**
```python
# Stored with tenant_id = NULL
rag_service.store_knowledge(
    category="nist",
    title="AC-2",
    content="...",
    tenant_id=None  # Shared/global
)
```

**RAG Search:**
```python
# Customer query gets:
# 1. Global knowledge (tenant_id IS NULL)
# 2. Customer-specific knowledge (tenant_id = customer-uuid)

results = rag_service.search(
    query="account management",
    tenant_id="customer-uuid"  # Gets both global + customer
)
```

---

## API Endpoints

### Ingestion

- `POST /internal/llm/git-ingestion/ingest` - Manual ingestion
- `POST /internal/llm/git-ingestion/webhook/github` - GitHub webhook
- `POST /internal/llm/git-ingestion/webhook/gitlab` - GitLab webhook
- `POST /internal/llm/git-ingestion/webhook/generic` - Generic webhook
- `POST /internal/llm/git-ingestion/poll` - Poll all repos

### Repository Management

- `POST /internal/llm/git-ingestion/repos/register` - Register repo
- `GET /internal/llm/git-ingestion/repos` - List repos
- `GET /internal/llm/git-ingestion/repos?tenant_id={id}` - List tenant repos
- `GET /internal/llm/git-ingestion/repos?repo_type=global` - List global repos

---

## Database Schema

### git_repositories

Tracks registered repositories:

```sql
CREATE TABLE git_repositories (
    id UUID PRIMARY KEY,
    tenant_id UUID,  -- NULL for global, UUID for customer
    repo_url TEXT NOT NULL,
    repo_type VARCHAR(20),  -- 'customer' or 'global'
    branch VARCHAR(100),
    paths JSONB,  -- Optional paths
    is_active BOOLEAN,
    last_ingested_at TIMESTAMPTZ,
    last_ingestion_status VARCHAR(20),
    ...
);
```

### git_ingestion_jobs

Tracks ingestion jobs:

```sql
CREATE TABLE git_ingestion_jobs (
    id UUID PRIMARY KEY,
    repository_id UUID REFERENCES git_repositories(id),
    tenant_id UUID,
    trigger_type VARCHAR(20),  -- 'webhook', 'scheduled', 'manual'
    status VARCHAR(20),  -- 'pending', 'running', 'completed', 'failed'
    files_processed INTEGER,
    records_loaded INTEGER,
    errors INTEGER,
    results JSONB,
    ...
);
```

---

## Security Considerations

### Webhook Verification

1. **Secret Tokens:**
   - Store webhook secrets per repository
   - Verify webhook signatures (GitHub HMAC, GitLab token)

2. **Tenant ID Validation:**
   - Validate tenant_id from webhook matches repository
   - Prevent cross-tenant data access

3. **Repository Access:**
   - Use SSH keys or access tokens for private repos
   - Store credentials securely (Vault, secrets manager)

### Authentication

```python
# Verify GitHub webhook signature
import hmac
import hashlib

def verify_github_webhook(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

---

## Error Handling

### Ingestion Failures

- **Tracked in `git_ingestion_jobs`:**
  - Status: "failed"
  - Error message stored
  - Can retry manually or automatically

### Retry Logic

```python
# Automatic retry for failed jobs
if job.status == "failed" and job.retry_count < 3:
    retry_ingestion(job.repository_id)
```

### Monitoring

- Track ingestion success rates
- Alert on repeated failures
- Monitor processing times

---

## Deployment

### Environment Variables

```bash
# Git ingestion settings
GIT_TEMP_DIR=/tmp/git_ingestion
GIT_POLL_INTERVAL_MINUTES=60

# Repository credentials (for private repos)
GIT_SSH_KEY_PATH=/path/to/ssh/key
GIT_ACCESS_TOKEN=ghp_xxx  # GitHub personal access token
```

### Docker Compose

```yaml
model_gateway:
  environment:
    - GIT_TEMP_DIR=/app/tmp/git_ingestion
    - GIT_POLL_INTERVAL_MINUTES=60
  volumes:
    - git_repos_cache:/app/tmp/git_ingestion
```

### Scheduled Polling Service

```bash
# Run as cron job or Kubernetes CronJob
# Every hour: poll all active repositories
0 * * * * curl -X POST http://model_gateway:8000/internal/llm/git-ingestion/poll
```

---

## Example: Customer Onboarding Flow

1. **Customer Signs Up:**
   - Tenant created in database
   - Tenant ID: `550e8400-e29b-41d4-a716-446655440000`

2. **Customer Creates Knowledge Base Repo:**
   ```bash
   # Customer creates: github.com/customer-xyz/kb
   # Adds: nist/controls.json, mitre/techniques.json
   ```

3. **Register Repository:**
   ```bash
   POST /internal/llm/git-ingestion/repos/register
   {
     "repo_url": "https://github.com/customer-xyz/kb",
     "repo_type": "customer",
     "tenant_id": "550e8400-e29b-41d4-a716-446655440000"
   }
   ```

4. **Initial Ingestion:**
   ```bash
   POST /internal/llm/git-ingestion/ingest
   {
     "repo_url": "https://github.com/customer-xyz/kb",
     "repo_type": "customer",
     "tenant_id": "550e8400-e29b-41d4-a716-446655440000"
   }
   ```
   
   **Result:**
   - Clones repository
   - Finds `nist/controls.json`, `mitre/techniques.json`
   - Generates embeddings
   - Stores in database with `tenant_id = 550e8400-...`

5. **Set Up Webhook:**
   - Customer configures GitHub webhook
   - URL: `https://api.sentinelgrid.com/internal/llm/git-ingestion/webhook/github?tenant_id=550e8400-...`
   - Events: Push

6. **Future Updates:**
   - Customer pushes changes → Webhook fires
   - Pipeline detects changed files
   - Processes new/modified entries
   - Updates vector database
   - No human intervention needed

---

## Monitoring & Logging

### Check Ingestion Status

```bash
# List recent ingestion jobs
GET /internal/llm/git-ingestion/jobs?repository_id={repo_id}

# Check repository status
GET /internal/llm/git-ingestion/repos/{repo_id}
```

### Database Queries

```sql
-- Check ingestion jobs
SELECT 
    repo.repo_url,
    job.status,
    job.files_processed,
    job.records_loaded,
    job.created_at
FROM git_ingestion_jobs job
JOIN git_repositories repo ON job.repository_id = repo.id
ORDER BY job.created_at DESC
LIMIT 10;

-- Check knowledge base entries per tenant
SELECT 
    CASE 
        WHEN tenant_id IS NULL THEN 'Global'
        ELSE 'Tenant: ' || tenant_id::text
    END as source,
    category,
    COUNT(*) as count
FROM cybersecurity_knowledge_base
GROUP BY tenant_id, category
ORDER BY source, category;
```

---

## Best Practices

1. **Repository Structure:**
   ```
   knowledge-base/
   ├── nist/
   │   └── controls.json
   ├── mitre/
   │   └── techniques.json
   ├── owasp/
   │   └── content.json
   └── playbooks/
       └── playbooks.json
   ```

2. **File Naming:**
   - Use descriptive names: `nist-controls.json`
   - Follow consistent structure
   - Include version information

3. **Webhook Configuration:**
   - Use secrets for verification
   - Limit to push events only
   - Test webhook delivery

4. **Tenant Isolation:**
   - Always specify tenant_id for customer repos
   - Verify tenant_id matches repository owner
   - Use NULL for global repos only

---

## Troubleshooting

### Webhook Not Firing

1. **Check webhook configuration:**
   - URL is correct
   - Events selected (Push)
   - Secret matches (if used)

2. **Check logs:**
   ```bash
   docker-compose logs model_gateway | grep webhook
   ```

3. **Test manually:**
   ```bash
   POST /internal/llm/git-ingestion/ingest
   ```

### Ingestion Failing

1. **Check repository access:**
   - Private repos need credentials
   - SSH keys or access tokens configured

2. **Check file formats:**
   - Valid JSON
   - Correct structure
   - Required fields present

3. **Check database:**
   - Vector database accessible
   - Embeddings service working
   - Sufficient storage

---

**Status:** ✅ Git-based data ingestion pipeline ready for implementation!

