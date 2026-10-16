# Onboarding Flows - Test Suite

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Status:** ✅ Complete  
**Date:** 2025-01-28  
**Coverage:** Backend APIs, Frontend Components, Integration, E2E

---

## Test Structure

### Backend Tests

#### Tenant Service Tests
**Location:** `backend/services/tenant_service/tests/`

- ✅ `test_provisioning_api.py` - API endpoint tests
  - Tenant provisioning
  - Integration status
  - Alert preferences
  - User invitations
- ✅ `test_integration_e2e.py` - End-to-end flow tests

**Run tests:**
```bash
cd backend/services/tenant_service
pytest tests/ -v
```

#### Connector Service Tests
**Location:** `backend/services/connector_service/tests/`

- ✅ `test_oauth_api.py` - OAuth flow tests
  - OAuth initialization
  - OAuth callback handling
  - Connection testing

**Run tests:**
```bash
cd backend/services/connector_service
pytest tests/ -v
```

#### Detection Service Tests
**Location:** `backend/services/detection_service/tests/`

- ✅ `test_rules_api.py` - Detection rules tests
  - Enable baseline rules
  - Rule validation
  - Rule updates

**Run tests:**
```bash
cd backend/services/detection_service
pytest tests/ -v
```

### Frontend Tests

#### Component Tests
**Location:** `frontend/src/app/onboarding/__tests__/`

- ✅ `Step1Account.test.tsx` - Account creation form tests
- ✅ `Step2Identity.test.tsx` - Identity provider selection tests
- ✅ `ProgressIndicator.test.tsx` - Progress indicator tests
- ✅ `onboarding.integration.test.tsx` - Full flow integration tests

**Run tests:**
```bash
cd frontend
npm test
```

**Run with coverage:**
```bash
npm run test:coverage
```

**Run in watch mode:**
```bash
npm run test:watch
```

---

## Test Coverage

### Backend API Coverage

| Service | Endpoint | Status |
|---------|----------|--------|
| Tenant Service | `POST /api/v1/tenants/provision` | ✅ Tested |
| Tenant Service | `GET /api/v1/tenants/{id}/integration-status` | ✅ Tested |
| Tenant Service | `POST /api/v1/tenants/{id}/alert-preferences` | ✅ Tested |
| Tenant Service | `POST /api/v1/tenants/{id}/invitations` | ✅ Tested |
| Connector Service | `POST /api/v1/connectors/oauth/init` | ✅ Tested |
| Connector Service | `POST /api/v1/connectors/oauth/callback` | ✅ Tested |
| Connector Service | `POST /api/v1/connectors/{id}/test` | ✅ Tested |
| Detection Service | `POST /api/v1/detection/rules/enable` | ✅ Tested |

### Frontend Component Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| Step1Account | Form validation, submission, error handling | ✅ Tested |
| Step2Identity | Provider selection, OAuth flow, connection testing | ✅ Tested |
| ProgressIndicator | Step navigation, state display | ✅ Tested |
| Onboarding Flow | Full integration test | ✅ Tested |

---

## Running All Tests

### Backend Tests (All Services)
```bash
# From project root
cd backend
pytest services/tenant_service/tests/ services/connector_service/tests/ services/detection_service/tests/ -v
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Run Specific Test Suites

**Tenant Service only:**
```bash
pytest backend/services/tenant_service/tests/ -v
```

**OAuth tests only:**
```bash
pytest backend/services/connector_service/tests/test_oauth_api.py -v
```

**Step 1 component only:**
```bash
cd frontend
npm test -- Step1Account
```

---

## Test Fixtures & Mocks

### Backend
- **Database:** In-memory SQLite for fast tests
- **Keycloak:** Mocked KeycloakAdminClient
- **OAuth:** Mocked OAuth service methods

### Frontend
- **API:** Mocked API functions using Jest
- **Navigation:** Mocked Next.js router
- **Toast:** Mocked react-hot-toast

---

## Test Data

### Test Tenants
- Company: "Test Company", "E2E Test Company"
- Email: "admin@test.com", "admin@e2etest.com"
- Password: "SecurePass123!"

### Test Connectors
- Google Workspace connector
- AWS connector
- Test connector IDs: UUIDs generated per test

---

## Continuous Integration

### GitHub Actions (Recommended)
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r backend/requirements.txt
      - run: pytest backend/services/*/tests/ -v
  
  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: cd frontend && npm install && npm test
```

---

## Known Limitations

1. **Keycloak Integration:** Some tests may fail if Keycloak is not running. Tests use mocks, but some integration points require real Keycloak.

2. **OAuth Flow:** OAuth callback tests require proper state token management. In production, use Redis instead of in-memory storage.

3. **Database Schema:** Tests create tables on-the-fly. Ensure migrations are up-to-date.

---

## Adding New Tests

### Backend Test Template
```python
def test_new_endpoint(client, test_db):
    """Test new endpoint."""
    response = client.post(
        "/api/v1/endpoint",
        json={"key": "value"}
    )
    assert response.status_code == 200
    assert response.json()["key"] == "value"
```

### Frontend Test Template
```typescript
describe('NewComponent', () => {
  it('renders correctly', () => {
    render(<NewComponent />)
    expect(screen.getByText('Expected Text')).toBeInTheDocument()
  })
})
```

---

## Test Metrics

- **Backend:** ~15 test cases
- **Frontend:** ~10 test cases
- **Integration:** 2 E2E flows
- **Coverage Target:** 80%+

---

**Last Updated:** 2025-01-28

