# Compliance Platform - Testing Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Version:** 1.0  
**Date:** December 2, 2025  
**Purpose:** Comprehensive testing guide for compliance platform

---

## Test Suite Overview

The compliance platform includes **6 comprehensive test suites** with **50+ individual tests**:

| Test Suite | File | Tests | Priority | Status |
|------------|------|-------|----------|--------|
| **Tenant Isolation** | `test_tenant_isolation.py` | 12 tests | 🔴 CRITICAL | ✅ Ready |
| **PDF Generation** | `test_pdf_generation.py` | 9 tests | 🟡 High | ✅ Ready |
| **Report Generation** | `test_report_generation.py` | 8 tests | 🟡 High | ✅ Ready |
| **LLM Integration** | `test_llm_integration.py` | 7 tests | 🔴 CRITICAL | ✅ Ready |
| **IAM Governance** | `test_iam_governance.py` | 10 tests | 🟢 Medium | ✅ Ready |
| **API Endpoints** | `test_compliance_api.py` | 8 tests | 🟡 High | ✅ Ready |
| **Performance** | `test_performance.py` | 6 tests | 🟢 Medium | ✅ Ready |

**Total:** 60+ automated tests

---

## Quick Start

### Run All Tests

```bash
# Run complete test suite
./scripts/run-compliance-tests.sh

# Output shows:
# 🔒 Tenant Isolation (CRITICAL): ✅ PASS
# 📄 PDF Generation: ✅ PASS
# 📊 Report Generation: ✅ PASS
# 🤖 LLM Integration: ✅ PASS
# 👥 IAM Governance: ✅ PASS
# 🌐 API Tests: ✅ PASS
```

### Run Specific Test Suite

```bash
cd backend/tests/compliance

# Run CRITICAL tenant isolation tests
pytest test_tenant_isolation.py -v

# Run PDF generation tests
pytest test_pdf_generation.py -v

# Run with coverage
pytest test_tenant_isolation.py --cov --cov-report=html
```

---

## Test Suites Detail

### 1. Tenant Isolation Tests (CRITICAL) 🔴

**File:** `test_tenant_isolation.py`  
**Purpose:** Verify Customer A cannot access Customer B's data  
**Priority:** CRITICAL - MUST PASS before production

**Tests:**
- ✅ `test_reports_tenant_isolation_database` - Database-level isolation
- ✅ `test_audit_logs_tenant_isolation` - Audit log isolation
- ✅ `test_access_review_campaigns_tenant_isolation` - Campaign isolation
- ✅ `test_control_status_tenant_isolation` - Control status isolation
- ✅ `test_llm_vector_db_metadata_structure` - Vector DB metadata
- ✅ `test_llm_query_tenant_isolation_with_mock` - LLM query filtering
- ✅ `test_report_query_requires_tenant_context` - Tenant context enforcement
- ✅ `test_schedule_query_tenant_scoped` - Schedule isolation
- ✅ `test_evidence_package_isolation` - Evidence isolation
- ✅ `test_no_report_enumeration` - Prevent ID enumeration
- ✅ `test_sql_injection_protection` - SQL injection protection

**Expected Output:**
```
test_tenant_isolation.py::test_reports_tenant_isolation_database PASSED
test_tenant_isolation.py::test_audit_logs_tenant_isolation PASSED
test_tenant_isolation.py::test_llm_query_tenant_isolation_with_mock PASSED
...
========================= 12 passed in 2.34s =========================
```

**⚠️ If ANY test fails:** DO NOT DEPLOY TO PRODUCTION!

### 2. PDF Generation Tests

**File:** `test_pdf_generation.py`  
**Purpose:** Verify professional PDF report generation

**Tests:**
- PDF engine initialization
- Simple PDF generation
- Date formatting filters
- Number formatting (1,000 → "1,000")
- Percentage formatting (87.5 → "87.5%")
- Chart generation (bar, pie, gauge, line)
- Base64 chart encoding

**Dependencies:** WeasyPrint, matplotlib

### 3. Report Generation Pipeline Tests

**File:** `test_report_generation.py`  
**Purpose:** Test end-to-end report generation workflow

**Tests:**
- Report record creation
- Report naming convention (Type_YYYY-MM-DD_TenantName.pdf)
- Report schedule creation
- Report access logging
- Scheduler initialization
- Cron expression parsing
- Data collection for reports

### 4. LLM Integration Tests (CRITICAL) 🔴

**File:** `test_llm_integration.py`  
**Purpose:** Verify LLM Q&A with tenant isolation

**Tests:**
- LLM ingestor initialization
- Report text chunking
- Report ingestion with metadata
- Q&A service initialization
- Query with tenant context
- **Tenant filter in vector search (CRITICAL)**
- Query logging for audit

**Security Focus:** Ensures Customer A cannot query Customer B's report data

