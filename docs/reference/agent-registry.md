# Canonical AI role catalog

Status: proposed role definitions with agreed naming, October 16, 2026. These rows
are not registered or enabled runtime capabilities. A role needs the complete
[agent contract](agentic-contracts.md), permitted tools and an evaluation suite
before implementation. [AGENTS.md](../../AGENTS.md) owns the naming rules;
[component categories](agent-components.md) describe existing source.

## Shared conventions

Use one canonical lowercase snake_case name across definition, configuration,
documentation and telemetry. For `identity_investigation_agent`, the Python class
is `IdentityInvestigationAgent` and a dedicated module, when needed, is
`identity_investigation_agent.py`. Store agent, prompt and model versions separately.
Worker/deployment names describe infrastructure and use kebab-case; several roles
may share one model, process or worker pool.

Start with supervisor, triage, identity, endpoint, exposure, response and verification
contracts. Add email and other bounded skills/roles when a workflow actually needs
their tool boundary or evaluations. A catalog entry is not an instruction to create
a service. A workflow may involve multiple conditional roles; it does not require
calling every role or creating an agent for every workflow.

All role-definition lifecycle statuses below are **proposed**. The selected naming
does not assert model-directed behavior in today's source. No role name grants
tools, approval rights or tenant scope.

| Label | Canonical name | Bounded reasoning responsibility |
| --- | --- | --- |
| SV | `security_supervisor_agent` | Own the case plan, propose task decomposition and reconcile findings; request scheduling through the runtime |
| TR | `security_triage_agent` | Assess initial signal quality, correlation, scope and missing evidence |
| VE | `security_verification_agent` | Evaluate independent authoritative outcome evidence against postconditions; do not approve or execute its own write |
| AS | `asset_context_agent` | Reconcile asset/service ownership, criticality and dependencies for human confirmation |
| ID | `identity_investigation_agent` | Investigate identity/session/privilege evidence; deterministic services enforce identity operations |
| EP | `endpoint_investigation_agent` | Interpret host/process/activity evidence and propose focused collection |
| TI | `intelligence_analysis_agent` | Assess intelligence relevance, quality and reliability |
| RP | `security_response_agent` | Compare containment/remediation options and business impact; propose exact actions |
| RC | `recovery_coordination_agent` | Assess recovery prerequisites, dependencies and restoration evidence |
| CO | `security_case_coordination_agent` | Reason about owners, handovers, tickets and deadlines; do not become another case scheduler |
| GR | `compliance_evidence_agent` | Map control/evidence needs and propose source-backed assessments and collection work |
| RK | `security_risk_assessment_agent` | Explain risk, impact and treatment choices for accountable owners |
| DE | `security_detection_engineering_agent` | Develop detection/hunting hypotheses and reviewable evaluations |
| EM | `email_investigation_agent` | Investigate messages, campaigns and collaboration evidence |
| CL | `cloud_posture_agent` | Assess cloud/SaaS posture relationships and remediation dependencies |
| EX | `exposure_assessment_agent` | Assess vulnerability applicability, exposure and fix priorities |
| NW | `network_investigation_agent` | Interpret network evidence, reachability and containment options |
| AP | `application_security_assessment_agent` | Assess application and software supply-chain findings in context |
| DS | `data_security_assessment_agent` | Assess data exposure and privacy evidence for authorized owners |
| AI | `ai_security_investigation_agent` | Investigate AI input/retrieval/tool/model threats and regression evidence |
| TP | `third_party_risk_assessment_agent` | Compare supplier evidence and business dependencies |
| VA | `security_validation_agent` | Plan and interpret explicitly authorized security tests within scope |
| SO | `security_platform_assurance_agent` | Assess telemetry, connector, automation and agent-evaluation failures |
| PE | `people_security_enablement_agent` | Tailor guidance and route security reports; no employment decisions |
| KY | `cryptography_management_agent` | Assess certificate/key/trust dependencies; PKI/KMS performs deterministic operations |
| OT | `ot_security_assessment_agent` | Optional industrial assessment within operations/safety authority; passive-first scope |

There are 25 core roles and one optional industrial role. Accountable humans retain
business, legal, risk-acceptance and safety decisions. Technical verification can
inform those decisions without replacing them.

## Existing declaration migration

[Current definitions](../../backend/libs/sg_agent_runtime/agents.py) use legacy
IDs. The mappings below are design dispositions, not active aliases. Bind each
alias to a versioned definition and a tested capability scope before use; never
combine old tool permissions by taking their union.

| Existing declaration | Target disposition |
| --- | --- |
| `soc_case_agent` | Retain as a legacy deterministic case-planning handler. The new model-directed supervisor is a separate definition, not a cosmetic alias |
| `soc_triage_agent`, `triage_agent` | Converge permitted intake work toward `security_triage_agent`; verify behavior, tools and clients before choosing an alias/version |
| `soc_investigation_agent`, `investigation_agent` | Decompose broad investigation into evidence-driven specialist tasks/skills under the supervisor; no automatic broad-permission alias |
| `soc_response_planner_agent`, `response_agent` | Migrate bounded proposal reasoning toward `security_response_agent`; execution moves through the common policy/action boundary |
| `soc_ticket_scribe_agent` | Documentation drafting is a skill/helper; use a separate case-coordination role only for evidence-dependent ownership/handover decisions |
| `compliance_agent` runtime declaration | Converge admitted reasoning toward `compliance_evidence_agent`; keep the deterministic compliance service distinct |

The classes `SOCResponsePlanner` and `SOCTicketScribe` are deterministic utilities,
even though related declaration names include “agent.” Source availability and
configuration still determine which generic loop handlers can actually run. No
new canonical role is counted as implemented by this catalog.
