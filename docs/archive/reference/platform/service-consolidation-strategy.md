# SentinelGrid Service Consolidation Strategy

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Objectives
- Cut the service footprint from ~60 compose entries to ~10 logical services without breaking tenant isolation, auth, or data integrity.
- Reduce operational drag (build times, deployments, observability noise) while keeping clear domain boundaries.
- Standardize API surfaces and background job orchestration (scanners, playbooks) so horizontal scaling is per-domain, not per-tool.

## Current State (high level)
- Control plane/UI: `frontend`, `api_gateway`, `model_gateway`, `SentinelGridAIShield` gateway/services.
- Identity & tenancy: `iam_agent`, `entitlement_agent`, `tenant_service`, `cert_service` + Keycloak.
- Telemetry/detection: `siem_agent`, `ingestion_service`, `observables_service`, `detection_service`, `wazuh_manager_service` (to be removed), `framework_service`.
- Response/workflows: `orchestrator`, `soar_agent`, `action_service`, `automated_response_service`, `ticketing_service`, `incident_service`, `reporting_service`.
- Asset/GRC: `cmdb_service`, `connector_service`, `vulnerability_service`, `compliance_service`.
- Scanners: job runner/scheduler (`backend/scripts/job_runner.py`, `backend/libs/sg_core/jobs/*`) calling containerized scanners + sidecars.
- Infra deps: Postgres, OpenSearch, Redis, Keycloak, StackStorm, Cortex, n8n, vLLM, Vault, Wazuh.

## Target Footprint (~10 logical services)
1) **Web/API**: frontend + API gateway + model gateway (optionally AIShield gateway) behind one ingress; feature-flag modules.
2) **Identity/Tenant**: IAM + entitlement + tenant + cert issuance in one service, backed by Keycloak.
3) **Telemetry/Detection**: ingestion, SIEM views, observables, detection rules/exec, Wazuh manager adapter, detection content service.
4) **Response/Playbooks**: orchestrator + SOAR + actions + automated response; n8n/StackStorm remain integrations.
5) **GRC/Asset**: CMDB + connectors + vulnerability + compliance + frameworks + reporting/ticket/incident APIs.
6) **Scanner Orchestrator**: single service exposing `/scan/*` endpoints and managing jobs; executes scanners via short-lived containers.
7) **AIShield Core**: existing AI security gateway/services (can be folded into Web/API later if needed).
8) **Job Runtime**: background job runner/scheduler (could merge into Scanner Orchestrator or Response depending on load).
9) **Observability**: shared metrics/logging/tracing sidecars (Grafana/Prom tail/OTel collector as needed).
10) **Stateful Stores**: Postgres, OpenSearch, Redis, Vault, Keycloak DB (as managed dependencies, not app services).
11) **Optional agent-only extras**: Wazuh **agent sidecars only**; no Wazuh server/manager in the stack. Endpoint telemetry is ingested via the sidecar and normalized in Telemetry/Detection.

## Design Principles
- Preserve domain boundaries; merge deployment units, not schemas, unless domains converge (e.g., IAM + entitlement).
- One API surface per domain with clear versioning; keep internal calls behind an internal gateway or service mesh.
- Background work via queues; no long-lived scanner processes—each scan runs in an isolated container/namespace.
- Keep security isolation: per-tenant authz enforced at API, DB row level, and job dispatch; do not share temp volumes between tenants.
- Strangler pattern for UI: keep routes stable; gate new consolidated endpoints behind feature flags and dual-write when needed.
- Observability first: standard request IDs, trace propagation, SLOs per domain (latency, error rate, queue depth, job success).

## Scanner Consolidation (key decision)
- **Approach**: A single Scanner API/service owns scheduling, dispatch, parsing, and persistence; actual tools (Prowler, Trivy, Gitleaks, Checkov, ZAP, Semgrep, etc.) run in ephemeral containers per job with resource caps.
- **Pros**: One deployable surface, consistent auth/ratelimiting, shared parsing code (`backend/libs/sg_core/jobs`), simpler scheduling API, reuse of fixtures/tests.
- **Cons**: Larger coordinator image; if misconfigured, scan jobs can contend for CPU/IO; requires isolation discipline to avoid cross-tenant leakage.
- **Mitigations**: Per-job namespaces, read-only mounts, tmpfs for outputs, resource requests/limits, timeouts, hardened base image, and allow specific scanners to scale via worker pools if needed.

