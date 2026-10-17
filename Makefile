.PHONY: help install dev up down logs test clean apply-ingestion-templates lint preview-check preview-secrets preview-history preview-iam-db preview-mcp preview-gateway-identity preview-gateway preview-workload-reads

PYTHON ?= python3
RUFF ?= ruff

help:
	@echo "SentinelGrid developer source preview (see RELEASE_SCOPE.md)"
	@echo "  make install          - Install isolated source-review test dependencies"
	@echo "  make preview-check    - Check paths, documentation, source hygiene, V013 schema, and IAM auth/policy and MCP/user/workload identity boundaries"
	@echo "  make preview-mcp       - Check discovery/protocol errors and unavailable legacy tools"
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

preview-check:
	$(PYTHON) scripts/check_public_preview.py
	$(PYTHON) -m unittest discover -s scripts/tests -v
	$(PYTHON) -m pytest --noconftest backend/tests/test_infrastructure_change_schema.py -q
	$(RUFF) check --select F821 backend SentinelGridAIShield SentinelGridPenTestAgent SentinelGridPostureAgent scripts
	$(PYTHON) -m pytest backend/agents/iam_agent/tests/test_auth_api.py backend/agents/iam_agent/tests/test_token_validator.py backend/agents/iam_agent/tests/test_config_security.py backend/agents/iam_agent/tests/test_policy_enforcement.py backend/agents/iam_agent/tests/test_authorize_tenant_isolation.py backend/agents/iam_agent/tests/test_policies_tenant_session.py backend/agents/iam_agent/tests/test_audit_tenant_controls.py backend/agents/iam_agent/tests/test_entitlements_tenant_isolation.py backend/agents/iam_agent/tests/test_access_requests_authorization.py backend/agents/iam_agent/tests/test_anomaly_detection.py backend/agents/iam_agent/tests/test_automation_request_context.py backend/agents/iam_agent/tests/test_source_admission.py backend/agents/iam_agent/tests/test_iam_acceptance_boundaries.py backend/agents/iam_agent/tests/test_sync_jobs_request_context.py backend/agents/iam_agent/tests/test_ai_editor_controls.py backend/agents/iam_agent/tests/test_protocols_request_context.py backend/agents/iam_agent/tests/test_ai_chat_request_context.py backend/agents/iam_agent/tests/test_ai_features_request_context.py backend/agents/iam_agent/tests/test_ai_chat_service.py backend/agents/iam_agent/tests/test_scim_controls.py backend/agents/iam_agent/tests/test_nhi_controls.py backend/agents/iam_agent/tests/test_itdr_controls.py backend/agents/iam_agent/tests/test_role_sync_controls.py backend/agents/iam_agent/tests/test_role_directory.py backend/agents/iam_agent/tests/test_governance_controls.py backend/agents/iam_agent/tests/test_governance_tenant_isolation.py backend/agents/iam_agent/tests/test_access_request_controls.py backend/agents/iam_agent/tests/test_role_mappings_access_requests_tenant_isolation.py -q

	$(MAKE) preview-mcp PYTHON="$(PYTHON)"
	$(MAKE) preview-gateway-identity PYTHON="$(PYTHON)"
	$(MAKE) preview-gateway PYTHON="$(PYTHON)"
	$(MAKE) preview-workload-reads PYTHON="$(PYTHON)"

preview-workload-reads:
	$(PYTHON) -m pytest -c backend/tests/workload_reads/pytest.ini backend/tests/workload_reads -q
	$(PYTHON) -m pytest -c backend/services/ticketing_service/tests/pytest-workload.ini backend/services/ticketing_service/tests/test_workload_read_boundary.py -q

preview-gateway:
	$(PYTHON) -m pytest -c backend/services/api_gateway/tests/pytest-identity.ini backend/services/api_gateway/tests/test_gateway_identity_boundary.py -q
	PYTHONPATH=backend/libs:backend/services/api_gateway $(PYTHON) -m pytest -c backend/services/api_gateway/pytest.ini backend/services/api_gateway/tests/test_auth_middleware.py backend/services/api_gateway/tests/test_config_security.py backend/services/api_gateway/tests/test_metrics.py -q

preview-gateway-identity:
	$(PYTHON) -m pytest -c backend/tests/gateway_identity/pytest.ini backend/tests/gateway_identity -q

preview-mcp:
	$(PYTHON) -m pytest -c backend/agents/mcp_server/tests/pytest.ini backend/agents/mcp_server/tests -q

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
