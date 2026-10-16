# Testing Guide - SentinelGrid Authentication

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This document describes the testing approach for SentinelGrid's authentication and authorization system.

## Test Structure

### Unit Tests
- **Location:** `backend/services/iam_agent/tests/`
- **Purpose:** Test individual components in isolation
- **Examples:**
  - `test_token_validator.py` - Token validation logic
  - `test_keycloak_client.py` - Keycloak API client

### Integration Tests
- **Location:** `backend/services/iam_agent/tests/integration/`
- **Purpose:** Test component interactions with external services (Keycloak)
- **Examples:**
  - `test_integration.py` - IAM Agent ↔ Keycloak integration

### End-to-End Tests
- **Location:** `backend/tests/test_auth_flow_e2e.py`
- **Purpose:** Test complete authentication flow across all services
- **Covers:**
  - Token generation from Keycloak
  - Token validation via IAM Agent
  - API Gateway authorization
  - Tenant isolation

## Running Tests

### Prerequisites

1. **Services Running:**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d keycloak iam_agent api_gateway postgres redis
   ```

2. **Keycloak Configured:**
   - Realm `agribotsai` created
   - User `admin@agribotsai.com` exists with password `ChangeMe123!`
   - `tenant_id` attribute set on user
   - Protocol mapper configured for `tenant_id` claim

3. **Database Migrated:**
   ```bash
   docker-compose -f docker-compose.dev.yml exec postgres psql -U sg -d sg -f /path/to/migrations/001_initial_schema.sql
   ```

### Run E2E Tests

#### Using the Test Script (Recommended)
```bash
./scripts/run-e2e-tests.sh
```

#### Using pytest directly
```bash
cd backend/tests
pytest test_auth_flow_e2e.py -v
```

#### Run specific test class
```bash
pytest test_auth_flow_e2e.py::TestTokenGeneration -v
pytest test_auth_flow_e2e.py::TestIAMAgentValidation -v
pytest test_auth_flow_e2e.py::TestAPIGatewayIntegration -v
```

#### Run specific test
```bash
pytest test_auth_flow_e2e.py::TestTokenGeneration::test_token_contains_tenant_id -v
```

### Run IAM Agent Unit Tests

```bash
cd backend/services/iam_agent
pytest tests/ -v
```

### Run with Coverage

```bash
pytest backend/tests/test_auth_flow_e2e.py --cov=backend/services/iam_agent --cov-report=html
```

## Test Configuration

### Environment Variables

Tests use the following environment variables (with defaults):

```bash
KEYCLOAK_URL=http://localhost:8081
IAM_AGENT_URL=http://localhost:8005
API_GATEWAY_URL=http://localhost:8082
TEST_REALM=agribotsai
TEST_CLIENT_ID=agribotsai-web
TEST_USERNAME=admin@agribotsai.com
TEST_PASSWORD=ChangeMe123!
```

Override in your shell or `.env` file:

```bash
export KEYCLOAK_URL=http://localhost:8081
export TEST_REALM=myrealm
pytest test_auth_flow_e2e.py -v
```

## Test Cases

### Token Generation Tests (`TestTokenGeneration`)

- ✅ `test_get_token_success` - Token can be retrieved from Keycloak
- ✅ `test_token_contains_required_claims` - Token has required JWT claims
- ✅ `test_token_contains_tenant_id` - Token includes `tenant_id` claim
- ✅ `test_token_contains_roles` - Token includes realm roles

### IAM Agent Validation Tests (`TestIAMAgentValidation`)

- ✅ `test_validate_token_success` - IAM Agent validates valid tokens
- ✅ `test_validate_token_with_tenant_id` - IAM Agent returns `tenant_id`
- ✅ `test_validate_token_with_roles` - IAM Agent returns user roles
- ✅ `test_validate_invalid_token` - IAM Agent rejects invalid tokens

### API Gateway Integration Tests (`TestAPIGatewayIntegration`)

- ✅ `test_api_gateway_health_check` - Health endpoint works
- ✅ `test_api_gateway_without_token` - Rejects unauthenticated requests
- ✅ `test_api_gateway_with_valid_token` - Accepts authenticated requests
- ✅ `test_api_gateway_with_tenant_id` - Works when `tenant_id` is present

### End-to-End Flow Tests (`TestEndToEndFlow`)

- ✅ `test_complete_auth_flow` - Complete flow: token → validation → API
- ✅ `test_multi_realm_support` - Supports multiple realms

## Troubleshooting

### Tests Failing: Services Not Available

**Error:** `Connection refused` or `503 Service Unavailable`

**Solution:**
```bash
# Check services are running
docker-compose -f docker-compose.dev.yml ps

