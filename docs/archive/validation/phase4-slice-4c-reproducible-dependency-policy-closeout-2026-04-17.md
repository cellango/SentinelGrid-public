# Phase 4 Slice 4C Closeout: Reproducible Dependency Policy

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 17, 2026  
**Scope:** Narrowed launch scope dependency and filesystem release gate  
**Decision:** Closed for the narrowed launch scope  
**Gate impact:** Slice `4C` is closed, but `G-08` remains open until Slice `4D` adds built-image scan evidence and base-image refresh discipline for the launch container set

## Goal

Turn dependency and source-tree risk from an ad hoc spot check into a repeatable release gate that measures the real narrowed launch package.

## Repo-Backed Changes

### Defined the narrowed launch dependency policy and effective install plans

`scripts/supply_chain/launch_scope_dependency_policy.json` now defines:

- which Python manifests must remain exact-pinned for the narrowed launch path
- which overlay manifests are allowed to stay ranged
- the effective install plan for each launch-scope Python service:
  - `api-gateway`
  - `iam-agent`
  - `siem-agent`
  - `orchestrator`
  - `model-gateway`
- the Node lockfile that represents the narrowed launch frontend dependency contract

That removes the earlier ambiguity where individual requirement files could look safe in isolation while the real shipped service dependency graph still differed once shared base layers were applied.

### Refreshed the shared launch dependency baseline so the policy passes honestly

The narrowed launch dependency baseline was updated in:

- `backend/docker/base-images/requirements/api-base.txt`
- `backend/docker/base-images/requirements/api-ml.txt`
- `backend/agents/iam_agent/requirements-specific.txt`
- `backend/services/model_gateway/requirements-specific.txt`

The important effect is that the shared Python service base, the shared ML base, the IAM embedding path, and the model-gateway overlay now resolve cleanly under the same policy that release CI enforces.

### Added reproducible audit helpers for policy verification and effective-manifest auditing

The new helper set is:

- `scripts/supply_chain/verify_launch_scope_dependency_policy.py`
- `scripts/supply_chain/run_launch_python_supply_chain_gate.py`
- `scripts/supply_chain/stage_launch_scope_filesystem.sh`

Together they now:

- reject non-exact pins in manifests that are supposed to be frozen
- materialize the effective launch install plan for each service instead of auditing arbitrary source files
- write machine-readable and human-readable summaries under the chosen artifact directory
- stage a narrowed launch source bundle for SBOM generation and filesystem scanning

### Wired continuous and release-time enforcement into GitHub Actions

The CI and release workflows now enforce the narrowed launch dependency contract in:

- `.github/workflows/test.yml`
- `.github/workflows/supply-chain-evidence.yml`
- `.github/workflows/build-push-deploy.yml`

The resulting release path now does all of the following before a deploy can proceed:

- runs frontend `npm audit --omit=dev --audit-level=high`
- validates the narrowed launch dependency policy
- runs `pip-audit` against the effective Python install plans
- stages the narrowed launch filesystem bundle
- generates a CycloneDX SBOM artifact
- runs a Trivy filesystem vulnerability scan against that staged launch bundle
- uploads the resulting artifacts for audit review

## Verification

### Dependency policy validation

- `python3 scripts/supply_chain/verify_launch_scope_dependency_policy.py --artifacts-dir /tmp/sg-supply-chain-check`
- result: `Launch-scope dependency policy is valid.`

### Effective Python launch-plan audit in clean Python 3.11

- `docker run --rm -v /path/to/SentinelGrid:/workspace -w /workspace python:3.11-slim bash -lc "python -m pip install --upgrade pip pip-audit >/tmp/pip-install.log && rm -rf artifacts/container-supply-chain && python scripts/supply_chain/verify_launch_scope_dependency_policy.py --artifacts-dir artifacts/container-supply-chain && python scripts/supply_chain/run_launch_python_supply_chain_gate.py --artifacts-dir artifacts/container-supply-chain"`
- result: all five narrowed launch effective manifests passed:
  - `api-gateway`
  - `iam-agent`
  - `siem-agent`
  - `orchestrator`
  - `model-gateway`

### Narrowed launch filesystem staging and scan

- `bash scripts/supply_chain/stage_launch_scope_filesystem.sh artifacts/local-launch-scope-fs`
- result: narrowed launch filesystem bundle staged successfully

- `docker run --rm -v /path/to/SentinelGrid:/workspace aquasec/trivy:0.64.1 fs --scanners vuln --severity HIGH,CRITICAL --format json --output /workspace/artifacts/local-trivy-fs-launch-scope.json /workspace/artifacts/local-launch-scope-fs`
- result: completed with exit code `0`
- result detail: `artifacts/local-trivy-fs-launch-scope.json` recorded `0` high / critical findings across the detected dependency target set

### CycloneDX SBOM generation

- `docker run --rm -v /path/to/SentinelGrid:/workspace anchore/syft:v1.29.0 dir:/workspace/artifacts/local-launch-scope-fs -o cyclonedx-json=/workspace/artifacts/local-launch-scope-sbom.cdx.json`
- result: completed with exit code `0`
- result detail: `artifacts/local-launch-scope-sbom.cdx.json` is a CycloneDX `1.6` SBOM with `219` components

### Focused regression coverage on touched launch services

- `PYTHONPATH=backend/services/api_gateway:backend/libs pytest backend/services/api_gateway/tests/test_auth_middleware.py backend/services/api_gateway/tests/test_request_tracing.py -q`
- result: `14 passed`

- `PYTHONPATH=backend/agents/iam_agent:backend/libs pytest backend/agents/iam_agent/tests/test_auth_api.py backend/agents/iam_agent/tests/test_gateway_state_binding.py backend/agents/iam_agent/tests/test_route_transport_security.py -q`
- result: `25 passed`

- `PYTHONPATH=backend/services/model_gateway:backend/libs pytest backend/services/model_gateway/tests/test_config_security.py backend/services/model_gateway/tests/test_base_model_service.py -q`
- result: `11 passed`, `1 skipped`

- `PYTHONPATH=backend/agents/siem_agent:backend/libs pytest backend/services/siem_agent/tests/test_internal_auth_contract.py -q`
- result: `3 passed`

### Helper script sanity checks

- `python3 -m py_compile scripts/supply_chain/verify_launch_scope_dependency_policy.py scripts/supply_chain/run_launch_python_supply_chain_gate.py`
- result: passed

- `bash -n scripts/supply_chain/stage_launch_scope_filesystem.sh`
- result: passed

## Residuals

- Slice `4C` does not replace built-image scanning. `G-08` remains open until Slice `4D` produces repeatable image-scan evidence against the built launch containers, not only source manifests and a staged filesystem bundle.
- The narrowed launch exception register remains empty. No dependency exception was required to close Slice `4C`.
- A broader orchestrator regression sweep is still noisy because `backend/services/orchestrator/app/api/snapshot.py` triggers a pre-existing route assertion during some test collection paths. That issue is real repo debt, but it is not caused by the Slice `4C` dependency-policy changes.

## Decision

For the narrowed launch scope:

- Phase 4 Slice 4C is closed
- the narrowed launch dependency policy is now explicit, reproducible, and artifact-backed
- CI and release workflows now enforce the launch dependency baseline instead of treating it as advisory
- all five effective Python launch install plans passed in a clean Python `3.11` environment
- the narrowed launch filesystem staging, Trivy scan path, and CycloneDX SBOM generation path are working
- Phase 4 should continue with Slice `4D`
