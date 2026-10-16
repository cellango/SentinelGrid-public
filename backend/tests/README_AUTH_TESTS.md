# Authentication Tests

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This directory contains comprehensive tests for the authentication system.

## Test Structure

### Unit Tests (`test_auth_api_client.py`)
- Tests for frontend auth API client functions
- Mocks HTTP calls
- Tests error handling
- Tests token storage

### Integration Tests (`test_auth_endpoints.py`)
- Tests for IAM Agent auth endpoints
- Uses FastAPI TestClient
- Tests API contracts
- Tests error responses

### E2E Tests (`test_auth_selenium.py`)
- Selenium browser tests
- Tests complete user flows
- Tests UI interactions
- Tests authentication state

## Running Tests

### All Tests
```bash
pytest backend/tests/test_auth_*.py -v
```

### Unit Tests Only
```bash
pytest backend/tests/test_auth_api_client.py -v -m unit
```

### Integration Tests Only
```bash
pytest backend/tests/test_auth_endpoints.py -v -m integration
```

### Selenium E2E Tests Only
```bash
pytest backend/tests/test_auth_selenium.py -v -m selenium
```

### With Coverage
```bash
pytest backend/tests/test_auth_*.py --cov=backend.services.iam_agent --cov-report=html
```

## Prerequisites

### Conda Environment Setup
All tests should be run in the correct conda environment:

```bash
# Activate conda environment
conda activate SentinelGrid  # or your environment name

# Or create/update environment from environment.yml
conda env create -f backend/tests/environment.yml
conda activate SentinelGrid
```

### For Unit and Integration Tests
- Conda environment activated
- Python 3.9+
- pytest
- pytest-asyncio
- pytest-mock
- httpx

### For Selenium Tests
- Conda environment activated
- Python 3.9+
- Selenium 4.15+
- ChromeDriver (automatically managed by webdriver-manager)
- Chrome browser installed

## Environment Variables

```bash
# IAM Agent URL
IAM_AGENT_URL=http://localhost:8005

# Website URL
WEBSITE_URL=http://localhost:3000

# Keycloak URL
KEYCLOAK_URL=http://localhost:8081

# Test credentials
TEST_USER_EMAIL=admin@sentinelgrid.ai
TEST_USER_PASSWORD=admin123

# CI mode (headless browser)
CI=true
```

## Selenium Test Setup

### Local Development
1. Install Chrome browser
2. Install dependencies: `pip install -r backend/tests/requirements.txt`
3. Run tests: `pytest backend/tests/test_auth_selenium.py -v`

### CI/CD
1. Set `CI=true` environment variable
2. Tests will run in headless mode
3. Ensure ChromeDriver is available (webdriver-manager handles this)

## Test Data

### Default Test User
- Email: `admin@sentinelgrid.ai`
- Password: `admin123`

### Test Company
- Company Name: `Test Company`
- Email: `test_{uuid}@example.com` (generated per test)

## Troubleshooting

### Selenium Tests Failing
1. Check Chrome browser is installed
2. Check ChromeDriver version matches Chrome version
3. Check website is running on `http://localhost:3000`
4. Check IAM Agent is running on `http://localhost:8005`

### Integration Tests Failing
1. Check IAM Agent is running
2. Check Keycloak is running
3. Check database is accessible
4. Check test user exists in Keycloak

### Unit Tests Failing
1. Check all mocks are properly configured
2. Check imports are correct
3. Check test data matches expected format

## Test Coverage

### Current Coverage
- Login flow: ✅
- Signup flow: ✅
- Logout flow: ✅
- Token refresh: ✅
- Error handling: ✅
- Form validation: ✅
- UI interactions: ✅

### Future Coverage
- Password reset flow
- Email verification
- MFA flows
- Session management
- Rate limiting

