# MCP Server Test Suite

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../../RELEASE_SCOPE.md) first.


Comprehensive test suite for the SentinelGrid MCP Server.

## Test Coverage

### Unit Tests

**SIEM Tools** (`test_siem_tools.py`)
- ✅ `search_logs` - Log searching functionality
- ✅ `get_detections` - Detection event retrieval
- ✅ `get_incidents` - Incident listing
- ✅ `create_incident` - Incident creation
- ✅ Error handling and API failures

**SOAR Tools** (`test_soar_tools.py`)
- ✅ `list_playbooks` - Playbook listing
- ✅ `get_playbook` - Playbook details
- ✅ `run_playbook` - Playbook execution
- ✅ `get_playbook_execution` - Execution status

**IAM Tools** (`test_iam_tools.py`)
- ✅ `get_user` - User retrieval
- ✅ `lock_account` - Account locking (high-risk)
- ✅ Authorization failures

**Security** (`test_security.py`)
- ✅ Authorization checks
- ✅ Tenant isolation
- ✅ Audit logging
- ✅ High-risk tool flagging
- ✅ Parameter sanitization
- ✅ Prompt injection protection

### Integration Tests

**MCP Server** (`test_integration.py`)
- ✅ Server creation
- ✅ Tool listing
- ✅ End-to-end tool execution
- ✅ Error handling
- ✅ Unknown tool handling

## Running Tests

### Run All Tests
```bash
cd backend/services/mcp_server
pytest
```

### Run Specific Test File
```bash
pytest tests/test_siem_tools.py
pytest tests/test_security.py
```

### Run With Coverage
```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Run Only Unit Tests
```bash
pytest -m unit
```

### Run Only Integration Tests
```bash
pytest -m integration
```

### Verbose Output
```bash
pytest -v
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── pytest.ini               # Pytest configuration
├── test_siem_tools.py       # SIEM tool tests
├── test_soar_tools.py       # SOAR tool tests
├── test_iam_tools.py        # IAM tool tests
├── test_security.py         # Security manager tests
└── test_integration.py      # End-to-end tests
```

## Fixtures

**conftest.py** provides shared fixtures:
- `mock_tenant_id` - Mock tenant ID
- `mock_user_id` - Mock user ID
- `mock_httpx_client` - Mock HTTP client
- `mock_service_clients` - Mock service clients
- `mock_security_manager` - Mock security manager
- `sample_*` - Sample data (incidents, playbooks, users, etc.)

## Mocking Strategy

Tests mock:
- HTTP clients (`httpx.AsyncClient`)
- Service clients (SIEM, SOAR, IAM agents)
- Security manager (authorization, audit)

This allows testing:
- Tool logic without external dependencies
- Authorization and audit flows
- Error handling
- API interactions

## CI/CD Integration

Add to `.github/workflows/test.yml`:

```yaml
- name: Test MCP Server
  run: |
    cd backend/services/mcp_server
    pytest --cov=app --cov-report=xml
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    files: backend/services/mcp_server/coverage.xml
```

## Test Scenarios Covered

### Happy Paths
- ✅ Successful tool execution
- ✅ Correct API calls
- ✅ Proper response formatting
- ✅ Authorization success
- ✅ Audit logging

### Error Cases
- ✅ API failures
- ✅ Network errors
- ✅ Authorization failures
- ✅ Tenant isolation violations
- ✅ Invalid parameters

### Security
- ✅ High-risk tool identification
- ✅ Audit log creation
- ✅ Parameter sanitization
- ✅ Prompt injection prevention
- ✅ Cross-tenant access prevention

## Adding New Tests

1. Create test file: `tests/test_<feature>.py`
2. Import required fixtures from `conftest.py`
3. Write test functions with `test_` prefix
4. Use `@pytest.mark.asyncio` for async tests
5. Mock external dependencies
6. Assert expected behavior
7. Run tests and verify coverage

Example:
```python
@pytest.mark.asyncio
async def test_my_feature(mock_service_clients, mock_security_manager):
    # Setup
    mock_service_clients.my_agent.get = AsyncMock(return_value=...)
    
    # Execute
    result = await my_tool.my_function(...)
    
    # Assert
    assert result == expected
    mock_security_manager.authorize_tool_call.assert_called_once()
```

