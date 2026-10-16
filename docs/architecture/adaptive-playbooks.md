# Adaptive playbooks, coverage and execution evidence

Status: accepted planning direction, October 16, 2026; implementation and runtime
qualification pending. This refines the [platform target](agentic-platform.md),
[logical contracts](../reference/agentic-contracts.md) and
[database plan](database-compatibility.md). No code, schema, framework dependency,
execution permission or workflow enablement is added by this document.

## One procedure library

| Term | Target meaning |
| --- | --- |
| Detection | Versioned recognition logic with source/query/parameter/entity contracts and tested matching/nonmatching behavior |
| Security use case | Stable WF-* coverage goal, applicability and required outcome evidence; not an executable definition |
| Playbook | Existing stable identity/key and editor, extended with immutable published versions for fixed, conditional or adaptive work |
| Subplaybook | Reusable versioned procedure with typed inputs/outputs, prerequisites, permitted effects and verification |
| Execution plan | Case-specific bounded tasks, chosen procedure versions, targets, dependencies and evidence questions; each accepted revision is retained |
| Runtime workflow | Control protocol executing an accepted plan; not another user-facing library alongside Playbooks |
| Case / run | A case correlates related work; each run pins its content, plan and runtime versions |

Preserve existing Playbook keys/UUIDs, tenant customizations, editor content and run
references. Keep WF-* IDs as stable coverage references. Map coverage goals to
existing Playbooks/variants and missing capabilities using many-to-many bindings;
do not generate one new executable per coverage row. Similar names are candidates
for comparison, not evidence of equivalence. Preserve source-specific triggers,
investigation hypotheses, outcomes and history when consolidating content.

The [catalog](../../cfg/playbooks/catalog.yaml) has 40 Playbook keys; richer or
code-authored versions of a key are content to reconcile, not additional identities.
Public [response packs](../../frontend/src/lib/playbooks/responsePacks.ts),
[playbook IR](../../backend/libs/sg_agent_runtime/playbook_ir_models.py) and
[case planning](../../backend/libs/sg_agent_runtime/soc_case_task_handler.py) also
need reconciliation. An editor graph, phase description or source count is not
qualified executable coverage. Unknown response-pack keys require an explicit
alias, separate definition or unresolved status; never silently guess the target.

## Immutable Playbook publication and compilation

A published version retains the complete source and canonical compiled payload,
schema/compiler version, source package/digest, planning contract, publication
decision and compatible runtime/tool versions. A digest alone cannot recover lost
content. Changes publish a new version; seeding cannot overwrite an active graph,
tenant customization or historical run definition. Archive/tombstone referenced
content rather than cascade-delete retained execution evidence.

Compile editor trigger/action forms, automated/manual/decision phases, code-authored
investigations and accepted assessment procedures into one validated task/procedure
contract. Preserve branch conditions, cross-phase dependencies, required joins,
prerequisites, artifacts, rollback descriptions and verification. Renaming node
types does not repair semantics or bind a tool. Unsupported nodes/tools, missing
required work and incompatible schemas block publication/execution; no all-skipped
graph may count as successful completion. Old content remains accessible through
versioned provenance and compatibility adapters.

## Detection routing and quality gates

The [detection catalog](../../cfg/detections/catalog.yaml),
[seeder](../../backend/scripts/seed_catalog_detections_playbooks.py) and
[monitor builder](../../backend/agents/siem_agent/app/config/monitor_definitions.py)
need explicit quality gates. Database-free probes of these source functions found
110 catalog definitions, 35 alert types, 22 first-seeded default disagreements,
15 distinct compiled query/trigger shapes and null query/trigger payloads for all
110 entries through the tested version-seeding path. These are bounded source-path
observations, not a live mapping export or a detection-efficacy measurement.

For each detection, record rule/query-template versions, effective parameters,
source schema, extraction, monitor identity, suppression/deduplication and freshness.
Test matching, nonmatching, malformed, delayed and cross-tenant events against its
actual hypothesis. Identical compiled queries can expose incomplete compilation;
they do not justify merging distinct detection requirements. Keep unqualified
definitions visibly blocked from automated response; qualify the pilot-required
subset before pilot enablement, with a disposition for every remaining definition.

Select an authenticated tenant's exact rule-version binding and applicable approved
Playbook version first. Apply tenant override precedence, capability readiness,
business constraints, severity and approval policy deterministically. Allow a
documented alert-type fallback only when explicitly configured. Hints are untrusted.
Persist candidates, exclusions, selected binding/version and concise reasons;
source ordering must not change the result. Correlate several alerts into a case
without losing their many-to-many task/evidence links or repeating containment.
Non-incident findings, requests and schedules do not need fake detection events.

Keep high-volume recognition deterministic. AI may investigate ambiguous evidence
and propose detector/tuning drafts; deployment and suppression changes follow their
own evaluated, approved publication path.

## Bounded adaptive planning

A Playbook version declares its outcome/applicability, mandatory evidence and
freshness, reusable procedures, permitted adaptation, invariants, protected targets,
service constraints, budgets, deadlines, completion predicates and reviewed fallback.
A stable runtime control protocol consumes plan data; models cannot generate and
execute arbitrary Python, shell, provider endpoints or credentials.

Retain full plan payload, parent/revision/hash, triggering evidence, validation
report, accepted rationale and planner/model/prompt/runtime versions. Validate
capabilities, tenant/entity scope, typed parameters, dependency reachability, joins,
mandatory evidence, approval gates, bounds and conflicts before scheduling. Model
confidence and advisory review flags cannot bypass mandatory human decisions.

