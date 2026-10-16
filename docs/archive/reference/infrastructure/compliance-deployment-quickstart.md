# Compliance Platform - Deployment Quickstart

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Estimated Time:** 60 minutes  
**Prerequisites:** PostgreSQL, Keycloak, Docker

---

## Step 1: Database Migrations (10 minutes)

```bash
cd /path/to/SentinelGrid

# Run all compliance migrations in order
psql -U sentinelgrid -d sentinelgrid << 'EOF'
\i backend/migrations/026_platform_audit_logs.sql
\i backend/migrations/027_access_review_campaigns.sql
\i backend/migrations/028_jml_workflows.sql
\i backend/migrations/029_mfa_enforcement_policies.sql
\i backend/migrations/030_compliance_control_library.sql
\i backend/migrations/031_evidence_repository.sql
\i backend/migrations/035_report_scheduling_and_storage.sql
EOF

# Verify tables created
psql -U sentinelgrid -d sentinelgrid -c "
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN (
    'platform_audit_logs',
    'access_review_campaigns',
    'jml_workflows',
    'mfa_enforcement_policies',
    'compliance_frameworks',
    'evidence_packages',
    'generated_reports',
    'report_schedules',
    'report_llm_documents'
  )
ORDER BY table_name;
"

# Should show 9 tables minimum
```

---

## Step 2: Ensure Postgres with pgvector (5 minutes)

```bash
# Start Postgres with pgvector (docker-compose.dev.yml uses pgvector/pgvector:pg16)
docker compose -f docker-compose.dev.yml up -d postgres

# Verify running
docker compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -c "SELECT extname FROM pg_extension WHERE extname='vector';"
```

---

## Step 3: Install Dependencies (10 minutes)

```bash
# Reporting Service
cd backend/services/reporting_service
pip install -r requirements.txt

# This installs:
# - weasyprint (PDF generation)
# - matplotlib (charts)
# - sentence-transformers (embeddings)
# - psycopg2-binary (Postgres/pgvector access)
# - PyPDF2 (PDF text extraction)
# - APScheduler (cron scheduling)

# Verify installations
python -c "import weasyprint; print('WeasyPrint OK')"
python -c "import matplotlib; print('Matplotlib OK')"
python -c "from sentence_transformers import SentenceTransformer; print('Transformers OK')"
python -c "import psycopg2; print('psycopg2 OK')"
```

---

## Step 4: Deploy Audit Service (5 minutes)

```bash
cd backend/services/audit_service

# Option A: Docker
docker build -t sentinelgrid/audit-service .
docker run -d \
  --name audit-service \
  -p 8010:8000 \
  -e DATABASE_URL="postgresql://sentinelgrid:sentinelgrid@localhost:5432/sentinelgrid" \
  sentinelgrid/audit-service

# Option B: Direct
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8010 &

# Verify health
curl http://localhost:8010/health
# Expected: {"status":"healthy"}
```

---

## Step 5: Configure Backups (5 minutes)

```bash
# Make scripts executable
chmod +x infra/shared/scripts/backup-*.sh
chmod +x infra/shared/scripts/restore-system.sh

# Configure environment (edit as needed)
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=sentinelgrid
export POSTGRES_PASSWORD=your_password
export POSTGRES_DB=sentinelgrid
export KEYCLOAK_URL=http://localhost:8080
export KEYCLOAK_ADMIN_USER=admin
export KEYCLOAK_ADMIN_PASSWORD=admin_password
export BACKUP_DIR=/var/backups/sentinelgrid
export S3_BACKUP_BUCKET=sentinelgrid-backups-yourdomain
export BACKUP_RETENTION_DAYS=30

# Test backup scripts
./infra/shared/scripts/backup-postgres.sh
./infra/shared/scripts/backup-keycloak.sh

# Setup cron jobs
crontab -e
# Add these lines:
0 2 * * * /path/to/infra/shared/scripts/backup-postgres.sh >> /var/log/sentinelgrid/backup-postgres.log 2>&1
0 3 * * * /path/to/infra/shared/scripts/backup-keycloak.sh >> /var/log/sentinelgrid/backup-keycloak.log 2>&1
```

---

## Step 6: Seed Control Library Data (10 minutes)

```bash
# Import SOC 2 controls
psql -U sentinelgrid -d sentinelgrid << 'EOF'
-- This will be part of a data migration script
-- For now, the JSON files are created in:
-- backend/services/compliance_service/app/data/

-- Frameworks are already seeded from migration 030
SELECT framework_name, version FROM compliance_frameworks;
EOF
```

