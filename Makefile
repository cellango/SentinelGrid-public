.PHONY: help install dev up down logs test clean apply-ingestion-templates lint preview-check preview-secrets preview-history preview-iam-db preview-mcp preview-gateway-identity preview-gateway preview-workload-reads preview-iam-identity preview-orchestrator-identity preview-soar-identity preview-ingestion-identity preview-connector-identity preview-detection-identity preview-observables-identity preview-wazuh-identity preview-workload-issuer preview-gateway-redis preview-action-authority preview-action-db preview-legacy-actions preview-application-db preview-action-role-db

PYTHON ?= python3
RUFF ?= ruff

help:
	@echo "SentinelGrid developer source preview (see RELEASE_SCOPE.md)"
	@echo "  make install          - Install isolated source-review test dependencies"
	@echo "  make preview-check    - Run tooling, source hygiene, V013 schema and selected identity/authority regressions"
	@echo "  make preview-tooling  - Check source/docs/contracts and tooling tests without application imports"
	@echo "  make preview-impact BASE=<commit> - Require contract mapping for changed paths"
	@echo "  make preview-frontend - Run focused auth tests using installed frontend dependencies"
	@echo "  make preview-mcp       - Check discovery/protocol errors and unavailable legacy tools"
	@echo "  make preview-application-db - Qualify full shared V001-V018 in a new native lab"
	@echo "  make preview-iam-db    - Test audit/RLS in an owned disposable PostgreSQL cluster"
	@echo "  make preview-secrets  - Scan candidate source with Gitleaks 8.30.1"
	@echo "  make preview-history  - Scan all locally available Git refs (full clone required)"
	@echo "  Frontend: cd frontend && npm ci --ignore-scripts && npm run test:preview"
	@echo "  Legacy runtime/build targets are experimental and outside preview support."

build-base:
	@echo "Building SentinelGrid base images..."
	@cd backend/docker/base-images && ./build-all.sh api
	@echo "Base images built successfully!"

install:
	$(PYTHON) -m pip install -r scripts/requirements-preview.txt

dev up:
	@echo "No supported full-stack runtime in the source preview. Read RELEASE_SCOPE.md."
	@exit 1

down:
	docker-compose -f docker-compose.dev.yml down

logs:
	docker-compose -f docker-compose.dev.yml logs -f

test: preview-check

preview-check: preview-tooling
	$(PYTHON) -m pytest --noconftest backend/tests/test_infrastructure_change_schema.py -q
	$(RUFF) check --select F821 backend SentinelGridAIShield SentinelGridPenTestAgent SentinelGridPostureAgent scripts
	$(PYTHON) -m pytest backend/agents/iam_agent/tests/test_auth_api.py backend/agents/iam_agent/tests/test_token_validator.py backend/agents/iam_agent/tests/test_config_security.py backend/agents/iam_agent/tests/test_policy_enforcement.py backend/agents/iam_agent/tests/test_authorize_tenant_isolation.py backend/agents/iam_agent/tests/test_policies_tenant_session.py backend/agents/iam_agent/tests/test_audit_tenant_controls.py backend/agents/iam_agent/tests/test_entitlements_tenant_isolation.py backend/agents/iam_agent/tests/test_access_requests_authorization.py backend/agents/iam_agent/tests/test_anomaly_detection.py backend/agents/iam_agent/tests/test_automation_request_context.py backend/agents/iam_agent/tests/test_source_admission.py backend/agents/iam_agent/tests/test_iam_acceptance_boundaries.py backend/agents/iam_agent/tests/test_sync_jobs_request_context.py backend/agents/iam_agent/tests/test_ai_editor_controls.py backend/agents/iam_agent/tests/test_protocols_request_context.py backend/agents/iam_agent/tests/test_ai_chat_request_context.py backend/agents/iam_agent/tests/test_ai_features_request_context.py backend/agents/iam_agent/tests/test_ai_chat_service.py backend/agents/iam_agent/tests/test_scim_controls.py backend/agents/iam_agent/tests/test_nhi_controls.py backend/agents/iam_agent/tests/test_itdr_controls.py backend/agents/iam_agent/tests/test_role_sync_controls.py backend/agents/iam_agent/tests/test_role_directory.py backend/agents/iam_agent/tests/test_governance_controls.py backend/agents/iam_agent/tests/test_governance_tenant_isolation.py backend/agents/iam_agent/tests/test_access_request_controls.py backend/agents/iam_agent/tests/test_role_mappings_access_requests_tenant_isolation.py -q

	$(MAKE) preview-iam-identity PYTHON="$(PYTHON)"
	$(MAKE) preview-mcp PYTHON="$(PYTHON)"
	$(MAKE) preview-gateway-identity PYTHON="$(PYTHON)"
	$(MAKE) preview-gateway PYTHON="$(PYTHON)"
	$(MAKE) preview-workload-reads PYTHON="$(PYTHON)"
	$(MAKE) preview-orchestrator-identity PYTHON="$(PYTHON)"
	$(MAKE) preview-soar-identity PYTHON="$(PYTHON)"
	$(MAKE) preview-ingestion-identity PYTHON="$(PYTHON)"
	$(MAKE) preview-connector-identity PYTHON="$(PYTHON)"
	$(MAKE) preview-detection-identity PYTHON="$(PYTHON)"
	$(MAKE) preview-observables-identity PYTHON="$(PYTHON)"
	$(MAKE) preview-wazuh-identity PYTHON="$(PYTHON)"
	$(MAKE) preview-workload-issuer PYTHON="$(PYTHON)"
	$(MAKE) preview-action-authority PYTHON="$(PYTHON)"
	$(MAKE) preview-legacy-actions PYTHON="$(PYTHON)"