## Tenant-aware scanner persistence
- **Tables (all indexed by tenant_id)**: `scans` (one per run; status, timings, error, summary JSONB, raw_artifact_url), `findings` (normalized columns + `raw_payload`/`evidence` JSONB + `fingerprint`), `assets` (existing), `scanner_registry` (global catalog of tools/versions).
- **Registry-driven growth**: Add/remove scanners by inserting/updating `scanner_registry` rows (name, version, image digest, parser id, default limits, metadata JSONB). No per-scanner tables.
- **Parser contract**: Parsers must emit tenant_id from job context, map to an `asset_id` (tenant-scoped lookup), set normalized fields (severity/category/title/description/detected_at), attach `raw_payload`/`evidence` JSONB, and compute `fingerprint = hash(scanner_id, tenant_id, asset_id/target, rule_id, location)` for dedup/upserts.
- **Artifacts**: Store full raw outputs in tenant-scoped object storage paths (e.g., `…/tenant/{tenant_id}/scans/{scan_id}.json`); DB only keeps URLs. Avoids bloating Postgres and keeps schema static.
- **Isolation**: Queue partitions by tenant_id; each job’s container receives only that tenant’s creds/config and uses unique temp paths/volumes; no sharing between tenants. RLS can be enabled as defense-in-depth.
- **Indexes**: B-tree on tenant_id + asset_id + scanner_id + scan_id + severity + detected_at; GIN on tags if needed. Only add JSONB path indexes when proven by queries.

## Scanner lifecycle (ephemeral)
- Job enqueued -> `scans` row created (`pending`).
- Worker launches a container for the selected scanner version (from registry) with per-job limits; container writes JSON to stdout or a temp file, then exits.
- Worker uploads raw output to tenant-scoped storage, invokes parser, upserts findings using `fingerprint`, links to assets, and updates `scans` (`completed/failed`) with summary stats.
- Timeouts/retries with backoff; failed jobs do not keep containers alive.

## Migration Phases
1) **Inventory & cut map** (week 1): finalize bundle list above; document owners; freeze new services unless approved.
2) **APIs & data contracts** (weeks 1–2): lock target APIs per bundle; define DB/schema ownership; add compatibility shims in `api_gateway`.
3) **Wave 1 merges** (weeks 2–3):
   - Identity/Tenant bundle (IAM + entitlement + tenant + cert) with shared migrations.
   - Scanner Orchestrator service created; `job_runner`/`job_scheduler` point to it; remove dedicated scanner services/sidecars from compose except ephemeral images.
4) **Wave 2 merges** (weeks 3–4):
   - Telemetry/Detection bundle.
   - Response/Playbooks bundle (orchestrator + SOAR + actions + auto-response).
5) **Wave 3 merges** (weeks 4–5):
   - GRC/Asset bundle (CMDB + connectors + vuln + compliance + frameworks + reporting/tickets/incidents).
   - Optional: fold AIShield gateway into Web/API if stable.
6) **Decommission & harden** (weeks 5–6): remove deprecated compose entries, update CI/CD, set resource policies, formalize SLOs and dashboards.

## Rollout & Safety
- Feature flags + routing rules at gateway; allow shadow traffic to new services before cutover.
- Dual-write during migrations where schemas merge; include backfill scripts and idempotent migrations.
- Backward compatibility windows (at least one release) for internal API consumers.
- Blue/green or canary per bundle; automated smoke tests per route and per queue type.

## Risks & Mitigations
- **Blast radius from large bundles**: enforce module boundaries in code, enforce circuit breakers, and set per-module error budgets.
- **Schema collisions**: allocate schemas per bundle in Postgres; avoid cross-bundle foreign keys; use service-level APIs for joins.
- **Scanner resource contention**: per-job limits and queue partitioning by scanner type/tenant priority.
- **Operational complexity during transition**: maintain a living cut map and owner matrix; weekly reviews to retire legacy endpoints.
- **Endpoint telemetry**: use Wazuh agent sidecars only; do not introduce/retain Wazuh server/manager. Normalize agent output in Telemetry/Detection.

