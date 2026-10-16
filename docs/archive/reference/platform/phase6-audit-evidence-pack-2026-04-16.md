# Phase 6 Audit Evidence Pack

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


> Historical note on April 16, 2026:
> This evidence pack remains useful as prior execution context, but it is not the current production decision baseline.
> The current repo-backed baseline is `docs/PRODUCTION_READINESS_AND_COMPETITIVE_AUDIT_2026-04-16.md`, and the active route to a fresh `Go` decision is `docs/PRODUCTION_GO_READINESS_IMPLEMENTATION_PLAN_2026-04-16.md`.

**Date:** April 16, 2026  
**Status:** Repo-local evidence assembled  
**Release recommendation:** `Go (tooling recommendation), pending named human signoff`  
**Purpose:** Collect the current-state architecture, control references, and fresh re-audit evidence required for Phase 6 release-candidate review.

## Executive Summary

The repo-local re-audit produced strong evidence in several areas:

- launch-scope auth routes, gateway controls, IAM transport controls, workflow coherence, and readiness tests are passing
- the multi-tenancy audit pack now passes in both smoke and full local live modes
- launch-boundary docs, trust materials, runbooks, and gated-feature inventory are all frozen

There are no remaining engineering blockers in the local live evidence set.

The remaining release action is named human signoff. The passed live evidence pack is:

- `artifacts/phase6/live-evidence/2026-04-16/161000-phase6-live-local/`

The remaining live steps are now packaged behind a single runner:

```bash
bash scripts/phase6/run-live-evidence-pack.sh --mode live
```

That runner emits `gate-review.json` and `gate-review.md` alongside the raw step artifacts so the final release discussion is based on a deterministic gate summary instead of manual interpretation.

## Fresh Audit Scope

This pack covers the audit scope defined in `docs/PRODUCTION_REMEDIATION_IMPLEMENTATION_PLAN.md`:

- authentication and session architecture
- tenant isolation
- secrets handling
- TLS and internal trust boundaries
- CORS and public API exposure
- queue / incident / graph coherence
- stub and mock removal from launch paths
- backup and recovery evidence
- deployment and rollback readiness

## Current-State Diagrams

### Auth And Session Flow

```text
Browser
  |
  v
Frontend login page
  |
  v
Next.js auth routes (/api/auth/login, /refresh, /logout)
  |
  v
IAM auth endpoints / Keycloak-backed token issuance
  |
  +--> Next.js sets HttpOnly access_token + refresh_token cookies
  |
  +--> Frontend rehydrates auth state through cookie-backed Next.js routes
         and keeps bearer state in memory only for legacy client callers
  |
  v
Middleware protects /dashboard using server-visible cookie or Authorization header
  |
  v
Frontend API calls reach /api and /api/v1 routes
  |
  +--> Same-origin cookies are the primary trust path
  +--> Legacy callers can attach Authorization: Bearer <memory-only token>
  |
  v
Backend auth helpers accept Authorization header or fallback access_token cookie
```

### Service-To-Service Trust Flow

```text
Frontend
  |
  +--> /api/* rewrite --> API Gateway
  |                       |
  |                       +--> Orchestrator (Bearer INTERNAL_SERVICE_TOKEN, TLS verify)
  |                       +--> IAM Agent (Bearer INTERNAL_SERVICE_TOKEN, TLS verify)
  |                       +--> SIEM Agent / SOAR / Ticketing / Model Gateway (internal token, TLS verify)
  |
  +--> /api/v1/* rewrite --> IAM Agent or other internal service

IAM Agent
  |
  +--> Keycloak admin/service-account access
  |      - KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT
  |      - KEYCLOAK_ADMIN_CLIENT_SECRET
  |      - KEYCLOAK_VERIFY_TLS
  |
  +--> Vault
         - VAULT_VERIFY_TLS

Orchestrator / SIEM / Ingestion / Model Gateway
  |
  +--> Internal downstream calls
         - INTERNAL_SERVICE_TOKEN
         - UPSTREAM_TLS_VERIFY
```

## Evidence Map

