# Phase 3 Slice 3D Closeout: Secret And Default-Credential Elimination

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 17, 2026  
**Scope:** Narrowed launch scope only  
**Decision:** Closed for the narrowed launch scope  
**Gate impact:** `G-07` is now passed

## What This Slice Had To Prove

The narrowed launch deployment path could not continue to rely on:

- placeholder internal-service tokens
- local default database, Redis, Keycloak, Vault, or OpenSearch endpoints
- production-by-omission runtime boot where services still defaulted to `development`
- production-looking helper scripts that silently fell back to placeholder secrets

This slice closes that gap in the repo-backed launch path.

## Repo-Backed Changes

### 1. Launch Helm values now force production-mode validation

The narrowed launch values for:

- `charts/values/api-gateway.yaml`
- `charts/values/iam-agent.yaml`
- `charts/values/model-gateway.yaml`
- `charts/values/orchestrator.yaml`
- `charts/values/siem-agent.yaml`

now set explicit production runtime env and runtime secret contracts.

Key effects:

- `ENVIRONMENT=production` is now explicit for the five launch services that need production-only validation
- the launch charts now consume runtime secrets through fixed `envFrom.secretRef` contracts:
  - `api-gateway-runtime`
  - `iam-agent-runtime`
  - `model-gateway-runtime`
  - `orchestrator-runtime`
  - `siem-agent-runtime`
- security booleans that must not drift are now fixed in values instead of being left implicit:
  - `UPSTREAM_TLS_VERIFY=true`
  - `KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT=true`
  - `KEYCLOAK_VERIFY_TLS=true`
  - `VAULT_VERIFY_TLS=true`
  - `PAYMENT_DEV_MODE=false`
  - `OPENSEARCH_USE_SSL=true`
  - `OPENSEARCH_VERIFY_CERTS=true`

### 2. The release workflow now fails closed if runtime secrets are missing

`.github/workflows/build-push-deploy.yml` now:

- runs `scripts/lint_production_default_secrets.sh`
- verifies the required runtime secrets exist in the target namespace before deploy

That closes the previous gap where a release could render and deploy while still depending on local defaults or omitted production secrets.

### 3. Production config guards now reject placeholder backing services

Shared helpers in `backend/libs/sg_core/service_security.py` now enforce:

- HTTPS-only browser origins for public CORS in production
- non-default database URLs in production
- authenticated Redis URLs in production
- HTTPS-only external Keycloak, Vault, and OpenSearch URLs in production

Those guards are now active in the launch-scope services that matter here:

- `backend/services/api_gateway/app/core/config.py`
- `backend/agents/iam_agent/app/core/config.py`
- `backend/services/orchestrator/app/core/config.py`
- `backend/agents/siem_agent/app/core/config.py`
- `backend/services/model_gateway/app/core/config.py`

`backend/services/model_gateway/app/core/database.py` now uses the resolved settings contract instead of its own independent `postgres:postgres@localhost` fallback.

### 4. Production-looking infra helpers no longer default to placeholder root secrets

The production Vault and infra helpers were tightened:

- `infra/vault/scripts/vault-prod-entrypoint.sh`
- `backend/scripts/init_vault_prod.sh`
- `infra/eks/variables.tf`
- `infra/vault/README_PROD.md`

Key effects:

- the old placeholder Vault root token is no longer a runtime default
- the old placeholder token is explicitly rejected if supplied
- Terraform no longer ships a default RDS password

### 5. Dev-only compose manifests are now explicitly marked as dev-only

- `docker-compose.dev.yml`
- `docker-compose.minimal.yml`

now carry top-level warnings that their local defaults and placeholder credentials are not part of the production deployment path.

## Verification

### Secret/default lint

- `bash ./scripts/lint_production_default_secrets.sh`
- result: passed

### Focused production config security tests

- `PYTHONPATH=backend/services/api_gateway:backend/libs pytest backend/services/api_gateway/tests/test_config_security.py -q`
- result: `7 passed`

- `PYTHONPATH=backend/agents/iam_agent:backend/libs pytest backend/agents/iam_agent/tests/test_config_security.py -q`
- result: `14 passed`

- `PYTHONPATH=backend/services/orchestrator:backend/libs pytest backend/services/orchestrator/tests/test_config_security.py -q`
- result: `2 passed`

- `PYTHONPATH=backend/agents/siem_agent:backend/libs pytest backend/agents/siem_agent/tests/test_config_security.py -q`
- result: `4 passed`

- `PYTHONPATH=backend/services/model_gateway:backend/libs pytest backend/services/model_gateway/tests/test_config_security.py -q`
- result: `4 passed`

- `PYTHONPATH=backend/libs pytest backend/tests/test_phase1_service_config_guards.py -q`
- result: `7 passed`

### Helm render verification

Rendered with sample ACM certificate ARNs where public ingresses require them:

- `api-gateway`
- `iam-agent`
- `model-gateway`
- `orchestrator`
- `siem-agent`

Confirmed in rendered manifests:

- explicit `ENVIRONMENT=production`
- expected `envFrom.secretRef` runtime contracts
- expected fixed security env values

Fail-closed path also verified:

- rendering `api-gateway` without `ingress.alb.certificateArn` still fails as expected

## Residuals

- This slice proves the repo-backed secret contract and deploy guard behavior, not a live cluster rollout with real secret objects.
- Some local helper scripts and test fixtures elsewhere in the repo still intentionally contain development defaults. They are not part of the narrowed launch deployment path and were not reclassified as production-safe.

## Decision

For the narrowed launch scope:

- Phase 3 Slice 3D is closed
- `G-07` is passed
- Phase 3 is complete

The next critical path item is Phase 4 Slice 4A: frontend dependency remediation.
