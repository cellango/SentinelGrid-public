# Detection System Testing Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Version:** 1.0  
**Date:** December 2, 2025  
**Test Coverage:** Unit, Integration, E2E, UI (Selenium)

---

## Overview

Comprehensive testing for the SIEM detection system with three test suites:

1. **Unit Tests** - Detection models, deduplication logic, monitor definitions
2. **E2E Integration Tests** - Full pipeline from detection to incident creation
3. **Selenium UI Tests** - Frontend dashboards and user workflows

---

## Test Suite 1: Unit Tests

### What's Tested

- Detection event data models
- Deduplication key generation
- Observable extraction logic
- NIST workflow transitions
- Monitor definition structure

### Run Unit Tests

```bash
cd backend/tests/siem

# Run all unit tests
pytest test_detection_monitors.py -v

# Run specific test
pytest test_detection_monitors.py::TestDetectionMonitors::test_suspicious_login_detection -v

# With coverage
pytest test_detection_monitors.py --cov=app.services --cov-report=html
```

### Expected Results

```
test_suspicious_login_detection .......................... PASSED
test_user_reported_phishing .............................. PASSED
test_email_campaign_detection ............................ PASSED
test_endpoint_malware_detection .......................... PASSED
test_ransomware_detection ................................ PASSED
test_cloud_storage_public ................................ PASSED
test_privilege_escalation ................................ PASSED
test_password_spray ...................................... PASSED
test_data_exfiltration ................................... PASSED
test_lost_device ......................................... PASSED

==================== 10 passed in 2.34s ====================
```

---

## Test Suite 2: End-to-End Integration Tests

### What's Tested

- Complete flow: Detection Event → Webhook → Incident Creation
- Database record creation (incidents, timeline, observables)
- NIST status tracking
- Deduplication and suppression
- All 10 alert types

### Prerequisites

```bash
# Services must be running
docker-compose up -d postgres opensearch siem-agent soar-agent

# Run migrations
psql -U sentinelgrid -d sentinelgrid_db -f backend/migrations/023_detection_rules_versioning.sql
psql -U sentinelgrid -d sentinelgrid_db -f backend/migrations/024_traceability_audit_trail.sql
psql -U sentinelgrid -d sentinelgrid_db -f backend/migrations/025_detection_deduplication.sql

# Seed suppression rules
python backend/services/soar_agent/app/services/deduplication_service.py --tenant-id <UUID>
```

### Run E2E Tests

```bash
cd backend/tests/siem

# Set environment variables
export OPENSEARCH_URL=http://localhost:9200
export SIEM_AGENT_URL=http://localhost:8001
export SOAR_AGENT_URL=http://localhost:8003
export INTERNAL_SERVICE_TOKEN=test-token-123
export TEST_TENANT_ID=550e8400-e29b-41d4-a716-446655440000

# Run E2E tests
pytest test_e2e_detection_flow.py -v -s

# Run specific test
pytest test_e2e_detection_flow.py::TestEndToEndDetectionFlow::test_01_suspicious_login_e2e -v -s
```

### Expected Results

```
==================================================
TEST 1: Suspicious Login End-to-End Flow
==================================================
✓ Created detection event: 550e8400-...
✓ Webhook received, HTTP 202
  Incident ID: 660e9500-...
  Status: accepted
✓ Incident verified in database
  External ID: SG-INC-A1B2C3D4
  Status: new (NIST phase: Detection & Analysis)
  Severity: high
✓ Lifecycle record verified
  Detection Event ID: 550e8400-...
✓ Timeline entry verified
  Event type: detection
  Action: detected
  NIST phase: detection_and_analysis
✓ Observables extracted: 2
  - ip: 203.0.113.10 (source: detection_rule)
  - email: jane.doe@example.com (source: detection_rule)

  Testing deduplication...
✓ Duplicate suppressed: duplicate

✅ Test PASSED: Suspicious Login E2E Flow

test_01_suspicious_login_e2e ............................ PASSED
test_02_phishing_report_e2e .............................. PASSED
test_03_endpoint_malware_e2e ............................. PASSED
test_04_deduplication_flow ............................... PASSED
test_05_all_alert_types .................................. PASSED

==================== 5 passed in 15.23s ====================
```

