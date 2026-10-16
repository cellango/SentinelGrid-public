# CSPM AI Agent Platform - Architecture

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


## Overview

The CSPM AI Agent Platform is an **Observable-Analyzer** system inspired by TheHive's Cortex. It provides cloud security posture management through dynamic, pluggable security analyzers.

## Core Concept: Observable-Analyzer Pattern

### Observables
Entities that can be analyzed:
- Cloud resources (AWS S3 bucket, EC2 instance, etc.)
- Repositories (GitHub, GitLab)
- Container images
- Web applications
- Kubernetes clusters

### Analyzers
Security tools that operate on observables:
- **Prowler**: AWS/Azure/GCP CSPM
- **ZAP**: Web application DAST
- **Trivy**: Container vulnerability scanning
- **Checkov**: IaC security scanning
- **Gitleaks**: Secret detection

### Dynamic Selection
When an observable is submitted for analysis:
1. Registry looks up applicable analyzers based on observable type
2. Filters by tags (e.g., "critical" analyzers only)
3. Runs all applicable analyzers **in parallel**
4. Aggregates findings from all tools
5. Stores unified findings in database

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   SentinelGrid API Gateway                  │
└───────────────────────┬─────────────────────────────────────┘
                        │
         ┌──────────────┴──────────────┐
         │                             │
         v                             v
┌─────────────────────┐    ┌──────────────────────────┐
│  Analyzer           │    │   MCP Server             │
│  Orchestrator       │    │   (AI Integration)       │
└──────────┬──────────┘    └──────────┬───────────────┘
           │                          │
           │ Triggers                 │ Queries
           v                          v
┌────────────────────────────────────────────┐
│         Analyzer Registry                  │
│  ┌─────────┬──────────┬────────┬────────┐ │
│  │ Prowler │   ZAP    │ Trivy  │Checkov │ │
│  └─────────┴──────────┴────────┴────────┘ │
└────────────────────────────────────────────┘
           │
           │ Stores findings
           v
