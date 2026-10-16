# Compliance Runtime Truth Inventory

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Status:** Active runtime inventory  
**Created:** 2026-04-27  
**Purpose:** Runtime inventory for Compliance module launch readiness.

## Current Runtime Position

The live Compliance module is best described as **evidence-backed compliance readiness with SOC 2 as the strongest supported framework path**.

Customers can select supported frameworks, review framework-scoped status, collect and review durable evidence, create evidence packages, generate evidence-backed report snapshots, schedule reports, and approve or reject supervised Compliance Agent recommendations. Non-SOC 2 frameworks must still be described with their limitations: catalog/gap/evidence-scope support is available, but broad automatic compliance determination is not.

## Compatibility Endpoints To Preserve

These endpoints are used by the current dashboard and reporting flows and must remain backward-compatible during the generalized framework refactor:

- `GET /api/v1/compliance/soc2/coverage`
- `GET /api/v1/compliance/dashboard`
- `POST /api/v1/compliance/evidence/collect`

## Framework Catalog Endpoints

Read-only framework catalog endpoints are now active:

- `GET /api/v1/compliance/frameworks`
- `GET /api/v1/compliance/frameworks/{framework_id}`
- `GET /api/v1/compliance/frameworks/{framework_id}/controls`

These endpoints expose bundled SOC 2, HIPAA, PCI DSS, and NIST 800-171 control data. Tenant selections are active through the framework selection endpoints.

## Tenant Framework Selection Endpoints

Tenant framework selection endpoints are now active:

- `GET /api/v1/compliance/framework-selections`
- `PUT /api/v1/compliance/framework-selections`

Current behavior:

- Selections are stored in `tenant_framework_selections`.
- Selections are tenant-scoped with row-level security.
- If a tenant has no explicit selections, onboarding `trustProfile.frameworks` can seed initial rows.
- Once explicit rows exist, onboarding data no longer overwrites them.

Current limitation:

- Non-SOC 2 selections receive truthful catalog/gap status until mapped signals and accepted evidence support the control.
- Frontend editing is gated by `NEXT_PUBLIC_COMPLIANCE_MULTI_FRAMEWORK_ENABLED`; without the flag, selections are read-only in the dashboard.

## Compliance Service Runtime

Active service:

- `backend/services/compliance_service/app/main.py`

Routers currently included:

- `backend/services/compliance_service/app/api/coverage.py`
- `backend/services/compliance_service/app/api/remediation.py`
- `backend/services/compliance_service/app/api/frameworks.py`
- `backend/services/compliance_service/app/api/framework_selections.py`
- `backend/services/compliance_service/app/api/evidence.py`
- `backend/services/compliance_service/app/api/agent_workflow.py`
- `backend/services/compliance_service/app/api/launch_readiness.py`

Current behavior:

- `/api/v1/compliance/soc2/coverage` builds SOC 2 readiness from IAM findings, posture findings, alerts, playbooks, and playbook executions.
- `/api/v1/compliance/dashboard` adapts the same SOC 2 coverage payload into dashboard shape.
- SOC 2 coverage is now generated through the generalized coverage model and then adapted back to the legacy SOC 2 response shape.
- Each control can include optional `coverage_status`, `coverage_confidence`, `coverage_severity`, `coverage_gaps`, and `coverage_trace` metadata.
- Generalized coverage endpoints are active:
  - `GET /api/v1/compliance/coverage`
  - `GET /api/v1/compliance/frameworks/{framework_id}/coverage`
  - `GET /api/v1/compliance/controls/{control_id}/status`
- `/api/v1/compliance/dashboard` now includes selected framework coverage summaries in addition to the existing SOC 2 dashboard fields.
- Remediation routes enhance findings and create remediation/playbook actions.

Current limitation:

- Coverage is SOC 2-centered.
- Framework starter packs are informational/product-pack data, not full framework activation.
- Framework catalog data is runtime-addressable through APIs, and selected frameworks beyond SOC 2 return truthful catalog/workflow coverage with `not_started` or `needs_evidence` controls until evidence and cross-framework signal mapping land.
- Launch-readiness endpoints expose framework limitations and tenant admin controls:
  - `GET /api/v1/compliance/launch-readiness`
  - `GET /api/v1/compliance/admin/settings`
  - `PUT /api/v1/compliance/admin/settings`

## API Gateway Runtime

Active route file:

- `backend/services/api_gateway/app/api/routes_compliance.py`

Live proxy routes:

- `GET /api/v1/compliance/soc2/coverage`
- `GET /api/v1/compliance/dashboard`
- `POST /api/v1/compliance/evidence/collect`

Compatibility routes:

- `GET /api/v1/compliance/report`
- `GET /api/v1/compliance/audit-trail`
- `GET /api/v1/compliance/orphaned-entitlements`

These routes are no longer empty stubs. `/compliance/report` is deprecated and backed by reporting-service data, `/compliance/audit-trail` reads compliance audit events, and `/compliance/orphaned-entitlements` derives orphaned grants from IAM/entitlement data.

## Framework Data

Framework/control data exists in:

- `backend/services/compliance_service/app/data/soc2_controls.json`
- `backend/services/compliance_service/app/data/hipaa_security_rule.json`
- `backend/services/compliance_service/app/data/pci_dss_requirements.json`
- `backend/services/compliance_service/app/data/nist_800_171_controls.json`

The framework JSON files are now active through the read-only framework catalog API. Consolidated schema support exists for framework/control/mapping tables, tenant control status, control evidence requirements, and tenant framework selections. Tenant selections are persisted, but coverage status persistence is not active yet.

## Coverage Model Runtime

Generalized coverage domain models and schema fields are now present for:

- control coverage,
- framework coverage,
- control signals,
- control gaps,
- evidence requirement status,
- coverage status, severity, confidence, and refresh metadata.

