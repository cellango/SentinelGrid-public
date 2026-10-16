# IAM Portal CI/CD Integration

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Overview

The IAM Portal smoke tests are integrated into our CI/CD pipeline via GitHub Actions. This ensures that IAM Portal functionality is automatically validated on every relevant code change.

## GitHub Actions Workflow

**File:** `.github/workflows/iam-portal-tests.yml`

### Triggers

The workflow runs automatically when:
- Code is pushed to `main` or `develop` branches that affects:
  - `backend/services/iam_agent/**`
  - `frontend/src/app/dashboard/iam/**`
  - `frontend/src/components/iam/**`
  - `frontend/src/lib/api/iam-portal.ts`
  - IAM Portal database migrations
  - The smoke test script itself
- Pull requests are opened to `main` or `develop` with the same file changes
- Manual workflow dispatch (via GitHub UI)

### What Gets Tested

1. **Service Startup**
   - PostgreSQL database initialization
   - Keycloak startup and readiness
   - Redis availability
   - IAM Agent service startup

2. **Database Migrations**
   - IAM Portal schema (`015_iam_portal_schema.sql`)
   - IAM Policies schema (`016_iam_policies_schema.sql`)

3. **Keycloak Seeding**
   - Automatic realm and client creation
   - Admin user provisioning
   - Protocol mapper configuration

4. **IAM Portal API Tests**
   - `GET /api/iam-portal/users` - List users
   - `POST /api/iam-portal/users` - Create user
   - Token-based authentication
   - Tenant isolation

### Workflow Steps

1. **Checkout code** - Get the latest code
2. **Set up Python** - Install Python 3.11
3. **Install dependencies** - Install required Python packages
4. **Wait for Keycloak** - Ensure Keycloak is fully ready
5. **Apply migrations** - Run database schema migrations
6. **Start IAM Agent** - Launch the IAM Agent service
7. **Seed Keycloak** - Trigger Keycloak seeding (if needed)
8. **Run smoke tests** - Execute the IAM Portal smoke test suite
9. **Cleanup** - Clean up any background processes

### Service Configuration

The workflow uses GitHub Actions service containers:

- **PostgreSQL 15**: Database for IAM Portal and Keycloak
- **Keycloak 25.0.6**: Identity provider
- **Redis 7**: Caching layer

All services are configured with health checks to ensure they're ready before tests run.

## Running Tests Locally

### Using the Smoke Test Script

```bash
# From project root
./scripts/iam-portal-smoke-test.sh
```

This script:
1. Gets an admin token from Keycloak
2. Tests user listing API
3. Creates a test user
4. Verifies user creation

### Using Make

```bash
make test-iam-portal
```

### Prerequisites

Before running tests locally, ensure:

1. **Services are running**:
   ```bash
   docker-compose -f docker-compose.dev.yml up -d \
     postgres keycloak redis iam_agent
   ```

2. **Database migrations applied**:
   ```bash
   docker-compose -f docker-compose.dev.yml exec postgres \
     psql -U sg -d sg -f backend/migrations/015_iam_portal_schema.sql
   
   docker-compose -f docker-compose.dev.yml exec postgres \
     psql -U sg -d sg -f backend/migrations/016_iam_policies_schema.sql
   ```

3. **Keycloak is seeded**:
   ```bash
   # The IAM Agent should auto-seed on startup
   # Verify with:
   curl http://localhost:8005/health | python3 -m json.tool
   ```

## Test Results

### Success Criteria

The workflow passes if:
- ✅ All services start successfully
- ✅ Database migrations apply without errors
- ✅ IAM Agent health check passes
- ✅ Admin token can be obtained
- ✅ User listing API returns 200
- ✅ User creation API returns 200/201
- ✅ Created user appears in subsequent listing

### Failure Handling

If tests fail:
1. Check the GitHub Actions logs for specific error messages
2. Verify service health endpoints manually
3. Review Keycloak logs for seeding issues
4. Check database connection and migration status

## Continuous Integration Best Practices

### Test Isolation

- Each test run uses a unique username (`ci-test-{timestamp}-{random}@example.com`)
- Tests clean up after themselves (or rely on test data isolation)
- Services are started fresh for each workflow run

### Performance

- Workflow timeout: 15 minutes
- Keycloak startup: ~60 seconds (with health checks)
- Total test execution: ~2-3 minutes

### Security

- No secrets are exposed in workflow logs
- Test tokens are scoped to test users only
- Database credentials are service-specific (not production)

## Extending the Tests

To add more tests to the CI pipeline:

1. **Add to smoke test script** (`scripts/iam-portal-smoke-test.sh`):
   ```bash
   # Test new endpoint
   curl -s -H "Authorization: Bearer $TOKEN" \
     "$API_BASE/new-endpoint" | python3 -m json.tool
   ```

2. **Or create a separate test file**:
   ```bash
   # backend/tests/test_iam_portal_api.py
   import pytest
   import httpx
   
   def test_new_endpoint(token):
       response = httpx.get(
           "http://localhost:8005/api/iam-portal/new-endpoint",
           headers={"Authorization": f"Bearer {token}"}
       )
       assert response.status_code == 200
   ```

3. **Update the workflow** to run the new tests

## Related Documentation

- [IAM Portal Testing Guide](iam-portal-testing-guide.md) - Comprehensive testing guide
- [IAM Portal Quick Start](iam-portal-quick-start.md) - Quick setup instructions
- [IAM Portal Docker Setup](iam-portal-docker-setup.md) - Docker configuration

## Troubleshooting

### Workflow Fails: Keycloak Not Ready

**Symptom**: Workflow times out waiting for Keycloak

**Solution**: 
- Increase health check retries in workflow
- Check Keycloak logs for startup errors
- Verify PostgreSQL is accessible from Keycloak container

### Workflow Fails: Migration Errors

**Symptom**: Database migration fails

**Solution**:
- Check if migrations were already applied
- Verify PostgreSQL connection
- Review migration SQL syntax

### Workflow Fails: Token Generation

**Symptom**: Cannot get admin token

**Solution**:
- Verify Keycloak realm is created
- Check admin user exists (`admin@sentinelgrid.ai`)
- Verify password is correct (`admin123`)
- Ensure protocol mappers are configured

### Workflow Fails: IAM Agent Not Ready

**Symptom**: IAM Agent health check fails

**Solution**:
- Check IAM Agent logs
- Verify Keycloak connection
- Check database connectivity
- Review IAM Agent configuration

