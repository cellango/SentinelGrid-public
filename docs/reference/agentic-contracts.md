# Case, execution and registry contracts

Status: design contract revision 1, October 16, 2026. Not implemented API or database schema.
These logical contracts implement the [selected target](../architecture/agentic-platform.md).
Existing [runtime models](../../backend/libs/sg_agent_runtime/models.py) and
[SOC models](../../backend/libs/sg_agent_runtime/soc_models.py) differ; do not assume
wire compatibility. Physical types, ORM, schemas and Flyway upgrades belong to the
database compatibility plan. No new migration number is assigned here.

## Common rules

IDs are opaque UUIDs unless explicitly described as stable definition keys. Tenant
UUID, authenticated principal/workload, actor authority and credential references
come from server-verified context, not model-generated arguments. Clients/models
may reference objects; each resolution is authorized under the current tenant and
case access policy. A tenant header or queue name alone is not proof of scope.

Use UTC timestamps, positive integer revisions and bounded collections/strings.
Choose explicit limits in the implementation contract. Budgets use bounded integer
token/time/cost units with named currency/unit where relevant. Names, priorities,
model confidence and analyst tiers never grant permissions. Preserve independent
contract, workflow, agent, prompt, model, tool and policy versions.

External API request DTOs and internal trusted envelopes are different. Validate
each caller/server request against one versioned contract. Only server code injects
trusted context. Reject unknown tools, forbidden fields, invalid versions, stale
revisions, unsupported operations and invalid state transitions with typed errors.
Do not fabricate a queued approval or mark an unconfigured effect completed.

## Application records

| Record | Required logical fields | Invariants |
| --- | --- | --- |
| Case | `case_id`, `tenant_id`, `case_kind`, `goal`, `case_revision`, business `status`, accountable owner/reference, entity/service refs, criticality/constraints, evidence refs, access class, timestamps | Cases may represent incidents, exposure, access reviews or control work; incident IDs are linked objects, not the universal case identity |
| Plan | `plan_id`, `case_id`, `plan_revision`, definition versions, typed task nodes, dependencies/conditions/joins, limits, desired outcomes | One active plan owner; append revisions; validate reachability and joins; feedback/model output cannot directly mutate execution state |
| Run request | `workflow_run_id`, `workflow_id`, `workflow_version`, trusted tenant/case, trigger/source event, correlation/deduplication key, requested scope, definition digest, timestamps | Persist with the outbox before intake acknowledgment; redelivery references the same logical request |
| Execution projection | workflow/run identity, engine reference, monotonic projection revision, observed status/step, observation time | Temporal owns scheduling history; this application view cannot independently claim or schedule tasks |
| Evidence reference | `evidence_id`, tenant/case scope, source locator/type/version, content digest where applicable, collection/observation times, freshness, access/retention rules, provenance | Preserve immutable source identity and known gaps; resolve under current access policy; do not put raw secrets or unrestricted evidence in workflow history |

Separate business case disposition from the state of a workflow run. Cases can have
multiple workflow runs/children. Case closure requires verification and accountable
acceptance; successful scheduling or a closed ticket is insufficient.

## Task and agent invocation

| Record | Required logical fields |
| --- | --- |
| Task envelope | `task_id`, `workflow_run_id`, trusted tenant/case, `parent_task_id` if delegated, goal, supported `task_type`, target definition/version, evidence refs, dependency IDs, scoped capability refs, plan/case revision, deadline, budget, idempotency key |
| Agent invocation | `agent_run_id`, `agent_definition_id`, canonical `agent_name`, `agent_version`, `prompt_version`, model policy/version reference, task reference, input/output schema versions, iteration/delegation limits |
| Agent result | task/run identity, typed outcome, findings with evidence refs, facts versus hypotheses, missing/stale data, uncertainty, proposed actions, requested specialist tasks, concise decision rationale, actual usage |

A result proposes work; only the runtime authorizes and schedules it. A deterministic
handler can return a typed task result without being labeled an AI agent. Preserve
that distinction in telemetry. Do not record hidden reasoning chains; retain
concise decisions, source evidence, proposed actions and evaluated outcomes.

Task states: `queued`, `running`, `waiting_for_evidence`, `waiting_for_approval`,
`blocked`, `succeeded`, `failed`, `cancelled`, `expired`. State transitions require
the current scoped identity, expected revision and legal transition. Terminal
analysis success does not imply that any proposed action executed or a case closed.

Model tool arguments contain only allowed operation parameters. Trusted tenant,
actor, approval decision and credential scope are outside the model-writable schema.
The adapter validates schemas and bounds again before any provider operation.

## Actions, approvals and receipts

| Record | Required logical fields | Invariants |
| --- | --- | --- |
| Action proposal | `action_id`, trusted tenant/case, plan/case revision, `tool_id`, `tool_version`, exact typed target refs, validated parameters, expected effect, risk/business impact, preconditions/dependencies, compensation, verification specification, policy version, expiry, proposal hash | Immutable approved content; model proposes parameters, runtime resolves authority and targets |
| Policy decision | decision ID/version, proposal hash, scoped principal/capabilities, allow/deny/approval-required result, reason, evaluated time and expiry | Evaluate current policy at execution; fail closed on unavailable authority; emergency authority is explicit policy |
| Approval | `approval_id`, action/proposal hash, tenant/case/plan/case revision, policy version, exact targets, approver identity/role, separation-of-duties decision, decision/time/expiry | Persist real pending/approved/rejected state; changes to bound content require a new decision; a signal or model statement is not approval |
| Action claim / receipt | `action_id`, stable idempotency key, tool/provider version, target refs, resource fence, attempt identity, provider request/effect IDs, typed execution outcome, timestamps, redacted receipt/evidence refs, reconciliation requirement | Retry identity is stable across workflow replay; ambiguous external state is reconciled before another effect |
| Verification | `verification_id`, action/case scope, verifier identity/definition, method/version, expected postconditions, observed authoritative state and service health, source/time/window, passed/failed/inconclusive result, residual gaps | Separate permitted verification from the write executor; simulation and HTTP success cannot establish verified real-world success |

