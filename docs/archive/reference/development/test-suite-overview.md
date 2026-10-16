# SentinelGrid Automated Test Suite Overview

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This document provides a comprehensive overview of all automated tests in the SentinelGrid codebase.

## Test Structure

### Backend Tests (`backend/tests/`)
Main test directory containing comprehensive test suites for the entire system.

### Service-Level Tests (`backend/services/*/tests/`)
Individual test suites for each microservice.

### Frontend Tests (`frontend/src/**/__tests__/`)
React component and page tests using Jest and React Testing Library.

---

## Backend Test Suites

### 1. Hero Flow Test Suites (Critical Business Flows)

These are the primary business flows that must pass before any release.

#### **Hero Flow 1: Fast Onboarding (Day-1 Findings)**
- **File**: `test_hero_flow_1_suite.py`
- **Tests**:
  - Tenant provisioning
  - Identity connector setup & event ingestion
  - Cloud connector setup & event ingestion
  - Detection rule execution & alert generation
  - AI snapshot generation
  - Dashboard data retrieval
- **Markers**: `@pytest.mark.hero_flow_1`

#### **Hero Flow 2: Suspicious Login Handled End-to-End**
- **File**: `test_hero_flow_2_suite.py`
- **Tests**:
  - Alert detection
  - Ticket creation
  - AI enrichment
  - Framework mapping (NIST/MITRE)
  - TheHive integration
  - Vulnerability/CMDB integration
  - NIST workflow
- **Markers**: `@pytest.mark.hero_flow_2`

#### **Hero Flow 3: User-Reported Phishing Triage**
- **File**: `test_hero_flow_3_suite.py`
- **Tests**:
  - Email ingestion
  - AI classification
  - Observable extraction
  - Threat intelligence enrichment
  - Email search and containment
  - Playbook execution
- **Markers**: `@pytest.mark.hero_flow_3`

#### **Hero Flow 4: Automated Threat Response**
- **File**: `test_hero_flow_4_suite.py`
- **Tests**:
  - Alert evaluation against playbook triggers
  - Playbook auto-trigger
  - Playbook execution
  - Action execution
  - Execution tracking
- **Markers**: `@pytest.mark.hero_flow_4`

#### **Hero Flow 5: Compliance Violation Remediation**
- **File**: `test_hero_flow_5_suite.py`
- **Tests**:
  - Finding enhancement with compliance metadata
  - Remediation plan generation
  - Remediation execution via playbook
  - Remediation tracking
  - Compliance status update
  - NIST mapping
- **Markers**: `@pytest.mark.hero_flow_5`

#### **Hero Flow 4 & 5 Extended Tests**
- **Files**:
  - `test_hero_flow_4_5_e2e.py` - End-to-end tests
  - `test_hero_flow_4_5_performance.py` - Performance tests
  - `test_hero_flow_4_5_security.py` - Security tests

### 2. Core Test Suites

#### **Integration Tests** (`test_integration.py`)
- API Gateway routing
- Frontend-backend integration
- Database integration
- External service integrations
- End-to-end flows

#### **Security Tests** (`test_security.py`)
- Authentication and authorization
- Input validation (SQL injection, XSS, path traversal)
- Secrets management
- CSRF protection
- Rate limiting
- HTTPS/HSTS
- Content Security Policy

#### **Performance Tests** (`test_performance.py`)
- API response times
- Concurrent request handling
- Database performance
- Resource usage
- Scalability

#### **Onboarding Flow Tests** (`test_onboarding_flow.py`)
- Complete onboarding wizard (all 4 steps)
- Dashboard integration
- Onboarding banner

#### **Authentication Tests**

**Unit Tests** (`test_auth_api_client.py`)
- Frontend auth API client functions
- HTTP call mocking
- Error handling
- Token storage

**Integration Tests** (`test_auth_endpoints.py`)
- IAM Agent auth endpoints
- API contracts
- Error responses
- Login, signup, logout, refresh token, get current user

**E2E Tests** (`test_auth_selenium.py`)
- Selenium browser tests
- Complete user flows
- UI interactions
- Authentication state
- Signup and login flows

