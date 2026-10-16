# Async Jobs, Tool Registry, and Scanners – Implementation Outline

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This complements the schema/seed in `V049__tool_registry_and_jobs.sql` and `backend/config/tool_registry.seed.yaml`.

## Components
- **tool_registry (DB)**: source of truth for tools (image, command template, parser).
- **jobs (DB)**: Postgres-backed queue for async work.
- **job runner**: process/container that polls `jobs` (`SELECT … FOR UPDATE SKIP LOCKED`), executes work, parses results, and writes findings/assets.
- **scheduler**: K8s CronJobs or a tiny scheduler container that enqueues recurring jobs.
- **API surface**: enqueue/status endpoints for UI and automation.

## Minimal APIs (proposed)
- `POST /jobs`  
  Body: `{ "tenant_id": "...", "job_type": "cloud_initial_scan", "payload": {...} }`  
  Returns: `{ "job_id": "..." }`
- `GET /jobs/{job_id}`  
  Returns: `{ job_id, status, attempts, error, started_at, finished_at }`
- `GET /jobs?tenant_id=...&job_type=...&status=...`  
  List/filter recent jobs.

## Runner behavior
- Poll `jobs` with `status='queued' AND next_run_at <= now()` using `FOR UPDATE SKIP LOCKED`.
- Set `status='running'`, increment `attempts`, set `started_at`.
- Dispatch by `job_type` to the right handler:
  - `cloud_initial_scan` / `cloud_daily_scan`: invoke tools from registry with categories `cloud_security` (and `image_security`), passing connector info and `include_db_security` flag.
  - `git_initial_scan` / `git_daily_scan`: invoke `git_security` tools with repo scope.
  - `ai_daily_summary`: run the summary job.
  - `golden_image_build`: run packer build + trivy scan.
- For each tool:
  - Render command_template with payload values (no secrets in template; inject from connectors/env).
  - Run container, capture JSON output, parse via parser_key, normalize to `findings` and `assets`, store raw_payload (compressed if large).
- On success: `status='completed'`, `finished_at=now()`.  
  On failure: record error, set `status='failed'` or reschedule by setting `next_run_at` + backoff until `max_attempts`.

## Scheduler/Cron enqueues
- Daily (UTC):
  - 02:00 → `ai_daily_summary`
  - 03:00 → `cloud_daily_scan` (include_db_security flag)
  - 04:00 → `git_daily_scan`
- Bi-weekly:
  - 04:00 every 14 days → `golden_image_build`
- Initial triggers (webhook/logic after feature toggle + connector ready):
  - `cloud_initial_scan` with connector_id + include_db_security
  - `git_initial_scan` with git_connector_id + scope (all_repos | selected + repo_ids)

## Findings/Assets mapping
- Parse each tool’s JSON into `findings` with: tenant_id, source_tool, asset_type/id, severity, category, title, description, remediation, evidence, raw_payload, detected_at.
- Maintain/lookup assets (`assets` table) by external_id + tenant_id; reuse asset_id when available.

## Tool registry usage
- At runner start: load active tools from `tool_registry` filtered by `job_type`.
- Tools can be disabled/marked experimental via `status`.
- Extend the registry by adding to YAML seed (for defaults) and/or DB directly for runtime overrides.

## Operational notes
- Keep secrets/credentials out of YAML; inject at runtime from connectors/env/secret mounts.
- Add basic metrics: job durations, failure counts per tool.
- Keep parser functions in code with unit tests against fixture outputs.