preview-workload-issuer:
	$(PYTHON) -m pytest -c backend/tests/workload_issuer/pytest.ini backend/tests/workload_issuer -q

preview-wazuh-identity:
	$(PYTHON) -m pytest -c backend/services/wazuh_manager_service/tests/pytest-identity.ini backend/services/wazuh_manager_service/tests -q

preview-observables-identity:
	$(PYTHON) -m pytest -c backend/services/observables_service/tests/pytest-identity.ini backend/services/observables_service/tests -q

preview-detection-identity:
	$(PYTHON) -m pytest -c backend/services/detection_service/tests/pytest-identity.ini backend/services/detection_service/tests/test_detection_identity_boundary.py -q

preview-connector-identity:
	$(PYTHON) -m pytest -c backend/services/connector_service/tests/pytest-identity.ini backend/services/connector_service/tests/test_connector_identity_boundary.py -q

preview-ingestion-identity:
	$(PYTHON) -m pytest -c backend/services/ingestion_service/tests/pytest-identity.ini backend/services/ingestion_service/tests/test_ingestion_identity_boundary.py -q

preview-soar-identity:
	$(PYTHON) -m pytest -c backend/agents/soar_agent/tests/pytest-identity.ini backend/agents/soar_agent/tests/test_soar_identity_boundary.py backend/agents/soar_agent/tests/test_config_security.py -q

preview-orchestrator-identity:
	$(PYTHON) -m pytest -c backend/services/orchestrator/tests/pytest-identity.ini backend/services/orchestrator/tests/test_orchestrator_identity_boundary.py backend/services/orchestrator/tests/test_config_security.py -q

preview-iam-identity:
	$(PYTHON) -m pytest backend/agents/iam_agent/tests/test_request_context_identity.py backend/agents/iam_agent/tests/test_request_context_internal_token.py -q

preview-workload-reads:
	$(PYTHON) -m pytest -c backend/tests/workload_reads/pytest.ini backend/tests/workload_reads -q
	$(PYTHON) -m pytest -c backend/services/ticketing_service/tests/pytest-workload.ini backend/services/ticketing_service/tests/test_workload_read_boundary.py -q

preview-gateway:
	PYTHONPATH=backend/libs:backend/services/api_gateway $(PYTHON) -m pytest -c backend/services/api_gateway/pytest.ini backend/services/api_gateway/tests -m 'not integration' -q

