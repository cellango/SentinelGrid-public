# SentinelGrid Approved Exception Register

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 16, 2026  
**Status:** Active approved-exception register  
**Purpose:** Provide the single canonical register for any residual production exception that is explicitly approved during the go-readiness program

## How To Use This Register

- Add rows only after the exception satisfies `docs/archive/reference/platform/production-risk-exception-policy-2026-04-16.md`.
- If an issue is not in this register, it is not an approved exception.
- Expired exceptions must be treated as open blockers until they are either remediated or re-approved.

## Register

| Exception ID | Status | Gate / Area | Affected Scope | Direct Owner | Rationale | Compensating Controls | Created | Review Date | Expiration | Final Approver | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EX-2026-04-18-01 | Approved | `G-08` / shared Python image lineage | `runtime-python`, `api-base`, `api-ml`, `api_gateway`, `orchestrator`, `siem_agent`, plus inherited runtime layers | Clement Ellango | The remaining Debian `ncurses` / `systemd` findings in the narrowed launch image set currently report no fixed version in Trivy and remain after the shared runtime was reduced and rebuilt. They do not affect trust boundaries directly and no critical findings remain. | non-root containers, read-only runtime hardening from Phase 3, network policy containment, HTTPS-only public ingress, weekly image-scan review, dated expiration | April 18, 2026 | April 25, 2026 | May 9, 2026 | Clement Ellango | `docs/archive/validation/phase4-slice-4d-base-image-and-image-scan-discipline-closeout-2026-04-18.md`; `artifacts/slice4d-pruned/launch-image-scan-summary.md`; `artifacts/phase7/re-audit/2026-04-18/slice7a-local/launch-images/launch-image-scan-summary.md` |
| EX-2026-04-18-02 | Approved | `G-08` / shared auth dependency chain | `api-base`, `api-ml`, `api_gateway`, `orchestrator`, `siem_agent`, `iam_agent`, `model_gateway` | Clement Ellango | `ecdsa 0.19.2` is pulled transitively through `python-jose`, and Trivy reports no known patched version. The narrowed launch auth path validates Keycloak tokens through `PyJWT` RSA / JWKS handling in `backend/agents/iam_agent/app/services/token_validator.py`, not ECDSA private-key signing. | RS256 / JWKS validation path, no ECDSA signing flow on the narrowed launch auth path, weekly review, explicit expiration | April 18, 2026 | April 25, 2026 | May 9, 2026 | Clement Ellango | `backend/agents/iam_agent/app/services/token_validator.py`; `docs/archive/validation/phase4-slice-4d-base-image-and-image-scan-discipline-closeout-2026-04-18.md`; `artifacts/slice4d-pruned/launch-image-scan-summary.md`; `artifacts/phase7/re-audit/2026-04-18/slice7a-local/launch-images/launch-image-scan-summary.md` |
| EX-2026-04-18-03 | Approved | `G-08` / Git-capable runtime flows | `iam_agent`, `model_gateway` | Clement Ellango | `libexpat1` and `libnghttp2-14` appear only in the Git-capable IAM / model-gateway images after the shared base was narrowed. Those findings currently report no fixed version and are tied to Git-backed provider / ingestion flows that are not the default narrowed self-serve launch promise. | issue is limited to Git-capable service images, not the default public auth / dashboard path; non-root runtime; network policy containment; weekly review; expiration gate | April 18, 2026 | April 25, 2026 | May 9, 2026 | Clement Ellango | `docs/archive/validation/phase4-slice-4d-base-image-and-image-scan-discipline-closeout-2026-04-18.md`; `artifacts/slice4d-pruned/launch-image-scan-summary.md`; `artifacts/phase7/re-audit/2026-04-18/slice7a-local/launch-images/launch-image-scan-summary.md` |

## Approved Exception Notes

### EX-2026-04-18-01

- not launch-disqualifying because no critical findings remain, no fix is currently published, and the issue sits behind hardened container/runtime controls rather than on a trust-boundary bug
- revoke the exception if Debian publishes a fixed version or if a different shared runtime image eliminates the affected packages
- close it by adopting patched distro packages or replacing the affected shared runtime lineage

### EX-2026-04-18-02

- not launch-disqualifying because the narrowed launch auth path uses `PyJWT` RSA / JWKS validation rather than ECDSA private-key signing
- revoke the exception if `ecdsa` publishes a fixed release, `python-jose` drops the vulnerable chain, or the code begins relying on ECDSA signing on the launch path
- close it by removing the transitive dependency or moving fully to a patched non-`ecdsa` JWT stack

### EX-2026-04-18-03

- not launch-disqualifying because the affected packages are limited to Git-capable IAM / model-gateway runtime flows outside the default narrowed self-serve launch promise
- revoke the exception if Git-backed flows become part of the default launch promise without deeper remediation
- close it by gating/removing those flows from the launch package, switching to a non-CLI Git implementation, or adopting patched distro packages

## Current Interpretation

As of April 18, 2026 after the Phase 7 Slice 7A re-audit:

- the register contains three approved `G-08` exceptions tied to the Phase 4 Slice 4D closeout and reaffirmed by the fresh `slice7a-reaudit` built-image scan
- no approved exception overrides an automatic `No-Go` condition
- any additional residual exception still must be added here before it is valid