**E2E Flow Tests** (`test_auth_flow_e2e.py`)
- Token generation
- IAM Agent validation
- API Gateway integration
- End-to-end authentication flow

#### **Realm Strategy Tests** (`test_realm_strategy_integration.py`)
- Realm creation integration
- Realm strategy integration

#### **Keycloak Tests**
- `test_keycloak_setup.py` - Keycloak setup and user management
- `test_keycloak_attribute_persistence.py` - Attribute persistence
- `selenium_test_account_activation.py` - UI-based account activation

#### **Model Tests** (`test_models.py`)
- Core database models
- Tenant creation
- Alert creation

#### **New Features Tests** (`test_new_features.py`)
- Multi-cloud integration
- Git security scanning
- Hardened images
- Onboarding API
- Agent management
- Git providers

#### **UI Component Tests** (`test_ui_components.py`)
- Onboarding wizard UI
- Dashboard components
- Settings page
- Git security UI
- Hardened images UI
- Responsive design

#### **Smoketest** (`smoketest.py`)
- Runs all Hero Flow test suites
- Critical pre-release validation
- Comprehensive test runner

---

## Service-Level Tests

### IAM Agent (`backend/services/iam_agent/tests/`)

#### Unit Tests
- `test_auth_api.py` - Authentication API endpoints
- `test_keycloak_client.py` - Keycloak client operations
- `test_token_validator.py` - Token validation logic
- `test_policy_management.py` - Policy management
- `test_ai_chat_service.py` - AI chat service
- `test_compliance_tracking.py` - Compliance tracking

#### Integration Tests
- `integration/test_integration.py` - Full integration tests

### Model Gateway (`backend/services/model_gateway/tests/`)

#### Core Services
- `test_base_model_service.py` - Base model service
- `test_base_model_service_expanded.py` - Expanded model service
- `test_adapter_manager_expanded.py` - Adapter manager
- `test_embeddings_service.py` - Embeddings service
- `test_unified_chat_service.py` - Unified chat service

#### RAG (Retrieval-Augmented Generation)
- `test_rag_service.py` - RAG service
- `test_rag_e2e.py` - RAG end-to-end tests
- `test_knowledge_base_loader.py` - Knowledge base loader

#### Git Ingestion
- `test_git_ingestion_service.py` - Git ingestion service
- `test_git_ingestion_api.py` - Git ingestion API
- `test_git_ingestion_e2e.py` - Git ingestion E2E tests
- `test_scheduled_ingestion.py` - Scheduled ingestion

#### Training
- `test_training_api.py` - Training API endpoints
- `test_adapter_training_service.py` - Adapter training service
- `test_training_data_service.py` - Training data service
- `test_e2e_training.py` - End-to-end training workflow
- `test_job_queue.py` - Job queue management

#### Inference
- `test_inference.py` - Model inference tests

### API Gateway (`backend/services/api_gateway/tests/`)
- `test_api_endpoints.py` - API endpoint tests
- `test_auth_middleware.py` - Authentication middleware
  - Authentication middleware tests
  - Tenant context tests

### SIEM Agent (`backend/services/siem_agent/tests/`)
- `test_hero_flow_1.py` - Hero Flow 1 integration
- `test_internal_api.py` - Internal API tests
  - Alert creation
  - Alert retrieval
  - Alert enrichment
  - Search functionality
- `test_integration.py` - Integration tests
  - SOC Agent integration
  - IAM Agent integration
  - SOAR Agent integration
  - End-to-end flow

### SOAR Agent (`backend/services/soar_agent/tests/`)
- `test_playbook_api.py` - Playbook CRUD operations
- `test_tenant_isolation.py` - Tenant isolation tests

### Ticketing Agent (`backend/services/ticketing_agent/tests/`)
- `test_hero_flow_2.py` - Hero Flow 2 integration

### Email Ingestion Service (`backend/services/email_ingestion_service/tests/`)
- `test_api.py` - Phishing API tests
- `test_email_parser.py` - Email parser tests
- `test_phishing_service.py` - Phishing service tests
- `test_containment.py` - Email search and deletion services

