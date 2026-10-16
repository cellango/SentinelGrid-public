# Phase 1 Slice 1B BFF / Session Boundary Closeout

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 16, 2026  
**Status:** Complete for the current narrowed launch scope  
**Owner:** Clement Ellango

## Purpose

Close the remaining browser-side bearer-token handling in the launch-critical frontend so the narrowed launch path relies on cookie-backed session semantics instead of client-constructed access-token headers.

## Scope Closed In This Slice

- sanitized auth BFF responses instead of returning raw tokens to browser code
- same-origin protection on cookie-mutating auth routes
- non-secret frontend session marker instead of browser-held bearer tokens
- API gateway compatibility for cookie-backed requests where the browser sends no `Authorization` header
- removal of the remaining `Authorization: Bearer ${token}` construction from launch-critical dashboard and IAM pages

## Code Areas Closed

- `frontend/src/components/iam/UserOnboardingWizard.tsx`
- `frontend/src/components/dashboard/NowDashboardPageContent.tsx`
- `frontend/src/app/(dashboard)/dashboard/iam/devices/page.tsx`
- `frontend/src/app/(dashboard)/dashboard/iam/my-devices/page.tsx`
- `frontend/src/app/(dashboard)/dashboard/iam/api-keys/page.tsx`
- `frontend/src/app/(dashboard)/dashboard/iam/privileged-access/page.tsx`
- `frontend/src/app/(dashboard)/dashboard/iam/reports/page.tsx`
- `frontend/src/app/(dashboard)/dashboard/iam/security-events/page.tsx`
- `frontend/src/app/(dashboard)/dashboard/iam/apps/catalog/page.tsx`
- `frontend/src/app/(dashboard)/dashboard/iam/identity-providers/page.tsx`
- `frontend/src/app/(dashboard)/dashboard/iam/people/page.tsx`
- `frontend/src/app/(dashboard)/dashboard/iam/my-profile/page.tsx`
- `frontend/src/app/(dashboard)/dashboard/iam/organization/page.tsx`
- `frontend/src/app/(dashboard)/dashboard/iam/my-account/page.tsx`
- `frontend/src/app/(dashboard)/dashboard/iam/certificates/page.tsx`
- `frontend/src/app/(dashboard)/dashboard/iam/certificates/[id]/page.tsx`
- `frontend/src/app/(dashboard)/dashboard/iam/certificates/enroll/page.tsx`

## What Changed

1. Remaining launch-critical pages no longer build browser-visible bearer headers from `useAuth().token`.
2. Raw same-origin `fetch` calls now use cookie-backed session semantics with `credentials: 'include'` where explicit fetch helpers remain.
3. Pages that only needed auth as a readiness gate now use `isAuthenticated` rather than carrying token state through the component tree.
4. Shared organization, onboarding, self-service, IAM portal, and certificate flows remain operable without browser access-token handling in the page layer.

## Verification Evidence

### Static Search Evidence

The following searches returned no matches after the slice closed:

- `rg -n 'Bearer \\$\\{token\\}' frontend/src/app frontend/src/components -g '*.{ts,tsx}'`
- `rg -n 'const \\{ token \\} = useAuth\\(|const \\{ token, user \\} = useAuth\\(|const \\{ tenantId, token \\} = useAuth\\(' frontend/src/app frontend/src/components -g '*.{ts,tsx}'`
- `rg -n 'enabled: !!token' frontend/src/app frontend/src/components -g '*.{ts,tsx}'`

### Targeted Test Evidence

- `npm test -- --runTestsByPath src/app/api/auth/login/__tests__/route.test.ts src/app/api/auth/refresh/__tests__/route.test.ts src/app/api/auth/logout/__tests__/route.test.ts src/app/api/auth/me/__tests__/route.test.ts src/middleware.test.ts`
  - result: `5` suites passed, `16` tests passed
- `pytest backend/services/api_gateway/tests/test_auth_middleware.py -q`
  - result: `13` tests passed

### Focused Frontend Lint Evidence

- `npx next lint --file 'src/components/iam/UserOnboardingWizard.tsx' --file 'src/components/dashboard/NowDashboardPageContent.tsx' --file 'src/app/(dashboard)/dashboard/iam/devices/page.tsx' --file 'src/app/(dashboard)/dashboard/iam/my-devices/page.tsx' --file 'src/app/(dashboard)/dashboard/iam/api-keys/page.tsx' --file 'src/app/(dashboard)/dashboard/iam/privileged-access/page.tsx' --file 'src/app/(dashboard)/dashboard/iam/reports/page.tsx' --file 'src/app/(dashboard)/dashboard/iam/security-events/page.tsx' --file 'src/app/(dashboard)/dashboard/iam/apps/catalog/page.tsx' --file 'src/app/(dashboard)/dashboard/iam/identity-providers/page.tsx' --file 'src/app/(dashboard)/dashboard/iam/people/page.tsx' --file 'src/app/(dashboard)/dashboard/iam/my-profile/page.tsx' --file 'src/app/(dashboard)/dashboard/iam/organization/page.tsx' --file 'src/app/(dashboard)/dashboard/iam/my-account/page.tsx' --file 'src/app/(dashboard)/dashboard/iam/certificates/page.tsx' --file 'src/app/(dashboard)/dashboard/iam/certificates/[id]/page.tsx' --file 'src/app/(dashboard)/dashboard/iam/certificates/enroll/page.tsx'`
  - result: no ESLint warnings or errors

## Residual Risk After Closeout

- `frontend/src/lib/api/client.ts` and `frontend/src/lib/auth/session.ts` still support the non-secret session-marker compatibility path for shared browser clients.
- `backend/services/api_gateway/app/main.py` still carries `AuthCookieMiddleware` because shared clients may still send the session marker during the transition period.
- That remaining compatibility layer is not a bearer-token exposure issue, but it should be narrowed further in later cleanup once the shared client path is explicitly reduced.

## Exit Decision

`Slice 1B` is closed for the current narrowed launch scope.

The browser-side launch-critical path no longer depends on raw bearer-token handling. Phase 1 should continue with `Slice 1C`.
