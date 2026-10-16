# AI Agent Runtime Drift Remediation Closeout

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2026-04-28  
**Status:** Complete  
**Scope:** AI-agent runtime deployment, Model Gateway contract alignment, SOC and Compliance agent hardening, product-facing inventory, and duplicate legacy service-tree cleanup.

## Final State

- Shared runtime library: `backend/libs/sg_agent_runtime`.
- Deployable runtime service: `backend/services/agent_runtime`.
- Canonical service agents: `backend/agents/iam_agent`, `backend/agents/siem_agent`, `backend/agents/soar_agent`, and `backend/agents/mcp_server`.
- Removed duplicate legacy trees: `backend/services/siem_agent`, `backend/services/entitlement_agent`, and `backend/services/ai_enrichment_agent`.
- Canonical internal LLM endpoint: Model Gateway `POST /v1/chat/completions`.
- Active runtime SOC agent: `soc_case_agent`, with deterministic planning that does not require model tokens.
- Declared SOC helper agents remain `declared_only` until their generic tool and approval paths are productized.
- Compliance Agent remains supervised, write tools require approval, and availability stays gated by `COMPLIANCE_AGENT_ENABLED`.

## Validation Evidence

Final cleanup and drift gates passed:

- `python ./scripts/check_agent_legacy_cleanup_readiness.py`
- `bash ./scripts/check_agent_module_drift.sh`
- `python ./scripts/check_agent_runtime_compose_wiring.py`
- `python ./scripts/supply_chain/verify_launch_scope_agent_targets.py`

Compose validation passed:

- `docker compose -f docker-compose.dev.yml config --services`

Focused backend tests passed:

- `env PYTHONPATH=backend/libs pytest backend/tests/test_phase1_service_config_guards.py backend/tests/test_agent_llm_client_model_gateway_contract.py backend/tests/test_agent_runtime_status_readiness.py backend/tests/test_compliance_agent_tools.py backend/tests/test_soc_case_runtime_client.py backend/tests/test_soc_agent_runtime_contracts.py -q`
- `env PYTHONPATH=backend/services/detection_service:backend/libs pytest backend/services/detection_service/tests/test_soc_case_agent_wiring.py -q`
- `env PYTHONPATH=backend/services/ticketing_service:backend/libs pytest backend/services/ticketing_service/app/tests/test_customer_managed_handoff.py backend/services/ticketing_service/tests/test_soc_case_refresh_routes.py -q`
- `env PYTHONPATH=backend/services/api_gateway:backend/libs pytest backend/services/api_gateway/tests/test_agents_routes.py -q`
- `env TEST_DATABASE_URL='sqlite:///./test_model_gateway.db' ADAPTER_STORAGE_PATH=/tmp/models/adapters BASE_MODEL_PATH=/tmp/models/base MODEL_CACHE=/tmp/models/cache DISABLE_RAG_ROUTES=true DISABLE_TRAINING_ROUTES=true PYTHONPATH=backend/services/model_gateway:backend/libs pytest backend/services/model_gateway/tests/test_embedding_seed_service.py backend/services/model_gateway/tests/test_guardrails_api.py backend/services/model_gateway/tests/test_openai_compat_api.py backend/services/model_gateway/tests/test_rag_service_smoke.py -q`

Results from the final validation sweep:

- Runtime/library tests: 33 passed.
- Detection SOC case-agent wiring tests: 3 passed.
- Ticketing SOC refresh and handoff tests: 16 passed.
- API Gateway agent inventory tests: 8 passed.
- Model Gateway compatibility/smoke tests: 9 passed.

## Acceptance Criteria Trace

| Acceptance criterion | Status |
|---|---|
| Dev stack has a real `agent_runtime` service. | Done |
| Runtime status distinguishes active, disabled, and declared-only agents. | Done |
| Generic LLM calls no longer point to missing Model Gateway endpoints. | Done |
| Compliance Agent and SOC Case Agent have working, tested task flows. | Done |
| Legacy duplicate service trees are removed. | Done |
| Docs and API inventory match the actual software tree. | Done |

## Residuals

- SOC helper agents marked `declared_only` are future product work, not drift remediation debt.
- Full autonomous SOC response execution remains out of scope; high-risk actions stay supervised through SOAR/action-service approval paths.
- Compliance generated output remains supervised recommendation or draft/report input, not audit attestation.
- `docker compose config` can still emit ordinary unset optional environment-variable warnings and the repository's existing obsolete `version` warning.