| Required Item | Source | Status |
| --- | --- | --- |
| architecture current-state diagram | `docs/archive/reference/platform/production-operations-topology-2026-04-15.md` | Complete |
| auth and session flow diagram | this document | Complete |
| service-to-service auth diagram | this document | Complete |
| secrets inventory | this document, `docs/archive/reference/infrastructure/vault-production-setup.md`, `docs/archive/operations/production-release-and-deploy.md` | Repo-local complete; environment-specific values still required for final diligence |
| CORS and ingress allowlist configs | `backend/libs/sg_core/service_security.py`, `backend/services/api_gateway/app/core/config.py`, `backend/agents/iam_agent/app/core/config.py`, `docs/archive/operations/production-release-and-deploy.md` | Complete |
| TLS verification closure report | `backend/services/api_gateway/tests/test_config_security.py`, `backend/services/api_gateway/tests/test_tls_verification_regression.py`, `backend/agents/iam_agent/tests/test_config_security.py`, `backend/agents/iam_agent/tests/test_route_transport_security.py`, `backend/agents/iam_agent/tests/test_service_client_security.py` | Complete |
| tenant-isolation test report | `artifacts/audit/multi-tenancy/2026-04-16/141839-local-smoke/`, `artifacts/audit/multi-tenancy/2026-04-16/105900-local-full-live-fixed/`, `docs/archive/operations/multi-tenancy-audit-execution.md` | Complete for the local compose-backed proof path; deploy-target rerun still recommended before final approval |
| launch-scope feature matrix | `docs/archive/reference/platform/production-launch-scope-decision-2026-04-15.md`, `docs/archive/reference/platform/phase5-gated-feature-inventory-2026-04-16.md` | Complete |
| list of gated / beta / non-launch features | `docs/archive/reference/platform/phase5-gated-feature-inventory-2026-04-16.md` | Complete |
| backup and restore test report | `docs/archive/operations/backup-restore-and-dr.md`, `infra/shared/scripts/backup-postgres.sh`, `infra/shared/scripts/backup-keycloak.sh`, `infra/shared/scripts/restore-system.sh`, `artifacts/drills/restore/2026-04-16/155237-postgres-live/`, `artifacts/drills/restore/2026-04-16/155928-keycloak-live/` | Complete for the local restore path; deploy-target rollback is still pending |
| runbooks and on-call docs | `docs/archive/operations/README.md`, `docs/archive/operations/production-support-and-incident-response.md`, `docs/archive/operations/monitoring-and-alerting.md`, `docs/archive/operations/production-release-and-deploy.md` | Complete |
| release checklist and rollback checklist | `docs/archive/operations/production-release-and-deploy.md`, `docs/archive/operations/database-migrations-and-bootstrap.md`, `docs/archive/reference/platform/phase6-release-candidate-signoff-2026-04-16.md` | Complete |

## Secrets, CORS, And TLS Control Summary

### Secrets inventory classes

The repo shows four launch-relevant secret classes:

1. deployment and cloud secrets
   - GitHub environment secrets such as `AWS_ECR_DEPLOY_ROLE_ARN`
2. internal service authentication secrets
   - `INTERNAL_SERVICE_TOKEN` per service
3. identity and secret-management credentials
   - `KEYCLOAK_ADMIN_CLIENT_SECRET`
   - `KEYCLOAK_CLIENT_SECRET`
   - `VAULT_TOKEN`
4. customer or connector material stored through onboarding
   - connector secrets written via Vault-backed onboarding flows

This pack intentionally records the inventory classes and source files, not the live secret values.

### CORS and ingress posture

- launch services use explicit `CORS_ORIGINS` allowlists in production
- `backend/libs/sg_core/service_security.py` rejects wildcard or empty allowlists in production
- gateway and IAM config validators separately fail closed in production if `CORS_ORIGINS` is wildcarded
- release and deploy runbooks freeze the public hosts and ingress expectations

### TLS and internal trust posture