Replan at safe boundaries when evidence or constraints change. Cancel only work
that can safely stop; preserve completed actions and their originating revision.
Merge results by task/accepted-attempt identity, not a flat last-writer-wins context.
Late results remain evidence under their old revision until the current assessment
accepts them. Required parallel work must join explicitly. Exhausted budgets,
missing evidence and unavailable connectors produce an owned unresolved outcome.

An unchanged logical action keeps its action ID and idempotency key across retries
and replans. Completed approvals/receipts remain historical facts. For pending work,
changed targets, parameters, prerequisites, risk context, policy or expiry invalidate
the affected authorization. Unrelated plan edits do not erase history. The initial
implementation requires a renewed decision when a bound revision changes; a later
explicit policy may support an audited carry-forward attestation after deterministic
equivalence and current-authority checks. No automatic approval reuse is implied.
Compensation is a separately authorized and verified action.

Urgent preauthorized procedures may run through the same durable intent/policy/
receipt boundary while broader investigation continues. Failure of the durable
authority path cannot silently enable a fallback executor.

## Evidence independent of recovery state

| Record | Retained evidence |
| --- | --- |
| Run manifest | Tenant/case/run, initiating events and selection binding, exact Playbook/subprocedure versions and full content refs, compiler/runtime build, contracts, policy and initial context refs |
| Plan and decision trail | Every full plan revision, validation, selected/rejected alternatives, supporting/contradicting evidence, uncertainty and concise accepted rationale |
| Execution events and attempts | Append-only event ID and per-run sequence, actor/time, task/attempt/revision, input/output refs and digests, typed states, action/policy/approval IDs and prior integrity reference |
| Artifacts and custody | Original bytes or policy-approved representation, source/event/collection times, content digest, protected location, redaction relationship, access/custody history, retention and legal hold |
| Effect and verification | Stable action intent, provider request/receipt, reconciliation and independent postcondition/service-health observations, exceptions and accountable disposition |
| Runtime history link | Engine execution/history identity, worker build and state schema; a recovery/diagnostic pointer, not the only audit record |

Persist authority and its event/outbox atomically before dispatch. Append-only role
permissions, integrity links, independent anchors, protected storage and restore/
export verification must be qualified; a hash chain alone cannot prevent privileged
rewriting or deletion. Apply customer retention and legal holds, not indefinite raw
incident retention. Keep credentials out of records and normal engine history.
Where policy permits, retain protected rendered model requests, structured outputs,
retrieval context, generation parameters and provider/deployment metadata, with a
separate redacted view. No hidden chain-of-thought or exact future model reproduction
is needed for reconstruction from recorded observable outputs.

Provide three distinct operations: **audit reconstruction** reads stored records
offline with zero model/provider calls; **simulation** gets a new identity and
effect-disabled adapters; **live continuation** requires current authorization and
durable state. UI and export show selected procedure, plan changes, skipped work
and reasons, approvals, receipts, verification and unresolved scope. Never use a
runtime replay/fork operation as the read-only audit viewer.

## Engine decision and qualification

The accepted [ADR](decisions/0001-case-runtime.md) still selects `case_runtime` with
Temporal. Adaptive plans and the evidence improvements above are application
requirements and do not require replacing that engine. The custom implementation
described as LangGraph-style in historical source is not proof of native LangGraph
use. No native LangGraph dependency/import was found in the reviewed public source.

Qualify the selected engine using the same privileged-account, phishing and exposure
charter fixtures, including fan-out/joins, pinned definitions, human waits, worker
death, persistence failure, cancellation, ambiguous effects and audit reconstruction.
Compare against a repaired fixed/conditional baseline with effects disabled. Set
owner-approved quality, recovery, latency and cost thresholds before rollout.

Engine reconsideration, including native LangGraph, is **deferred** as future item
`FUT-001`, with no target date or dependency on the active delivery plan. Current
runtime work qualifies Temporal only. A failed qualification gate blocks enablement
and records evidence; it does not automatically start an alternative-engine spike.
Revisit only when the owner prioritizes a concrete qualification gap or measured
operating concern. Replacement requires evidence, an accepted superseding ADR,
storage/security/operations review and a single-owner cutover plan. No additional
engine, checkpointer or reasoning-library experiment is scheduled by this design.

Official [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence),
[interrupt](https://docs.langchain.com/oss/python/langgraph/interrupts) and
[time-travel](https://docs.langchain.com/oss/python/langgraph/use-time-travel)
guidance describes state recovery and node re-execution. These mechanisms still
need application authorization and safe effect handling. Temporal's
[workflow model](https://docs.temporal.io/workflow-execution) likewise does not
replace the application evidence and action records.

## Delivery order

1. Preserve effective definitions, tenant overrides, bindings and run history;
   compare source to any authorized deployment export. Disable misleading execution
   paths before trusting effects. No live export was taken by this planning review.
2. Correct shared identity/routing, graph/tool, approval and tenant contracts; publish
   immutable Playbook versions without a second executable catalog.
3. Add run manifests, append-only events/artifacts and offline reconstruction;
   preserve existing histories and pair ORM/Flyway changes.
4. Qualify the selected runtime with the three scenario fixtures and a fixed baseline.
5. Shadow routing/plans with effects disabled; cut over by scoped tenant/use case
   with only one owner per live run and a tested drain/recovery path.
6. Expand measured adaptive composition and reusable procedures; fill catalog gaps
   by value and qualified capability, preserving all stable WF-* coverage IDs.

Source migration, product implementation and tenant enablement remain distinct.
The existing source-preview release is unchanged. New table names here are design
proposals; use the database plan and contributor rules for actual implementation.
