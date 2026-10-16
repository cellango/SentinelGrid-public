# Tenant Isolation Tests

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../../RELEASE_SCOPE.md) first.


This test suite ensures that playbook operations are properly isolated by tenant. It verifies that:

## Test Coverage

### ✅ Tenant Isolation in CRUD Operations
- **List Playbooks**: Tenants only see their own playbooks
- **Get Playbook**: Tenants cannot access other tenants' playbooks (404)
- **Update Playbook**: Tenants cannot update other tenants' playbooks (404)
- **Delete Playbook**: Tenants cannot delete other tenants' playbooks (404)
- **Copy Playbook**: Tenants cannot copy other tenants' playbooks (404)
- **Validate Playbook**: Tenants cannot validate other tenants' playbooks (404)

### ✅ Tenant Assignment
- **Create Playbook**: New playbooks are assigned to the correct tenant

### ✅ Execution Isolation
- **Execute Playbook**: Tenants cannot execute other tenants' playbooks
- **Execution Status**: Tenants cannot access other tenants' execution status

### ✅ Filter Isolation
- **Category Filters**: Filters work correctly within tenant boundaries
- **Template Filters**: Template playbooks are tenant-isolated

### ✅ Security
- **Missing Tenant Header**: Requests without tenant header are rejected (401)
- **Invalid Tenant Header**: Invalid formats are rejected
- **Empty Tenant Header**: Empty headers are rejected

## Running the Tests

```bash
# Run all tenant isolation tests
cd backend/agents/soar_agent
pytest tests/test_tenant_isolation.py -v

# Run specific test class
pytest tests/test_tenant_isolation.py::TestTenantIsolation -v

# Run with coverage
pytest tests/test_tenant_isolation.py --cov=app --cov-report=html
```

## Test Data

The tests use:
- **Tenant 1**: Creates 3 playbooks (phishing category)
- **Tenant 2**: Creates 2 playbooks (malware category)

Each test verifies that cross-tenant access attempts result in 404 (not found) responses, ensuring proper tenant isolation.

## Security Considerations

These tests are critical for ensuring:
1. **Data Privacy**: Tenants cannot access other tenants' data
2. **Prevention of Data Leakage**: Cross-tenant queries are impossible
3. **Compliance**: Multi-tenant isolation requirements are met
4. **Attack Prevention**: Prevents unauthorized access to other tenants' playbooks

## Test Structure

```python
class TestTenantIsolation:
    """Test tenant isolation in playbook operations."""
    - test_list_playbooks_tenant_isolation
    - test_get_playbook_cross_tenant_access_denied
    - test_update_playbook_cross_tenant_access_denied
    - test_delete_playbook_cross_tenant_access_denied
    - test_copy_playbook_cross_tenant_access_denied
    - test_validate_playbook_cross_tenant_access_denied
    - test_create_playbook_tenant_assignment
    - test_execute_playbook_cross_tenant_access_denied
    - test_list_playbooks_with_filters_tenant_isolation
    - test_template_playbooks_tenant_isolation
    - test_execution_status_tenant_isolation

class TestTenantHeaderValidation:
    """Test tenant header validation and security."""
    - test_missing_tenant_header_rejected
    - test_invalid_tenant_header_format
    - test_empty_tenant_header_rejected
```

## Integration with CI/CD

These tests should be run in every CI/CD pipeline to ensure tenant isolation is never compromised by code changes.