- API Gateway production config requires `UPSTREAM_TLS_VERIFY=true`
- IAM production config requires:
  - `KEYCLOAK_VERIFY_TLS=true`
  - `VAULT_VERIFY_TLS=true`
  - `UPSTREAM_TLS_VERIFY=true`
- service-account-backed Keycloak admin access is supported and tested in IAM

## Repo-Local Re-Audit Execution

The following commands were executed on April 16, 2026:

1. `scripts/audit/multi-tenancy/run-full-audit.sh --profile smoke --env local --keep-going`
   Result: passed
   Artifact root: `artifacts/audit/multi-tenancy/2026-04-16/141839-local-smoke/`
2. `npm test -- --runInBand --watch=false 'src/app/api/auth/login/__tests__/route.test.ts' 'src/app/api/auth/refresh/__tests__/route.test.ts' 'src/app/api/auth/logout/__tests__/route.test.ts' 'src/middleware.test.ts'`
   Result: `11 passed`
3. `pytest backend/agents/iam_agent/tests/test_auth_api.py -q`
   Result: `9 passed`
4. `npm test -- --runInBand --watch=false 'src/app/api/auth/login/__tests__/route.test.ts' 'src/app/api/auth/refresh/__tests__/route.test.ts' 'src/app/api/auth/logout/__tests__/route.test.ts' 'src/app/api/auth/me/__tests__/route.test.ts'`
   Result: `10 passed`
5. `npm test -- --runInBand --watch=false --runTestsByPath 'src/app/(dashboard)/__tests__/layout.test.tsx'`
   Result: `3 passed`
6. `npx next lint --file 'src/lib/api/auth.ts' --file 'src/lib/providers/AuthProvider.tsx' --file 'src/lib/api/client.ts' --file 'src/lib/api/onboarding.ts' --file 'src/lib/api/marketing.ts' --file 'src/lib/api/payment.ts' --file 'src/lib/api/iam-portal.ts' --file 'src/lib/api/git-providers.ts' --file 'src/lib/api/git-scanning.ts' --file 'src/lib/api/hardened-images.ts' --file 'src/app/(marketing)/auth/callback/page.tsx' --file 'src/app/(dashboard)/layout.tsx' --file 'src/components/compliance/pages/ComplianceReportSchedulesPage.tsx'`
   Result: passed
7. `npx next lint --file 'src/app/api/auth/me/route.ts' --file 'src/app/api/auth/exchange-code/route.ts' --file 'src/app/api/v1/devices/[[...path]]/route.ts' --file 'src/app/api/v1/roles/[[...path]]/route.ts' --file 'src/lib/auth/session.ts'`
   Result: passed
8. `pytest backend/services/api_gateway/tests/test_auth_middleware.py backend/services/api_gateway/tests/test_config_security.py backend/services/api_gateway/tests/test_tls_verification_regression.py backend/services/api_gateway/tests/test_readiness.py -q`
   Result: `18 passed`
9. `pytest backend/agents/iam_agent/tests/test_config_security.py backend/agents/iam_agent/tests/test_service_client_security.py backend/agents/iam_agent/tests/test_route_transport_security.py backend/agents/iam_agent/tests/test_admin_auth_runtime.py -q`
   Result: `23 passed`
10. `pytest backend/services/api_gateway/tests/test_playbooks_routes_tenant_session.py backend/services/api_gateway/tests/test_playbook_executions_routes_tenant_session.py -q`
   Result: `10 passed`
11. `PYTHONPATH=backend/agents/soar_agent:backend/libs pytest backend/agents/soar_agent/tests/test_playbook_routes_tenant_session.py backend/agents/soar_agent/tests/test_playbook_execution_service_refresh.py -q`
   Result: `15 passed`
12. `PYTHONPATH=.:../../libs pytest tests/test_readiness.py -q` from `backend/services/orchestrator`
   Result: `3 passed`
13. `PYTHONPATH=../../libs:. pytest tests/test_readiness.py tests/test_main_metrics.py -q` from `backend/services/ingestion_service`
   Result: `5 passed`
14. `pytest tests/test_readiness.py -q` from `backend/services/model_gateway`
   Result: `3 passed`
