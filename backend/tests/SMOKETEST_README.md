# SentinelGrid Smoketest Runner

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


## Overview

The smoketest runner validates all Hero Flows - our primary business flows. **This is CRITICAL: we cannot release if any Hero Flow is broken.**

## Hero Flows

1. **Hero Flow 1: Fast Onboarding (Day-1 Findings)**
   - Tenant provisioning
   - Identity connector setup & event ingestion
   - Cloud connector setup & event ingestion
   - Detection rule execution & alert generation
   - AI snapshot generation
   - Dashboard data retrieval

2. **Hero Flow 2: Suspicious Login Handled End-to-End**
   - Alert detection
   - Ticket creation
   - AI enrichment
   - Framework mapping (NIST/MITRE)
   - TheHive integration
   - Vulnerability/CMDB integration
   - NIST workflow

3. **Hero Flow 3: User-Reported Phishing Triage**
   - Email ingestion
   - AI classification
   - Observable extraction
   - Threat intelligence enrichment
   - Email search and containment
   - Playbook execution

4. **Hero Flow 4: Automated Threat Response**
   - Alert evaluation against playbook triggers
   - Playbook auto-trigger
   - Playbook execution
   - Action execution
   - Execution tracking

5. **Hero Flow 5: Compliance Violation Remediation**
   - Finding enhancement with compliance metadata
   - Remediation plan generation
   - Remediation execution via playbook
   - Remediation tracking
   - Compliance status update

## Running the Smoketest

### Option 1: Direct Python Execution

```bash
cd /path/to/SentinelGrid
python backend/tests/smoketest.py
```

### Option 2: Via Pytest

```bash
cd /path/to/SentinelGrid
pytest backend/tests/smoketest.py -v
```

### Option 3: Run Individual Hero Flow Suites

```bash
# Hero Flow 1
pytest backend/tests/test_hero_flow_1_suite.py -v -m hero_flow_1

# Hero Flow 2
pytest backend/tests/test_hero_flow_2_suite.py -v -m hero_flow_2

# Hero Flow 3
pytest backend/tests/test_hero_flow_3_suite.py -v -m hero_flow_3

# Hero Flow 4
pytest backend/tests/test_hero_flow_4_suite.py -v -m hero_flow_4

# Hero Flow 5
pytest backend/tests/test_hero_flow_5_suite.py -v -m hero_flow_5
```

## Test Suite Files

### Main Test Suites

- `backend/tests/test_hero_flow_1_suite.py` - Hero Flow 1 comprehensive tests
- `backend/tests/test_hero_flow_2_suite.py` - Hero Flow 2 comprehensive tests
- `backend/tests/test_hero_flow_3_suite.py` - Hero Flow 3 comprehensive tests
- `backend/tests/test_hero_flow_4_suite.py` - Hero Flow 4 comprehensive tests
- `backend/tests/test_hero_flow_5_suite.py` - Hero Flow 5 comprehensive tests

### Additional Test Files

- `backend/agents/siem_agent/tests/test_hero_flow_1.py` - Hero Flow 1 SIEM Agent tests
- `backend/services/ticketing_agent/tests/test_hero_flow_2.py` - Hero Flow 2 Ticketing tests
- `backend/tests/test_hero_flow_4_5_e2e.py` - Hero Flow 4 & 5 E2E tests
- `backend/tests/test_hero_flow_4_5_performance.py` - Hero Flow 4 & 5 performance tests
- `backend/tests/test_hero_flow_4_5_security.py` - Hero Flow 4 & 5 security tests

## Environment Variables

The smoketest uses the following environment variables for service URLs:

