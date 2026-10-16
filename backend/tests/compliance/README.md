# Compliance Platform - Test Suite

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../RELEASE_SCOPE.md) first.


Comprehensive automated testing for compliance platform features.

---

## 🚀 Quick Start

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
cd ../../..
./scripts/run-compliance-tests.sh

# Or run from this directory
pytest -v
```

---

## 📊 Test Files

| File | Purpose | Tests | Critical |
|------|---------|-------|----------|
| `test_tenant_isolation.py` | Tenant isolation security | 12 | 🔴 YES |
| `test_pdf_generation.py` | PDF report generation | 9 | 🟡 |
| `test_report_generation.py` | Report pipeline | 8 | 🟡 |
| `test_llm_integration.py` | LLM Q&A with isolation | 7 | 🔴 YES |
| `test_iam_governance.py` | IAM features | 14 | 🟢 |
| `test_compliance_api.py` | API endpoints | 8 | 🟡 |
| `test_performance.py` | Performance benchmarks | 6 | 🟢 |

**Total:** 64 tests

---

## 🔒 Critical Security Tests

### Tenant Isolation (12 tests)

These tests verify that Customer A CANNOT access Customer B's data:

1. **Database Level:** Report queries filter by tenant_id + realm
2. **Audit Logs:** Cross-tenant audit log access blocked
3. **Access Reviews:** Campaign data isolated per tenant
4. **LLM Vector DB:** Metadata includes tenant filters
5. **LLM Queries:** Search results filtered by tenant
6. **API Endpoints:** All endpoints enforce tenant checks
7. **Report Schedules:** Schedules scoped to tenant
8. **Evidence Packages:** Evidence isolated per tenant
9. **ID Enumeration:** Cannot enumerate other tenant's report IDs
10. **SQL Injection:** Parameterized queries protect against injection

**⚠️ ALL MUST PASS before production deployment!**

---

## 🧪 Test Fixtures

### Database Fixtures
- `test_engine` - Test database engine
- `db_session` - Auto-rollback session

### Tenant Fixtures
- `tenant_a` - Acme Corp (tenant_id, name, realm)
- `tenant_b` - TechStart Inc (tenant_id, name, realm)
- `test_user_a` - Admin user for Tenant A
- `test_user_b` - Admin user for Tenant B

### Mock Fixtures
- `mock_embedding_model` - Mocked SentenceTransformer
- `mock_llm_client` - Mocked LLM for answer generation (when vector path is enabled)
- `sample_report_data` - Sample report data structure

### Utility Fixtures
- `temp_report_dir` - Temporary directory for test files

---

## 🏃 Running Tests

### Run All Tests

```bash
# From project root
./scripts/run-compliance-tests.sh

# From test directory
pytest -v
```

### Run Specific Suite

```bash
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

# Run tests matching keyword
pytest -k "tenant" -v
pytest -k "llm" -v
pytest -k "mfa" -v
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov --cov-report=html --cov-report=term

# View HTML coverage report
open htmlcov/index.html
```

---

## 📋 Test Checklist

### Before Deployment

- [ ] Install test dependencies
- [ ] Setup test database
- [ ] Run migrations on test database
- [ ] Run full test suite
- [ ] **VERIFY: All tenant isolation tests pass** 🔴
- [ ] **VERIFY: All LLM integration tests pass** 🔴
- [ ] Review test output
- [ ] Fix any failures
- [ ] Document any skipped tests

### After Deployment

- [ ] Run smoke tests in production
- [ ] Verify tenant isolation with real data
- [ ] Test report generation
- [ ] Test LLM Q&A
- [ ] Monitor for errors

---

## 🔧 Test Database Setup

```bash
# Create test database
createdb -U sentinelgrid sentinelgrid_test

# Run compliance migrations
export POSTGRES_DB=sentinelgrid_test
./scripts/run-compliance-migrations.sh

# Set test database URL
export TEST_DATABASE_URL="postgresql://sentinelgrid:sentinelgrid@localhost:5432/sentinelgrid_test"
```

---

## 📖 Test Examples

### Example 1: Testing Tenant Isolation

```python
def test_tenant_isolation_example(db_session, tenant_a, tenant_b):
    # Create data for both tenants
    for tenant in [tenant_a, tenant_b]:
        db_session.execute(
            text("INSERT INTO table (tenant_id, ...) VALUES (:tenant_id, ...)"),
            {"tenant_id": str(tenant["id"])}
        )
    db_session.commit()
    
    # Query as Tenant A
    result = db_session.execute(
        text("SELECT * FROM table WHERE tenant_id = :tenant_id"),
        {"tenant_id": str(tenant_a["id"])}
    )
    
    # Verify isolation
    data = result.fetchall()
    assert len(data) == 1  # Only Tenant A's data
```

### Example 2: Testing API with Mocks

```python
def test_api_example(mock_embedding_model):
    service = ReportQAService(embedding_model=mock_embedding_model)
    
    result = service.query_reports(user_context, "Test query")
    
    # Vector path is disabled until pgvector wiring is added
    assert result.get("error") == "Service unavailable"
```

---

## ⚠️ Important Notes

### Critical Tests MUST Pass

The test runner script will **BLOCK deployment** if critical tests fail:

```bash
if [ $TENANT_ISOLATION_STATUS -ne 0 ]; then
    echo "🚨 DO NOT DEPLOY TO PRODUCTION! 🚨"
    exit 1
fi
```

### Optional Dependencies

Some tests require optional dependencies:
- **WeasyPrint:** PDF generation tests
- **Matplotlib:** Chart generation tests
- **Qdrant:** LLM integration tests (can use mocks)
- **sentence-transformers:** Embedding tests (can use mocks)

If missing, tests will be skipped with warnings.

### Test Database

Tests use a separate test database to avoid affecting production data. Always use `TEST_DATABASE_URL` environment variable.

---

## 📈 Success Criteria

✅ **All critical tests pass** (tenant isolation, LLM security)  
✅ **Report generation tests pass**  
✅ **IAM governance tests pass**  
✅ **Performance benchmarks met**  
✅ **No security vulnerabilities found**

---

## 🆘 Troubleshooting

### Tests fail with import errors

```bash
# Ensure PYTHONPATH is set
export PYTHONPATH="${PWD}:${PYTHONPATH}"

# Or install package in editable mode
pip install -e backend/services/reporting_service
```

### Database connection errors

```bash
# Check PostgreSQL is running
pg_isready

# Verify test database exists
psql -U sentinelgrid -l | grep sentinelgrid_test

# Create if missing
createdb -U sentinelgrid sentinelgrid_test
```

### WeasyPrint not found

```bash
# macOS
brew install pango cairo
pip install weasyprint

# Ubuntu
sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0
pip install weasyprint
```

---

## 📞 Support

**Test failures?**
1. Check test output for specific error
2. Review `docs/archive/reference/development/compliance-testing-guide.md`
3. Check troubleshooting section
4. Contact development team

**Security test failures?**
1. **CRITICAL:** Do not deploy
2. Investigate immediately
3. Document finding
4. Fix and re-test

---

**Version:** 1.0  
**Status:** ✅ Ready for Execution  
**Last Updated:** December 2, 2025
