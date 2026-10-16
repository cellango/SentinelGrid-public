# Agent and module categories

Status: source inventory, reviewed October 15, 2026. It replaces the earlier
runtime-inventory status report; listed code and declarations are not deployment
or activation evidence.

| Category | Source owner | Review interpretation |
| --- | --- | --- |
| Shared task/agent runtime | [sg_agent_runtime](../../backend/libs/sg_agent_runtime/), [runtime service](../../backend/services/agent_runtime/) | Inspect task models, dispatch, tools, approval/auth context, and feature flags |
| Domain services with legacy agent paths | [IAM](../../backend/agents/iam_agent/), [SIEM](../../backend/agents/siem_agent/), [SOAR](../../backend/agents/soar_agent/) | Long-running API services; distinct from model-driven task loops |
| Tool catalog/MCP | [MCP service](../../backend/agents/mcp_server/) | Declared tools need their own authorization and execution review |
| Platform models/RAG | [Model gateway](../../backend/services/model_gateway/) | Model calls, embeddings, training, and provider configuration are runtime work |
| AI runtime security | [AI Shield](../../SentinelGridAIShield/) | Separate component; not the platform Model Gateway |
| Posture subsystem | [Posture Agent](../../SentinelGridPostureAgent/) | Separate services/analyzers and experimental frontend |
| Pentest subsystem | [PenTest Agent](../../SentinelGridPenTestAgent/) | Authorization/scanner/playbook source; active scans and exploitation excluded |
| Endpoint collectors/packages | [SentinelGuard](../../SentinelGuard/), [Wazuh references](../../agents/wazuh/) | Endpoint source and third-party package references are different from LLM agents |

[Gateway agent inventory routes](../../backend/services/api_gateway/app/api/routes_agents.py)
and [runtime service](../../backend/libs/sg_agent_runtime/service.py) distinguish
runtime declarations/status from enabled execution. Inspect flags and handlers;
not every declared helper has an operational task loop or registered write tools.
The special `soc_case_agent` handler runs the deterministic response-pack planner
and template scribe; a declaration or display label does not make that handler
model-directed. Other definitions may enter the generic model loop when their
configuration and registered tools permit it. See [legacy declaration dispositions](agent-registry.md).

Internal tokens, tenant context, approval replay, network effects, and model/provider
fallbacks remain review targets. No agent loop, endpoint enrollment, provider call,
or scanner is part of the supported source-check command.

The [target ownership map](../architecture/agentic-platform.md) records planned
responsibility changes. `case_runtime`, `identity_service`, `response_service` and
other target names are not renamed source paths or operational aliases. The
[accepted runtime decision](../architecture/decisions/0001-case-runtime.md) requires
a separate implementation and qualification step.
