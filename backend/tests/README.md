# Testing Guide

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This directory contains comprehensive test suites for SentinelGrid.

## Test Suites

### 1. End-to-End Tests (`test_onboarding_flow.py`)
Tests the complete user flows:
- Onboarding wizard (all 4 steps)
- Dashboard integration
- Onboarding banner

**Run:**
```bash
pytest backend/tests/test_onboarding_flow.py -v
```

### 2. Security Tests (`test_security.py`)
Tests security vulnerabilities and best practices:
- Authentication and authorization
- Input validation (SQL injection, XSS, path traversal)
- Secrets management
- CSRF protection
- Rate limiting
- HTTPS/HSTS

**Run:**
```bash
pytest backend/tests/test_security.py -v
```

### 3. Performance Tests (`test_performance.py`)
Tests performance and scalability:
- API response times
- Concurrent request handling
- Database performance
- Resource usage
- Load handling

**Run:**
```bash
pytest backend/tests/test_performance.py -v
```

### 4. Integration Tests (`test_integration.py`)
Tests integration between components:
- API Gateway routing
- Frontend-backend integration
- Database integration
- External service integrations
- End-to-end flows

**Run:**
```bash
pytest backend/tests/test_integration.py -v
```

### 5. Authentication Tests (`test_auth_selenium.py`)
Selenium-based tests for authentication flows:
- Signup flow
- Login flow
- Dashboard access

**Run:**
```bash
pytest backend/tests/test_auth_selenium.py -v
```

### 6. IAM UI Tests (`test_iam_ui_selenium.py`)
Selenium-based tests for IAM portal UI:
- People page (user management)
- Add User functionality
- My Access page
- Policies page
- Access Review (Campaigns/Certifications)

**Run:**
```bash
# Run all IAM UI tests
pytest backend/tests/test_iam_ui_selenium.py -v

# Run specific test (Add User functionality)
pytest backend/tests/test_iam_ui_selenium.py::TestIAMPeoplePage::test_add_user_functionality -v

# Run with visible browser (for debugging)
HEADLESS=false pytest backend/tests/test_iam_ui_selenium.py::TestIAMPeoplePage::test_add_user_functionality -v -s
```

**Note:** These tests use Vault to retrieve credentials. Ensure Vault is running and accessible.

## Running All Tests

### Using Conda Environment (Recommended)

The tests are designed to run in the `SentinelTest` conda environment:

```bash
# Setup conda environment (first time only)
cd backend/tests
./setup-conda-env.sh

# Activate environment
conda activate SentinelTest

# Run tests
pytest -v

# Or use the test runner script from project root
./scripts/run-tests.sh
```

### Direct Execution

```bash
# Run all tests
pytest backend/tests/ -v

# Run with coverage
pytest backend/tests/ --cov=backend --cov-report=html

# Run specific test suite
pytest backend/tests/test_security.py -v

# Run specific test
pytest backend/tests/test_security.py::TestAuthentication::test_unauthenticated_access_denied -v
```

## Environment Variables

Set these environment variables for testing:

```bash
export WEBSITE_URL="https://localhost:3443"
export API_URL="https://localhost:3443/api/v1"
export TEST_EMAIL="test@example.com"
export TEST_PASSWORD="TestPassword123!"  # Fallback if Vault unavailable
export TEST_TOKEN="your_test_token"
export HEADLESS="true"  # For Selenium tests
export CI="true"  # For CI/CD environments

# Vault configuration (for credential retrieval)
export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="sentinelgrid-dev-root-token"
```

**Note:** Tests will automatically try to fetch credentials from Vault. If Vault is unavailable, they will fall back to environment variables.

## Test Data

Test data should be:
- Isolated per test
- Cleaned up after tests
- Not dependent on external state
- Fast to set up and tear down

## Continuous Integration

Tests are run in CI/CD pipeline:
- On every pull request
- Before merging to main
- On scheduled basis (nightly)

## Writing New Tests

1. Follow pytest conventions
2. Use descriptive test names
3. Add docstrings explaining what is tested
4. Use fixtures for common setup
5. Clean up after tests
6. Make tests independent and repeatable

## Test Coverage Goals

- Unit tests: >80% coverage
- Integration tests: All critical paths
- E2E tests: All user flows
- Security tests: All security-critical areas
