# Phase 4 Slice 4B Closeout: Model Gateway Dependency Remediation

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 17, 2026  
**Scope:** Narrowed launch scope model gateway only  
**Decision:** Closed for the narrowed launch scope  
**Gate impact:** Model gateway portion of `G-08` is now closed, but `G-08` remains open until Slice `4C` and Slice `4D` produce the release-gate, SBOM, and image-scan evidence required by the acceptance contract

## Goal

Remove the known model-gateway production dependency findings that were still blocking the narrowed launch path.

## Repo-Backed Changes

### Replaced the vulnerable Hugging Face stack with launch-approved pins

`backend/services/model_gateway/requirements-specific.txt` and `backend/services/model_gateway/requirements.txt` now pin the narrowed launch model-gateway stack to:

- `transformers` `5.5.4`
- `huggingface-hub` `1.11.0`
- `accelerate` `1.13.0`
- `peft` `0.19.1`
- `datasets` `4.8.4`
- `sentence-transformers` `5.4.1`

That removes the earlier vulnerable `transformers` resolution path and replaces the legacy `huggingface-hub==0.23.0` compatibility pin with a current non-affected line.

### Removed the unfixable `diskcache` path from the launch dependency set

- `llama-cpp-python` is no longer included in the launch dependency manifests
- the transitive `diskcache` package only appeared because of `llama-cpp-python`
- the package was not referenced directly anywhere in `backend/services/model_gateway/`

Because the current `diskcache` advisory has no upstream fixed release, the narrowed launch baseline now treats `llama.cpp` as an optional non-production runtime that must be installed manually outside the launch package if someone wants local experimentation.

### Switched the launch runtime default to `transformers`

The production-facing model-gateway defaults now align to the safe runtime path in:

- `backend/services/model_gateway/app/core/config.py`
- `backend/services/model_gateway/app/services/base_model_service.py`
- `backend/services/model_gateway/Dockerfile`
- `backend/services/model_gateway/scripts/test_model_loading.py`
- `charts/values/model-gateway.yaml`

That removes the previous contradiction where the launch dependency set was being cleaned up but the service still defaulted to the `llama_cpp` runtime path.

### Repaired the current base-model test harness to match the live runtime contract

`backend/services/model_gateway/tests/test_base_model_service.py` now mocks the optional `llama_cpp` module at the import boundary instead of patching attributes that do not exist on the live module. The mock-generation test was also updated so it explicitly exercises the `llama_cpp` fallback path instead of assuming it is still the global default runtime.

## Verification

### Production dependency audit

- `/tmp/sg-pipaudit/bin/pip-audit -r backend/services/model_gateway/requirements-specific.txt -f json`
- result: `No known vulnerabilities found`

- `/tmp/sg-pipaudit/bin/pip-audit -r backend/services/model_gateway/requirements.txt -f json`
- result: `No known vulnerabilities found`

### Focused config and readiness regression suite

- `PYTHONPATH=backend/services/model_gateway:backend/libs pytest backend/services/model_gateway/tests/test_config_security.py backend/services/model_gateway/tests/test_readiness.py backend/services/model_gateway/tests/test_request_tracing.py -q`
- result: `11 passed`

### Base-model runtime regression suite

- `PYTHONPATH=backend/services/model_gateway:backend/libs pytest backend/services/model_gateway/tests/test_base_model_service.py -q`
- result: `6 passed`, `1 skipped`

### Dependency provenance check

- repo search confirmed `diskcache` is not referenced directly under `backend/services/model_gateway/`
- dry-run resolution confirmed `diskcache` was introduced only through `llama-cpp-python`

## Residuals

- the earlier shared base-image drift in `backend/docker/base-images/requirements/api-ml.txt` was later closed in Slice `4C`. The remaining follow-on for this area is built-image scan and base-image refresh discipline in Slice `4D`.
- `backend/services/model_gateway/scripts/README.md` still documents manual `llama_cpp` usage as an optional CPU path. That is acceptable as non-launch helper documentation, but it is no longer the narrowed launch default.
- `G-08` remains open until Slice `4C` and Slice `4D` add the required CI enforcement, SBOM generation, and built-image scan evidence for the full narrowed launch package.

## Decision

For the narrowed launch scope:

- Phase 4 Slice 4B is closed
- the model-gateway production dependency baseline no longer carries unresolved known vulnerability findings in either audited requirement set
- the narrowed launch runtime default now aligns with the safe `transformers` path instead of the removed `llama_cpp` dependency line
- Phase 4 should continue with Slice `4C`
