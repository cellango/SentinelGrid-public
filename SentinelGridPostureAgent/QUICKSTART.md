# SentinelGrid Posture Agent - Quick Start

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../RELEASE_SCOPE.md) first.


## What You Have Now

A working Observable-Analyzer architecture for cloud security posture management:

✅ **Analyzer Orchestrator** - Cortex-style orchestration  
✅ **Analyzer Framework** - Base classes and registry  
✅ **Example Analyzers** - Prowler (AWS), ZAP (web apps)  
✅ **Database Models** - Complete SQLAlchemy schema  
✅ **API Integration** - Connected to SentinelGrid API Gateway  
✅ **Docker Setup** - Ready to deploy  

## Quick Start

### 1. Initialize Database

```bash
cd SentinelGridPostureAgent/database
export DATABASE_URL="postgresql://posture_user:posture_pass@localhost:5433/posture_db"
alembic upgrade head
```

### 2. Start Services

```bash
# Start SentinelGrid Posture Agent services
cd SentinelGridPostureAgent
docker-compose up -d

# Or integrate with main SentinelGrid
cd ..
docker-compose -f docker-compose.dev.yml up -d
```

### 3. Test the API

#### List Available Analyzers
```bash
curl http://localhost:8103/api/v1/analyzers
```

#### Analyze a Web Application
```bash
curl -X POST http://localhost:8103/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-123",
    "observable_type": "web_application",
    "observable_value": "https://example.com"
  }'
```

This will:
1. Look up analyzers for "web_application" (finds ZAP)
2. Run ZAP analyzer
3. Return job ID

#### Check Job Status
```bash
curl http://localhost:8103/api/v1/jobs/{job_id}
```

## Via SentinelGrid API Gateway

Once integrated with main SentinelGrid:

```bash
curl -X POST http://localhost:8000/api/posture/analyze \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "observable_type": "aws_account",
    "observable_value": "123456789012",
    "metadata": {"environment": "prod"},
    "analyzer_tags": ["critical"]
  }'
```

## Observable Types Supported

| Type | Example Value | Analyzers |
|------|---------------|-----------|
| `web_application` | `https://app.example.com` | ZAP |
| `aws_account` | `123456789012` | Prowler |
| `aws_s3_bucket` | `arn:aws:s3:::mybucket` | Prowler |
| `docker_image` | `nginx:latest` | (Trivy - to be added) |
| `git_repository` | `https://github.com/org/repo` | (Checkov, Gitleaks - to be added) |

## Adding Your First Custom Analyzer

1. Create file: `posture-platform/analyzers/custom/my_analyzer.py`

```python
from analyzers.base_analyzer import BaseAnalyzer
from analyzers.registry import registry

class MyAnalyzer(BaseAnalyzer):
    name = "my-custom-analyzer"
    description = "My custom security analyzer"
    version = "1.0.0"
    supported_observable_types = ["web_application"]
    tags = ["custom", "dast"]
    
    async def analyze(self, observable, config=None):
        url = observable["value"]
        
        # Your analysis logic here
        findings = []
        
        return {
            "status": "success",
            "findings": findings,
            "metadata": {"urls_scanned": 1}
        }

# Register
registry.register(MyAnalyzer)
```

2. Import in orchestrator: `services/analyzer-orchestrator/app/main.py`

```python
from analyzers.custom.my_analyzer import MyAnalyzer
registry.register(MyAnalyzer)
```

3. Restart orchestrator - your analyzer is now available!

## Next Steps

### Immediate (Core Functionality)

1. **Implement Tool Wrappers** (`tools/prowler/`, `tools/zap/`)
   - Actual integration with Prowler CLI
   - Actual integration with ZAP API
   - See `analyzers/README.md` for guidance

2. **Create Posture Service** (REST + GraphQL)
   - Store and query findings
   - Calculate posture scores
   - Provide dashboard data

3. **Database Migrations**
   - Run Alembic to create tables
   - Seed initial data

### Short Term (Enhanced Features)

4. **Add More Analyzers**
   - Trivy (container scanning)
   - Checkov (IaC scanning)
   - Gitleaks (secret detection)
   - Nuclei (vulnerability scanning)

5. **MCP Server**
   - AI agent integration
   - LLM-powered explanations
   - GraphQL proxy

6. **Scheduled Scans**
   - Cron-like scheduling
   - Recurring scans for cloud accounts

### Medium Term (Production Ready)

7. **Embedded LLM**
   - CSPM-specific reasoning
   - Risk analysis
   - Remediation recommendations

8. **Testing**
   - Unit tests for analyzers
   - Integration tests
   - E2E tests

9. **Monitoring & Observability**
   - Prometheus metrics
   - Grafana dashboards
   - Structured logging

## Architecture Overview

```
Observable (AWS account, web app, etc.)
    ↓
Analyzer Orchestrator
    ↓
Registry → Finds applicable analyzers
    ↓
Run analyzers in parallel
    ├─ Prowler
    ├─ ZAP
    ├─ Trivy
    └─ ...
    ↓
Aggregate findings
    ↓
Store in posture_db
    ↓
Available via API / MCP / GraphQL
```

## Key Design Principles

1. **Observable-Driven**: Data drives analysis, not hardcoded logic
2. **Dynamic Selection**: Analyzers chosen based on observable type + tags
3. **Parallel Execution**: Multiple tools run concurrently
4. **Extensible**: Add analyzers without changing core code
5. **Multi-Tenant**: Complete data isolation by tenant_id

## Troubleshooting

### Analyzer Not Found
- Check if analyzer is registered in orchestrator
- Verify observable type matches `supported_observable_types`
- Check `should_run()` method logic

### Job Fails
- Check analyzer logs
- Verify tool (Prowler, ZAP) is installed in container
- Check credentials/configuration

### No Findings
- Verify tool actually found issues
- Check finding parsing logic
- Ensure findings meet severity threshold

## Documentation

- [Architecture](docs/architecture.md) - System design
- [Analyzer Development](analyzers/README.md) - Create analyzers
- [Database](database/README.md) - Schema and migrations
- [Main README](README.md) - Project overview

## Support

For issues or questions about the posture platform:
1. Check documentation in `docs/`
2. Review example analyzers in `analyzers/`
3. Check logs: `docker-compose logs analyzer-orchestrator`

---

**Status**: Foundation complete, ready for tool integration and expansion