## Immediate Actions
- Ratify target bundle list and owners.
- Stand up Scanner Orchestrator service definition (reuse `backend/libs/sg_core/jobs` handlers/executors) and remove long-running scanner containers from compose (keep images for jobs).
- Draft API contracts for Identity/Tenant and Telemetry/Detection bundles and add them to `api_gateway`.
- Add observability standards (logging, tracing, metrics) as acceptance criteria for each merged bundle.
- Remove Wazuh manager/server from compose; keep only Wazuh agent sidecars feeding Telemetry/Detection.

## Step-by-step kickoff (first two weeks)
1) **Freeze and inventory (Day 1)**  
   - Freeze new services. Export current service list (`docker-compose.*.yml`) and tag owners. Identify all infra dependencies (Keycloak, Vault, Postgres, OpenSearch, Redis, EJBCA/Step CA, Wazuh agent usage).
2) **Target bundle map (Day 1–2)**  
   - Confirm the 10-bundle target (Web/API, Identity/Tenant, Telemetry/Detection, Response/Playbooks, GRC/Asset, Scanner Orchestrator, AIShield, Job runtime, Observability, Stateful stores; Wazuh agents only). Document owner per bundle.
3) **Define contracts (Day 2–4)**  
   - Draft API contracts for Identity/Tenant and Telemetry/Detection in `api_gateway` (request/response, auth, rate limits).  
   - Draft Scanner Orchestrator API: `/scan/cloud`, `/scan/git`, `/scan/app`, `/scan/status`, `/scans/{id}`. Include authz and tenant scoping rules.
4) **Schema and registry plan (Day 3–5)**  
   - Lock the tenant-aware schema for `scans`, `findings`, `scanner_registry`, `scan_stats` (as in this doc).  
   - Define scanner registry format (name, version, image digest, parser id, default limits, metadata JSONB).
5) **Compose pruning plan (Day 4–5)**  
   - Mark services to remove in dev compose: Wazuh manager, duplicate scanners running as services, unused extras. Keep EJBCA/Step CA, Vault, Keycloak as separate containers. Plan the delta to reach the 10-bundle footprint.
6) **Build Scanner Orchestrator skeleton (Day 5–7)**  
   - Fork existing `sg_core/jobs` handlers/executors into a new service entry; add registry lookup, per-job container launch, artifact upload, parser invocation, and `scans` bookkeeping.  
   - Wire job_runner/scheduler to call the new orchestrator API instead of direct handlers.
7) **Telemetry/Detection consolidation plan (Day 7–9)**  
   - Outline how `siem_agent`, `ingestion_service`, `observables_service`, `detection_service`, `framework_service` converge into one service. Keep interface compatibility via gateway shims.
8) **Identity/Tenant consolidation plan (Day 7–9)**  
   - Plan merge of `iam_agent`, `entitlement_agent`, `tenant_service`, `cert_service` (with EJBCA/Step CA separate). Define migrations and config/secret alignment with Keycloak.
9) **Observability baseline (Day 9–10)**  
   - Establish request ID/trace propagation, metrics (p95 latency, error rate, queue depth), and dashboards per bundle. Add SLOs as acceptance criteria.
10) **Approval and execution gates (Day 10–14)**  
   - Review cut map, contracts, schema plan, and orchestrator skeleton. Approve compose pruning and begin Wave 1 merges (Identity/Tenant + Scanner Orchestrator).

## Step 1: Freeze and inventory (completed)
- **Freeze**: pause addition of new services until consolidation waves start.
- **Service inventory snapshot (Dec 2025)**:
  - `docker-compose.dev.yml` (61 entries): runtime base images; frontend; api_gateway; orchestrator; model_gateway; opensearch + dashboards; siem_agent; soar_agent; iam_agent; entitlement_agent; tenant_service; ingestion_service; connector_service; detection_service; automated_response_service; compliance_service; analyzer-orchestrator; ticketing_service; action_service; reporting_service; vulnerability_service; cmdb_service; framework_service; incident_service; email_ingestion_service; observables_service; mcp_server; job_runner; job_scheduler; gitleaks_sidecar; scanner images (cloud/gitleaks/checkov/zap/semgrep/ai_summary/golden_image_builder); postgres; model_gateway migrations; keycloak_db; keycloak; redis; vault-prod; flyway runners; stackstorm; cortex; n8n; llm_server; cert_service; ejbca + ejbca_db; step-ca; sentinelgrid_ai_shield_gateway; ai_shield_services; wazuh-manager (to be removed); wazuh_manager_service (to be removed).
  - `docker-compose.minimal.yml` (18 entries): frontend; api_gateway; orchestrator; model_gateway; llm_server_mock; opensearch; siem_agent; soar_agent; iam_agent; tenant_service; postgres; keycloak_db; keycloak; redis; cert_service; step-ca; model_gateway_migrations; soar_agent_flyway.
  - `docker-compose.test.yml` (4 entries): postgres-test; redis-test; keycloak-test; postgres-iam-test.
  - `docker-compose.dev.yml` (vault service).
