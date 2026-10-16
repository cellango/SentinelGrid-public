# Compliance Operations

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Purpose

Diagnose and support compliance framework selection, evidence collection, evidence export, Compliance Agent recommendations, and compliance report generation without reading service source code.

## Primary Services

| Service | Internal base URL | Operator endpoints |
| --- | --- | --- |
| compliance-service | `http://compliance_service:8000` | `/health`, `/metrics`, `/metrics/prometheus` |
| reporting-service | `http://reporting_service:8000` | `/health`, `/metrics`, `/metrics/prometheus` |
| api-gateway | `http://api_gateway:8000` | `/api/v1/compliance/*`, `/api/v1/reports/*` |

Use `X-Request-ID`, `X-Correlation-ID`, `X-Tenant-ID`, and audit event IDs when correlating logs across services.

## Metrics And Alerts

Primary compliance metrics:

- `compliance_evidence_collection_total{outcome,source_system,collection_method}`
- `compliance_evidence_collection_tasks_total{status,task_type}`
- `compliance_stale_evidence_items{tenant_id}`
- `compliance_framework_selection_changes_total{framework_id,status}`
- `compliance_agent_recommendation_decisions_total{state,trigger_type}`
- `compliance_report_generation_total{outcome,report_format,template_type}`
- `compliance_report_generation_failures_total{report_format,template_type}`

Production alert rules:

- `SentinelGridComplianceEvidenceCollectionFailuresDetected`
- `SentinelGridComplianceReportGenerationFailuresDetected`
- `SentinelGridComplianceStaleEvidenceDetected`

Quick checks:

```bash
curl -fsS http://compliance_service:8000/metrics | jq
curl -fsS http://compliance_service:8000/metrics/prometheus | rg 'compliance_evidence|compliance_stale|compliance_agent'
curl -fsS http://reporting_service:8000/metrics | jq
curl -fsS http://reporting_service:8000/metrics/prometheus | rg 'compliance_report_generation'
```

## Phase 8 Migration Backfill

Use this after schema migrations are current and before launch validation. The backfill is dry-run by default and does not create evidence items.

Dry-run all tenants:

```bash
PYTHONPATH=backend/services/compliance_service:backend/libs \
  python backend/scripts/backfill_compliance_phase8.py
```

Apply for one tenant:

```bash
PYTHONPATH=backend/services/compliance_service:backend/libs \
  python backend/scripts/backfill_compliance_phase8.py --tenant-id <tenant-id> --apply
```

Expected behavior:

- tenants with existing `tenant_framework_selections` are skipped
- tenants with onboarding trust profiles are seeded from `trustProfile.frameworks`
- tenants without framework signals receive an explicit SOC 2 selection from `legacy_soc2_readiness`
- legacy compliance reports receive metadata markers that explain they do not have durable evidence snapshots
- `evidence_items_created` must remain `0`

## Launch Readiness And Admin Controls

Use this before enabling Compliance for a customer or demo tenant.

Check runtime launch metadata:

```bash
curl -fsS -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant-id>" \
  "http://api_gateway:8000/api/v1/compliance/launch-readiness" | jq
```

Check tenant admin controls:

```bash
curl -fsS -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant-id>" \
  "http://api_gateway:8000/api/v1/compliance/admin/settings" | jq
```

Disable Compliance Agent workflows for one tenant:

```bash
curl -fsS -X PUT -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant-id>" \
  -H "Content-Type: application/json" \
  -d '{"compliance_agent_workflows":false}' \
  "http://api_gateway:8000/api/v1/compliance/admin/settings" | jq
```

The tenant controls are bounded by platform flags. If `COMPLIANCE_AGENT_ENABLED=false`, a tenant admin cannot make `compliance_agent_workflows` effective until operators enable the platform flag and restart the relevant services.

## Compliance Demo Tenant Seed

Use this when preparing the launch demo tenant. Dry-run first:

```bash
PYTHONPATH=backend/services/compliance_service:backend/libs \
  python backend/scripts/seed_compliance_launch_demo.py --tenant-slug demo
```

Apply after reviewing the planned objects:

```bash
PYTHONPATH=backend/services/compliance_service:backend/libs \
  python backend/scripts/seed_compliance_launch_demo.py --tenant-slug demo --apply
```

Expected seed objects:

- selected frameworks: SOC 2 active, HIPAA evaluating, PCI DSS evaluating
- SOC 2 Q2 evidence package
- accepted IAM access review and MFA policy evidence items
- completed IAM evidence collection task
- generated SOC 2 evidence-summary report metadata
- proposed HIPAA missing-evidence Compliance Agent recommendation

## Failed Evidence Collection

Trigger examples:

- `SentinelGridComplianceEvidenceCollectionFailuresDetected`
- user reports missing IAM, configuration, policy, or audit-log evidence
- `compliance_evidence_collection_tasks_total{status="failed"}` increases

Triage:

1. Capture tenant ID, framework ID, evidence type, request/correlation ID, and actor.
2. Check collection counters and stale evidence gauge:

```bash
curl -fsS http://compliance_service:8000/metrics | jq '.counters.compliance_evidence_collection_tasks_total'
curl -fsS http://compliance_service:8000/metrics | jq '.counters.compliance_evidence_collection_total'
curl -fsS http://compliance_service:8000/metrics | jq '.gauges.compliance_stale_evidence_items'
```

3. List recent collection tasks for the tenant:

```bash
curl -fsS -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant-id>" \
  "http://api_gateway:8000/api/v1/compliance/evidence/tasks?limit=20" | jq
```

4. Check the evidence inventory for the expected framework/control:

```bash
curl -fsS -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant-id>" \
  "http://api_gateway:8000/api/v1/compliance/evidence?framework_id=<framework-id>&control_id=<control-id>" | jq
```

5. If evidence exists but is expired, schedule recollection from the evidence item:

```bash
curl -fsS -X POST -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant-id>" \
  -H "Content-Type: application/json" \
  -d '{"reason":"manual_refresh","metadata":{"operator_reason":"failed_collection_recovery"}}' \
  "http://api_gateway:8000/api/v1/compliance/evidence/<evidence-id>/recollection-task" | jq
```

Containment:

- Do not mark a control supported by expired evidence.
- If evidence collection is unavailable for a tenant, communicate that compliance status is degraded, not audit-ready.
- If cross-tenant data appears in a response, treat it as Sev-1 and switch to `production_support_and_incident_response.md`.

## Missing Framework Mappings

Trigger examples:

- selected framework has no controls or shows unexpected gaps
- Compliance dashboard cannot explain a SOC 2, HIPAA, PCI, NIST, or CMMC control
- report sections show unmapped controls or empty control evidence mapping

Triage:

1. Confirm the tenant selected the framework:

```bash
curl -fsS -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant-id>" \
  "http://api_gateway:8000/api/v1/compliance/framework-selections" | jq
```

2. Confirm framework catalog and controls are available:

```bash
curl -fsS "http://api_gateway:8000/api/v1/compliance/frameworks/<framework-id>" | jq
curl -fsS "http://api_gateway:8000/api/v1/compliance/frameworks/<framework-id>/controls" | jq
```

3. Check generalized coverage:

```bash
curl -fsS -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant-id>" \
  "http://api_gateway:8000/api/v1/compliance/frameworks/<framework-id>/coverage?include_evidence=true&include_gaps=true" | jq
```

4. Check whether framework selection changes recently increased:

```bash
curl -fsS http://compliance_service:8000/metrics | jq '.counters.compliance_framework_selection_changes_total'
```

Resolution:

- If the framework is not selected, use the framework-selection UI or `PUT /api/v1/compliance/framework-selections`.
- If catalog controls are missing, stop promising coverage for that framework and open a framework catalog defect.
- If controls exist but evidence mapping is empty, continue through the failed evidence collection workflow.