15. `PYTHONPATH=.:../../libs pytest tests/test_readiness.py tests/test_request_tracing.py -q` from `backend/agents/siem_agent`
    Result: `6 passed`
16. `PYTHONPATH=.:../../libs pytest tests/test_main_readiness.py -q` from `backend/agents/iam_agent`
    Result: `3 passed`
17. `bash -n infra/shared/scripts/backup-postgres.sh infra/shared/scripts/backup-keycloak.sh infra/shared/scripts/restore-system.sh`
    Result: passed
18. `docker compose -f docker-compose.minimal.yml up -d postgres`
    Result: passed
19. `POSTGRES_URL=postgresql://sg:sg@localhost:5432/sg POSTGRES_ADMIN_URL=postgresql://sg:sg@localhost:5432/sg AUDIT_PROVISION_RLS_VERIFIER=true AUDIT_RLS_VERIFIER_ROLE=sg_audit_verifier AUDIT_RLS_VERIFIER_PASSWORD=sg_audit_verifier bash scripts/audit/multi-tenancy/run-full-audit.sh --profile full --env local --run-id 105900-local-full-live-fixed --keep-going`
    Result: passed
    Artifact root: `artifacts/audit/multi-tenancy/2026-04-16/105900-local-full-live-fixed/`
20. `BACKUP_DIR=/path/to/SentinelGrid/artifacts/drills/backups/phase6-local POSTGRES_HOST=localhost POSTGRES_PORT=5432 POSTGRES_USER=sg POSTGRES_PASSWORD=sg POSTGRES_DB=sg bash infra/shared/scripts/backup-postgres.sh`
    Result: passed
21. `POSTGRES_HOST=localhost POSTGRES_PORT=5432 POSTGRES_USER=sg POSTGRES_PASSWORD=sg POSTGRES_DB=sg bash infra/shared/scripts/run-restore-drill.sh --component postgres --backup-file /path/to/SentinelGrid/artifacts/drills/backups/phase6-local/sentinelgrid_db_20260416_105215.sql.gz --mode live`
    Result: passed
    Artifact root: `artifacts/drills/restore/2026-04-16/155237-postgres-live/`
22. `docker compose -f docker-compose.minimal.yml up -d keycloak_db keycloak`
    Result: passed
23. `BACKUP_DIR=/path/to/SentinelGrid/artifacts/drills/backups/phase6-local-keycloak KEYCLOAK_URL=http://localhost:8080 KEYCLOAK_ADMIN_REALM=master KEYCLOAK_ADMIN_USER=admin KEYCLOAK_ADMIN_PASSWORD=admin KEYCLOAK_ADMIN_CLIENT_ID=admin-cli bash infra/shared/scripts/backup-keycloak.sh`
    Result: passed
24. `KEYCLOAK_URL=http://localhost:8080 KEYCLOAK_ADMIN_REALM=master KEYCLOAK_ADMIN_USER=admin KEYCLOAK_ADMIN_PASSWORD=admin KEYCLOAK_ADMIN_CLIENT_ID=admin-cli bash infra/shared/scripts/run-restore-drill.sh --component keycloak --backup-file /path/to/SentinelGrid/artifacts/drills/backups/phase6-local-keycloak/keycloak_20260416_105709.tar.gz --mode live`
    Result: passed
    Artifact root: `artifacts/drills/restore/2026-04-16/155928-keycloak-live/`
25. `kind create cluster --name phase6-local`
    Result: passed
26. `helm install phase6-rollback-smoke charts/common-service -n sg-core -f charts/values/phase6-rollback-smoke.yaml`
    Result: passed
27. `helm upgrade phase6-rollback-smoke charts/common-service -n sg-core -f charts/values/phase6-rollback-smoke.yaml --set image.tag=1.27.5`
    Result: passed
28. `bash infra/shared/scripts/run-release-rollback-drill.sh --release phase6-rollback-smoke --revision 1 --namespace sg-core --mode live`
    Result: passed
    Artifact root: `artifacts/drills/rollback/2026-04-16/161002-phase6-rollback-smoke-rollback-live/`