- **Infra separation**: open-source infra components to remain standalone: Keycloak (+ keycloak_db), Vault, OpenSearch, Redis, EJBCA/Step CA (choose one), Postgres, and Wazuh agents only (drop wazuh manager/server).

## Step 2: Target bundle map (ready for owner assignment)
- **Web/API**: `frontend`, `api_gateway`, `model_gateway`; optionally `sentinelgrid_ai_shield_gateway` if we keep it separate from the main gateway.
- **Identity/Tenant**: `iam_agent`, `entitlement_agent`, `tenant_service`, `cert_service` (app-side). Backed by standalone `keycloak` + `keycloak_db`, and CA backend (`ejbca` + `ejbca_db` OR `step-ca`).
- **Telemetry/Detection**: `siem_agent`, `ingestion_service`, `observables_service`, `detection_service`, `framework_service`, `analyzer-orchestrator` (posture agent). Remove `wazuh-manager`/`wazuh_manager_service`; rely on Wazuh agents as sidecars feeding this bundle.
- **Response/Playbooks**: `orchestrator`, `soar_agent`, `action_service`, `automated_response_service`, `ticketing_service`, `incident_service`, `reporting_service`; integrations `n8n`, `stackstorm`.
- **GRC/Asset**: `cmdb_service`, `connector_service`, `vulnerability_service`, `compliance_service`; (shares frameworks data via API, not DB joins).
- **Scanner Orchestrator**: new service to front `/scan/*`; uses `job_runner`/`job_scheduler` as workers; replace dedicated scanner containers with ephemeral runs (keep scanner images pulled as needed). Deprecate `gitleaks_sidecar` as a long-lived service.
- **AIShield Core**: `ai_shield_services` (and optionally `sentinelgrid_ai_shield_gateway` if not folded into Web/API).
- **Job Runtime**: `job_runner`, `job_scheduler` (can merge into Scanner Orchestrator or Response later).
- **Observability**: add shared collector/metrics/logging sidecar (not yet in compose; to be added).
- **Stateful Stores**: `postgres`, `opensearch`, `redis`, `vault-prod`, `keycloak_db`, `ejbca_db` (or `step-ca` internal storage), migration runners (`migrations_flyway`, `model_gateway_migrations`, `model_gateway_data_migrations`, `soar_agent_flyway`).

## Step 3: Define contracts (in progress)
- **Identity/Tenant API (via api_gateway)**: authn via Keycloak, authz by tenant. Endpoints to standardize:
  - `/identity/users`, `/identity/groups`, `/identity/roles`, `/identity/policies` (CRUD with search/pagination).
  - `/tenants` (create/update/list), `/tenants/{id}/settings`, `/tenants/{id}/certs` (issue/revoke certs via cert_service).
  - `/auth/token/introspect`, `/auth/token/impersonate` (admin-only).
  - Common: rate limits per tenant; consistent error model; audit IDs for every call.
- **Telemetry/Detection API**:
  - Ingest: `/telemetry/logs` (batch), `/telemetry/events`, `/telemetry/observables/enrich`.
  - Detection: `/detection/rules`, `/detection/rules/{id}/test`, `/detection/findings`, `/detection/health`.
  - SIEM views: `/siem/search`, `/siem/aggregations`.
  - All scoped by tenant; align with existing `siem_agent`/`ingestion_service` contracts but collapse into one surface.
- **Scanner Orchestrator API**:
  - `/scan/cloud`, `/scan/git`, `/scan/app` (POST enqueue) with tenant scoping from auth; request includes target refs and scanner set/versions (optional override).
  - `/scans` (list), `/scans/{id}` (status, summary, links), `/scans/{id}/findings` (paged), `/scans/{id}/raw` (signed URL to artifact).
  - Authz: tenant-based, with optional admin cross-tenant path; rate limits per tenant; idempotency keys for enqueue.