## Report Export Failure

Trigger examples:

- `SentinelGridComplianceReportGenerationFailuresDetected`
- report remains `FAILED` or `PENDING`
- download route returns 404, 403, or 500

Triage:

1. Check reporting metrics:

```bash
curl -fsS http://reporting_service:8000/metrics | jq '.counters.compliance_report_generation_total'
curl -fsS http://reporting_service:8000/metrics | jq '.counters.compliance_report_generation_failures_total'
```

2. Inspect the report record and download path:

```bash
curl -fsS -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant-id>" \
  "http://api_gateway:8000/api/v1/reports/<report-id>" | jq
curl -fsS -I -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant-id>" \
  "http://api_gateway:8000/api/v1/reports/<report-id>/download"
```

3. If generation failed, create a fresh report after confirming the template and requested format:

```bash
curl -fsS -X POST -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant-id>" \
  -H "Content-Type: application/json" \
  -d '{"template_id":"<template-id>","format":"pdf","framework_ids":["soc2"],"include_gaps":true}' \
  "http://api_gateway:8000/api/v1/reports/generate" | jq
```

Containment:

- Do not manually edit generated report files.
- If the report includes compliance evidence, verify the report metadata includes a compliance snapshot hash before sharing externally.
- If storage is unavailable or file paths are missing, treat the report as not generated even if a database row exists.

## Tenant Evidence Export Request

Use this path when a customer asks for an evidence package or auditor-facing export.

Steps:

1. Verify requester identity, tenant ID, and export role. Required roles include `admin`, `tenant_admin`, `compliance_manager`, `compliance_officer`, `evidence_reviewer`, or `report_exporter`.
2. List or create the evidence package:

```bash
curl -fsS -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant-id>" \
  "http://api_gateway:8000/api/v1/compliance/evidence/packages?framework_id=<framework-id>" | jq
```

3. Export the package:

```bash
curl -fsS -X POST -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant-id>" \
  -H "Content-Type: application/json" \
  -d '{"export_format":"zip","manifest":{"requested_for":"auditor_export"}}' \
  "http://api_gateway:8000/api/v1/compliance/evidence/packages/<package-id>/export" | jq
```

4. Verify item integrity before external handoff:

```bash
curl -fsS -X POST -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant-id>" \
  -H "Content-Type: application/json" \
  -d '{"observed_hash_sha256":"<64-character-sha256>","verification_method":"hash_compare"}' \
  "http://api_gateway:8000/api/v1/compliance/evidence/<evidence-id>/verify" | jq
```

Rules:

- Never export evidence using another tenant's token or tenant header.
- Expired or stale evidence must be disclosed as stale and should not support audit claims.
- Completed exports are immutable; create a new export if the scope changes.

## Agent Disabled Or Fallback Mode

Trigger examples:

- Compliance Agent recommendations are not appearing after evidence/report actions
- dashboard chat returns deterministic compliance context instead of operational recommendations
- `COMPLIANCE_AGENT_ENABLED=false`

Triage:

1. Confirm module capability flags:

```bash
curl -fsS -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant-id>" \
  "http://api_gateway:8000/api/v1/compliance/capabilities" | jq
```

2. Check recommendation queue and decision metrics:

```bash
curl -fsS -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant-id>" \
  "http://api_gateway:8000/api/v1/compliance/agent/recommendations?state=proposed" | jq
curl -fsS http://compliance_service:8000/metrics | jq '.counters.compliance_agent_recommendation_decisions_total'
```

3. If the agent is disabled, use manual evidence collection, review, and report-generation workflows. Do not claim autonomous compliance remediation is active.
4. If recommendations exist but cannot be approved or rejected, check role mappings and use `POST /api/v1/compliance/agent/recommendations/{recommendation_id}/decision`.

Containment:

- Agent fallback mode is a product capability degradation, not a compliance failure by itself.
- Any customer-facing statement must say recommendations require human approval and do not constitute an audit attestation.
