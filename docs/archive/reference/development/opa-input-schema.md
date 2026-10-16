# OPA Input Schema (SentinelGrid)

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Standard JSON payload every service/gateway should send to OPA (`data.sentinelgrid.authz.allow`).

```json
{
  "input": {
    "tenant_id": "t-123",
    "user": {
      "id": "u-456",
      "roles": ["admin", "analyst"],
      "groups": ["team-a"],
      "email": "alice@example.com"
    },
    "request": {
      "service": "api-gateway",
      "path": "/api/v1/siem/detections/123",
      "method": "GET"
    },
    "resource": {
      "type": "detection",
      "id": "123",
      "owner_tenant": "t-123"
    },
    "context": {
      "client": "web-ui",
      "plan_tier": "protect_defend_comply"
    }
  }
}
```

## Field reference
- `tenant_id`: caller’s tenant. Required.
- `user`: identity from JWT (id, roles, groups, email). Required.
- `request`: service name, HTTP path, method. Required.
- `resource`: logical type/id plus `owner_tenant`. Default owner is tenant_id if unknown.
- `context`: additional attributes (client/app, plan_tier, time/ip if available).

## Helper
- Python helper at `backend/libs/sg_core/opa.py` builds this shape and calls OPA.
- Configure OPA URL via `OPA_URL` env (default `http://opa:8181/v1/data/sentinelgrid/authz/allow`).

## Result contract
- Expect `{"result": true|false}` or `{"result": {"allow": true|false}}`. Fail closed on errors.
