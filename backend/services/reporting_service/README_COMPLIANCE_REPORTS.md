# Compliance Reports - Implementation Guide

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../RELEASE_SCOPE.md) first.


Professional compliance reports with PDF/CSV export, scheduling, and LLM Q&A.

---

## Report Types

### 1. SOC 2 Coverage Report
**Template:** `soc2_coverage_report.html`  
**Purpose:** SOC 2 Type II audit preparation  
**Audience:** Auditors, CISO, Compliance team

**Sections:**
- Executive Summary (coverage %, gaps)
- Control Coverage by Category (CC1-CC9)
- Per-Control Details with evidence
- Gap Analysis
- Evidence Summary

### 2. IAM & MFA Hygiene Report
**Template:** `iam_mfa_hygiene_report.html`  
**Purpose:** Access control compliance  
**Audience:** IT Security, Auditors

**Sections:**
- User Statistics
- MFA Coverage (overall & privileged)
- Privileged Access Analysis
- Access Reviews Summary
- Dormant Accounts

### 3. Log Coverage & Retention Report
**Template:** `log_coverage_report.html`  
**Purpose:** Logging compliance proof  
**Audience:** Auditors, SecOps

**Sections:**
- Connected Log Sources
- Retention Configuration
- Coverage Gaps
- Log Integrity Status

### 4. Incident & Response Report
**Template:** `incident_response_report.html`  
**Purpose:** Incident response effectiveness  
**Audience:** Executives, SOC team

**Sections:**
- Incident Statistics
- Response Metrics (MTTD/MTTR)
- Playbook Usage
- Actions Taken

### 5. Cloud Posture Report
**Template:** `cloud_posture_report.html`  
**Purpose:** Cloud security status  
**Audience:** Engineering, Compliance

**Sections:**
- Posture Score by Provider
- Top Findings
- Remediation Status
- CIS Benchmark Mapping

### 6. NIST CSF Coverage Report
**Template:** `nist_csf_report.html`  
**Purpose:** NIST CSF alignment proof  
**Audience:** Executives, Auditors

**Sections:**
- Function Coverage (5 functions)
- Per-Function Metrics
- Maturity Assessment

### 7. Security One-Pager
**Template:** `security_onepager_report.html`  
**Purpose:** Customer-facing security summary  
**Audience:** Customers' customers (RFPs)

**Sections:**
- Security Posture Summary
- Key Capabilities
- Compliance Status
- Security Metrics

---

## Report Generation Flow

```python
# 1. Collect data (tenant-scoped)
data = collect_report_data(tenant_id, realm_name, report_type)

# 2. Generate HTML from template
html = render_template(template_name, data, tenant_config)

# 3. Convert HTML → PDF
pdf_path = pdf_engine.generate_pdf(html, output_path)

# 4. Export data → CSV
csv_path = csv_exporter.export_table(data, csv_output_path)

# 5. Store in database
report = create_generated_report(
    tenant_id=tenant_id,
    realm_name=realm_name,
    report_type=report_type,
    file_path_pdf=pdf_path,
    file_path_csv=csv_path
)

# 6. Ingest to Vector DB for LLM Q&A
llm_ingestor.ingest_report(report)

# 7. Mark as ready
report.status = 'ready'
db.commit()
```

---

## Professional PDF Features

### Branding
- Tenant logo on cover page
- Custom primary/secondary colors
- Tenant name throughout

### Layout
- A4 page size
- 2.5cm margins
- Page numbers
- Headers and footers
- Table of contents (optional)

### Content
- Cover page with metadata
- Executive summary (1 page)
- Detailed sections with tables
- Charts and visualizations (embedded as images)
- Confidentiality notice

### Styling
- Professional typography (Arial)
- Color-coded badges (success/warning/danger)
- Responsive tables
- Section breaks (page breaks)
- Metric cards with large values

---

## CSV Export

Each report includes CSV export with:
- All data tables from the report
- Multiple sheets (if multiple tables)
- Headers with human-readable names
- Formatted values (dates, percentages)

**Example CSV Structure:**
```csv
=== SOC 2 Control Coverage ===

Control ID,Control Name,Status,Coverage Level,Evidence Count
CC6.1,Logical and physical access controls,Implemented,Full,5
CC6.2,Prior authorization of access,Implemented,Full,3
CC6.3,Remove access when no longer required,Implemented,Full,4
```

---

## Automated Scheduling

### Cron Expressions

```bash
# Daily at 9am
0 9 * * *

# Weekly on Monday 9am
0 9 * * MON

# Monthly on 1st at 9am
0 9 1 * *

# Quarterly on 1st at 9am
0 9 1 */3 *

# First Monday of month at 9am
0 9 1-7 * MON
```