```bash
# Service URLs
export SIEM_AGENT_URL="http://localhost:8001"
export IAM_AGENT_URL="http://localhost:8005"
export ORCHESTRATOR_URL="http://localhost:8012"
export TENANT_SERVICE_URL="http://localhost:8007"
export CONNECTOR_SERVICE_URL="http://localhost:8008"
export DETECTION_SERVICE_URL="http://localhost:8006"
export TICKETING_AGENT_URL="http://localhost:8003"
export AI_ENRICHMENT_AGENT_URL="http://localhost:8011"
export FRAMEWORK_SERVICE_URL="http://localhost:8015"
export SOAR_AGENT_URL="http://localhost:8004"
export VULNERABILITY_SERVICE_URL="http://localhost:8009"
export CMDB_SERVICE_URL="http://localhost:8016"
export INCIDENT_SERVICE_URL="http://localhost:8017"
export EMAIL_INGESTION_SERVICE_URL="http://localhost:8018"
export AUTOMATED_RESPONSE_SERVICE_URL="http://localhost:8013"
export COMPLIANCE_SERVICE_URL="http://localhost:8017"
export POSTURE_AGENT_URL="http://localhost:8010"

# Test configuration
export TEST_TENANT_ID="<your-test-tenant-id>"
export INTERNAL_SERVICE_TOKEN="internal-service-token-change-in-production"
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Smoketest

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  smoketest:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r backend/tests/requirements.txt
          pip install pytest pytest-asyncio httpx
      
      - name: Start services
        run: |
          docker-compose up -d
          sleep 30  # Wait for services to be ready
      
      - name: Run smoketest
        run: |
          python backend/tests/smoketest.py
        env:
          TEST_TENANT_ID: ${{ secrets.TEST_TENANT_ID }}
          INTERNAL_SERVICE_TOKEN: ${{ secrets.INTERNAL_SERVICE_TOKEN }}
      
      - name: Stop services
        if: always()
        run: |
          docker-compose down
```

## Test Markers

Tests are marked with pytest markers for easy filtering:

- `@pytest.mark.hero_flow_1` - Hero Flow 1 tests
- `@pytest.mark.hero_flow_2` - Hero Flow 2 tests
- `@pytest.mark.hero_flow_3` - Hero Flow 3 tests
- `@pytest.mark.hero_flow_4` - Hero Flow 4 tests
- `@pytest.mark.hero_flow_5` - Hero Flow 5 tests
- `@pytest.mark.integration` - Integration tests requiring real services
- `@pytest.mark.unit` - Unit tests that can run in isolation
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.security` - Security tests

## Expected Output

### Success

```
================================================================================
SENTINELGRID SMOKETEST RUNNER
================================================================================

Running 5 Hero Flow test suites...

Running Hero Flow 1...
  ✅ Hero Flow 1 PASSED (12.3s)

Running Hero Flow 2...
  ✅ Hero Flow 2 PASSED (15.7s)

...

================================================================================
SMOKETEST SUMMARY
================================================================================

Total Test Suites: 5
Passed: 5
Failed: 0
Total Duration: 65.2s

================================================================================
✅ ALL SMOKETESTS PASSED - READY FOR RELEASE
================================================================================
```

### Failure

```
================================================================================
SMOKETEST SUMMARY
================================================================================

Total Test Suites: 5
Passed: 4
Failed: 1
Total Duration: 58.1s

FAILED TEST SUITES:
--------------------------------------------------------------------------------
  ❌ Hero Flow 2 (15.2s)
     ERROR: Connection refused
     ...

================================================================================
❌ SMOKETESTS FAILED - DO NOT RELEASE
================================================================================

CRITICAL: One or more Hero Flows are broken.
Please fix all failing tests before proceeding with release.
```

## Troubleshooting

### Services Not Available

If tests are skipped with "Service not available", ensure:

1. All services are running (check `docker-compose ps`)
2. Service URLs are correct in environment variables
3. Services are accessible from the test runner
4. Health checks are passing

### Timeout Issues

If tests timeout:

1. Increase timeout in `smoketest.py` (default: 300 seconds)
2. Check service logs for errors
3. Verify network connectivity
4. Check service resource usage

### Test Failures

If tests fail:

1. Check service logs for errors
2. Verify test data is correct
3. Check database connectivity
4. Verify authentication tokens are valid
5. Check service dependencies

## Pre-Release Checklist

Before releasing, ensure:

- [ ] All Hero Flow test suites pass
- [ ] No skipped tests (unless intentional)
- [ ] All integration tests pass
- [ ] Performance tests meet thresholds
- [ ] Security tests pass
- [ ] Smoketest exit code is 0

## Maintenance

### Adding New Tests

1. Add tests to the appropriate Hero Flow test suite file
2. Mark tests with appropriate pytest markers
3. Ensure tests follow the existing pattern
4. Update this README if needed

### Updating Service URLs

Update environment variables in:
- `smoketest.py`
- Individual test suite files
- CI/CD configuration
- This README

## Support

For issues with the smoketest:

1. Check service logs
2. Verify environment variables
3. Review test output for specific errors
4. Check pytest configuration in `pytest.ini`