preview-gateway-redis:
	test -n "$(SG_TEST_REDIS_SOCKET)"
	SG_TEST_REDIS_SOCKET="$(SG_TEST_REDIS_SOCKET)" $(PYTHON) -m pytest -c backend/services/api_gateway/tests/pytest-boundaries.ini backend/services/api_gateway/tests/test_gateway_budgets.py -q

preview-gateway-identity:
	$(PYTHON) -m pytest -c backend/tests/gateway_identity/pytest.ini backend/tests/gateway_identity -q

preview-mcp:
	$(PYTHON) -m pytest -c backend/agents/mcp_server/tests/pytest.ini backend/agents/mcp_server/tests -q
	$(PYTHON) -m pytest -c backend/agents/mcp_server/transport_tests/pytest-http.ini backend/agents/mcp_server/transport_tests -q

preview-secrets:
	$(PYTHON) scripts/scan_public_secrets.py snapshot

preview-history:
	$(PYTHON) scripts/scan_public_secrets.py history

test-welcome-dashboard:
	@echo "Running welcome dashboard E2E test..."
	@./scripts/run-welcome-dashboard-test.sh

rebuild-and-test-dashboard:
	@echo "Rebuilding containers without cache and running dashboard test..."
	@./scripts/rebuild-and-test-dashboard.sh

test-iam-portal:
	@echo "Running IAM Portal smoke tests..."
	@./scripts/iam-portal-smoke-test.sh

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +

apply-ingestion-templates:
	@echo "Applying ingestion service templates..."
	@./backend/services/ingestion_service/scripts/apply_templates.sh
	@echo "Applying endpoint (wazuh-alerts) templates..."
	@./scripts/wazuh/create-opensearch-templates.sh

lint:
	$(RUFF) check --select F821 backend SentinelGridAIShield SentinelGridPenTestAgent SentinelGridPostureAgent scripts

# This suite starts and stops its own socket-only synthetic cluster; no DB_URL.
preview-iam-db:
	$(PYTHON) -m pytest backend/agents/iam_agent/tests/test_iam_database.py -q

# Proposal/approval and bypass containment; does not enable provider execution.
preview-action-authority:
	PYTHONPATH=backend/libs:backend/services/case_runtime $(PYTHON) -m pytest -c backend/services/case_runtime/tests/pytest.ini backend/services/case_runtime/tests/test_action_boundary.py backend/services/case_runtime/tests/test_canonical_vectors.py -q

preview-legacy-actions:
	PYTHONPATH=backend/libs:backend/services/action_service $(PYTHON) -m pytest -c backend/services/case_runtime/tests/pytest.ini backend/services/action_service/tests/test_action_execution.py -q

# Separate non-skipping gate: reviewed PG/Flyway, owned synthetic cluster only.
preview-action-db:
	PYTHONPATH=backend/libs:backend/services/case_runtime $(PYTHON) -m pytest -c backend/services/case_runtime/tests/pytest.ini backend/services/case_runtime/tests/test_action_database.py backend/services/case_runtime/tests/test_mcp_case_records_database.py -q

# Separate native gate; missing tools fail rather than skip. No existing DB input.
preview-application-db:
	$(PYTHON) scripts/qualify_application_database.py

# Full shared catalog and current privilege boundary; no existing DB input.
preview-action-role-db:
	SG_ACTION_DB_PROFILE=shared_application PYTHONPATH=backend/libs:backend/services/case_runtime $(PYTHON) -m pytest -c backend/services/case_runtime/tests/pytest.ini backend/services/case_runtime/tests/test_action_database.py backend/services/case_runtime/tests/test_mcp_case_records_database.py backend/services/case_runtime/tests/test_database_role.py -q

# Read-only developer checks. Dependencies must already be installed.
.PHONY: preview-tooling preview-impact preview-frontend
preview-tooling:
	$(PYTHON) scripts/check_public_preview.py
	$(PYTHON) scripts/check_contracts.py
	$(PYTHON) -m unittest discover -s scripts/tests -v

preview-impact:
	@test -n "$(BASE)" || (echo "Set BASE to the reviewed commit"; exit 1)
	$(PYTHON) scripts/check_contracts.py --base "$(BASE)"

preview-frontend:
	cd frontend && npm run test:preview