- **Common contract rules**:
  - Enforce tenant_id from auth, not caller input; gateway injects tenant context headers for downstream.
  - Standard error envelope and pagination.
  - Trace propagation headers required; request IDs logged.
  - Rate limits per tenant and per endpoint class.

## Step 4: Schema and scanner registry plan (ready)
- **Tenant-aware core tables**:
  - `scanner_registry`: `id`, `name`, `version`, `image_digest`, `parser`, `default_limits` (JSONB), `metadata` (JSONB), `active`.
  - `scans`: `id`, `tenant_id`, `scanner_id`, `target_ref`, `status`, `started_at`, `finished_at`, `error`, `raw_artifact_url`, `summary` (JSONB). **Status:** migration `V070__scanner_orchestrator_schema.sql` added.
  - `findings`: `id`, `tenant_id`, `asset_id`, `scanner_id`, `scan_id`, `severity`, `category`, `title`, `description`, `detected_at`, `created_at`, `updated_at`, `fingerprint`, `raw_payload` (JSONB), `evidence` (JSONB), `tags` (JSONB). **Status:** columns added in `V070__scanner_orchestrator_schema.sql`.
  - Optional: `scan_stats` (JSONB aggregates per run); `fingerprint_index` as a materialized view or index.
- **Parser contract**:
  - Input: tenant context, `scanner_id`, `scan_id`, raw artifact (JSON) from storage.
  - Output: findings with normalized fields + JSONB; compute `fingerprint = hash(scanner_id, tenant_id, asset_id/target, rule_id, location)` and upsert to avoid dupes.
  - Map to `asset_id` via tenant-scoped lookup; no cross-tenant joins.
- **Artifacts**:
  - Store raw outputs in object storage under `tenant/{tenant_id}/scans/{scan_id}.json`. Keep only URLs in `scans.raw_artifact_url`.
- **Indexing**:
  - B-tree on (`tenant_id`, `asset_id`, `scanner_id`, `scan_id`, `severity`, `detected_at`), plus `fingerprint`. Add GIN on `tags` only if needed.
- **Growth model**:
  - Adding/removing scanners only updates `scanner_registry` + parser code; no per-scanner tables. Add stored columns later only for fields that become hot query paths.

## Step 5: Compose pruning plan (ready)
- **Remove/avoid**:
  - `wazuh-manager`, `wazuh_manager_service` (keep agent sidecars only). **Status:** removed from `docker-compose.dev.yml`.
  - Long-lived scanner containers: `gitleaks_sidecar`, `cloud_scanner*`, `git_scanner_*`, `app_scanner_*`, `ai_summary`, `golden_image_builder` as services. Keep images available for on-demand runs. **Status:** removed from `docker-compose.dev.yml`.
  - Duplicate/legacy services not in target bundles (review `analyzer-orchestrator` if redundant once Telemetry/Detection consolidates).
- **Keep as standalone infra**:
  - `keycloak` + `keycloak_db`, `vault-prod`, `opensearch`, `redis`, `postgres`, CA backend (`ejbca` + `ejbca_db` OR `step-ca`).
- **App bundles to keep**:
  - Web/API, Identity/Tenant, Telemetry/Detection, Response/Playbooks, GRC/Asset, Scanner Orchestrator, AIShield Core (if separate), Job runtime, Observability (to be added).
- **Migrations/one-shot**:
  - Retain migration runners (`migrations_flyway`, `model_gateway_migrations`, `model_gateway_data_migrations`, `soar_agent_flyway`) but ensure they are run-once tasks, not long-lived.

## Step 6: Build Scanner Orchestrator skeleton (next)
- **Service definition**:
  - Add a new service entry in compose for the Scanner Orchestrator API. Reuse `backend/libs/sg_core/jobs` handlers/executors as a base. **Status:** `scanner_orchestrator` (port 8025) added; `/scan/{scan_type}` persists to `scans` and dispatches async to workers. Worker tries registry-driven per-scan containers (docker run with payload/output mounts + parser) and falls back to in-process handlers; raw artifacts saved locally under `SCAN_ARTIFACT_ROOT` (default `/tmp/scans`).
  - Responsibilities: enqueue scans, look up registry, launch per-job scanner containers with resource limits, upload raw artifacts, invoke parsers, write `scans`/`findings`, and expose `/scan/*` + `/scans/*` endpoints.
