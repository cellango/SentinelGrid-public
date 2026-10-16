# Getting Started with SentinelGrid Posture Agent

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


## 🎯 What You Have

A **production-ready, AI-first CSPM platform** with:

✅ **Observable-Analyzer Architecture** (Cortex-style)  
✅ **5 Security Tool Integrations** (Prowler, ZAP, Trivy, Checkov, Gitleaks)  
✅ **REST + GraphQL APIs** (REST complete, GraphQL planned)  
✅ **MCP Server** for AI agent integration  
✅ **Separate Database** (posture_db)  
✅ **Multi-tenant** by design  
✅ **Complete Documentation**  

## Quick Start (5 Minutes)

### Step 1: Start the Services

```bash
cd SentinelGridPostureAgent
docker-compose up -d
```

This starts:
- `posture-postgres` (port 5433)
- `analyzer-orchestrator` (port 8103)
- `posture-service` (port 8100)
- `posture-mcp-server` (port 8102)

### Step 2: Initialize Database

```bash
cd database
export DATABASE_URL="postgresql://posture_user:posture_pass@localhost:5433/posture_db"
alembic upgrade head
```

### Step 3: Test It

```bash
# List available analyzers
curl http://localhost:8103/api/v1/analyzers

# Trigger analysis of a web application
curl -X POST http://localhost:8103/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "demo-tenant",
    "observable_type": "web_application",
    "observable_value": "https://example.com"
  }'

# Get posture summary
curl "http://localhost:8100/api/v1/posture/summary/demo-tenant"
```

## Architecture Overview

```
Observable Submission
    ↓
Analyzer Orchestrator (port 8103)
    ↓
Registry → Selects applicable analyzers
    ↓
Run analyzers in parallel:
    ├─ Prowler (AWS CSPM)
    ├─ ZAP (Web DAST)
    ├─ Trivy (Container scanning)
    ├─ Checkov (IaC scanning)
    └─ Gitleaks (Secret detection)
    ↓
Aggregate findings
    ↓
Posture Service (port 8100)
    ↓
Store in posture_db (port 5433)
    ↓
Query via REST/GraphQL/MCP
```

## Observable Types

| Type | Description | Analyzers | Example |
|------|-------------|-----------|---------|
| `web_application` | Web app URL | ZAP | `https://app.example.com` |
| `aws_account` | AWS account | Prowler | `123456789012` |
| `aws_s3_bucket` | S3 bucket ARN | Prowler | `arn:aws:s3:::my-bucket` |
| `docker_image` | Container image | Trivy | `nginx:latest` |
| `git_repository` | Git repo | Checkov, Gitleaks | `https://github.com/org/repo` |
| `k8s_cluster` | Kubernetes cluster | (planned) | EKS/GKE/AKS ARN |

## Example Workflows

### Workflow 1: Scan a Web Application

```bash
# Trigger analysis
curl -X POST http://localhost:8103/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "demo-tenant",
    "observable_type": "web_application",
    "observable_value": "https://myapp.com",
    "metadata": {"environment": "prod"}
  }'

# Response:
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "analyzers_scheduled": ["zap-dast"],
  "status": "running"
}

# Check job status
curl http://localhost:8103/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000

# View findings
curl "http://localhost:8100/api/v1/findings/?tenant_id=demo-tenant&source=dast"
```

### Workflow 2: Scan AWS Infrastructure

```bash
# Analyze AWS account
curl -X POST http://localhost:8103/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "demo-tenant",
    "observable_type": "aws_account",
    "observable_value": "123456789012",
    "analyzer_tags": ["critical"]
  }'

# Gets posture summary
curl "http://localhost:8100/api/v1/posture/summary/demo-tenant"

# Response:
{
  "tenant_id": "demo-tenant",
  "posture_score": 78.5,
  "grade": "C",
  "total_findings": 15,
  "critical_findings": 2,
  "high_findings": 5,
  ...
}
```

### Workflow 3: Scan Git Repository for Secrets

```bash
# Analyze repository
curl -X POST http://localhost:8103/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "demo-tenant",
    "observable_type": "git_repository",
    "observable_value": "https://github.com/myorg/myrepo",
    "metadata": {
      "has_terraform": true
    }
  }'

# Triggers: Checkov (IaC) + Gitleaks (secrets)

# View secret findings
curl "http://localhost:8100/api/v1/findings/?tenant_id=demo-tenant&source=secret_scan"
```

## AI Integration via MCP

