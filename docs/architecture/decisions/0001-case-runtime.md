# ADR 0001: One case runtime with durable workflow execution

Date: October 16, 2026.
Status: accepted target architecture; implementation and runtime qualification pending.

## Context

The source preview contains a Redis-backed [task queue](../../../backend/libs/sg_agent_runtime/task_queue.py)
and [case memory](../../../backend/libs/sg_agent_runtime/memory.py), an
[agent loop](../../../backend/libs/sg_agent_runtime/agent_loop.py), deterministic
[case planning](../../../backend/libs/sg_agent_runtime/soc_case_task_handler.py),
and [playbook execution](../../../backend/agents/soar_agent/app/services/playbook_execution_service.py).
These are useful migration inputs. Their existence does not establish a single
durable owner for case execution, exact approval enforcement, or verified outcomes.

The target must support long human waits, conditional and parallel tasks, retries,
cancellation, restart recovery and changes against external systems. Building an
agent graph alone does not provide those application guarantees. One case may
coordinate incident, exposure, review and control workflows; the organization must
not be serialized behind a global supervisor process.

## Decision

Use a single logical **`case_runtime`** facade with **Temporal as its durable
workflow execution engine** and Python workers. PostgreSQL remains the application
system of record for cases, plan definitions/revisions, approvals, evidence
references, action proposals/receipts and an outbox. Temporal owns orchestration
history, timers, dependencies and scheduled execution progress. Redis may transport
notifications or cache data; it is not an independent case scheduler or authority.

This selects the implementation direction. This documentation change installs no
SDK/server, enables no execution path and does not qualify a deployment. Start
qualification in an isolated local environment; a hosted service or paid plan is
not part of this decision. Dependency pins, licenses, operations and deployment
changes require their normal implementation review.

The planned application owner is `backend/services/case_runtime/`. That directory
does not yet exist. Existing `sg_agent_runtime` contracts, case adapters, response
packs, compliance helpers and playbook IR are migration inputs, not a second runtime
to keep active alongside it. Preserve behavior and compatibility while moving each
accepted capability. Retire competing case scheduling paths only after parity and
recovery gates pass.

## Authority and consistency

| Concern | Sole authority | Other representations |
| --- | --- | --- |
| Case identity, access, business status and evidence references | Application PostgreSQL through `case_runtime`/authorized domain APIs | UI/search projections; a closed workflow alone cannot close a case |
| Workflow scheduling, timers, dependency progress and replay | Temporal, accessed through `case_runtime` | PostgreSQL execution-status views are projections; they cannot independently schedule work |
| Proposal content, approval decisions and effect receipts | Application PostgreSQL and deterministic policy/connector checks | Workflow history references immutable IDs and hashes; a signal is a notification, not approval proof |
| Raw telemetry and semantic retrieval | Their source stores, referenced by the case | Neither search nor a vector match authorizes an action |

1. Commit an accepted trigger, case/run request and outbox record atomically in the
   application database. Only then acknowledge intake. A dispatcher starts or
   signals a stable workflow identity derived from trusted tenant/case/run IDs.
   Redelivery uses the same logical operation ID.
2. Keep workflow control deterministic. Model calls, provider I/O and application
   database effects run as bounded activities. Persist model decisions as typed
   activity results; never call an LLM again merely to replay a scheduling decision.
3. Before an external write, the activity verifies current caller/tenant scope,
   definition versions, resource ownership, policy and the exact durable approval.
   It records an action claim with a stable idempotency key and resource fencing.
   Workflow replay, actor labels and model output cannot grant permission.
4. Record provider receipts and reconcile ambiguous effects. If a provider timed
   out after a possible write, query authoritative state before retry; unsupported
   reconciliation produces a blocker or accountable human task. A workflow engine
   cannot make every external mutation exactly once.
5. Commit approval decisions and completion events to PostgreSQL with an outbox
   notification. Resume re-reads and validates that record. Missed/duplicate signals
   are recoverable; a fabricated or stale signal never authorizes execution.
6. Update application projections with monotonic revisions and idempotent writes.
   If the workflow succeeded but projection persistence failed, retry projection
   reconciliation without repeating the effect. If durable authority is unavailable,
   stop before further effects. Never use local/in-memory execution as a successful
   fallback for an unavailable durable path.

