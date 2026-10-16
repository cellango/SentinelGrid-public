# Hero Flow 1 Test Suite

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../../RELEASE_SCOPE.md) first.


This directory contains end-to-end tests for **Hero Flow 1: Fast Onboarding**.

## Overview

Hero Flow 1 validates the complete onboarding experience:
1. Tenant provisioning
2. Identity connector setup & event ingestion
3. Cloud connector setup & event ingestion
4. Detection rule execution & alert generation
5. AI snapshot generation
6. Dashboard data retrieval

## Test Structure

### `test_hero_flow_1.py`
Main test suite with:
- **Unit Tests**: Test each step of the onboarding flow in isolation
- **Integration Tests**: Test complete end-to-end flow
- **Real Service Tests**: Tests that require actual services running

### `conftest_hero_flow.py`
Pytest fixtures providing:
- Test tenant data
- Mock events (identity, cloud)
- Mock alerts
- Mock security snapshots
- Service URLs

## Running Tests

### Unit Tests (No Services Required)
```bash
cd backend/agents/siem_agent
pytest tests/test_hero_flow_1.py::TestHeroFlow1Onboarding -v
```

### Integration Tests (Mocked Services)
```bash
pytest tests/test_hero_flow_1.py::TestHeroFlow1Integration -v
```

### Real Service Tests (Requires Services Running)
```bash
# Start services first
docker-compose -f docker-compose.dev.yml up -d

# Run integration tests
pytest tests/test_hero_flow_1.py::TestHeroFlow1RealServices -v -m integration
```

### Run All Tests
```bash
pytest tests/test_hero_flow_1.py -v
```

## Test Coverage

### Step 1: Tenant Provisioning
- ✅ Tenant created in database
- ✅ Keycloak realm created
- ✅ Admin user created
- ✅ Tenant ID returned

### Step 2: Identity Connector
- ✅ Connector configuration stored
- ✅ Initial user sync completed
- ✅ Sign-in logs ingestion started
- ✅ Identity events appearing in SIEM

### Step 3: Cloud Connector
- ✅ Cloud connector configured
- ✅ CloudTrail ingestion started
- ✅ GuardDuty alerts integration
- ✅ Cloud events appearing in SIEM

### Step 4: Detection Rules
- ✅ Detection rules active
- ✅ Failed login alerts generated
- ✅ New admin user alerts generated
- ✅ Suspicious cloud action alerts generated

### Step 5: AI Snapshot
- ✅ Orchestrator generates snapshot
- ✅ Summary includes event/alert counts
- ✅ Top findings identified
- ✅ AI explanation provided
- ✅ Recommendations generated

### Step 6: Dashboard
- ✅ Events count displayed
- ✅ Alerts count displayed
- ✅ Top alerts shown
- ✅ Security snapshot visible

## Prerequisites

### For Unit Tests
- Python 3.11+
- pytest
- pytest-asyncio
- unittest.mock

### For Integration Tests
- All unit test dependencies
- Docker & Docker Compose
- Services running:
  - SIEM Agent
  - OpenSearch
  - PostgreSQL
  - Redis
  - Keycloak
  - IAM Agent
  - Orchestrator (optional)

## Configuration

Update service URLs in `test_hero_flow_1.py`:
```python
SIEM_AGENT_URL = "http://siem_agent:8000"
IAM_AGENT_URL = "http://iam_agent:8000"
ORCHESTRATOR_URL = "http://orchestrator:8000"
INTERNAL_TOKEN = "internal-service-token-change-in-production"
```

Or set via environment variables:
```bash
export SIEM_AGENT_URL=http://localhost:8003
export IAM_AGENT_URL=http://localhost:8005
export INTERNAL_TOKEN=your-token-here
```

## Mock Data

Tests use mock data for:
- Tenant IDs (random UUIDs)
- Events (identity, cloud)
- Alerts (various severities)
- Security snapshots

Real integration tests can use actual test data by:
1. Provisioning a test tenant
2. Configuring test connectors
3. Generating test events
4. Verifying alerts and snapshots

## Troubleshooting

### Tests Fail with Connection Errors
- Verify services are running: `docker-compose ps`
- Check service URLs are correct
- Verify internal service token matches

### Tests Timeout
- Increase timeout in test configuration
- Check service health endpoints
- Verify network connectivity

### Mock Data Issues
- Ensure fixtures are properly imported
- Check UUID generation is working
- Verify datetime formatting

## Next Steps

1. **Implement Real Connectors**: Replace mocks with actual connector implementations
2. **Add Test Data**: Create test datasets for realistic scenarios
3. **Performance Testing**: Add load tests for onboarding flow
4. **Error Scenarios**: Test failure cases and error handling
5. **Multi-Tenant Testing**: Test concurrent onboarding for multiple tenants

## Related Documentation

- `Hero Flows Roadmap` (historical reference unavailable)
- [SIEM Agent Implementation Plan](../../../../docs/archive/README.md#retired-references)
- [Integration Guide](../docs/INTEGRATION_GUIDE.md)

