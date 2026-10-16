# Tenant identifier guidance

- Programmatic calls must use tenant UUIDs to enforce hard isolation boundaries.
- Slugs are customer-friendly but should be translated to UUIDs at the gateway edge and only in rare, read-oriented cases; downstream services remain UUID-only.
- Reject any slug that does not map to the authenticated tenant/realm; never mix tenant scopes.

# Flyway migration naming and schema targeting

- Database schema changes must update both the SQLAlchemy model layer and a Flyway migration in the same change. Do not add tables, columns, indexes, constraints, or schema-affecting raw SQL without the matching model update.
- All database schema changes must be made through Flyway-managed migrations. Do not rely on runtime table creation, ad hoc SQL, service startup migration runners, or legacy/non-Flyway migration folders for new schema changes.
- Use `V###__<schema>_<short_action>.sql` (Flyway version, zero-padded 3 digits, double underscore, snake_case description). Example: `V008__security_ops_add_incident_tags.sql`.
- Versions increment globally across all schemas (Flyway orders by version, not description); do not reuse or reorder.
- Keep one migration per logical change and per schema; avoid mixing schemas in the same file.
- Set the search path at the top for the target schema (e.g., `SET search_path = security_ops, public;`) and avoid cross-schema dependencies; if unavoidable, add them in a follow-up migration and document clearly.

# Component and AI agent naming

These conventions apply to new components. Migrate existing names deliberately,
with compatible API, deployment and installed endpoint identities. A naming change
alone never establishes a capability or permission.

| Responsibility | Canonical pattern | Example |
| --- | --- | --- |
| Model-directed reasoning | `<domain>_<role>_agent` | `identity_investigation_agent` |
| Installed endpoint software | `<purpose>_sensor` | `endpoint_sensor` |
| Telemetry collection | `<source>_collector` | `cloudtrail_collector` |
| Deterministic domain operations | `<domain>_service` | `identity_service` |
| Stateful execution infrastructure | `<purpose>_runtime` | `case_runtime` |
| Protocol/model access | `<purpose>_gateway` | `model_gateway` |
| Bounded job execution | `<purpose>_runner` | `scan_runner` |
| Provider integration | `<provider>_connector` | `jira_connector` |
| Logical callable operation | `<domain>.<action>` | `identity.revoke_sessions` |

- Call a component an AI agent only when a model selects or adapts investigation
  steps, tools or delegated work from evidence. APIs, scanners, fixed playbooks,
  queue consumers, template generators and a single summary call are not agents
  merely because they participate in an AI workflow.
- Use the [canonical role catalog](reference/agent-registry.md). Add a separate role
  only for a distinct reasoning responsibility, capability boundary or evaluation
  suite; otherwise use a bounded skill/tool. Several roles can share a model,
  process or worker pool. Roles are not deployment requirements.
- Use lowercase snake_case for logical names, PascalCase for Python classes and
  kebab-case for deployment names. Example: `identity_investigation_agent`,
  `IdentityInvestigationAgent`, and an infrastructure deployment such as `agent-worker`.
  Do not put tenant, environment, model or version into the canonical role name.
- Keep one canonical name across registry/configuration/docs/telemetry. Store
  `agent_version`, `prompt_version`, `model_version`, `tool_version` and
  `workflow_version` independently. Pin immutable versions/digests for active runs.
- Distinguish `agent_definition_id`, `agent_run_id`, `sensor_id`, `case_id`, `task_id`,
  `workflow_run_id`, `action_id` and `tool_call_id`. Do not introduce an ambiguous
  unqualified `agent_id` in new interfaces. Resolve legacy fields in an endpoint-
  and tenant-aware compatibility adapter; never globally rename their meaning.
- Keep logical tool IDs separate from transport names using an explicit versioned
  mapping. For example, `identity.revoke_sessions` may map to
  `identity_revoke_sessions`. Check collisions and preserve existing wire names
  and capability policies until clients migrate.
- Preserve vendor terms such as Wazuh Agent in vendor interfaces and existing
  SentinelGuard branding/installed identities. Describe the software category
  explicitly; do not rename sensor installations into AI reasoning runs.
- Inventory source modules, APIs, Compose/Helm/DNS names, queues, environment keys,
  registry IDs, metrics and integrations together before a rename. Use scoped,
  versioned compatibility aliases with tests; aliases cannot widen permissions.

# Reasoning, authority and execution ownership

Follow the [target architecture](architecture/agentic-platform.md),
[runtime ADR](architecture/decisions/0001-case-runtime.md) and
[logical contracts](reference/agentic-contracts.md). They describe the selected
future design; the [source map](architecture/overview.md) and release scope describe
what is currently present and verified.

- `case_runtime` is the selected sole case-orchestration facade. The target uses
  Temporal for durable scheduling/history and PostgreSQL for application case,
  approval, evidence and action records. Neither the current Redis helpers nor a
  source rename implements that target. Add dependencies and migrate behavior only
  in their implementation tasks, with the documented qualification gates.
- Keep authentication, authorization, tenant isolation, exact action approval and
  provider operations deterministic. Models propose; the runtime authorizes and
  schedules; typed domain tools execute; independent checks verify effects.
- Derive tenant UUID/caller authority from verified server context. Do not accept
  trusted tenant, credentials, approval decisions or expanded capabilities from
  model arguments, external evidence or a queue/deployment name.
- Use one action boundary for API/MCP/static-playbook/scheduled/AI entrypoints.
  Separate task success, accepted/executed/verified action outcomes and case closure.
  Unsupported, missing, failed or simulated capability cannot claim real verified
  success. Preserve authenticated manual waits and explicit blocked outcomes.
- Document each component/role as present, partial, proposed, validated or retired,
  with evidence and scope. A declaration is not enablement, and an accepted ADR is
  not runtime qualification. Keep private planning evidence out of public source documentation. Keep
  implementation details out of product user flows unless they help users decide.