- **Worker wiring**:
  - Update `job_runner`/`job_scheduler` to call the orchestrator API instead of invoking handlers directly. Optionally embed worker logic inside the orchestrator service if we merge runtimes. **Status:** job_runner delegates scan jobs to orchestrator with fallback; scheduler calls orchestrator for cloud/git and falls back to jobs on failure. Orchestrator executes asynchronously via a worker pool; container-per-scan wiring is next.
- **Triggering model**:
  - Onboarding: after signup/config passes health checks, trigger first scans (cloud/git/app) via orchestrator to seed baseline findings; surface scan_ids to UX.
  - Scheduler: keep `job_scheduler` calling orchestrator on cadence; allow per-tenant schedules/env or DB-backed schedules; skip tenants that fail health checks.
  - On-demand: expose `/scan/*` for manual runs; enforce per-tenant rate limits/concurrency.
  - As new scanners land in `scanner_registry`, opt them into onboarding and scheduler without schema/service changes.
- **Ephemeral execution**:
  - Per job: pull image digest from registry, run container with tmpfs output, inject tenant-scoped creds/config, enforce timeouts/limits, collect stdout/file, then exit.
- **Artifacts**:
  - Upload raw output to tenant-scoped object storage; store URL in `scans.raw_artifact_url`; do not persist blobs in Postgres.
- **Parsers**:
  - Bind parser selection to `scanner_registry.parser`. Ensure parser contract (tenant_id, asset lookup, fingerprinting) is implemented.
- **API surface**:
  - `/scan/cloud|git|app` (enqueue), `/scans` (list), `/scans/{id}` (status), `/scans/{id}/findings`, `/scans/{id}/raw` (signed URL).
- **Isolation and quotas**:
  - Queue partitioning by tenant_id and scanner type; per-scanner concurrency caps; request/limits per container; kill on timeout.

## Step 7: Telemetry/Detection consolidation plan (outline)
- **Scope**: unify `siem_agent`, `ingestion_service`, `observables_service`, `detection_service`, `framework_service`, and posture `analyzer-orchestrator` into one service boundary.
- **API**: one surface for ingest (`/telemetry/logs|events`), enrichment (`/observables/enrich`), detection (`/detection/rules|findings|health`), and SIEM search (`/siem/search|aggregations`).
- **Data**: keep Postgres + OpenSearch; no cross-bundle DB joins. Use service APIs for framework content.
- **Migration**: preserve existing routes via gateway shims; dual-run old/new paths during cutover if needed. Remove Wazuh manager; only ingest from agent sidecars.
- **Scaling**: separate ingest/detection workers internally; enforce tenant-based partitioning and rate limits.

## Step 8: Identity/Tenant consolidation plan (outline)
- **Scope**: merge `iam_agent`, `entitlement_agent`, `tenant_service`, `cert_service` into one service. Keep Keycloak and CA (EJBCA/Step CA) as standalone infra.
- **API**: `/identity/*`, `/tenants/*`, `/auth/*`, `/certs/*` through gateway with consistent authz and rate limits.
- **Data**: single schema for app-side IAM/tenant data; Keycloak remains external IdP store; cert issuance calls CA backend over API.
- **Migration**: unify migrations; deprecate duplicate endpoints; maintain backward-compatible aliases during cutover.
- **Secrets/config**: align env/secret names across merged services; standardize Keycloak and CA config injection.

## Step 9: Observability baseline (outline)
- **Tracing/IDs**: enforce request IDs and trace propagation headers at gateway and all bundles; log request ID + tenant_id.
- **Metrics**: counters/histograms per endpoint and worker: request rate, p95 latency, error rate, queue depth, job success/fail, scan duration.
- **Dashboards**: per-bundle SLO views; alerts on SLO burn and queue backlog.
- **Logs**: structured logs with tenant_id, request_id, route, status; ensure PII-safe logging.

## Step 10: Approval and execution gates (outline)
- **Gate 1**: approve bundle map, API contracts, schema/registry plan, compose pruning list.
- **Gate 2**: approve Scanner Orchestrator skeleton and worker wiring; turn off long-lived scanner services.
- **Wave 1 execution**: Identity/Tenant merge + Scanner Orchestrator live, compose pruned (remove Wazuh manager, scanner services).
- **Wave 2/3 execution**: Telemetry/Detection and Response/Playbooks merges; GRC/Asset merge; optional AIShield fold-in; add Observability collector.
