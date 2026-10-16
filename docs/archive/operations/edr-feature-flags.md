# EDR Feature Flags (per tenant)

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Use these endpoints in `tenant_service` to toggle endpoint telemetry sources for a tenant:

- `GET /api/v1/tenants/{tenant_id}/feature-flags`  
  Returns `edr_openedr_enabled` (default true) and `edr_velociraptor_enabled` (default false).
- `POST /api/v1/tenants/{tenant_id}/feature-flags` with JSON body  
  ```json
  {
    "edr_openedr_enabled": true,
    "edr_velociraptor_enabled": false
  }
  ```
  Updates flags; values are persisted in `tenant_preferences.feature_flags`.

Operational guidance:
- Keep OpenEDR enabled by default for new tenants; disable per tenant via the POST call if they opt out.
- Enable Velociraptor per tenant only when collection/hunt use cases are approved.
- When disabling a source, also stop/disable the corresponding sidecar via your config management and systemd units.
- Audit: `tenant_preferences.updated_at` tracks last change; log change requests in the ticketing system.