Approval states include `pending`, `approved`, `rejected`, `expired`, `revoked`.
Submission failure is an explicit task/blocker plus durable retry, not a synthetic
pending approval. Reject forged/changed/replayed decisions and enforce current
target ownership and approver authority on resume and before execution.

Compute `proposal_hash` as SHA-256 over an
[RFC 8785 canonical JSON](https://www.rfc-editor.org/rfc/rfc8785) representation of
the versioned proposal's bound fields: action/tenant/case IDs, plan and case revisions,
tool ID/version, targets, parameters, expected effect, risk/constraints, preconditions,
compensation, verification specification, policy version and expiry. Exclude the
hash itself, mutable execution status and transport credentials. Implementations
must publish exact field names/normalization and cross-language test vectors before
using this as an approval boundary; never substitute an arbitrary JSON dump.

Track action outcomes independently: accepted, dispatched, executed, ambiguous,
failed, cancelled or unsupported, with verification `pending`, `passed`, `failed`
or `inconclusive` and an explicit simulation indicator. A task waiting on manual
completion remains waiting until authenticated evidence is recorded. Effectful
operations that cannot be reconciled safely remain blocked for human ownership.

## Three definition registries

Registry data declares permitted designs; registration does not grant a tenant
permission to run them. Pin immutable versions/digests on every invocation. Allow
incomplete proposal records for design review, but require all executable fields
before implementation/validation/enablement.

| Registry | Required deployable-definition fields |
| --- | --- |
| Workflow | stable `workflow_id`, slug, name/description, independent version/digest, owner, applicability, trigger/input schema, evidence/freshness requirements, typed graph and completion criteria, permitted roles/tool capabilities, action/policy references, limits, evaluation suite, lifecycle status |
| Agent | `agent_definition_id`, canonical `agent_name`, version/digest, purpose, supported tasks, prompt version, input/output schemas, permitted versioned tools, model/data policy, evidence requirements, delegation/iteration/time/cost limits, escalation and evaluation suite, lifecycle status |
| Tool | stable logical `tool_id`, version/digest, description, validated input/output schemas, read/write/impact classification, provider capability, target/scope rules, credential reference policy, authorization/approval requirements, bounds/timeouts/rate limits, idempotency/reconciliation and verification/receipt contracts, owner/tests, lifecycle status |

Lifecycle: `proposed`, `designed`, `implemented`, `validated`, `enabled`, `retired`.
Tenant enablement is a separate record binding tenant, definition versions,
connector capabilities, approved policy/authority, limits, accountable owner and
rollout evidence. A globally validated workflow can remain unavailable to a tenant.
Retirement blocks new runs while existing runs are drained, cancelled or migrated
under an explicit plan; never silently swap versions on active work.

Logical tool keys use `<domain>.<action>`, for example `identity.revoke_sessions`.
Use an explicit versioned wire-name mapping, such as `identity_revoke_sessions`,
where a transport/provider requires or conventionally uses another spelling. Detect
mapping collisions; names are not permission boundaries. Preserve old MCP/tool
names until their clients and capability policies migrate together.

## Human, scheduling and connector contracts

Manual tasks identify an accountable team/person, permitted decision, deadline,
escalation/on-call route, evidence required for completion and scope. Business risk,
legal/privacy conclusions, employment decisions and external communication require
their authorized human owners. Approval and execution duties remain separable.

Alert/finding/request/schedule/business/control/parent-workflow intake carries a
typed trigger, trusted context, stable source/deduplication identity and applicability.
Scheduled redelivery does not create another effect. Parent/child workflows retain
one reconciled action ledger and explicit cancellation/dependency behavior.

Each provider operation declares required/optional/unavailable capability, version,
scoped credential lookup, schemas, target/egress/query constraints, rate/time limits,
idempotency support, effect receipts, authoritative reconciliation/verification,
owner and current contract/provider test evidence. Missing integrations produce
limited-evidence or blocked outcomes. Synthetic and real provider results remain
distinguishable. Ticket synchronization follows case records asynchronously.

## Compatibility and implementation gates

Existing `agent_id`, incident-as-case IDs, legacy task states and flat tool names
remain current interfaces. An adapter must resolve their meaning by endpoint and
tenant. Do not globally rewrite `agent_id` into either a definition ID or run ID.
Map `pending` to `queued` only in a tested adapter; `claimed` requires an actual
execution lease before a running projection; legacy `completed` must not become
verified action success or closed case by translation.

Before these contracts become executable, require schema/contract validation,
cross-tenant denial, changed/expired/forged approvals, unsupported tools, graph
branch/join checks, duplicate/redelivered triggers, checkpoint/DB/model/provider
failure, cancellation, worker replay/upgrades and independent-verification tests.
Physical storage and authoritative/projection boundaries are mapped in the
[database compatibility plan](../architecture/database-compatibility.md); versions,
callers and tools migrate together under the
[runtime ADR](../architecture/decisions/0001-case-runtime.md).
