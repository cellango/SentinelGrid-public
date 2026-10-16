package sentinelgrid.authz

import future.keywords.in

# Helpers
base_input := {
  "tenant_id": "demo-tenant",
  "user": {
    "id": "user-123",
    "roles": ["analyst"],
    "groups": ["demo-group"],
    "email": "analyst@demo.sentinelgrid.ai"
  },
  "request": {
    "service": "siem-api",
    "path": "/api/v1/detections/123",
    "method": "GET"
  },
  "resource": {
    "type": "detection",
    "id": "123",
    "owner_tenant": "demo-tenant"
  },
  "context": {
    "client": "web-ui",
    "plan_tier": "protect_defend_comply"
  }
}

test_admin_can_access_any_resource_in_tenant {
  input := base_input with {
    "user": {"id": "admin-1", "roles": ["admin"], "groups": [], "email": "admin@demo.sentinelgrid.ai"}
  }
  allow with input as input
}

test_defender_can_edit_detection {
  input := base_input with {
    "user": {"id": "def-1", "roles": ["defender"], "groups": [], "email": "def@demo.sentinelgrid.ai"},
    "request": {"service": "siem-api", "path": "/api/v1/detections/123", "method": "POST"}
  }
  allow with input as input
}

test_defender_cannot_delete_detection {
  input := base_input with {
    "user": {"id": "def-1", "roles": ["defender"], "groups": [], "email": "def@demo.sentinelgrid.ai"},
    "request": {"service": "siem-api", "path": "/api/v1/detections/123", "method": "DELETE"}
  }
  not allow with input as input
}

test_analyst_read_only_detection {
  allow with input as base_input
}

test_cross_tenant_denied {
  input := base_input with {
    "resource": {"type": "detection", "id": "123", "owner_tenant": "other-tenant"}
  }
  not allow with input as input
}

test_compliance_requires_top_tier {
  input := base_input with {
    "resource": {"type": "compliance", "id": "c-1", "owner_tenant": "demo-tenant"},
    "context": {"client": "web-ui", "plan_tier": "protect_defend"}
  }
  not allow with input as input
}

test_compliance_allowed_with_top_tier {
  input := base_input with {
    "user": {"id": "admin-1", "roles": ["admin"], "groups": [], "email": "admin@demo.sentinelgrid.ai"},
    "resource": {"type": "compliance", "id": "c-1", "owner_tenant": "demo-tenant"},
    "context": {"client": "web-ui", "plan_tier": "protect_defend_comply"}
  }
  allow with input as input
}
