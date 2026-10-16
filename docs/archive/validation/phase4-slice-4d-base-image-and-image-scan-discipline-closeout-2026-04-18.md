# SentinelGrid Phase 4 Slice 4D Base Image And Image Scan Discipline Closeout

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 18, 2026  
**Status:** Complete for the narrowed launch scope with approved residual exceptions  
**Gate impact:** `G-08` passed with approved exceptions `EX-2026-04-18-01` through `EX-2026-04-18-03`

## Scope

This slice closed the last Phase 4 gap between dependency-manifest scanning and actual built-image evidence.

The work focused on:

1. building the real narrowed launch image set from the shared image graph
2. scanning built images instead of relying only on source-tree or filesystem evidence
3. hardening the shared runtime and frontend runner images
4. making the image-scan gate fail closed instead of reporting findings while still exiting `0`

## What Changed

1. `scripts/supply_chain/build_launch_scope_images.sh` now builds the narrowed launch image set as a first-class evidence artifact, records image-inspect output, and captures the exact scan target list used at release time.
2. `scripts/supply_chain/scan_launch_scope_images.sh` now:
   - scans built images, not only staged filesystems
   - exits nonzero when any high / critical finding remains
   - uses a shared Trivy cache under `.cache/trivy` so repeated scans do not redownload the DB for every run
3. `frontend/next.config.mjs` and `frontend/Dockerfile` now use Next.js standalone output in the final image, remove `npm` / `npx` from the runtime layer, and eliminate the prior frontend image findings.
4. `backend/docker/base-images/Dockerfile.runtime-python` now applies Debian security updates and keeps the shared runtime narrower than the earlier build-tool / dev-header-heavy variant.
5. `backend/agents/iam_agent/Dockerfile` now inherits `api-ml` instead of reinstalling the full ML runtime on top of `api-base`.
6. `backend/services/model_gateway/Dockerfile` and `backend/agents/iam_agent/Dockerfile` install `git` only where Git-backed runtime flows still exist, instead of dragging that package into every Python launch image through the shared foundation.

## Verification

Commands executed:

- `bash ./scripts/supply_chain/build_launch_scope_images.sh --artifacts-dir artifacts/slice4d-pruned --image-tag slice4d-pruned --frontend-api-base /api --frontend-api-url /api --frontend-iam-url /api/v1/iam`
- `bash ./scripts/supply_chain/scan_launch_scope_images.sh --artifacts-dir artifacts/slice4d-pruned`

Evidence artifacts:

- `artifacts/slice4d-pruned/launch-image-build-summary.md`
- `artifacts/slice4d-pruned/launch-image-build-inspect.json`
- `artifacts/slice4d-pruned/launch-image-scan-summary.md`
- `artifacts/slice4d-pruned/launch-image-scan-summary.json`
- `artifacts/slice4d-pruned/launch-image-scans/`

## Result

The final built-image posture for the narrowed launch set is:

- `sentinelgrid/frontend:slice4d-pruned`: `0` high / critical findings
- `sentinelgrid/runtime-python:slice4d-pruned`: `6` high, `0` critical
- `sentinelgrid/api-base:slice4d-pruned`: `7` high, `0` critical
- `sentinelgrid/api-ml:slice4d-pruned`: `7` high, `0` critical
- `sentinelgrid/api_gateway:slice4d-pruned`: `7` high, `0` critical
- `sentinelgrid/orchestrator:slice4d-pruned`: `7` high, `0` critical
- `sentinelgrid/siem_agent:slice4d-pruned`: `7` high, `0` critical
- `sentinelgrid/iam_agent:slice4d-pruned`: `9` high, `0` critical
- `sentinelgrid/model_gateway:slice4d-pruned`: `9` high, `0` critical

This is a material improvement over the first built-image scan taken during this slice, which showed:

- `5` critical plus `179-180` high findings across the shared Python lineage
- `11` high findings in the frontend image

The current slice therefore removes all critical findings from the narrowed launch image set, fully clears the frontend runtime image, and leaves only a bounded set of no-fix high findings.

## Residual Exception Set

All remaining findings in `artifacts/slice4d-pruned/launch-image-scan-summary.json` currently report `FixedVersion: None`.

Approved residual exceptions are now recorded in `docs/archive/reference/platform/production-approved-exception-register-2026-04-16.md`:

- `EX-2026-04-18-01`: shared Debian runtime no-fix findings in the Python image lineage
- `EX-2026-04-18-02`: transitive `ecdsa` no-fix finding through `python-jose`
- `EX-2026-04-18-03`: Git-enabled IAM / model-gateway runtime findings (`libexpat1`, `libnghttp2-14`) on non-default Git-capable flows

These exceptions are bounded, reviewed, dated, and backed by compensating controls. None override an automatic `No-Go` condition because:

- there are no remaining critical dependency findings in the narrowed launch image set
- the affected findings are all no-fix highs
- the Git-specific residuals are limited to Git-capable flows outside the core default auth / dashboard path

## Decision

- Slice `4D` is complete for the narrowed launch scope.
- `G-08` is passed with approved exceptions.
- Phase 4 is complete.
- The next critical path item is `Phase 5 / Slice 5A`.