Temporal namespaces, queues and workflow identifiers are routing mechanisms, not
tenant authorization controls. Every application read, resume and activity still
requires verified context. Keep credentials and raw sensitive evidence out of
workflow history; use scoped references, redacted results and an explicit
history/access/encryption/retention policy.

Temporal's own persistence is vendor infrastructure with a separate lifecycle and
storage boundary. Application tables and paired ORM/Flyway migrations remain under
[the project database rules](../../development/database-changes.md). The
[database compatibility plan](../database-compatibility.md) defines the proposed
physical application schema and vendor/application storage separation. Neither
document assigns migration versions or implements that storage.

## Research refinement: adaptive Playbooks

The [adaptive Playbook design](../adaptive-playbooks.md) treats WF-* entries as
coverage goals and reuses immutable versions of the existing Playbook library.
Case-specific plan data may change within reviewed constraints while this engine
remains the sole scheduler. Run manifests, full plan/definition payloads, append-only
events and protected artifacts provide audit evidence independently of engine history.

A later research proposal prefers native LangGraph, but reports on a custom engine
described as LangGraph-style rather than a native implementation. Its useful domain
requirements do not demonstrate a failure of the selected Temporal direction.
Retain this decision; qualify it against the same three scenario fixtures, repaired
fixed baseline and recovery/approval/evidence gates. A justified alternative spike
may inform a superseding ADR; no second live scheduler, dependency or vendor storage
is introduced by this refinement.

## Alternatives

| Option | Assessment | Decision |
| --- | --- | --- |
| Existing Redis queue/agent loop as authoritative case engine | Reuses source but would require a new durable scheduler, human-wait/recovery protocol, leases and reconciliation around it | Preserve contracts and useful handlers; replace its case ownership during migration |
| Extend a first-party PostgreSQL checkpointed graph engine | Close to existing workflow concepts; SentinelGrid would own replay, scheduling, failure recovery, version compatibility and operational correctness | Reuse graph/IR concepts after tests; do not retain an independent executor |
| LangGraph with durable checkpoints | Useful graph and interruption mechanisms; still requires SentinelGrid's effect, policy and cross-service consistency boundary | Do not adopt as a second authoritative case engine; bounded reasoning libraries can be evaluated later without owning external effects |
| Temporal behind `case_runtime` | Durable orchestration primitives fit long waits, recorded activities and restart recovery; adds a service, SDK and operating responsibilities | Selected for the target; qualify against the acceptance gates below |

This is an engineering judgment for the target requirements, not a benchmark result.
[Temporal workflow execution](https://docs.temporal.io/workflow-execution) and the
[Python SDK guide](https://docs.temporal.io/develop/python) describe its workflow and
worker model. Its [activity documentation](https://docs.temporal.io/activity-definition)
explains why repeated external activity execution still needs idempotency.
[Self-hosting guidance](https://docs.temporal.io/self-hosted-guide) covers the added
deployment/operations boundary. [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
and [interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) informed
the alternative assessment; their capabilities do not remove SentinelGrid's own
authorization or action-reconciliation duties.

## Consequences and qualification gates

The selected direction adds operational cost and requires SDK/server versioning,
worker replay compatibility, service recovery, access control, retention, audit and
dependency/provenance review. There is no claim that infrastructure cost is constant
or that the existing preview runs Temporal.

Before replacing an execution path or trusting automated effects, demonstrate:

- Caller/server contract validation and denial of cross-tenant reads, resumes and actions.
- Manual waits and exact approved actions surviving process termination and restart.
- No extra supported external effects after redelivery, worker death, stale approval,
  provider timeout, database failure or projection replay.
- Branch reachability, parallel joins, bounded loops, cancellation, resource conflicts
  and explicit compensation/blocked partial outcomes.
- Independent verification, evidence freshness and case-specific closure criteria.
- Replay compatibility across a worker/definition upgrade and recovery of outbox/signal gaps.
- Measured local operating requirements, restore evidence and a reviewed data/security boundary.

Failure of these gates blocks enablement. If qualification shows the selected
engine unsuitable, supersede this ADR with evidence and one replacement authority;
do not silently fall back to a competing scheduler. See the
[target architecture](../agentic-platform.md) and [contracts](../../reference/agentic-contracts.md).