Current limitation:

- The generalized signal mapping engine is active for the SOC 2 compatibility path only.
- Audit-log and durable evidence-item mapping are not active yet.
- Selected HIPAA, PCI DSS, NIST 800-171, ISO 27001 starter, and customer questionnaire frameworks receive generalized coverage envelopes, but control status remains catalog/workflow `not_started` unless SOC 2 signal mapping applies.
- New `tenant_control_status` coverage fields are ready for persistence, but production coverage writes have not been redirected to them yet.

## Framework Mapping Service Runtime

Framework mapping service routes are active for:

- `POST /api/v1/framework/map`
- `POST /api/v1/framework/map/nist`
- `POST /api/v1/framework/map/mitre`
- `POST /api/v1/framework/map-to-nist`
- `POST /api/v1/framework/map-to-soc2`
- `GET /api/v1/framework/nist/{control_id}`
- `GET /api/v1/framework/mitre/{technique_id}`
- `GET /api/v1/framework/soc2/{criterion_id}`

Current behavior:

- Internal service calls can authenticate with the configured internal service token and must propagate `X-Tenant-ID`.
- Mapping request bodies with `tenant_id` are rejected if they do not match the authenticated tenant context.
- Compliance finding enhancement now calls framework mapping with the real tenant context.

Current limitation:

- NIST/MITRE catalog detail endpoints still return placeholder detail objects outside the mapped IDs.
- Mapping is deterministic/static plus future AI placeholders; it is not yet backed by durable evidence or selected framework coverage.

## Evidence Runtime

Current evidence behavior:

- API gateway proxies evidence collection to the IAM agent.
- IAM evidence collection can return evidence-shaped payloads.
- Dashboard/reporting counts detections, checks, playbooks, and executions as reportable evidence-like objects.
- Consolidated schema now has a durable evidence repository foundation: normalized evidence items, packages, control links, collection tasks, reviews, exports, integrity metadata, retention fields, and RLS on new evidence lifecycle tables.
- Compliance Service now exposes durable evidence repository APIs:
  - `GET /api/v1/compliance/evidence`
  - `POST /api/v1/compliance/evidence`
  - `GET /api/v1/compliance/evidence/{evidence_id}`
  - `POST /api/v1/compliance/evidence/{evidence_id}/review`
  - `POST /api/v1/compliance/evidence/packages`
  - `GET /api/v1/compliance/evidence/packages/{package_id}`
  - `POST /api/v1/compliance/evidence/packages/{package_id}/export`
- API gateway proxies those evidence repository APIs and blocks cross-tenant override attempts.
- Evidence creation, review, package creation, and export requests are role-gated by Compliance Service token roles.
- IAM compliance evidence collection now attempts to persist into the Compliance evidence repository:
  - API-derived IAM evidence is written as durable evidence items with provenance, hashes, idempotency keys, and SOC 2 control links where mappings exist.
  - Unsupported or unavailable IAM evidence paths create durable collection tasks with `needs_connector` or `manual_evidence_required` status.
  - Placeholder success values are no longer returned as audit-ready evidence from the IAM collector.

Current limitation:

- IAM evidence item review is still required before evidence can support audit-ready status.
- IAM persistence depends on Compliance Service availability and the caller having the required compliance evidence role.
- Non-IAM runtime collectors are not yet wired to write durable evidence.
- Placeholder evidence values must not be treated as audit-ready evidence.

## Reporting Runtime

Current reporting behavior:

- Reporting service can generate and persist PDF/CSV reports.
- Report templates include compliance, SOC 2, trust artifact, and evidence-summary style exports.
- Report shares and generated report records exist.

Current limitation:

- Evidence-backed reports depend on the caller selecting the correct frameworks, controls, and evidence packages.
- Binary report storage/export worker health must be monitored separately from report metadata creation.
- Legacy reports created before Phase 8 are marked as metadata-only if no durable evidence snapshot exists.

## AI Agent Runtime

Current agent-related assets:

- `backend/libs/sg_agent_runtime/agents.py` defines `compliance_agent`.
- Frontend can display a compliance agent badge/context.

Current limitation:

- Compliance Agent write actions are supervised recommendations and require human approval.
- Tenant controls can disable Compliance Agent workflows; they cannot override `COMPLIANCE_AGENT_ENABLED=false`.
- Questionnaire assist remains deterministic/template-driven and should not be described as autonomous compliance determination.

## Frontend Runtime

Current surfaces:

- `frontend/src/components/compliance/pages/ComplianceDashboardPage.tsx`
- `frontend/src/components/compliance/FrameworkSelectionPanel.tsx`
- `frontend/src/components/compliance/pages/ComplianceReportsPage.tsx`
- `frontend/src/components/compliance/pages/ComplianceReportSchedulesPage.tsx`
- `frontend/src/components/compliance/FrameworkStarterPacksPanel.tsx`
- `frontend/src/components/compliance/ComplianceWorkflowPanel.tsx`
- `frontend/src/lib/api/compliance.ts`

Current limitation:

- Framework picker editing is feature-flagged.
- Evidence Center and Compliance Agent workbench are present, but customer claims must follow the framework limitations in `docs/archive/validation/compliance/compliance-customer-guide-2026-04-28.md`.

## Launch Guardrails

Product and UI copy should avoid implying:

- full HIPAA/PCI/CMMC compliance tracking,
- automatic legal or auditor-ready determinations,
- evidence-backed status when evidence is pending, rejected, expired, or absent,
- autonomous Compliance AI Agent execution.

Truthful labels should use terms such as:

- compliance readiness,
- selected framework status,
- reviewed evidence,
- evidence-backed report snapshots,
- supervised Compliance Agent recommendations,
- framework catalog and gap tracking.
