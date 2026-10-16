# AI Strategy (Tenant-Safe, Grounded, Assistive)

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This document defines how we use AI across SentinelGrid with strict tenant isolation, grounded answers, and human-in-the-loop controls. It complements `docs/vulnerability-remediation-plan.md`.

## Principles
- Tenant-first: every AI query and result is scoped to the caller’s tenant; cross-tenant data is never loaded or returned.
- Grounded: responses cite only indexed facts (vector store + live APIs) and avoid speculation; clearly indicate when data is missing.
- Assistive, not autonomous by default: AI drafts actions (tickets, configs, playbooks); humans approve unless explicitly enabled for automation.
- Auditable: log prompts, sources, and actions for compliance; configurable retention per tenant.
- Minimal exposure: least-privilege service tokens; no long-lived broad scopes; no PII leakage.

## Architecture (chat + retrieval)
- Per-tenant vector namespace/index; mandatory `tenant_id` filter on all queries.
- Embeddings include metadata: tenant_id, resource_type (finding, fix_group, runbook, asset), severity, env, service/app, tags, timestamp.
- Retrieval pipeline:
  1. Extract tenant_id from auth context; enforce role-based policy (e.g., restrict sensitive data to admins).
  2. Build query with tenant filter + optional facets (severity, service, env).
  3. Retrieve top-k chunks; rerank; optionally blend with live API facts (e.g., current SLA status).
  4. Compose answer with citations to sources (scan IDs, fix groups, tickets).
- Model usage: prefer small, grounded models for Q&A; for remediation drafts, use structured prompts with fixed fields (summary, steps, validation).

## Guardrails
- Hard tenant filter on every retrieval and action.
- Role-aware views: e.g., non-admins can’t see other teams’ assets/tickets if restricted by policy.
- No free-form actions: ticket creation, config changes, or deployments require explicit confirmation; batch/auto modes are opt-in per tenant.
- Redact secrets/PII in prompts; never embed secrets; strip access tokens from logs.
- Rate limits and abuse detection per tenant and per user.

## Use Cases (initial)
- Vulnerability Q&A: “Which critical vulns are internet-exposed on payments?”, “What fixes clear CVE-2025-XXXX on Ubuntu 22?” Ground on FixGroups and findings.
- Ticket drafting: propose ticket payloads from FixGroups with SLA-based due dates; keep human approval.
- Remediation playbooks: generate concise steps + validation for OS patches, dependency upgrades, base-image rebuilds, config hardening.
- Explainer mode: plain-language summaries of scans/incidents with top risks and affected assets.
- Prevention nudges: surface “stop the bleeding” insights (outdated base images, missing dependency automation).

## Embedding/Indexing Plan
- Sources to embed (per tenant):
  - Findings (normalized vulns with CVEs, components, exposure, severity).
  - FixGroups (type, guidance, fixed_in_target, assets, CVEs, priority, SLA).
  - Scan summaries (top risks, counts, timelines).
  - Runbooks/KB (curated per tenant; mark as shared or private).
- Index fields (metadata for filtering): tenant_id, service/app, env, severity, exploit_flag, asset_type, cve_id, fix_group_id, scan_id, tags, updated_at.
- Updates: push on scan ingest; upsert on ticket/status changes; prune stale/closed items periodically.

## UI Integration (chat everywhere)
- Global chat widget reads auth context (tenant_id, roles); all prompts auto-include tenant filter.
- Answer cards with citations (scan/fix_group/ticket links); show when data is missing or stale.
- Quick actions: “Draft ticket for this FixGroup,” “Show top 10 criticals in prod,” “Explain this scan.”
- Opt-in “sensitive mode” toggle to hide asset identifiers for non-admins.

## Automation Levels
- L0: Read-only Q&A and summaries (default).
- L1: Drafts (tickets, remediation steps) requiring user confirm.
- L2: Batch apply (e.g., create tickets for top FixGroups) with tenant-level enablement and audit.
- L3 (future, opt-in): Trigger rescans/rebuilds for non-prod with policy gates.

## Observability & Quality
- Log: prompt, retrieved sources, model version, latency, user/tenant, action outcome.
- Metrics: answer acceptance, ticket draft acceptance, hallucination reports, SLA impact (MTTR, overdue reduction).
- Feedback loop: thumbs-up/down with reason; feed into reranking and prompt tuning.

## Open Items
- Define per-tenant retention/anonymization policy for logs.
- Add redaction step for any PII/secret patterns before embedding.
- Allow tenants to bring their own model/key if required; still enforce tenant filtering.