### 5. IAM Governance Tests

**File:** `test_iam_governance.py`  
**Purpose:** Test access reviews, JML, MFA features

**Tests:**
- Access review campaign creation
- Review item creation
- Review decision recording with audit
- Joiner workflow creation
- Leaver workflow creation
- Workflow step tracking
- MFA policy creation
- User MFA status tracking
- MFA compliance violations
- Audit event logging
- Audit change tracking
- Evidence package creation
- Evidence item addition

### 6. API Endpoint Tests

**File:** `test_compliance_api.py`  
**Purpose:** Test REST API endpoints

**Tests:**
- Audit logs API (GET /api/v1/audit/logs)
- Audit export API (GET /api/v1/audit/export)
- Report list API (GET /api/v1/reports) - tenant-scoped
- Report download authorization
- LLM query API (POST /api/v1/reports/query)
- Schedule creation API
- Schedule listing

### 7. Performance Tests

**File:** `test_performance.py`  
**Purpose:** Verify acceptable performance under load

**Tests:**
- Single report generation time (< 30s target)
- Concurrent report generation (10 concurrent)
- Report list query performance (< 100ms)
- Audit log query performance (< 100ms)
- LLM query response time (< 5s target)
- Large CSV export memory usage

---

## Test Configuration

### Test Database

**Setup test database:**
```bash
# Create test database
createdb -U sentinelgrid sentinelgrid_test

# Run migrations
psql -U sentinelgrid -d sentinelgrid_test << 'EOF'
\i backend/migrations/026_platform_audit_logs.sql
\i backend/migrations/027_access_review_campaigns.sql
\i backend/migrations/028_jml_workflows.sql
\i backend/migrations/029_mfa_enforcement_policies.sql
\i backend/migrations/030_compliance_control_library.sql
\i backend/migrations/031_evidence_repository.sql
\i backend/migrations/035_report_scheduling_and_storage.sql
EOF
```

**Environment variable:**
```bash
export TEST_DATABASE_URL="postgresql://sentinelgrid:sentinelgrid@localhost:5432/sentinelgrid_test"
```

### Test Dependencies

```bash
# Install test requirements
cd backend/tests/compliance
pip install -r requirements-test.txt

# Includes:
# - pytest (testing framework)
# - pytest-asyncio (async tests)
# - pytest-mock (mocking)
# - pytest-cov (coverage)
# - Optional: weasyprint, matplotlib
```

---

## Running Tests

### Run All Tests

```bash
# Comprehensive test run
./scripts/run-compliance-tests.sh

# With verbose output
./scripts/run-compliance-tests.sh | tee test-results.log
```

### Run Specific Test Suite

```bash
cd backend/tests/compliance

# Tenant isolation only (CRITICAL)
pytest test_tenant_isolation.py -v

# With detailed output
pytest test_tenant_isolation.py -v -s

# Stop on first failure
pytest test_tenant_isolation.py -x
```

### Run Specific Test

```bash
# Run single test
pytest test_tenant_isolation.py::TestTenantIsolation::test_reports_tenant_isolation_database -v

# Run tests matching pattern
pytest -k "tenant_isolation" -v
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=backend.services.reporting_service --cov-report=html

# View coverage
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

---

## Test Fixtures

### Available Fixtures (conftest.py)

- `test_engine` - Test database engine
- `db_session` - Database session (auto-rollback)
- `tenant_a` - Test tenant A (Acme Corp)
- `tenant_b` - Test tenant B (TechStart Inc)
- `test_user_a` - Test user for Tenant A
- `test_user_b` - Test user for Tenant B
- `sample_report_data` - Sample report data
- `mock_embedding_model` - Mocked embedding model
- `mock_llm_client` - Mocked LLM client
- `temp_report_dir` - Temporary directory for files

**Usage:**
```python
def test_something(db_session, tenant_a, test_user_a):
    # Use fixtures
    assert tenant_a["name"] == "Acme Corp"
```

---

## Test Patterns

### Testing Tenant Isolation

```python
def test_tenant_isolation_pattern(db_session, tenant_a, tenant_b):
    """Pattern for testing tenant isolation."""
    # 1. Create data for Tenant A
    db_session.execute(
        text("INSERT INTO table (tenant_id, ...) VALUES (:tenant_id, ...)"),
        {"tenant_id": str(tenant_a["id"])}
    )
    
    # 2. Create data for Tenant B
    db_session.execute(
        text("INSERT INTO table (tenant_id, ...) VALUES (:tenant_id, ...)"),
        {"tenant_id": str(tenant_b["id"])}
    )
    
    db_session.commit()
    
    # 3. Query as Tenant A
    result = db_session.execute(
        text("SELECT * FROM table WHERE tenant_id = :tenant_id"),
        {"tenant_id": str(tenant_a["id"])}
    )
    
    data_a = result.fetchall()
    
    # 4. Verify Tenant A only sees their data
    assert len(data_a) > 0
    # 5. Verify Tenant B's data NOT in results
    # Add specific assertions
