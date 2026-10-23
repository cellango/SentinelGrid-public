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
- Use the [canonical role catalog](docs/reference/agent-registry.md). Add a separate role
  only for a distinct reasoning responsibility, capability boundary or evaluation
  suite; otherwise use a bounded skill/tool. Several roles can share a model,
  process or worker pool. Roles are not deployment requirements.
- Use lowercase snake_case for logical names, PascalCase for Python classes and
  kebab-case for deployment names. Example: `identity_investigation_agent`,
  `IdentityInvestigationAgent`, and an infrastructure deployment such as `agent-worker`.
  Do not put tenant, environment, model or version into the canonical role name.
- Keep one canonical name across registry/configuration/docs/telemetry. Store
  `agent_version`, `prompt_version`, `model_version`, `tool_version` and
  `playbook_version`, runtime build, and legacy `workflow_version` independently.
  Pin immutable versions/digests for active runs; retain compatible legacy fields.
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

# Workflow and orchestration guardrails

## Architectural decision

Temporal is the approved execution engine for enterprise cybersecurity workflows
and incident orchestration, behind the single `case_runtime` facade. PostgreSQL
owns application case, approval, evidence and action records. Existing alternative
engines are migration debt, not precedent for adding new engines.

Follow the [target architecture](docs/architecture/agentic-platform.md),
[runtime ADR](docs/architecture/decisions/0001-case-runtime.md) and
[logical contracts](docs/reference/agentic-contracts.md). They describe the selected
target design; the [source map](docs/architecture/overview.md) and
[release scope](RELEASE_SCOPE.md) describe what is currently present and verified.
Confirm actual deployment and integration before claiming Temporal is implemented.
Neither the current Redis helpers nor a source rename implements that target.
Add dependencies and migrate behavior only in their implementation tasks, with the
documented qualification gates.

## One execution authority

- Route new incident workflows and playbook executions through Temporal via
  `case_runtime`.
- Temporal owns task scheduling, dependencies, retries, durable timers, approval
  waits, cancellation and execution recovery.
- Do not introduce another component that independently owns these responsibilities
  for the same workflow.
- Do not implement custom durable workflow engines, checkpoint managers, retry
  schedulers or approval polling loops.
- Do not use in-process background tasks as the durable execution mechanism for
  security workflows.

Normal functions, bounded loops and parallel computation inside a task are allowed.
They must not become independent workflow runtimes.

## Existing engines and queues

- Do not add new core security workflows to n8n, StackStorm or the custom
  "LangGraph-style" engine.
- Existing integrations may receive necessary fixes during migration.
- Preserve useful connectors, action implementations and workflow definitions when
  replacing their execution machinery.
- Do not migrate active executions by silently changing their runtime. Drain them
  or use an explicit migration procedure.
- Existing background-job queues may continue serving their documented workloads.
  Do not expand them into incident orchestration.
- Do not undertake unrelated queue migrations as part of routine feature work.

## LangGraph and other agent frameworks

- LangGraph is not an approved replacement for Temporal.
- Adding LangGraph or another agent runtime requires an explicit architecture
  decision and user authorization.
- If approved, its scope must be bounded and documented, such as investigation
  reasoning within a Temporal-managed step.
- It must not independently own incident lifecycle, production action retries,
  long approval waits or incident completion.
- Document how retries, checkpoints, cancellation and concurrent execution interact
  with Temporal. One responsibility must have one owner.

## Agent behavior and action execution

- AI agents may propose plans, select eligible specialists, interpret evidence and
  recommend actions.
- Validate proposed tasks against registered capabilities, tenant policy,
  permissions, dependencies and execution budgets.
- Keep authentication, authorization, tenant isolation, exact action approval and
  provider operations deterministic. Models propose; the runtime authorizes and
  schedules; typed domain tools execute; independent checks verify effects.
- Derive tenant UUID/caller authority from verified server context. Do not accept
  trusted tenant, credentials, approval decisions or expanded capabilities from
  model arguments, external evidence or a queue/deployment name.
- Use one action boundary for API/MCP/static-playbook/scheduled/AI entrypoints.
- Execute external effects through approved connectors under Temporal.
- Never execute LLM calls or external I/O directly in deterministic Temporal
  Workflow code; place them in Activities or approved SDK integrations.
- Use stable operation IDs and deduplication for effects that may be retried.
- Do not claim exactly-once external effects merely because Temporal is used.
- Model confidence, skill instructions and agent output cannot grant permissions
  or bypass required approvals.

## One playbook library

- Maintain one canonical, versioned playbook/procedure library. Preserve existing
  Playbook keys/UUIDs and the editor; publish immutable procedure versions supporting
  fixed, conditional and adaptive modes.
- Workflow catalog entries and WF-* IDs describe desired security outcomes; they
  are not instructions to create another executable workflow for every catalog item.
- Incident-specific plans reference existing procedures where possible.
- Runtime representations are derived artifacts, not independently maintained
  copies of playbook logic.
- Pin applicable playbook, plan, skill, model and policy versions for each run.
- The workflow is the control graph; the execution plan is bounded case-specific
  task data. Reuse typed subplaybooks; validate graph semantics and mandatory work
  before scheduling. Follow the
  [adaptive design](docs/architecture/adaptive-playbooks.md).

## Separate ownership

- SentinelGrid owns security incident facts, evidence and disposition. PostgreSQL
  owns application records; execution-status projections must not become schedulers.
- Temporal owns execution state and recovery.
- The selected ticketing provider owns assigned work and ticket status.
- Ticket updates are events to evaluate, not automatic authority to close a
  security incident or launch unrestricted actions.
- Workflow checkpoints and execution histories do not replace retained application
  evidence. Keep full definition/plan payloads, manifests, events, artifacts and
  effect receipts under retention/access policy.
- Audit reconstruction makes no model/provider calls; simulation is effect-disabled
  and separately identified. Recovery history alone is not the audit trail.

## Required checks before implementation

Before adding workflow-related code:

1. Identify the existing workflow, procedure, Activity, connector or queue that
   should be extended.
2. State which component owns execution and recovery.
3. Check for duplicate scheduling, retries, approvals or lifecycle state.
4. Reuse existing contracts before creating another service or abstraction.
5. If the approved architecture cannot meet the requirement, document the specific
   gap before proposing another engine.

Do not add an orchestration dependency, container, service, scheduler or persistent
execution loop as an incidental implementation detail.

## Exceptions

A new engine requires a recorded architecture decision covering:

- The requirement the approved architecture cannot reasonably satisfy.
- Alternatives considered and evidence supporting the exception.
- Exact responsibility boundaries and authoritative state.
- Recovery, retry, cancellation, authorization and evidence behavior.
- Operating cost, ownership, migration and retirement strategy.

A dependency being popular or described as "agentic" is insufficient.
Do not implement the exception before explicit user authorization.

## Completion criteria

Workflow changes must:

- Use the approved execution path.
- Report actual pending, running, waiting, failed, cancelled or verified completion
  states. Separate task success, accepted/executed/verified action outcomes and
  case closure.
- Never report success from a stub, mock, queued request or proposed action.
  Unsupported, missing, failed or simulated capability cannot claim real verified
  success. Preserve authenticated manual waits and explicit blocked outcomes.
- Include appropriate recovery and duplicate-effect checks.
- Preserve historical execution and evidence references.
- Update architecture documentation when responsibility boundaries change.
- Document each component/role as present, partial, proposed, validated or retired,
  with evidence and scope. A declaration is not enablement, and an accepted ADR is
  not runtime qualification.

Keep private planning evidence out of public source documentation. Keep
implementation details out of product user flows unless they help users decide.
