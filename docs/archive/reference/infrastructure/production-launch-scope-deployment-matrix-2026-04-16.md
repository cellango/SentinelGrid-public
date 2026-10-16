# SentinelGrid Launch Scope To Deployment Matrix

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 16, 2026  
**Status:** Phase 0 canonical deployment-truth matrix  
**Purpose:** Map the approved launch boundary to the services actually built, deployed, operated, and supported so engineering, product, GTM, and support are working from the same surface definition

## How To Use This Document

- If a marketed feature area is not mapped here, it is not launch-ready.
- If a mapped feature depends on a service that is not currently built and deployed in the launch workflow, the feature must be:
  - added to deploy scope,
  - gated in product,
  - or removed from launch claims.
- This matrix is the Phase 0 answer to: "What exactly ships?"

## Current Launch Workflow Baseline

The current launch deployment workflow in `.github/workflows/build-push-deploy.yml` builds and deploys:

- `frontend`
- `api_gateway`
- `iam_agent`
- `model_gateway`
- `orchestrator`
- `siem_agent`

Everything in the launch package must resolve to those deployment units or be explicitly qualified as an external dependency, a controlled add-on, or out of scope.

## Matrix

| Launch Area | Canonical Routes / Surface | Primary Backend / Runtime Dependencies | Current Launch Deploy Coverage | Primary Runbooks | Direct Support Owner | Current Phase 0 Decision |
| --- | --- | --- | --- | --- | --- | --- |
| Product shell, marketing, auth entry | `frontend/src/app/(marketing)/*`, `/login`, `/signup` | `frontend`, `iam_agent`, `api_gateway` | Covered | `docs/archive/operations/production-release-and-deploy.md`, `docs/archive/operations/production-support-and-incident-response.md` | Frontend Lead + IAM / Identity Lead | In launch scope |
| Operator landing, Now queue, dashboard shell | `/dashboard`, `/dashboard/now`, `/dashboard/welcome`, `/dashboard/war-room` | `frontend`, `api_gateway`, `orchestrator`, `siem_agent` | Covered | `docs/archive/operations/monitoring-and-alerting.md`, `docs/archive/operations/production-support-and-incident-response.md` | Product Lead + Platform / Backend Lead | In launch scope |
| Alerts, detections, log triage, SIEM views | `/dashboard/alerts`, `/dashboard/siem`, `/dashboard/log-management` | `frontend`, `api_gateway`, `siem_agent`, `orchestrator` | Covered | `docs/archive/operations/monitoring-and-alerting.md`, `docs/archive/operations/production-support-and-incident-response.md` | SIEM / Backend Lead | In launch scope |
| Incident workflow and guided response | `/dashboard/incidents`, `/dashboard/war-room`, `/dashboard/security-graph` | `frontend`, `api_gateway`, `orchestrator`, `siem_agent` | Covered, but still security-gated by orchestrator and SOAR trust fixes | `docs/archive/operations/production-support-and-incident-response.md`, `docs/archive/operations/monitoring-and-alerting.md` | Product Lead + Platform / Backend Lead | In launch scope after Phase 1 / 2 blocker closure |
| IAM, access hygiene, onboarding, identity | `/dashboard/iam`, `/dashboard/requests`, signup and onboarding surfaces | `frontend`, `api_gateway`, `iam_agent` | Covered | `docs/archive/operations/database-migrations-and-bootstrap.md`, `docs/archive/operations/production-support-and-incident-response.md` | IAM / Identity Lead | In launch scope |
| Cloud posture and scan surfaces | `/dashboard/posture`, `/dashboard/scans` | `frontend`, `api_gateway`, `orchestrator`, external scanner integrations | Partially covered; frontend and orchestration paths deploy, but external scanner/operator dependencies must stay qualified | `docs/archive/operations/production-release-and-deploy.md`, `docs/archive/operations/monitoring-and-alerting.md` | Platform / Backend Lead | In launch scope only for supported scanner paths with explicit qualification |
| Endpoint coverage and hardened image path | `/dashboard/endpoint-protection` | `frontend`, `api_gateway`, `iam_agent`, external SentinelGuard / Wazuh / packaging workflows | Partially covered; console path exists but endpoint delivery is not fully represented by the launch deploy workflow | `docs/archive/operations/production-release-and-deploy.md`, `docs/archive/operations/production-support-and-incident-response.md` | Product Lead + Platform / Backend Lead | In launch scope only as qualified coverage path, not full EDR parity |
| Baseline compliance and reporting | `/dashboard/compliance`, `/dashboard/reports` | `frontend`, `api_gateway`, reporting/compliance downstream services not present in launch deploy workflow | Not fully covered by current deploy workflow | `docs/archive/operations/production-support-and-incident-response.md`, `docs/archive/operations/backup-restore-and-dr.md` | Product Lead + Platform / Backend Lead | Must be narrowed to the subset provably backed by the deployed path or added to deploy scope |
| AI Shield controlled add-on | `/dashboard/ai-security`, `/dashboard/ai-governance`, standalone `SentinelGridAIShield/` | `SentinelGridAIShield/gateway`, `SentinelGridAIShield/services`, optional exports into platform workflows | Not covered in the current launch deploy workflow | Separate controlled-add-on runbook required before launch | AI Shield Lead | Controlled add-on only; not default launch scope |
| Partner / MSP operating model | partner and multi-tenant operator surfaces | `frontend`, `api_gateway`, `iam_agent`, `orchestrator`, support process and tenancy controls | Partially covered technically; support/process model still required | `docs/PARTNER_MSP_OPERATING_MODEL.md`, `docs/archive/operations/production-support-and-incident-response.md` | Product Lead + Support Lead | Qualified sales-assisted scope only |
| Pentest platform | `/dashboard/penetration-testing`, `SentinelGridPenTestAgent/` | dedicated pentest services and workflows | Not covered | none in launch runbooks | none for launch | Out of scope |
| Non-canonical legacy or subsystem surfaces | `website/`, `SentinelGridPostureAgent/frontend/` | separate apps and services | Not part of launch deploy workflow | none for launch | none for launch | Non-canonical / out of launch surface |