### Detection Service (`backend/services/detection_service/tests/`)
- `test_rules.py` - Detection rule tests
  - Failed logins rule
  - New admin rule
  - Suspicious cloud rule
- `test_rules_api.py` - Rules API tests
- `test_scheduler.py` - Scheduler tests
- `test_integration.py` - Integration tests

### Connector Service (`backend/services/connector_service/tests/`)
- `test_oauth_api.py` - OAuth API tests
  - OAuth flow tests
  - Connector test endpoint

### Tenant Service (`backend/services/tenant_service/tests/`)
- `test_provisioning_api.py` - Tenant provisioning API
- `test_integration_e2e.py` - End-to-end integration tests

### Framework Service (`backend/services/framework_service/tests/`)
- `test_framework_mapping.py` - Framework mapping tests

### AI Enrichment Agent (`backend/services/ai_enrichment_agent/tests/`)
- `test_enrichment_integration.py` - Enrichment integration tests

### Action Agent (`backend/services/action_agent/tests/`)
- `test_action_execution.py` - Action execution tests

### Entitlement Agent (`backend/services/entitlement_agent/tests/`)
- `unit/test_entitlement_crud.py` - CRUD operations
- `integration/test_entitlement_integration.py` - Integration tests

---

## Frontend Tests

### Test Framework
- **Framework**: Jest with React Testing Library
- **Configuration**: `frontend/jest.config.js`
- **Setup**: `frontend/jest.setup.js`

### Test Files

#### Component Tests
- `frontend/src/components/phishing/__tests__/PhishingReportCard.test.tsx`
  - Renders report information
  - Displays classification badge
  - Displays status badge
  - Displays confidence score
  - Handles click events

#### Page Tests
- `frontend/src/app/(dashboard)/dashboard/phishing/__tests__/page.test.tsx`
  - Renders phishing reports
  - Displays empty state
  - Filters reports by search query

### Test Scripts (from `package.json`)
- `npm test` - Run all tests
- `npm run test:watch` - Run tests in watch mode
- `npm run test:coverage` - Run tests with coverage

---

## Test Configuration

### Backend Test Configuration

#### Pytest Configuration (`backend/tests/pytest.ini`)
- **Markers**:
  - `unit` - Unit tests
  - `integration` - Integration tests
  - `e2e` - End-to-end tests
  - `selenium` - Selenium browser tests
  - `auth` - Authentication tests
  - `slow` - Slow running tests
- **Asyncio mode**: auto
- **Timeout**: 300 seconds (for selenium tests)
- **Verbosity**: Enabled by default

#### Test Environment (`backend/tests/environment.yml`)
- Python 3.11
- pytest >= 7.4.0
- pytest-asyncio >= 0.21.0
- pytest-cov >= 4.1.0
- pytest-mock >= 3.12.0
- httpx >= 0.25.0
- fastapi >= 0.104.0

#### Test Dependencies (`backend/tests/requirements.txt`)
- pytest==7.4.3
- pytest-asyncio==0.21.1
- pytest-mock==3.12.0
- pytest-cov==4.1.0
- httpx==0.25.2
- selenium==4.15.2
- webdriver-manager==4.0.1
- responses==0.24.1

### Frontend Test Configuration

#### Jest Configuration (`frontend/jest.config.js`)
- Test environment: jsdom
- Module name mapper for `@/` alias
- Coverage collection from `src/**/*.{js,jsx,ts,tsx}`
- Setup files: `jest.setup.js`

#### Test Dependencies (from `package.json`)
- @testing-library/jest-dom
- @testing-library/react
- @testing-library/user-event
- jest
- jest-environment-jsdom

---

## Test Execution Scripts

### Main Test Runner (`scripts/run_tests.sh`)
- Runs tests for specific services or all services
- Supports conda environment
- Options:
  - `--service` / `-s`: Run tests for specific service
  - `--coverage` / `-c`: Generate coverage report
  - `--verbose` / `-v`: Verbose output
  - `--marker` / `-m`: Run tests with specific marker