### Schedule Configuration

```python
# Create schedule
schedule = {
    "report_type": "soc2_coverage",
    "schedule_name": "Weekly SOC 2 Report",
    "cron_expression": "0 9 * * MON",
    "timezone": "America/New_York",
    "recipients": ["compliance@acme.com"],
    "is_active": True
}

# System automatically:
# 1. Generates report at scheduled time
# 2. Stores PDF & CSV
# 3. Ingests to Vector DB
# 4. Emails to recipients
# 5. Updates schedule status
```

---

## LLM Q&A Integration (pgvector path)

### How It Will Work

1. **Ingestion**: Report text extracted from PDF and chunked.
2. **Embedding**: Each chunk converted to an embedding by the embedding service.
3. **Storage**: Embeddings stored in PostgreSQL with the pgvector extension, with tenant/realm metadata.
4. **Query**: User query converted to an embedding.
5. **Search**: Vector similarity search with mandatory tenant/realm filter.
6. **Generation**: LLM generates answer from retrieved chunks.
7. **Audit**: Query logged for compliance.

**Note:** The legacy Qdrant flow is removed. The current code keeps vector Q&A disabled until the pgvector-backed embedding ingestion endpoint is wired in.

### Example Queries (once enabled)

- "What is our overall SOC 2 compliance score?"
- "How many users have MFA enabled?"
- "What were our top security incidents last month?"
- "Show me our audit log retention policy?"
- "What is our cloud security posture score?"

---

## File Naming Convention

All reports follow this naming pattern:

```
{ReportType}_{YYYY-MM-DD}_{TenantName}.{pdf|csv}

Examples:
- SOC2_Coverage_Report_2025-12-02_AcmeCorp.pdf
- IAM_MFA_Hygiene_Report_2025-12-02_AcmeCorp.csv
- NIST_CSF_Coverage_2025-12-02_TechStartup.pdf
```

Date format: `YYYY-MM-DD` (ISO 8601)

---

## Storage Structure

### S3 Bucket Organization

```
s3://sentinelgrid-reports/
  {tenant_id}/
    {realm_name}/
      SOC2_Coverage_Report_2025-12-02_AcmeCorp.pdf
      SOC2_Coverage_Report_2025-12-02_AcmeCorp.csv
      IAM_MFA_Hygiene_Report_2025-12-02_AcmeCorp.pdf
      ...
```

**Security:**
- Tenant-namespaced paths
- Server-side encryption (SSE-S3)
- Pre-signed URLs for downloads (5-minute expiration)
- Bucket policy denies public access

---

## Dependencies

```txt
weasyprint>=60.0        # PDF generation
matplotlib>=3.7.0       # Charts
sentence-transformers   # LLM embeddings
PyPDF2                 # PDF text extraction
APScheduler            # Cron scheduling
jinja2                 # Template rendering
psycopg2-binary        # Postgres/pgvector access
```

---

## Testing

### Generate Test Report

```bash
curl -X POST http://localhost:8000/api/v1/reports/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {TOKEN}" \
  -d '{
    "report_type": "soc2_coverage",
    "period_start": "2025-11-01",
    "period_end": "2025-11-30"
  }'
```

### Test LLM Q&A

```bash
curl -X POST http://localhost:8000/api/v1/reports/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {TOKEN}" \
  -d '{"query": "What is our MFA coverage?"}'
```

---

## Troubleshooting

### WeasyPrint Installation Issues

**macOS:**
```bash
brew install pango cairo
pip install weasyprint
```

**Ubuntu:**
```bash
sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0
pip install weasyprint
```

### Vector path disabled

- The legacy Qdrant path is removed. Enable vector Q&A by wiring the embedding service to Postgres with pgvector (see docs/archive/reference/ai/embeddings-and-vector-db-process.md).

### Report Generation Timeout

Increase timeout in `app/core/config.py`:
```python
REPORT_GENERATION_TIMEOUT = 120  # seconds
```

---

## Production Checklist

- [ ] All dependencies installed (weasyprint, matplotlib, etc.)
- [ ] Qdrant deployed and accessible
- [ ] S3 bucket configured with encryption
- [ ] Backup scripts configured in cron
- [ ] Report schedules configured for customers
- [ ] **CRITICAL:** Tenant isolation tests passing
- [ ] Monitoring and alerting configured

---

**Status:** ✅ Production Ready  
**Version:** 1.0.0  
**Last Updated:** December 2, 2025