---

## Step 7: Test Report Generation (15 minutes)

```bash
# Test SOC 2 report generation
curl -X POST http://localhost:8000/api/v1/reports/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -d '{
    "report_type": "soc2_coverage",
    "period_start": "2025-11-01",
    "period_end": "2025-11-30"
  }'

# Check report status
curl http://localhost:8000/api/v1/reports

# Download report (once ready)
curl http://localhost:8000/api/v1/reports/{report_id}/download/pdf \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -o SOC2_Report.pdf

# View PDF
open SOC2_Report.pdf  # macOS
# or
xdg-open SOC2_Report.pdf  # Linux
```

---

## Step 8: Test LLM Q&A (10 minutes)

```bash
# Wait for report to be ingested (automatic, ~1 minute after generation)

# Query your reports
curl -X POST http://localhost:8000/api/v1/reports/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -d '{
    "query": "What is our overall SOC 2 compliance coverage?"
  }'

# Expected response:
{
  "query": "What is our overall SOC 2 compliance coverage?",
  "answer": "Based on your SOC 2 Coverage Report, your overall compliance coverage is 87.5%...",
  "sources": [...]
}
```

---

## Step 9: Setup Report Schedule (5 minutes)

```bash
# Create weekly SOC 2 report schedule
curl -X POST http://localhost:8000/api/v1/reports/schedules \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -d '{
    "report_type": "soc2_coverage",
    "schedule_name": "Weekly SOC 2 Report",
    "cron_expression": "0 9 * * MON",
    "recipients": ["compliance@yourcompany.com"],
    "is_active": true
  }'

# Verify schedule
curl http://localhost:8000/api/v1/reports/schedules
```

---

## Step 10: Test Tenant Isolation (CRITICAL - 10 minutes)

```bash
cd backend/tests/compliance

# Run security tests
pytest test_tenant_isolation.py -v

# All tests MUST pass:
# ✓ test_reports_tenant_isolation_database
# ✓ test_audit_logs_tenant_isolation
# ✓ test_access_review_campaigns_tenant_isolation
# ✓ test_llm_query_tenant_isolation

# If any test fails, DO NOT DEPLOY TO PRODUCTION
```

---

## Verification Checklist

- [ ] All 7 migrations ran successfully
- [ ] Qdrant is running and accessible
- [ ] Audit service health check passes
- [ ] Reporting service dependencies installed
- [ ] Backup scripts execute successfully
- [ ] Test report generates and downloads
- [ ] LLM Q&A returns relevant answers
- [ ] Report schedule created successfully
- [ ] **CRITICAL**: Tenant isolation tests pass
- [ ] Frontend compliance pages load

---

## Troubleshooting

### Issue: WeasyPrint Installation Fails

**macOS:**
```bash
brew install pango cairo
pip install weasyprint
```

**Ubuntu/Debian:**
```bash
sudo apt-get install -y libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
pip install weasyprint
```

### Issue: Postgres/pgvector Connection Failed

```bash
# Check if Postgres is running
docker compose -f docker-compose.dev.yml ps postgres

# View logs
docker compose -f docker-compose.dev.yml logs postgres

# Restart if needed
docker compose -f docker-compose.dev.yml restart postgres
```

### Issue: Report Generation Timeout

**Increase timeout in reporting service:**
```python
# In app/core/config.py
REPORT_GENERATION_TIMEOUT = 120  # seconds
```

---

## Production Considerations

### S3 Configuration

```bash
# Create production S3 buckets
aws s3 mb s3://sentinelgrid-reports-prod
aws s3 mb s3://sentinelgrid-backups-prod

# Enable versioning (for backups)
aws s3api put-bucket-versioning \
  --bucket sentinelgrid-backups-prod \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket sentinelgrid-reports-prod \
  --server-side-encryption-configuration '{"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}'

# Set bucket policy (deny public access)
aws s3api put-public-access-block \
  --bucket sentinelgrid-reports-prod \
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

### Monitoring

```bash
# Monitor report generation
tail -f /var/log/sentinelgrid/reporting-service.log

# Monitor audit logs
tail -f /var/log/sentinelgrid/audit-service.log

# Monitor backup jobs
tail -f /var/log/sentinelgrid/backup-*.log
```

---

**Status:** Ready for Deployment  
**Last Updated:** December 2, 2025
