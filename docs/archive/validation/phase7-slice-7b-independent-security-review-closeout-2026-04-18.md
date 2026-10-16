# SentinelGrid Phase 7 Slice 7B Independent Security Review Closeout

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 18, 2026  
**Status:** Complete for the narrowed launch scope  
**Gate impact:** Slice `7B` exit gate passed; no unresolved independent critical finding remains against the narrowed launch boundary  
**Purpose:** Record the focused independent-style security review performed after the Phase 7A re-audit and document the resulting findings, fixes, and residuals

## Scope

This slice covered the narrowed launch package only.

The review focused on:

1. the live narrowed-launch frontend edge under HTTPS
2. launch-scope backend and frontend code paths using an external SAST engine
3. triage of independently surfaced findings against the actual narrowed launch boundary

This was executed as the “equivalent independent review” allowed by the Phase 7 plan. It was intentionally different from the earlier repo regression suites.

## Review Method

Two tool-driven review passes were used:

1. **OWASP ZAP baseline** against a disposable local HTTPS frontend target built from the current launch image
2. **Semgrep OWASP Top Ten** against the narrowed launch code paths via the standalone Semgrep container

Evidence roots:

- initial ZAP pass: `artifacts/phase7/independent-review/2026-04-18/slice7b-local/zap/`
- post-fix ZAP rerun: `artifacts/phase7/independent-review/2026-04-18/slice7b-local/zap-rerun/`
- initial Semgrep pass: `artifacts/phase7/independent-review/2026-04-18/slice7b-local/semgrep/semgrep-owasp-top-ten.json`
- post-fix Semgrep rerun: `artifacts/phase7/independent-review/2026-04-18/slice7b-local/semgrep-rerun/semgrep-owasp-top-ten.json`

## Initial Findings

### ZAP Initial Result

The first live ZAP pass produced no fail-level findings, but it did surface actionable warnings:

- medium: `CSP: Wildcard Directive`
- medium: `CSP: script-src unsafe-inline`
- medium: `CSP: style-src unsafe-inline`
- low: `Server` version leakage
- low: `X-Powered-By` leakage
- low: insufficient site isolation against Spectre

### Semgrep Initial Result

The first Semgrep pass produced `23` findings:

- `18` `ERROR` findings from `python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text`
- `5` `WARNING` findings from `python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure`

Most of these were concentrated in IAM code paths, with one launch-scope API gateway hit in `backend/services/api_gateway/app/api/routes_jobs.py`.

## Fixes Applied During The Review

The review was not treated as a read-only report. The following findings were hardened during the slice:

1. [frontend/next.config.mjs](../../../frontend/next.config.mjs) now sets `poweredByHeader: false` to remove framework disclosure.
2. [frontend/nginx.conf](../../../frontend/nginx.conf) now:
   - sets `server_tokens off`
   - adds `Cross-Origin-Opener-Policy`
   - adds `Cross-Origin-Resource-Policy`
   - removes the broad `https:` image source from the CSP, which cleared the wildcard-directive warning
3. [backend/services/api_gateway/app/api/routes_jobs.py](../../../backend/services/api_gateway/app/api/routes_jobs.py) no longer builds the `WHERE` clause with an f-string; it now uses a static parameterized query.
4. IAM log lines were sanitized in:
   - [backend/agents/iam_agent/app/api/auth.py](../../../backend/agents/iam_agent/app/api/auth.py)
   - [backend/agents/iam_agent/app/api/self_service.py](../../../backend/agents/iam_agent/app/api/self_service.py)
   - [backend/agents/iam_agent/app/middleware/admin_audit.py](../../../backend/agents/iam_agent/app/middleware/admin_audit.py)
   - [backend/agents/iam_agent/app/services/keycloak_admin_client.py](../../../backend/agents/iam_agent/app/services/keycloak_admin_client.py)
   - [backend/agents/iam_agent/app/services/token_validator.py](../../../backend/agents/iam_agent/app/services/token_validator.py)

## Post-Fix Result

### ZAP Rerun

The rerun removed the header-leak and wildcard-CSP findings entirely.

Remaining ZAP findings on the updated frontend image:

- medium: `CSP: script-src unsafe-inline` (`5` instances)
- medium: `CSP: style-src unsafe-inline` (`5` instances)
- low: `Insufficient Site Isolation Against Spectre Vulnerability` (`12` instances)
- low: `ZAP is Out of Date` (`1` instance, tool-side)
- informational: suspicious comments, modern web application, non-storable content, and a potential user-controllable HTML attribute on `/demo`

There were still:

- `0` fail-level findings
- `0` high / critical findings

### Semgrep Rerun

The rerun reduced the result set from `23` to `20` findings:

- `17` `ERROR` findings from `avoid-sqlalchemy-text`
- `3` `WARNING` findings from the logging rule

Important interpretation:

1. the only launch-scope API gateway finding was removed by the `routes_jobs.py` hardening
2. the remaining `avoid-sqlalchemy-text` findings are pattern-based raw-SQL warnings, not confirmed SQL injection findings
3. the remaining logging warnings are false positives against sanitized log lines that no longer record token bodies, response bodies, email addresses, user IDs, or client IDs

## Finding Disposition

### No Unresolved Independent Critical Finding

No independent critical or fail-level finding remains against the narrowed launch boundary.

That satisfies the Slice `7B` exit gate.

### Residual Medium / Low Findings

The remaining findings are not ignored; they are explicitly classified:

1. `script-src 'unsafe-inline'` and `style-src 'unsafe-inline'` remain medium-severity frontend CSP hardening items. They are not launch-blocking because the review did not identify an actual execution path or exploit chain, and the narrowed launch edge already enforces HTTPS, HSTS, `frame-ancestors 'none'`, `X-Content-Type-Options`, and the other Phase 1/3 controls. They should still be reduced in a post-launch CSP nonce/hash pass.
2. the Spectre/site-isolation warning is low severity and did not expose a tenant-isolation or auth-boundary break in the review. It remains a hardening item, not a launch blocker.
3. the remaining Semgrep `avoid-sqlalchemy-text` results are not confirmed SQLi defects in the narrowed launch path. The reviewed patterns use named bind parameters and static or allowlisted clause assembly. They should be refactored over time, but they do not constitute an unresolved independent critical finding.

## Verification

Commands executed:

- `docker run --rm --network phase7b-net ... ghcr.io/zaproxy/zaproxy:stable zap-baseline.py ...`
- `docker run --rm -v <repo>:/src returntocorp/semgrep:latest semgrep scan --config p/owasp-top-ten ...`
- `docker build -t sentinelgrid/frontend:slice7b-review ... frontend`
- `pytest backend/services/api_gateway/tests/test_jobs_routes_tenant_session.py -q` -> `3 passed`
- `pytest backend/agents/iam_agent/tests/test_auth_api.py -q` -> `13 passed`
- `python3 -m py_compile ...` over the touched backend files -> passed

Local verification limitation:

- `pytest backend/agents/iam_agent/tests/test_self_service.py -q` could not be collected in this workstation Python environment because `python-multipart` is missing. That is an environment dependency issue, not a regression caused by this slice.

## Decision

- Slice `7B` is complete for the narrowed launch scope.
- No unresolved independent critical finding remains against the narrowed launch boundary.
- Phase 7 should continue with `Slice 7C`.