## Current Mismatches That Must Be Resolved

### 1. Compliance and reporting are still broader in product language than the current launch deployment path

Current implication:

- `frontend` can surface compliance and reporting experiences
- the launch workflow does not currently deploy a dedicated compliance or reporting service

Required Phase 0 decision:

- either add the required service deployments and runbooks
- or narrow the launch promise to evidence and reporting paths supported by the current operator workflow

### 2. Endpoint coverage is a valid launch story, but not a full self-contained deployed stack inside the current workflow

Current implication:

- the console can present endpoint coverage
- the actual delivery path depends on external packaging, deployment, and telemetry operations outside the six deployed launch services

Required Phase 0 decision:

- qualify endpoint as a guided coverage path, not full EDR parity

### 3. AI Shield cannot be treated as generally available in the default launch package

Current implication:

- the UI and docs can imply AI management breadth
- the current launch deployment workflow does not deploy AI Shield components

Required Phase 0 decision:

- keep AI Shield as a controlled add-on until it has its own hardened deployment, authz, and runbook set

### 4. Partner / MSP motion is real, but not default self-serve

Current implication:

- technical building blocks exist
- operational controls and support expectations still need qualification

Required Phase 0 decision:

- keep this as a qualified sales-assisted motion

## Required Follow-On Actions

1. Use this matrix to review every page in the launch demo and website.
2. Remove or gate any page whose backing service path is missing from the deploy workflow.
3. Review the runbook set and add missing launch-service ownership where there is still no support path.
4. Revisit this matrix after Phase 5 scope compression so the final Phase 7 re-audit can use it as the deployment truth set.

## Phase 0 Exit Condition Covered By This Doc

Phase 0 deployment-mapping work is complete when:

- every launch-safe feature has a deployed or explicitly qualified service path
- every unsupported feature is visibly gated or out of scope
- every launch feature has a runbook and support owner