# Start required services
docker-compose -f docker-compose.dev.yml up -d keycloak iam_agent api_gateway
```

### Tests Failing: tenant_id Missing

**Error:** `test_token_contains_tenant_id` fails

**Solution:**
1. Verify user attribute is set:
   ```bash
   ./infra/shared/scripts/fix-tenant-id.sh agribotsai <tenant-uuid>
   ```

2. Verify protocol mapper exists:
   ```bash
   docker-compose -f docker-compose.dev.yml exec keycloak \
     /opt/keycloak/bin/kcadm.sh get clients -r agribotsai \
     -q clientId=agribotsai-web --fields protocolMappers
   ```

3. Generate a new token (tokens are cached, old tokens won't have new claims):
   ```bash
   ./infra/shared/scripts/get-token.sh agribotsai agribotsai-web admin@agribotsai.com ChangeMe123!
   ```

### Tests Failing: 403 Forbidden

**Error:** API Gateway returns 403 even with valid token

**Possible Causes:**
- `tenant_id` missing from token (see above)
- User not assigned to tenant in database
- Protocol mapper not configured correctly

**Solution:**
1. Check token contains `tenant_id` (see troubleshooting above)
2. Verify tenant exists in database:
   ```bash
   docker-compose -f docker-compose.dev.yml exec postgres \
     psql -U sg -d sg -c "SELECT * FROM tenants WHERE slug = 'agribotsai';"
   ```

### Tests Timing Out

**Solution:**
- Increase timeout in test file or environment variable
- Check service logs for errors:
  ```bash
  docker-compose -f docker-compose.dev.yml logs iam_agent --tail 50
  docker-compose -f docker-compose.dev.yml logs api_gateway --tail 50
  ```

## Continuous Integration

Tests should be run in CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Run E2E Tests
  run: |
    docker-compose -f docker-compose.dev.yml up -d
    sleep 30  # Wait for services to be ready
    ./scripts/run-e2e-tests.sh
```

## Test Data Management

### Test Users

Test users are managed in Keycloak. To create a new test user:

```bash
docker-compose -f docker-compose.dev.yml exec keycloak \
  /opt/keycloak/bin/kcadm.sh create users -r agribotsai \
  -s username=testuser@example.com \
  -s email=testuser@example.com \
  -s enabled=true
```

### Test Tenants

Test tenants are managed in PostgreSQL:

```sql
INSERT INTO tenants (id, name, slug, status, created_at)
VALUES (gen_random_uuid(), 'Test Tenant', 'test-tenant', 'active', NOW());
```

## Best Practices

1. **Isolation:** Each test should be independent and not rely on state from other tests
2. **Cleanup:** Tests should clean up any data they create
3. **Idempotency:** Tests should be runnable multiple times without side effects
4. **Real Services:** E2E tests use real services, not mocks
5. **Error Messages:** Assertions should include descriptive error messages

## Future Improvements

- [ ] Add performance/load tests
- [ ] Add security tests (token expiration, signature validation)
- [ ] Add multi-tenant isolation tests
- [ ] Add tests for role-based access control
- [ ] Add negative test cases (expired tokens, revoked tokens)

