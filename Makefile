.PHONY: help install dev up down logs test clean apply-ingestion-templates lint preview-check preview-secrets preview-history

PYTHON ?= python3
RUFF ?= ruff

help:
	@echo "SentinelGrid developer source preview (see RELEASE_SCOPE.md)"
	@echo "  make install          - Install isolated source-review test dependencies"
	@echo "  make preview-check    - Check paths, documentation, source hygiene, V013 schema, and IAM auth/policy"
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
	$(PYTHON) -m pytest backend/agents/iam_agent/tests/test_auth_api.py backend/agents/iam_agent/tests/test_token_validator.py backend/agents/iam_agent/tests/test_config_security.py backend/agents/iam_agent/tests/test_policy_enforcement.py backend/agents/iam_agent/tests/test_authorize_tenant_isolation.py backend/agents/iam_agent/tests/test_policies_tenant_session.py -q

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