┌────────────────────────────────────────────┐
│        Posture Database (posture_db)       │
│  ┌──────────┬──────────┬────────────────┐ │
│  │Observables│ Findings │ Assets         │ │
│  │Jobs      │ Scores   │ Cloud Accounts │ │
│  └──────────┴──────────┴────────────────┘ │
└────────────────────────────────────────────┘
```

## Components

### 1. Analyzer Orchestrator
**Purpose**: Cortex-style orchestration of security analyzers

**Responsibilities**:
- Receive analysis requests for observables
- Look up applicable analyzers from registry
- Execute analyzers in parallel
- Aggregate findings
- Store results in posture-service

**API Endpoints**:
- `POST /api/v1/analyze` - Trigger analysis
- `GET /api/v1/jobs/{job_id}` - Check job status
- `GET /api/v1/analyzers` - List available analyzers
- `GET /api/v1/observable-types` - List supported types

### 2. Analyzer Registry
**Purpose**: Central registry mapping observable types to analyzers

**Features**:
- Dynamic analyzer registration
- Tag-based filtering
- Observable type mapping
- Metadata about each analyzer

### 3. Base Analyzer Class
**Purpose**: Abstract base for all analyzers

**Key Methods**:
- `analyze(observable, config)` - Run analysis
- `should_run(observable)` - Decide if analyzer applies
- `get_priority(observable)` - Execution priority
- `estimate_duration(observable)` - Duration estimate

### 4. Posture Service (Future)
**Purpose**: Core REST + GraphQL API

**Responsibilities**:
- Store and query findings
- Calculate posture scores
- Manage assets and relationships
- Provide GraphQL for complex queries

### 5. MCP Server (Future)
**Purpose**: AI agent integration via Model Context Protocol

**Capabilities**:
- Query posture data
- Trigger analyses
- Explain findings using LLM
- Risk path analysis

### 6. Embedded LLM (Future)
**Purpose**: CSPM-specific AI reasoning

**Capabilities**:
- Risk analysis explanations
- Remediation recommendations
- Natural language posture summaries
- Compliance gap analysis

## Database Schema

### Separate Database: `posture_db`
- **Why**: Clean separation for future spin-off
- **Port**: 5433 (vs main SentinelGrid on 5432)
- **ORM**: SQLAlchemy

### Tables

**observables**: Entities that can be analyzed
- id, tenant_id, observable_type, observable_value, metadata, tags

**assets**: Physical/logical infrastructure assets
- id, tenant_id, asset_id, asset_type, cloud_account_id, risk_score

**findings**: Unified findings from all analyzers
- id, tenant_id, asset_id, source, tool, severity, status, evidence

**analyzer_jobs**: Track analyzer execution
- id, tenant_id, analyzer_name, observable_type, status, findings_count

**posture_scores**: Calculated risk scores
- id, tenant_id, scope_type, scope_id, score, grade, findings_breakdown

**cloud_accounts**: Connected cloud accounts
- id, tenant_id, provider, account_id, role_arn, status

**repositories**: Code repositories
- id, tenant_id, repo_url, has_terraform, has_dockerfile, scan_enabled

## Multi-Tenancy

Every table includes `tenant_id` column with index. All queries MUST filter by tenant_id to ensure data isolation.

## Scalability

- **Parallel Execution**: Analyzers run concurrently via asyncio
- **Job Queue**: Redis-based queue for async processing
- **Horizontal Scaling**: Stateless services can scale independently
- **Database Partitioning**: Future: partition by tenant_id

## Security

- **Credential Management**: Encrypted at rest, use secret managers
- **API Authentication**: JWT tokens from main SentinelGrid
- **Internal Services**: Use internal service tokens
- **Network Isolation**: Services communicate via internal network

## Observable Types

| Type | Description | Analyzers |
|------|-------------|-----------|
| `web_application` | Web app | ZAP, Nuclei, SSL |
| `aws_s3_bucket` | S3 bucket | Prowler S3 |
| `aws_account` | AWS account | Prowler full scan |
| `docker_image` | Container | Trivy, Grype |
| `git_repository` | Git repo | Checkov, Gitleaks |
| `k8s_cluster` | K8s cluster | Kube-bench, Falco |

## Data Flow: Analyzing a Web Application

1. User submits: `POST /api/posture/analyze`
   ```json
   {
     "observable_type": "web_application",
     "observable_value": "https://app.example.com"
   }
   ```

2. API Gateway proxies to Analyzer Orchestrator

3. Orchestrator queries registry:
   - Finds: ZAP, Nuclei, SSL analyzers

4. Orchestrator runs all 3 analyzers in parallel

5. Each analyzer returns findings:
   - ZAP: 5 findings (2 high, 3 medium)
   - Nuclei: 2 findings (1 critical, 1 high)
   - SSL: 1 finding (1 low)

6. Orchestrator aggregates: 8 total findings

7. Orchestrator stores findings in posture_db

8. Returns job ID to user

9. User can query: `GET /api/posture/jobs/{job_id}`

## Extension Points

### Adding New Analyzers

1. Create analyzer class inheriting from `BaseAnalyzer`
2. Define metadata (name, version, supported types, tags)
3. Implement `analyze()` method
4. Register with registry
5. Done! No changes to orchestrator needed

### Adding New Observable Types

1. Add to `ObservableType` enum in models
2. Create analyzers supporting the new type
3. Register analyzers
4. Observable type is now supported

## Future Enhancements

- **Posture Service**: Full REST + GraphQL API
- **MCP Server**: AI agent integration
- **Embedded LLM**: CSPM-specific reasoning
- **Scheduled Scans**: Cron-like scheduling
- **Webhooks**: Real-time notifications
- **Custom Analyzers**: Plugin system for third-party analyzers

## Performance Considerations

- **Parallel Execution**: Up to N analyzers run concurrently
- **Timeout Handling**: Each analyzer has configurable timeout
- **Resource Limits**: Analyzers can specify resource requirements
- **Caching**: Cache analyzer results for duplicate observables
- **Rate Limiting**: Prevent abuse of expensive analyzers

## Monitoring

- **Analyzer Success Rate**: Track success/failure per analyzer
- **Execution Duration**: Monitor analyzer performance
- **Finding Volume**: Track findings per tenant/analyzer
- **Queue Depth**: Monitor job queue backlog
- **Database Performance**: Track query performance

## Deployment

### Development
```bash
cd posture-platform
docker-compose up -d
```

### Production
- Use managed PostgreSQL
- Use managed Redis
- Deploy services to Kubernetes
- Use secret managers for credentials
- Enable database backups
- Configure auto-scaling

## Related Documentation

- `Data Model` (historical reference unavailable) - Database schema details
- [Analyzer Development](../analyzers/README.md) - How to create analyzers
- `API Reference` (historical reference unavailable) - REST API documentation
- `MCP Integration` (historical reference unavailable) - AI agent integration

