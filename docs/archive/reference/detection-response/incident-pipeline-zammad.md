
> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.

## Incident Management (Pipeline + Ticketing with Zammad)

This document captures the actionable plan to stand up the SaaS-managed incident pipeline and ticketing with Zammad, aligned to the earlier requirements (NIST IR workflow, dedup/suppression, enrichment, automatic ticketing, tenant ownership).

### 1) Ownership & Tenant Settings
- Add a tenant-level field: `incident_management_mode` = `saas_managed` | `customer_managed`.
- Default to `saas_managed`; SOC Manager role in our realm owns tickets for this mode.
- For `customer_managed`, route to customer SOC manager and optionally bypass Zammad.

### 2) Pipeline Stages (per incident)
1. **Ingress**: detection → alert → incident candidate (include tenant_id, realm, severity, category, MITRE, controls, asset/user, dedup key).
2. **Dedup**: hash on `(tenant_id, category|alert_type, asset/user, severity bucket, time window)`; merge into existing open incident when hash matches.
3. **Suppression**: rule-based drops (maintenance windows, known benign sources, low-severity + allowlist).
4. **Enrichment**: add MITRE, control mappings, asset/user context, past-similar incidents, and recommended playbook(s).
5. **Ticketing**: create/update ticket in Zammad (SaaS) or mark as customer-managed; store external ticket id/provider on the incident.
6. **Workflow**: enforce NIST IR phases via incident state machine; sync status to ticket.

### 3) Zammad Integration Plan
- **Config**: env vars `ZAMMAD_URL`, `ZAMMAD_TOKEN`, `ZAMMAD_GROUP`, `ZAMMAD_PRIORITY_MAP`, `ZAMMAD_SLA_MINUTES_DEFAULT`.
- **API client** (ticketing_service): create/update Zammad ticket with subject, article (HTML/text), priority, state, tags (tenant, realm, alert/incident ids), and custom fields for:
  - `sg_incident_id`, `sg_tenant_id`, `sg_alert_ids`, `sg_severity`, `sg_mitre`, `sg_controls`.
- **Sync rules**:
  - Incident open → Zammad state = `new`/`open`.
  - Incident in progress → `pending reminder` or `open`.
  - Incident resolved → `closed`.
  - Propagate assignee from SOC Manager to Zammad owner when SaaS-managed.
- **Failure handling**: retry w/ backoff; if Zammad down, queue locally and mark incident as `ticket_pending`.

### 4) Services & Endpoints to Touch
- **ticketing_service**:
  - Add Zammad client + mapper; feature flag for provider (`zammad` vs `thehive` legacy).
  - On ticket create/update, call Zammad; persist `external_id`, `external_ticket_provider='zammad'`.
- **incident_service / detection_service / orchestrator**:
  - Route incident creation through the pipeline above; pass dedup key and enrichment to ticketing_service.
  - Expose `incident_management_mode` in the incident creation context.
- **api_gateway**:
  - Proxy incident and ticket endpoints; surface `external_ticket_provider` and `external_ticket_id` to UI.

### 5) Dedup & Suppression Defaults
- Dedup window: 30 minutes (configurable). Key parts: alert_type/category + entity (user or asset) + severity bucket.
- Suppress if: severity=low AND source in allowlist; or during maintenance window for the asset; or if rule/tag = `suppress`.
- Store dedup/suppression decision and rationale on incident/audit.

### 6) Enrichment/Data Completeness
- Ensure incidents carry: `category`, `severity`, `mitre_tactics/techniques`, `nist_controls`, `asset_id`, `user_identifier`, `recommended_playbook`, `related_alert_ids`.
- Populate `related_detections` for UI, and timeline events for audit (status changes, dedup hits, ticket sync).

### 7) UI Readiness (already partially done)
- Incidents UI accepts `external_ticket_provider/id`, phase/status/assignee, related detections, timeline, control/MITRE fields.
- Alerts UI shows related incidents, audit feed, playbook execution, control coverage.

### 8) Incremental Delivery Checklist
1. Add Zammad client + config and provider switch in `ticketing_service`; persist external ticket refs.
2. Add pipeline hook in detection/incident creation to call ticketing service with dedup/suppression/enrichment inputs.
3. Add tenant flag `incident_management_mode`; default SaaS-managed.
4. Add audit entries for dedup/suppress/ticket actions; expose via API (replace current stub).
5. Seed demo incidents/alerts with full MITRE/control/recommended data for UI sanity until live data flows.

### Parking Lot (later)
- Continuous playbook execution status stream.
- Advanced suppression rules editor and per-tenant overrides.
- Customer-managed mode orchestration (Jira/ServiceNow connectors).
- SLA metrics (MTTD/MTTR) and per-tenant reporting in UI.