### E2E Test Runner (`scripts/run-e2e-tests.sh`)
- Runs end-to-end authentication tests
- Checks service availability
- Validates Keycloak, IAM Agent, and API Gateway

### Additional Test Scripts
- `scripts/run-onboarding-tests.sh` - Onboarding flow tests
- `scripts/run-signup-selenium-test.sh` - Signup Selenium tests
- `scripts/test-admin-login.py` - Admin login tests
- `scripts/test_keycloak_auth.py` - Keycloak authentication tests
- `scripts/test-user-profile-api.py` - User profile API tests
- `scripts/iam-portal-smoke-test.sh` - IAM portal smoke tests

### Realm Strategy Test Scripts (`backend/tests/`)
- `run_all_realm_tests.sh` - Run all realm tests
- `run_auth_tests.sh` - Run authentication tests
- `run_realm_strategy_tests.sh` - Run realm strategy tests

---

## Test Coverage Goals

- **Unit tests**: >80% coverage
- **Integration tests**: All critical paths
- **E2E tests**: All user flows
- **Security tests**: All security-critical areas

---

## Running Tests

### Backend Tests

```bash
# Run all tests
pytest backend/tests/ -v

# Run with coverage
pytest backend/tests/ --cov=backend --cov-report=html

# Run specific test suite
pytest backend/tests/test_security.py -v

# Run Hero Flow tests
pytest backend/tests/test_hero_flow_1_suite.py -v -m hero_flow_1

# Run smoketest (all Hero Flows)
python backend/tests/smoketest.py

# Run via test runner script
./scripts/run_tests.sh --service iam_agent --coverage
```

### Frontend Tests

```bash
cd frontend

# Run all tests
npm test

# Run in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage
```

### Service-Specific Tests

```bash
# IAM Agent tests
pytest backend/services/iam_agent/tests/ -v

# Model Gateway tests
pytest backend/services/model_gateway/tests/ -v

# API Gateway tests
pytest backend/services/api_gateway/tests/ -v
```

---

## Environment Variables

### Backend Test Environment

```bash
# Service URLs
export SIEM_AGENT_URL="http://localhost:8001"
export IAM_AGENT_URL="http://localhost:8005"
export API_GATEWAY_URL="http://localhost:8082"
export KEYCLOAK_URL="http://localhost:8081"
export WEBSITE_URL="https://localhost:3443"
export API_URL="https://localhost:3443/api/v1"

# Test credentials
export TEST_EMAIL="test@example.com"
export TEST_PASSWORD="TestPassword123!"
export TEST_TOKEN="your_test_token"
export TEST_TENANT_ID="<your-test-tenant-id>"
export INTERNAL_SERVICE_TOKEN="internal-service-token-change-in-production"

# Test configuration
export HEADLESS="true"  # For Selenium tests
export CI="true"  # For CI/CD environments
```

---

## Test Statistics

### Backend Tests
- **Total test files**: ~93 Python test files
- **Hero Flow suites**: 5 main suites + 3 extended suites
- **Core test suites**: 8+ comprehensive suites
- **Service-level tests**: 15+ services with dedicated test suites

### Frontend Tests
- **Test files**: 2+ component/page test files
- **Test framework**: Jest + React Testing Library
- **Coverage**: Configured but coverage goals not specified

### Test Types
- **Unit tests**: Service-level unit tests
- **Integration tests**: Cross-service integration
- **E2E tests**: Full user flow tests
- **Selenium tests**: Browser-based UI tests
- **Performance tests**: Load and scalability tests
- **Security tests**: Security vulnerability tests

---

## Pre-Release Checklist

Before releasing, ensure:
- [ ] All Hero Flow test suites pass
- [ ] No skipped tests (unless intentional)
- [ ] All integration tests pass
- [ ] Performance tests meet thresholds
- [ ] Security tests pass
- [ ] Smoketest exit code is 0

---

## Notes

- Hero Flow tests are **CRITICAL** - they validate primary business flows
- Tests use pytest markers for easy filtering
- Most tests require services to be running
- Selenium tests require Chrome browser
- Tests support both conda and virtual environments
- CI/CD integration examples available in documentation