29. `POSTGRES_URL=postgresql://sg:sg@localhost:5432/sg POSTGRES_ADMIN_URL=postgresql://sg:sg@localhost:5432/sg AUDIT_PROVISION_RLS_VERIFIER=true AUDIT_RLS_VERIFIER_ROLE=sg_audit_verifier AUDIT_RLS_VERIFIER_PASSWORD=sg_audit_verifier POSTGRES_HOST=localhost POSTGRES_PORT=5432 POSTGRES_USER=sg POSTGRES_PASSWORD=sg POSTGRES_DB=sg KEYCLOAK_URL=http://localhost:8080 KEYCLOAK_ADMIN_REALM=master KEYCLOAK_ADMIN_USER=admin KEYCLOAK_ADMIN_PASSWORD=admin KEYCLOAK_ADMIN_CLIENT_ID=admin-cli BACKUP_DIR=/tmp/phase6-live-backups bash scripts/phase6/run-live-evidence-pack.sh --mode live --rollback-release phase6-rollback-smoke --rollback-revision 1 --rollback-namespace sg-core --run-id 161000-phase6-live-local`
    Result: passed
    Artifact root: `artifacts/phase6/live-evidence/2026-04-16/161000-phase6-live-local/`

## Final Evidence Outcome

The final Phase 6 live evidence pack reports:

- `overall_status: passed`
- `recommended_decision: go`
- `ready_for_signoff: true`
- `blocking_items: []`

The decisive artifact is:

- `artifacts/phase6/live-evidence/2026-04-16/161000-phase6-live-local/gate-review.md`

## Phase 6 Live-Execution Support Tooling

The repo now includes the following Phase 6 closeout helpers:

- `scripts/phase6/run-live-evidence-pack.sh`
- `scripts/phase6/evaluate-live-evidence.py`
- `scripts/audit/multi-tenancy/prepare-live-rls-inputs.sh`
- `scripts/audit/multi-tenancy/discover-live-tenant-pair.py`
- `infra/shared/scripts/run-restore-drill.sh`
- `infra/shared/scripts/run-release-rollback-drill.sh`

The current plan-mode rehearsal artifact is:

- `artifacts/phase6/live-evidence/2026-04-16/154500-phase6-plan-gatereview/`

The current local live data-plane evidence artifacts are:

- `artifacts/audit/multi-tenancy/2026-04-16/105900-local-full-live-fixed/`
- `artifacts/drills/restore/2026-04-16/155237-postgres-live/`
- `artifacts/drills/restore/2026-04-16/155928-keycloak-live/`
- `artifacts/drills/rollback/2026-04-16/161002-phase6-rollback-smoke-rollback-live/`
- `artifacts/phase6/live-evidence/2026-04-16/161000-phase6-live-local/`

Those artifacts close the local Phase 6 engineering scope and leave only named human signoff outstanding.

## Positive Findings

- gateway and IAM production config guards are working
- transport-TLS regression tests are passing
- multi-tenancy smoke audit artifact pack is producing clean results
- full local multi-tenancy audit pack now passes against a compose-backed Postgres target
- live row-level-security proof now passes with a non-bypass verifier role and real tenant-pair evidence
- playbook execution and approval-state tests are passing
- launch-scope readiness tests are passing across the core services
- launch auth no longer persists bearer tokens in browser storage on the launch path
- local PostgreSQL backup and restore drill now passes with evidence
- local Keycloak backup and restore drill now passes with evidence
- local Helm rollback drill now passes on a Docker-backed kind cluster using the repo rollback script
- the full live Phase 6 evidence pack now passes end to end
- launch scope, trust pack, gated-feature inventory, and support runbooks are frozen and internally consistent

## Recommendation

Use this pack as the Phase 6 audit base and proceed to named approver review.

The final evidence pack is:

```bash
artifacts/phase6/live-evidence/2026-04-16/161000-phase6-live-local/gate-review.md
```

The next mandatory action is:

1. record named human signoff
