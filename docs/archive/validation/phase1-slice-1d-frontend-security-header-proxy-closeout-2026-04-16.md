# Phase 1 Slice 1D Frontend Security Header And Proxy Cleanup Closeout

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 16, 2026  
**Status:** Complete for the current narrowed launch scope  
**Owner:** Clement Ellango

## Purpose

Close the remaining frontend edge behavior that could reintroduce permissive cross-origin handling after the BFF/session-boundary changes.

## Scope Closed In This Slice

- removal of wildcard dev-style preflight behavior from the production-facing frontend proxy
- explicit browser security headers for the narrowed launch path
- same-origin proxy coverage for browser-visible routes that were still calling internal service hosts directly
- cookie-to-bearer resolution at the frontend edge for proxied service routes that still expect bearer auth

## Code Areas Closed

- `frontend/nginx.conf`
- `frontend/src/lib/api/ai-chat.ts`
- `frontend/src/lib/api/auth.ts`
- `frontend/src/lib/api/leads.ts`
- `frontend/src/lib/api/onboarding.ts`

## What Changed

1. `frontend/nginx.conf` no longer serves the old wildcard `OPTIONS` preflight response on `/api/`.
2. The frontend edge now sets explicit `Content-Security-Policy`, `Referrer-Policy`, and `Permissions-Policy` headers in addition to the existing HSTS, frame, and content-type protections.
3. The frontend edge now strips proxied `Access-Control-Allow-*` headers so upstream service CORS behavior is not reflected back out as a browser-facing policy on the narrowed launch path.
4. Browser-facing routes that were still bypassing the edge now have same-origin proxy coverage:
   - `/internal/iam/chat`
   - `/api/v1/auth/signup`
   - `/api/v1/auth/reset-password-direct`
   - `/api/v1/leads/*`
   - `/api/v1/payment/*`
   - `/api/v1/marketing/*`
   - `/api/v1/connectors/*`
   - `/api/v1/rules/*`
5. The edge now resolves `Authorization` from the existing `access_token` cookie when the browser does not send a bearer header, which keeps the cookie-backed frontend posture intact on those proxied paths.
6. Browser-side API helpers for IAM chat, public signup, lead capture, and onboarding connector/detection flows now prefer current-origin routes instead of browser calls to internal service hosts.

## Verification Evidence

### Frontend Proxy Validation

- `nginx -t -p /tmp/nginx-sentinelgrid -c /tmp/nginx-sentinelgrid/conf/nginx.test.conf -g 'error_log stderr notice; pid /tmp/nginx-sentinelgrid/nginx.pid;'`
  - result: syntax ok and test successful against a disposable wrapper config with local temporary certs

### Focused Frontend Lint Evidence

- `npx next lint --file src/lib/api/ai-chat.ts --file src/lib/api/auth.ts --file src/lib/api/leads.ts --file src/lib/api/onboarding.ts`
  - result: no ESLint warnings or errors

### Targeted Regression Evidence

- `npm test -- --runTestsByPath 'src/components/dashboard/__tests__/OnboardingBanner.test.tsx' 'src/components/marketing/__tests__/DemoRequestForm.test.tsx' 'src/components/ai-chat/__tests__/CommandPalette.test.tsx' 'src/app/(dashboard)/__tests__/layout.test.tsx'`
  - result: `4` suites passed, `11` tests passed

### Source Sweep Evidence

- `rg -n 'http://localhost:8000|http://localhost:8005|http://localhost:8006|http://iam_agent:8000|http://api_gateway:8000' frontend/src/app frontend/src/components -g '*.{ts,tsx}'`
  - result: remaining matches are limited to Next.js server route handlers and tests, not active browser page/component call sites

## Residual Risk After Closeout

- The CSP still allows `'unsafe-inline'` for scripts and styles. That is intentional for now because the current Next.js runtime, theme bootstrap script, and several UI components still rely on inline behavior. A later hardening pass should move this to a nonce- or hash-based CSP.
- This slice fixes the browser-side edge and proxy inconsistency, but it does not close every backend tenant-trust issue behind connector or detection routes. Those deeper tenant/auth trust boundaries remain Phase 2 work.
- Some shared frontend libraries still retain server-side fallback URLs for non-browser execution paths. The narrowed launch browser path now prefers same-origin routes, but the fallback constants still exist.

## Exit Decision

`Slice 1D` is closed for the current narrowed launch scope.

The frontend edge no longer reintroduces wildcard cross-origin behavior, and the remaining launch-visible browser flows covered in this slice now use the same-origin proxy model. Phase 2 began with `Slice 2A`.