---

## Test Suite 3: Selenium UI Tests

### What's Tested

- Detection rules page loads
- All 10 rules displayed
- Category filtering
- Rule detail pages
- Detection events dashboard
- Event filtering
- Navigation (event → incident)
- Responsive design (desktop, tablet, mobile)

### Prerequisites

```bash
# Frontend must be running
cd frontend
npm run dev

# Install Selenium dependencies
pip install selenium webdriver-manager

# ChromeDriver will be downloaded automatically
```

### Run Selenium Tests

```bash
cd backend/tests/siem

# Set frontend URL
export FRONTEND_URL=http://localhost:3000

# Run all UI tests
pytest test_detection_ui_selenium.py -v -s

# Run specific test class
pytest test_detection_ui_selenium.py::TestDetectionRulesUI -v -s

# Run with visible browser (non-headless)
# Edit test file: Remove "--headless" from chrome_options
```

### Expected Results

```
==================================================
UI TEST 1: Detection Rules Page Load
==================================================
Navigating to: http://localhost:3000/dashboard/siem/detection-rules
✓ Page loaded
✓ Page title: Detection Rules
✓ Screenshot saved: test_screenshots/detection_rules_page.png

✅ Test PASSED: Page loads correctly

==================================================
UI TEST 2: All 10 Rules Displayed
==================================================
✓ Found 10 detection rules
✓ Rule names:
  - SG-DET-001: Suspicious Login / Account Takeover
  - SG-DET-002: User-Reported Phishing
  - SG-DET-003: Email Security Phishing Campaign
  - SG-DET-004: Endpoint Malware Detection
  - SG-DET-005: Ransomware Suspected

✅ Test PASSED: Rules displayed

test_01_detection_rules_page_loads ....................... PASSED
test_02_all_rules_displayed .............................. PASSED
test_03_category_filtering ............................... PASSED
test_04_rule_detail_page ................................. PASSED
test_05_detection_events_page ............................ PASSED
test_06_event_incident_navigation ........................ PASSED
test_07_responsive_design ................................ PASSED

==================== 7 passed in 28.45s ====================
```

### Screenshots Generated

After running Selenium tests, check `test_screenshots/`:

```
test_screenshots/
├── detection_rules_page.png          # Full rules list
├── detection_rules_filtered.png      # After category filter
├── detection_rule_detail.png         # Rule detail page
├── detection_events_page.png         # Events dashboard
├── detection_events_filtered.png     # After filtering
├── incident_from_detection.png       # Incident detail
├── detection_rules_desktop.png       # Responsive: Desktop
├── detection_rules_laptop.png        # Responsive: Laptop
├── detection_rules_tablet.png        # Responsive: Tablet
├── detection_rules_mobile.png        # Responsive: Mobile
└── journey_*.png                     # User journey screenshots
```

---

## Combined Test Runner

### Run All Tests

```bash
# Automated script runs all test suites
./scripts/run-detection-tests.sh
```

Output:
```
========================================
SentinelGrid Detection System Test Suite
========================================

Checking environment...
✓ Python 3 found
✓ Docker found
✓ Dependencies installed
✓ Created test_screenshots directory

========================================
Running Test Suites
========================================

1. Unit Tests (Detection Models & Logic)
   ... (10 tests)

2. End-to-End Integration Tests
   ✓ Services are running, executing E2E tests
   ... (5 tests)

3. Selenium UI Tests (Frontend)
   ✓ Frontend is running, executing Selenium tests
   ... (7 tests)

========================================
Test Summary
========================================
✓ UI Screenshots available in: test_screenshots/
✓ Test execution complete
```

---

## Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test-detection.yml
name: Detection System Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
      
      opensearch:
        image: opensearchproject/opensearch:2.11.0
        env:
          discovery.type: single-node
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r backend/tests/requirements-test.txt
      
      - name: Run unit tests
        run: |
          cd backend/tests/siem
          pytest test_detection_monitors.py -v
      
      - name: Run E2E tests
        run: |
          # Start services
          docker-compose up -d siem-agent soar-agent
          
          # Wait for services
          sleep 10
          
          # Run tests
          cd backend/tests/siem
          pytest test_e2e_detection_flow.py -v
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: |
            test_screenshots/
            htmlcov/
```

---

## Test Coverage Goals

| Component | Target Coverage | Current |
|-----------|----------------|---------|
| Detection Models | 90% | ✅ Achieved |
| Detection Manager | 85% | ✅ Achieved |
| Monitor Manager | 80% | ✅ Achieved |
| Incident Creator | 90% | ✅ Achieved |
| Deduplication Service | 90% | ✅ Achieved |
| NIST Workflow | 95% | ✅ Achieved |
| UI Components | 70% | ✅ Achieved |

---

## Troubleshooting Tests

### E2E Tests Fail with Connection Error

**Error:** `Connection refused to http://localhost:8003`

**Solution:**
```bash
# Verify services are running
docker-compose ps

# Check service health
curl http://localhost:8001/health  # SIEM Agent
curl http://localhost:8003/health  # SOAR Agent

# View logs
docker logs siem-agent
docker logs soar-agent
```

### Selenium Tests Fail with Element Not Found

**Error:** `NoSuchElementException: Unable to locate element`

**Solutions:**
1. **Increase wait time:**
   ```python
   driver.implicitly_wait(20)  # Increase from 10 to 20
   ```

2. **Use explicit waits:**
   ```python
   WebDriverWait(driver, 20).until(
       EC.presence_of_element_located((By.ID, "element-id"))
   )
   ```

3. **Check if frontend is running:**
   ```bash
   curl http://localhost:3000
   ```

### Database Tests Fail

**Error:** `relation "detection_deduplication" does not exist`

**Solution:**
```bash
# Run missing migration
psql -U sentinelgrid -d sentinelgrid_db -f backend/migrations/025_detection_deduplication.sql
```

---

## Test Data Management

### Generate Fresh Test Data

```bash
cd backend/tests/siem/data

# Generate for specific tenant
python generate_test_logs.py \
  --tenant-id <UUID> \
  --realm sentinelgrid \
  --output-dir ./test_data

# Cleanup old test data
rm -rf ./test_data
```

### Cleanup Test Incidents

```sql
-- Delete test incidents (use with caution!)
DELETE FROM incidents 
WHERE tenant_id = '<test-tenant-uuid>'
  AND title LIKE '%Test%';

-- Or mark as test
UPDATE incidents
SET raw_payload = jsonb_set(
    raw_payload,
    '{is_test}',
    'true'::jsonb
)
WHERE tenant_id = '<test-tenant-uuid>';
```

---

## Performance Benchmarks

### Target Performance

| Operation | Target | Acceptance |
|-----------|--------|------------|
| Detection event ingestion | < 100ms | < 500ms |
| Duplicate check | < 50ms | < 200ms |
| Incident creation | < 1s | < 3s |
| Observable extraction | < 200ms | < 500ms |
| Timeline entry | < 100ms | < 300ms |
| UI page load | < 2s | < 5s |

### Run Performance Tests

```bash
# Use pytest-benchmark
pip install pytest-benchmark

# Run with benchmarking
pytest test_e2e_detection_flow.py --benchmark-only
```

---

## Summary

✅ **Unit Tests** - 10 tests for detection logic  
✅ **E2E Tests** - 5 tests for complete pipeline  
✅ **Selenium Tests** - 7 tests for UI functionality  
✅ **Test Runner Script** - Automated execution  
✅ **CI/CD Ready** - GitHub Actions workflow provided  

**Total Test Coverage:** 22 automated tests

---

**Run All Tests:**
```bash
./scripts/run-detection-tests.sh
```

**Next:** Review test screenshots and validate in your environment.

---

**Document Owner:** QA & Security Engineering  
**Last Updated:** December 2, 2025

