# Multi-Tenancy Remediation Status

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Status:** Remediation Complete, Audit Closure Pending  
**Last Updated:** 2026-03-30  
**Audience:** Engineering, Security, Compliance, Audit

**Related**
- [MULTI_TENANCY_AUDIT_READINESS_PLAN.md](../README.md#retired-references)
- [MULTI_TENANCY_AUDIT_EXECUTION_SPEC.md](multi-tenancy-audit-execution-spec.md)
- [MULTI_TENANCY_AUDIT_IMPLEMENTATION_BACKLOG.md](multi-tenancy-audit-implementation-backlog.md)
- [MULTI_TENANCY_DEFENSIBLE_REMEDIATION_WORKLIST.md](multi-tenancy-defensible-remediation-worklist.md)
- [docs/archive/operations/multi-tenancy-audit-execution.md](../operations/multi-tenancy-audit-execution.md)

## Purpose

This document records the current state of the multi-tenancy remediation program so work can pause and resume cleanly later.

It is the current handoff snapshot for:

- what has been completed
- what is still open
- what decisions are blocked on policy, not code
- what artifact set should be treated as the current baseline

## Current Baseline

Latest baseline artifact:

- `artifacts/audit/multi-tenancy/2026-03-30/110555-local-smoke`

Baseline results from `remediation/summary.json`:

| Metric | Current Value |
|---|---:|
| Audit status | `passed` |
| Catalog mismatches | `0` |
| Live exposure failures | `0` |
| Plain DB routes | `3` |
| Plain DB routes without tenant signal | `0` |
| Critical routes | `0` |
| Review-required routes | `0` |

Interpretation:

- The dangerous class of routes is now closed: there are no remaining `critical_routes`.
- The runtime remediation backlog is now closed: there are no remaining `high_risk` owner queues.
- The remediation-only review backlog is now closed: there are no remaining `review_required` owner queues.
- The only remaining program work is audit-evidence closure and packaging.
- The audit pack itself is operational and producing repeatable artifacts.

## Completed Work

### Audit Pack And Evidence System

Completed:

- repeatable audit pack under `scripts/audit/multi-tenancy/`
- manifest, profiles, runbook, and artifact packaging
- route inventory exporter
- RLS catalog and runtime verification
- curated two-tenant negative suite
- blocked-violation evidence collector
- remediation report, owner queues, and remediation program generation

Result:

- the tenant-isolation evidence workflow is now scriptable and repeatable
- the current artifact tree can be regenerated on demand

### Phase P1: Database RLS Parity

Completed:

- live database RLS parity remediation
- live verification that catalog drift is `0`
- live verification that sampled exposure failures are `0`

Result:

- the database platform queue is closed

### Phase P2: Control-Plane Critical Route Remediation

Completed:

- API Gateway critical routes cleared
- IAM Agent critical routes cleared
- Entitlement Agent critical routes cleared

Result:

- all control-plane `critical` plain-session routes are at `0`

### Phase P3: Secondary Service Critical Route Remediation

Completed critical-route cleanup for:

- tenant-service
- metadata-service
- compliance-service
- framework-service
- soar-agent
- automated-response-service
- cert-service
- connector-service
- reporting-service public share path
- siem-agent router family
- observables-service
- model-gateway critical families

Result:

- global `critical_routes` is now `0`
- global `plain_db_routes_without_tenant_signal` is now `0`

### Additional High-Risk Cleanup Already Completed

Completed slices include:

- API Gateway runtime high-risk queue reduced to `0`
- SOAR Agent high-risk queue reduced to `0`
- detection-service rules family moved to tenant-scoped access
- model-gateway vuln chat route moved to tenant-scoped access
- metadata-service asset and vulnerability routes moved to authenticated query-tenant session helpers
- connector-service CRUD, sync, test, and OAuth init routes moved to tenant-scoped sessions
- email-ingestion-service phishing and containment routes moved to query-tenant scoped sessions
- cmdb-service asset routes moved to query-tenant scoped sessions
- cert-service user-facing CA, certificate, and bootstrap-token routes moved to tenant-scoped sessions
- ticketing-service ticket CRUD, comment, search, and tab routes moved to tenant-scoped sessions
- wazuh-manager-service agent registration and lifecycle routes moved to tenant-scoped sessions
- vulnerability-service CVE lookup, search, and sync routes moved to authenticated query-tenant sessions
- ai-enrichment-agent enrichment trigger and retrieval routes moved to authenticated query-tenant sessions
- compliance-service coverage and dashboard routes moved to authenticated tenant-scoped sessions
- entitlement-agent compliance and role-mapping routes moved to tenant-scoped access
- reporting-service tenant-owned report and share routes moved to tenant-scoped sessions
- reporting-service shared template browsing and on-demand generation aligned with tenant-scoped RLS
- reporting-service scheduled report routes restricted to tenant-owned templates only
- model-gateway shared framework loaders moved to an explicit superadmin-scoped DB path
- model-gateway git-ingestion routes split between tenant-owned access and explicit platform-operation access
- iam-agent governance routes moved to request-context-backed tenant-scoped sessions
- iam-agent role-mapping routes moved to request-context-backed tenant-scoped sessions
- iam-agent app-catalog routes moved to request-context-backed tenant-scoped sessions
- iam-agent app inventory routes moved to request-context-backed tenant-scoped sessions
- iam-agent device management routes moved to request-context-backed tenant-scoped sessions
- iam-agent git provider routes moved to request-context-backed tenant-scoped sessions
- iam-agent git scanning routes moved to request-context-backed tenant-scoped sessions
- iam-agent hardened-image routes moved to request-context-backed tenant-scoped sessions
- iam-agent user-onboarding invitation and bulk-upload routes moved to request-context-backed tenant-scoped sessions
- iam-agent onboarding setup routes moved from header/fallback tenant resolution to authenticated request-context resolution
- iam-agent payment conversion routes hardened with backend-issued provisioning tokens, checkout-session matching, and explicit approved public-boundary classification
- iam-agent organization provisioning routes moved to an explicit superadmin DB path and approved as platform-admin boundaries
- iam-agent realm provisioning and realm status routes moved from placeholder platform-admin auth to authenticated request-context enforcement and approved platform-admin boundaries
- iam-agent external IdP diagnostic routes moved from public probe surfaces to authenticated admin-only request-context enforcement
- iam-agent public OIDC state issuance plus OIDC/SAML callback routes moved to explicit approved public-auth boundaries with server-side state binding and compatibility-query validation
- iam-agent identity stats route moved from a raw `X-Tenant-ID` public surface to an explicit internal orchestrator analytics boundary with tenant-scoped Keycloak counts
- iam-agent dashboard snapshot route moved from token-or-header tenant fallback to authenticated request-context tenant derivation
- iam-agent marketing funnel summary moved from a public reporting surface to an explicit internal service-token analytics boundary
- iam-agent lead lookup moved from a bare public UUID probe to an approved token-bound pre-tenant boundary with minimized response payloads
- api-gateway orchestrator scan and tenant-path routes moved from generic review-required surfaces to explicit authenticated gateway boundaries backed by same-tenant path enforcement and token-derived tenant resolution
- api-gateway SIEM search, detection-rule detail, and entity-timeline proxies moved from generic review-required surfaces to explicit authenticated gateway boundaries backed by token-derived tenant forwarding
- api-gateway compliance dashboard, SOC 2 coverage, and evidence-collect proxies moved from generic review-required surfaces to explicit authenticated gateway boundaries, with body tenant overrides now rejected on mismatch
- api-gateway AI activity read/write proxies moved from generic review-required surfaces to explicit authenticated gateway boundaries, with query and body tenant overrides now rejected on mismatch
- api-gateway onboarding status and completion proxies moved from generic review-required surfaces to explicit authenticated gateway boundaries, and caller-supplied X-Tenant-ID hints are ignored for both IAM proxying and initial scan enqueue
- api-gateway vulnerability and dashboard chat proxies moved from generic review-required surfaces to explicit authenticated gateway boundaries, and any body tenant override is now rejected on mismatch
- api-gateway IAM dashboard snapshot moved from a generic review-required surface to an explicit authenticated gateway boundary, and caller-supplied X-Tenant-ID hints are ignored
- api-gateway incident updates moved from a generic review-required surface to an explicit authenticated gateway boundary, and caller-supplied X-Tenant-ID hints are ignored
- api-gateway AI Shield ingest moved from a generic review-required surface to an explicit internal service-token boundary, and any body org_id must now match the dispatch tenant header
- api-gateway login and refresh routes moved from pending review to an explicit approved pre-auth hint boundary that allowlists only X-Tenant-ID and X-Realm before identity is established or refreshed
- api-gateway ingest pipeline simulation moved from pending review to an explicit approved shared diagnostic boundary for platform pipeline testing

## Remaining Work

The remaining work is no longer remediation. It is final audit closure.

If the immediate goal is to make the audit claim technically defensible before investing more in audit packaging, use:

- [MULTI_TENANCY_DEFENSIBLE_REMEDIATION_WORKLIST.md](multi-tenancy-defensible-remediation-worklist.md)

### Remaining Owner Queues

Current owner queue index is:

- `artifacts/audit/multi-tenancy/2026-03-30/110555-local-smoke/remediation/owner-queues/index.md`

Current remaining queues:

| Owner | Critical | High Risk | Review Required |
|---|---:|---:|---:|
| database-platform | 0 | 0 | 0 |

### Review-Required Surfaces

There are no remaining `review_required` control-plane surfaces in the current baseline.

### Reporting-Service Policy Decision Status

The `reporting-service` policy decision is now resolved.

Implemented outcome:

- shared `report_templates` rows with `tenant_id IS NULL` remain readable under tenant-scoped sessions for browsing and on-demand generation
- schedule state is tenant-owned only, so shared system templates are no longer directly schedulable
- RLS and route behavior are now aligned through `backend/migrations_consolidated/V004__report_template_shared_select_policy.sql`

Result:

- `reporting-service` is out of the remaining owner queue
- there is no remaining active policy-dependent owner queue in the current runtime backlog

### Model-Gateway Status

`model-gateway` is now effectively closed out of the runtime backlog.

Completed slices now cover:

- `backend/services/model_gateway/app/api/knowledge_base_loader.py`
- `backend/services/model_gateway/app/api/rag.py`
- `backend/services/model_gateway/app/api/git_ingestion.py`

Implemented outcome:

- shared framework loaders now use an explicit superadmin-scoped DB path
- generic RAG write APIs are now tenant-owned only
- git-ingestion now separates tenant-owned repository operations from explicit platform-operation global access
- `model-gateway` is out of the remaining owner queue

### Entitlement-Agent Status

`entitlement-agent` is now effectively closed out of the runtime backlog.

Completed slices now cover:

- `backend/services/entitlement_agent/app/api/entitlements.py`
- `backend/services/entitlement_agent/app/api/bulk_operations.py`
- `backend/services/entitlement_agent/app/api/governance.py`
- `backend/services/entitlement_agent/app/api/access_requests.py`
- `backend/services/entitlement_agent/app/api/authorize.py`
- `backend/services/entitlement_agent/app/api/role_mappings.py`
- `backend/services/entitlement_agent/app/api/compliance.py`

Implemented outcome:

- entitlement CRUD, bulk, governance, access-request, authorization, role-mapping, and compliance routes now derive tenant scope from authenticated identity
- public query/body tenant selectors are now treated as same-tenant assertions instead of sources of authority
- `entitlement-agent` is out of the remaining owner queue

### IAM-Agent Status

`iam-agent` is now closed out of both the runtime backlog and the review-closure queue.

Completed in the latest slice:

- `backend/agents/iam_agent/app/api/entitlements.py`
- `backend/agents/iam_agent/app/api/bulk_operations.py`
- `backend/agents/iam_agent/app/api/authorize.py`
- `backend/agents/iam_agent/app/api/access_requests.py`
- `backend/agents/iam_agent/app/api/request_context.py`
- `backend/agents/iam_agent/app/api/iam_portal.py`
- `backend/agents/iam_agent/app/api/onboarding.py`
- `backend/agents/iam_agent/app/api/policies.py`
- `backend/agents/iam_agent/app/api/governance.py`
- `backend/agents/iam_agent/app/api/role_mappings.py`
- `backend/agents/iam_agent/app/api/app_catalog.py`
- `backend/agents/iam_agent/app/api/apps.py`
- `backend/agents/iam_agent/app/api/devices.py`
- `backend/agents/iam_agent/app/api/git_providers.py`
- `backend/agents/iam_agent/app/api/git_scanning.py`
- `backend/agents/iam_agent/app/api/hardened_images.py`
- `backend/agents/iam_agent/app/api/user_onboarding.py`
- `backend/agents/iam_agent/app/api/onboarding.py`
- `backend/agents/iam_agent/app/api/compliance.py`
- `backend/agents/iam_agent/app/api/audit.py`
- `backend/agents/iam_agent/app/api/automation.py`
- `backend/agents/iam_agent/app/api/ai_features.py`
- `backend/agents/iam_agent/app/api/mfa.py`
- `backend/agents/iam_agent/app/api/protocols.py`
- `backend/agents/iam_agent/app/api/ai_chat.py`
- `backend/agents/iam_agent/app/api/sync_jobs.py`
- `backend/agents/iam_agent/app/api/payment.py`
- `backend/agents/iam_agent/app/api/marketing.py`
- `backend/agents/iam_agent/app/api/leads.py`

Implemented outcome:

- added a request-context-backed tenant-scoped DB session helper for token-authenticated IAM routes
- moved the entitlement, bulk entitlement, authorization, and access-request families off plain sessions and onto tenant-scoped sessions
- removed the hidden plain-session audit logger dependency from access-request mutations by reusing the route-scoped tenant session
- moved the full IAM portal service dependency chain off plain sessions and onto tenant-scoped sessions
- moved the onboarding route family off the local plain DB dependency and onto tenant-scoped sessions derived from onboarding auth state
- replaced the onboarding family header/fallback tenant helper with authenticated request-context resolution
- moved the policy route family off the plain policy-service DB dependency and onto tenant-scoped sessions
- moved the remaining governance, role-mapping, catalog, inventory, device, git-integration, hardened-image, and user-onboarding families off plain sessions and onto tenant-scoped sessions
- moved the compliance status, gap, report, and evidence families from caller-controlled query/body tenant resolution to authenticated request-context resolution
- moved the audit log, review, analysis, statistics, and export families from caller-controlled tenant selectors to authenticated request-context resolution
- bound audit-review completion to the authenticated reviewer identity instead of a caller-controlled query reviewer ID
- moved the automation risk-response, revoke, remediation, predictive, and workflow trigger families from caller-controlled tenant selectors to authenticated request-context resolution
- made workflow execution status an authenticated internal boundary instead of an unauthenticated internal lookup
- moved the AI anomaly, risk, and recommendation families from caller-controlled query/body tenant selectors to authenticated request-context resolution
- moved the biometric enrollment, verification, lookup, deletion, and adaptive-auth families from caller-controlled query/body tenant selectors to authenticated request-context resolution
- moved the protocol configuration, connection test, integration creation, integration listing, integration sync, and integration test families from caller-controlled query/body tenant selectors to authenticated request-context resolution
- moved the AI chat, conversation management, and suggestion families from caller-controlled tenant selectors and unauthenticated internal boundaries to authenticated request-context resolution
- scoped in-memory conversation reads and deletes to the authenticated tenant boundary
- moved the sync-job creation, listing, execution, retry, scheduling, schedule mutation, and statistics families from caller-controlled tenant selectors and ambiguous internal boundaries to authenticated request-context resolution
- added tenant ownership checks to in-memory sync jobs and schedules and fixed a route-order shadowing bug where `/schedules` and `/statistics` were being captured by `/{job_id}`
- hardened the payment conversion flow with backend-issued provisioning tokens, lead-expiry validation, and stored checkout-session matching before account creation
- converted the three payment routes from generic pending public-record review to an explicit approved pre-tenant commercial boundary and Stripe-signed callback model
- moved the organization provisioning routes onto an explicit superadmin DB path while retaining authenticated `PLATFORM_ADMIN` enforcement
- converted the two `iam_orgs.py` routes from pending review to approved platform-admin provisioning boundaries
- replaced the placeholder realm provisioning authorization gate with authenticated `PLATFORM_ADMIN` request-context enforcement
- converted the two `realms.py` routes from pending review to approved platform-admin provisioning boundaries
- moved the external IdP OIDC and SAML diagnostic routes behind authenticated admin request-context enforcement
- converted the two `external_idp.py` diagnostic routes from pending public probe surfaces to authenticated tenant-admin/platform-admin boundaries
- moved the public OIDC state issuance route plus OIDC/SAML callback routes onto explicit server-side state binding with compatibility-query validation
- converted `/auth/oidc/state`, `/auth/oidc/callback`, and `/auth/saml/acs` from pending query-tenant review surfaces to approved public-auth boundaries
- moved the identity stats route onto an explicit internal orchestrator analytics boundary with service-token verification and tenant-scoped Keycloak counts
- moved the dashboard snapshot route from token-or-header tenant fallback to authenticated request-context tenant derivation
- moved the marketing funnel summary route onto an explicit internal analytics boundary requiring the internal service token
- converted the public lead lookup route into an approved pre-tenant lookup boundary gated by a backend-issued provisioning token and minimized commercial-state response payload
- reduced the `iam-agent` high-risk queue from `138` to `0`
- reduced the `iam-agent` review-required queue from `94` to `0`

### Metadata-Service Status

`metadata-service` is now effectively closed out of the runtime backlog.

Completed in the latest slice:

- `backend/services/metadata_service/app/api/assets.py`
- `backend/services/metadata_service/app/api/vulnerabilities.py`

Approach:

- added authenticated query-tenant validation
- moved the remaining query-tenant routes onto tenant-scoped DB access
- kept the existing incident and tenant route protections in place

### Detection-Service Status

`detection-service` is now effectively closed out of the runtime backlog.

Completed in the latest slice:

- `backend/services/detection_service/app/api/rules.py`

Approach:

- added service-local tenant-scoped DB helpers
- moved the rules family from plain sessions to authenticated tenant-scoped sessions
- enforced same-tenant validation on `/rules/enable`

### Connector-Service Status

`connector-service` is now effectively closed out of the runtime backlog.

Completed in the latest slice:

- `backend/services/connector_service/app/api/connectors.py`

Approach:

- moved connector CRUD, sync, and connection-test routes from plain sessions to `get_tenant_session`
- enforced same-tenant validation on `/connectors/oauth/init`
- left OAuth callback on its existing resolved-tenant callback path

### Email-Ingestion-Service Status

`email-ingestion-service` is now effectively closed out of the runtime backlog.

Completed in the latest slice:

- `backend/services/email_ingestion_service/app/api/phishing.py`
- `backend/services/email_ingestion_service/app/api/containment.py`

Approach:

- added a local query-tenant session helper in `backend/services/email_ingestion_service/app/core/database.py`
- moved all remaining phishing and containment routes from plain sessions to the query-tenant session helper
- kept the service on its existing query-tenant contract while making the DB session RLS-capable

### CMDB-Service Status

`cmdb-service` is now effectively closed out of the runtime backlog.

Completed in the latest slice:

- `backend/services/cmdb_service/app/api/assets.py`

Approach:

- added a local query-tenant session helper in `backend/services/cmdb_service/app/core/database.py`
- moved the full asset CRUD, search, vulnerability-link, and cloud-sync route family from plain sessions to the query-tenant session helper
- kept the service on its existing query-tenant contract while making the DB session RLS-capable

### Cert-Service Status

`cert-service` is now effectively closed out of the runtime backlog.

Completed in the latest slice:

- `backend/services/cert_service/app/api/certificates.py`

Approach:

- moved the remaining user-facing CA, certificate, and bootstrap-token routes from plain sessions to `get_tenant_session`
- kept service enrollment and agent enrollment on their existing resolved-tenant enrollment paths
- preserved bootstrap-token tenant scoping by continuing to source tenant identity from JWT context

### Ticketing-Service Status

`ticketing-service` is now effectively closed out of the runtime backlog.

Completed in the latest slice:

- `backend/services/ticketing_service/app/api/tickets.py`

Approach:

- added a local tenant-scoped DB helper in `backend/services/ticketing_service/app/core/database.py`
- moved the ticket create, get, update, comment, search, and tab routes from plain sessions to `get_tenant_session`
- kept tenant identity on the existing authenticated `X-Tenant-ID` contract while making the DB session RLS-capable

### Wazuh-Manager-Service Status

`wazuh-manager-service` is now effectively closed out of the runtime backlog.

Completed in the latest slice:

- `backend/services/wazuh_manager_service/app/api/agents.py`

Approach:

- added a local tenant-scoped DB helper in `backend/services/wazuh_manager_service/app/core/database.py`
- moved the agent service dependency from plain sessions to `get_tenant_session`
- kept tenant identity on the existing JWT-derived authorization path while making the DB session RLS-capable

### Vulnerability-Service Status

`vulnerability-service` is now effectively closed out of the runtime backlog.

Completed in the latest slice:

- `backend/services/vulnerability_service/app/api/vulnerabilities.py`

Approach:

- added authenticated query-tenant validation and tenant-scoped DB helpers in `backend/services/vulnerability_service/app/core/database.py`
- moved the vulnerability get, search, and sync routes from plain sessions to `get_query_tenant_session`
- enforced same-tenant validation for the existing query-tenant contract instead of leaving the tenant selector caller-controlled

### AI-Enrichment-Agent Status

`ai-enrichment-agent` is now effectively closed out of the runtime backlog.

Completed in the latest slice:

- `backend/services/ai_enrichment_agent/app/api/enrichment.py`

Approach:

- added authenticated query-tenant validation and tenant-scoped DB helpers in `backend/services/ai_enrichment_agent/app/core/database.py`
- moved the enrichment trigger and retrieval routes from plain sessions to `get_query_tenant_session`
- enforced same-tenant validation for the existing query-tenant contract instead of leaving the tenant selector caller-controlled

### Compliance-Service Status

`compliance-service` is now effectively closed out of the runtime backlog.

Completed in the latest slice:

- `backend/services/compliance_service/app/api/coverage.py`

Approach:

- moved the SOC 2 coverage and dashboard routes from plain sessions to `get_tenant_session`
- changed tenant resolution to derive from authenticated identity and only tolerate `X-Tenant-ID` or query `tenant_id` when they match the authenticated tenant
- preserved proxy compatibility while removing the caller-controlled tenant selector as an effective source of authority

### Phase P4 Audit Closure Still Open

Still required:

- expand the curated negative suite across the now-approved shared and authenticated control-plane boundaries
- run a real `full` audit in the audit environment
- archive the final passing binder for audit use

## Recommended Resume Order

### Best Mechanical Next Slice

There is no remaining mechanical runtime slice in the remediation-only backlog.

Reason:

- `critical_routes = 0`
- all active `high_risk` owner queues are now `0`
- the remaining work is audit-evidence closure, not additional route remediation

### Separate Policy Decision Track

There is no active policy-dependent owner queue left in the current runtime backlog.

### Review Track

There is no remaining remediation-only review track in the current baseline.

## Suggested Resume Checklist

When this work resumes:

1. Re-run the current smoke baseline:
   `scripts/audit/multi-tenancy/run-full-audit.sh --profile smoke --env local`
2. Confirm the new artifact still matches the current baseline expectations.
3. Start the parked audit-evidence phase.
4. Expand the curated negative suite across the approved shared and authenticated control-plane boundaries.
5. Run the real `full` audit profile in the audit environment and archive the final passing binder.
5. Re-run the smoke audit after each material review-closure tranche.
6. Update this document with the new baseline artifact and remaining queue counts.

## Definition Of Done For This Program

This program is not done when the audit pack passes a smoke run.

It is done when:

- `critical_routes = 0`
- `high_risk` queues are `0`
- `review_required` queues are explicitly resolved or approved
- the reporting shared-template access model is documented and enforced
- the `full` audit profile passes in the audit environment
- the final evidence binder is archived for audit reuse