```

### Testing API Endpoints

```python
@pytest.mark.asyncio
async def test_api_endpoint(mock_jwt_token):
    """Pattern for testing API endpoints."""
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    
    # Mock authentication
    # Call endpoint
    response = client.get(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {mock_jwt_token}"}
    )
    
    # Verify response
    assert response.status_code == 200
```

---

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Compliance Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: sentinelgrid_test
          POSTGRES_USER: sentinelgrid
          POSTGRES_PASSWORD: sentinelgrid
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r backend/tests/compliance/requirements-test.txt
      
      - name: Run migrations
        run: |
          ./scripts/run-compliance-migrations.sh
      
      - name: Run tests
        run: |
          ./scripts/run-compliance-tests.sh
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Test Data

### Sample Test Data

**Tenant A (Acme Corp):**
- tenant_id: Generated UUID
- realm: "acme-corp"
- users: admin@acme.com, user@acme.com
- reports: SOC 2, IAM/MFA reports

**Tenant B (TechStart Inc):**
- tenant_id: Different UUID
- realm: "techstart"
- users: admin@techstart.com
- reports: NIST CSF report

**Expected Behavior:**
- Tenant A queries return ONLY Tenant A data
- Tenant B queries return ONLY Tenant B data
- Cross-tenant access returns 404 (not 403 to prevent enumeration)

---

## Critical Test Scenarios

### Scenario 1: Cross-Tenant Report Access (CRITICAL)

**Setup:**
1. Create report for Tenant A
2. Create report for Tenant B

**Test:**
1. User from Tenant A queries reports
2. Should see ONLY Tenant A's report
3. Should NOT see Tenant B's report

**Expected:** ✅ PASS  
**If FAIL:** 🚨 SECURITY VULNERABILITY - Do not deploy!

### Scenario 2: LLM Query Isolation (CRITICAL)

**Setup:**
1. Ingest report for Tenant A (contains "MFA coverage: 87%")
2. Ingest report for Tenant B (contains "MFA coverage: 62%")

**Test:**
1. User from Tenant A queries "What is our MFA coverage?"
2. Should get answer: "87%" (from Tenant A's report)
3. Should NOT get answer: "62%" (from Tenant B's report)

**Expected:** ✅ PASS  
**If FAIL:** 🚨 SECURITY VULNERABILITY - Data leakage!

### Scenario 3: Report Download Authorization

**Setup:**
1. Create report for Tenant B (report_id: abc-123)

**Test:**
1. User from Tenant A tries to download report abc-123
2. API should return 404 (not found)
3. Should NOT reveal that report exists

**Expected:** ✅ PASS  
**If FAIL:** 🚨 Information disclosure vulnerability

---

## Performance Benchmarks

### Report Generation
- **Target:** < 30 seconds per report
- **Test:** Generate SOC 2 report with real data
- **Measured:** TBD after deployment

### Database Queries
- **Target:** < 100ms for listing queries
- **Test:** List 1000 reports with filters
- **Measured:** Should be < 100ms with proper indexes

### LLM Queries
- **Target:** < 5 seconds per query
- **Test:** Query with 5 relevant report chunks
- **Measured:** Depends on LLM model performance

### Concurrent Generation
- **Target:** 100 concurrent report generations
- **Test:** Stress test with ThreadPoolExecutor
- **Measured:** Should handle without errors

---

## Manual Testing Checklist

### After Deployment

- [ ] **Generate SOC 2 Report**
  - [ ] Report generates successfully
  - [ ] PDF downloads correctly
  - [ ] CSV downloads correctly
  - [ ] Charts are visible in PDF
  - [ ] Date is in filename
  - [ ] Tenant name is in filename

- [ ] **Test LLM Q&A**
  - [ ] Ask "What is our MFA coverage?"
  - [ ] Get relevant answer from reports
  - [ ] Cannot query other tenant's data
  - [ ] Query is logged in audit trail

- [ ] **Test Report Scheduling**
  - [ ] Create weekly schedule
  - [ ] Verify next run time calculated
  - [ ] Check schedule appears in list
  - [ ] Test email delivery (if configured)

- [ ] **Test Tenant Isolation**
  - [ ] Login as Tenant A
  - [ ] See only Tenant A's reports
  - [ ] Try accessing Tenant B's report ID → 404
  - [ ] Query LLM about Tenant B's data → No results

- [ ] **Test Access Reviews**
  - [ ] Create campaign
  - [ ] Generate review items
  - [ ] Submit approve/revoke decisions
  - [ ] Verify audit trail

- [ ] **Test JML Workflows**
  - [ ] Create joiner workflow
  - [ ] Verify steps execute
  - [ ] Create leaver workflow
  - [ ] Verify access revocation

---

## Troubleshooting Tests

### Issue: Tests Fail with "WeasyPrint not found"

**Solution:**
```bash
# macOS
brew install pango cairo
pip install weasyprint