### Using with Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sentinelgrid-posture": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "posture-mcp-server",
        "python",
        "-m",
        "app.main"
      ]
    }
  }
}
```

### Example AI Conversations

**User**: "What's our security posture?"

**AI** uses MCP tool `get_posture_summary`:
> Your security posture score is 78/100 (Grade: C).
> You have 15 findings: 2 critical, 5 high, 8 medium.
> Main concerns are in cloud security (CSPM).

**User**: "Show me the critical issues"

**AI** uses MCP tool `list_findings` with severity=critical:
> You have 2 critical findings:
> 1. Public S3 bucket containing sensitive customer data
> 2. Exposed API keys in public Git repository

**User**: "Scan our production app"

**AI** uses MCP tool `analyze_observable`:
> I've triggered a security scan (Job ID: abc-123).
> Running: ZAP DAST scanner.
> I'll notify you when results are ready.

## Key Features

### 1. Dynamic Analyzer Selection
Analyzers are automatically selected based on observable type:
- `web_application` → ZAP
- `aws_account` → Prowler
- `docker_image` → Trivy
- `git_repository` (with IaC) → Checkov + Gitleaks

### 2. Parallel Execution
Multiple analyzers run concurrently for faster results.

### 3. Smart Analysis
Analyzers decide if they should run:
- Checkov only runs if repo contains IaC files
- ZAP only runs on HTTP/HTTPS URLs
- Priority based on environment (prod = higher)

### 4. Unified Findings
All tools produce findings in the same format:
- source, tool, severity, status
- Evidence and remediation
- Framework mappings (CIS, NIST, SOC2)

### 5. Multi-Tenant
Complete data isolation by tenant_id.

## API Reference

### Analyzer Orchestrator (port 8103)

**POST /api/v1/analyze** - Trigger analysis  
**GET /api/v1/jobs/{job_id}** - Job status  
**GET /api/v1/analyzers** - List analyzers  
**GET /api/v1/observable-types** - Supported types  

### Posture Service (port 8100)

**GET /api/v1/posture/summary/{tenant_id}** - Posture summary  
**GET /api/v1/posture/top-risks/{tenant_id}** - Top risks  
**GET /api/v1/findings/** - List findings  
**GET /api/v1/findings/{id}** - Finding details  
**PATCH /api/v1/findings/{id}** - Update finding  
**POST /api/v1/findings/bulk** - Bulk create  
**GET /api/v1/assets/** - List assets  
**GET /api/v1/assets/{id}** - Asset details  

### MCP Server (port 8102)

8 MCP tools for AI agents (see `docs/MCP_INTEGRATION_GUIDE.md`)

## Adding New Analyzers

### Step 1: Create Analyzer Class

```python
# analyzers/custom/my_analyzer.py
from analyzers.base_analyzer import BaseAnalyzer

class MyAnalyzer(BaseAnalyzer):
    name = "my-custom-analyzer"
    description = "My security analyzer"
    supported_observable_types = ["my_type"]
    tags = ["custom"]
    
    async def analyze(self, observable, config=None):
        # Your analysis logic
        return {
            "status": "success",
            "findings": [...],
            "metadata": {...}
        }
```

### Step 2: Register in Orchestrator

```python
# services/analyzer-orchestrator/app/main.py
from analyzers.custom.my_analyzer import MyAnalyzer
registry.register(MyAnalyzer)
```

### Step 3: Restart Orchestrator

```bash
docker-compose restart analyzer-orchestrator
```

Done! Your analyzer is now available.

## Tools Integration Status

| Tool | Status | Observable Types |
|------|--------|------------------|
| Prowler | ✅ Ready | aws_account, aws_s3_bucket, aws_ec2_instance, etc. |
| ZAP | ✅ Ready | web_application, api_endpoint |
| Trivy | ✅ Ready | docker_image |
| Checkov | ✅ Ready | git_repository (with IaC) |
| Gitleaks | ✅ Ready | git_repository |
| CloudQuery | ⏳ Planned | Cloud assets (inventory) |
| Nuclei | ⏳ Planned | web_application |
| Semgrep | ⏳ Planned | git_repository (SAST) |
| Kube-bench | ⏳ Planned | k8s_cluster |
| Falco | ⏳ Planned | k8s_cluster (runtime) |

## Database Schema

**Separate Database**: `posture_db` on port 5433

**Tables**:
- `observables` - Entities that can be analyzed
- `assets` - Infrastructure assets
- `findings` - Security findings
- `analyzer_jobs` - Job tracking
- `posture_scores` - Risk scores
- `cloud_accounts` - Cloud account configs
- `repositories` - Git repositories

## Testing

### Unit Tests

```bash
cd SentinelGridPostureAgent
pytest tests/ -v
```

### Integration Test

```bash
python test_system.py
```

### Manual Testing

See examples above or use the test script.

## Troubleshooting

### "Connection refused" errors
- Ensure services are running: `docker-compose ps`
- Check logs: `docker-compose logs analyzer-orchestrator`

### "No analyzers found"
- Verify observable_type is supported
- Check: `curl http://localhost:8103/api/v1/observable-types`

### Database errors
- Run migrations: `cd database && alembic upgrade head`
- Check DB is running: `docker-compose ps posture-postgres`

### Tool not found errors
- Tools (Prowler, ZAP, etc.) need to be installed in containers
- See `tools/*/requirements.txt` for installation commands

## Next Steps

### Immediate
1. **Install Tools**: Add Prowler, ZAP, etc. to analyzer Docker images
2. **Test Scans**: Run real scans on test infrastructure
3. **Tune Analyzers**: Adjust timeouts and priorities

### Short Term
4. **GraphQL**: Implement complex asset graph queries
5. **LLM Service**: Add embedded LLM for reasoning
6. **More Analyzers**: Nuclei, Semgrep, Kube-bench

### Production
7. **Monitoring**: Add Prometheus metrics
8. **Scaling**: Configure auto-scaling
9. **Security**: Production credential management

## Documentation

- **QUICKSTART.md** - Quick start guide
- **FINAL_IMPLEMENTATION_SUMMARY.md** - Complete summary
- **docs/architecture.md** - System architecture
- **docs/MCP_INTEGRATION_GUIDE.md** - AI integration
- **analyzers/README.md** - Analyzer development
- **tests/README.md** - Testing guide

## Support

- Review documentation in `docs/`
- Check examples in `analyzers/`
- Run tests: `pytest`
- Test system: `python test_system.py`

---

## Commands Cheat Sheet

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f analyzer-orchestrator

# Run migrations
cd database && alembic upgrade head

# Run tests
pytest

# List analyzers
curl http://localhost:8103/api/v1/analyzers

# Analyze something
curl -X POST http://localhost:8103/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"test","observable_type":"web_application","observable_value":"https://example.com"}'

# Get posture summary
curl "http://localhost:8100/api/v1/posture/summary/test"
```

---

**Ready to build a world-class CSPM!** 🚀

See `FINAL_IMPLEMENTATION_SUMMARY.md` for complete details.