# Ubuntu/Debian
sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0
pip install weasyprint

# Run tests again
pytest test_pdf_generation.py -v
```

### Issue: Vector tests fail (embedding service not available)

**Solution:**
```bash
# Start Postgres with pgvector for tests
docker compose -f docker-compose.dev.yml up -d postgres

# Or skip LLM/vector tests
pytest -m "not llm" -v
```

### Issue: Database connection failed

**Solution:**
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Create test database if missing
createdb -U sentinelgrid sentinelgrid_test

# Run migrations
./scripts/run-compliance-migrations.sh

# Set correct DATABASE_URL
export TEST_DATABASE_URL="postgresql://sentinelgrid:sentinelgrid@localhost:5432/sentinelgrid_test"
```

### Issue: Import errors

**Solution:**
```bash
# Install all dependencies
pip install -r backend/tests/compliance/requirements-test.txt

# Add project to PYTHONPATH
export PYTHONPATH="${PWD}/backend:${PYTHONPATH}"
```

---

## Test Markers

### Marking Tests

```python
@pytest.mark.slow
def test_long_running():
    """Test that takes >5 seconds."""
    pass

@pytest.mark.integration
def test_integration():
    """Integration test requiring external services."""
    pass

@pytest.mark.critical
def test_security():
    """Critical security test that must pass."""
    pass
```

### Running Marked Tests

```bash
# Run only critical tests
pytest -m critical -v

# Skip slow tests
pytest -m "not slow" -v

# Run integration tests
pytest -m integration -v
```

---

## Coverage Goals

### Target Coverage

- **Tenant Isolation:** 100% (MUST be perfect)
- **Report Generation:** 80%+
- **LLM Integration:** 90%+
- **IAM Governance:** 70%+
- **API Endpoints:** 80%+

### Generate Coverage Report

```bash
cd backend/tests/compliance

# Run with coverage
pytest --cov=backend.services.reporting_service \
       --cov=backend.services.compliance_service \
       --cov=backend.services.model_gateway.app.services.report_qa_service \
       --cov-report=html \
       --cov-report=term

# View report
open htmlcov/index.html
```

---

## Security Test Checklist

Before production deployment, verify:

- [ ] ✅ All tenant isolation tests pass
- [ ] ✅ No cross-tenant data access possible
- [ ] ✅ LLM queries filtered by tenant
- [ ] ✅ Report downloads require authorization
- [ ] ✅ SQL injection protection verified
- [ ] ✅ No ID enumeration possible
- [ ] ✅ All access logged for audit
- [ ] ✅ Vector DB metadata includes tenant filter

**If ANY item fails:** STOP and fix before deployment.

---

## Automated Testing in CI/CD

### Pre-Deployment Gate

```bash
# In CI/CD pipeline, before deploying:

# 1. Run critical tests
./scripts/run-compliance-tests.sh

# 2. Check exit code
if [ $? -ne 0 ]; then
    echo "❌ Tests failed - blocking deployment"
    exit 1
fi

# 3. If passed, proceed with deployment
echo "✅ Tests passed - proceeding with deployment"
```

---

## Test Maintenance

### Adding New Tests

1. Add test to appropriate file
2. Follow existing patterns
3. Update this guide
4. Run full suite to verify

### Test Review Frequency

- **After each feature:** Run affected test suite
- **Before each deployment:** Run full suite
- **Weekly:** Full suite + performance tests
- **Monthly:** Full suite + load tests

---

## Support

**Issues with tests?**
1. Check troubleshooting section above
2. Review test output carefully
3. Check logs in `/var/log/sentinelgrid/`
4. Contact development team

**Security test failures?**
1. **STOP immediately**
2. Do not deploy to production
3. Investigate root cause
4. Fix and re-test
5. Document finding

---

## Test Results Interpretation

### Exit Codes

- `0` - All tests passed ✅
- `1` - Some tests failed ❌
- `2` - Test execution error ⚠️

### Test Output

```
========================= test session starts =========================
collected 60 items

test_tenant_isolation.py::test_reports_tenant_isolation_database PASSED [8%]
test_tenant_isolation.py::test_audit_logs_tenant_isolation PASSED [16%]
...
========================= 60 passed in 45.23s =========================
```

**Interpretation:**
- `PASSED` - Test succeeded ✅
- `FAILED` - Test failed ❌
- `SKIPPED` - Test skipped (usually due to missing dependencies)
- `ERROR` - Test execution error

---

**Document Owner:** QA Team  
**Last Updated:** December 2, 2025  
**Status:** ✅ Test Suite Ready
