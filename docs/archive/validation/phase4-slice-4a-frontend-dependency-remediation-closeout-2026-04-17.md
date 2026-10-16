# Phase 4 Slice 4A Closeout: Frontend Dependency Remediation

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 17, 2026  
**Scope:** Narrowed launch scope frontend only  
**Decision:** Closed for the narrowed launch scope  
**Gate impact:** Frontend portion of `G-08` is now closed, but `G-08` remains open until the remaining launch-scope dependency slices complete

## Goal

Remove the known frontend production dependency findings that were still blocking the narrowed launch path.

## Repo-Backed Changes

### Upgraded vulnerable direct frontend packages

`frontend/package.json` and `frontend/package-lock.json` now move the narrowed launch frontend onto:

- `axios` `^1.15.0`
- `next` `^15.5.15`
- `yaml` `^2.8.3`
- `eslint-config-next` `^15.5.15`
- `recharts` `^3.8.1`

### Removed the remaining vulnerable transitive paths

- `recharts` no longer pulls the `lodash` runtime path that was carrying the remaining `high` frontend audit finding
- `frontend/package.json` now adds an `overrides` entry forcing `follow-redirects` to `1.16.0` so the `axios` transitive path resolves to the patched line

### Made the frontend audit sticky in CI

`.github/workflows/test.yml` now:

- runs the frontend job on Node `20`
- executes `npm audit --omit=dev --audit-level=high` after `npm ci`

That turns the frontend production dependency audit into a standing CI gate instead of a one-off manual check.

### Cleaned up the Next.js monorepo build warning

`frontend/next.config.mjs` now sets `outputFileTracingRoot` explicitly so Next 15 no longer guesses at the monorepo root from multiple lockfiles.

### Absorbed the surfaced Next 15 and chart-typing compatibility fixes

The dependency upgrades exposed a small number of real compatibility issues that are now closed in-repo:

- `frontend/src/app/(marketing)/demo/page.tsx`
  - updated to the async `searchParams` page-prop contract Next 15 expects
- `frontend/src/app/api/scans/[id]/route.ts`
- `frontend/src/app/api/v1/devices/[[...path]]/route.ts`
- `frontend/src/app/api/v1/roles/[[...path]]/route.ts`
  - updated to the async `params` route-handler contract Next 15 expects
- `frontend/src/components/campaigns/CampaignProgress.tsx`
- `frontend/src/components/compliance/ComplianceMetrics.tsx`
  - updated pie-chart label formatting to satisfy stricter `recharts` 3 typing around optional `percent`
- the known frontend test mocks that were blocking lint were also given explicit display names so the production build can complete

## Verification

### Production dependency audit

- `npm audit --omit=dev --audit-level=high --json`
- result: `0 high`, `0 critical`, `0 total`

### Dependency graph check

- `npm ls recharts lodash follow-redirects --all`
- result:
  - `recharts@3.8.1`
  - no remaining `lodash` runtime dependency path
  - `follow-redirects@1.16.0 overridden`

### Narrowed frontend regression suite

- `npx jest --runInBand --watch=false --runTestsByPath "src/app/(marketing)/login/__tests__/page.test.tsx" "src/app/api/auth/login/__tests__/route.test.ts" "src/components/onboarding/__tests__/OnboardingWizard.test.tsx" "src/components/dashboard/__tests__/OnboardingBanner.test.tsx" "src/components/onboarding/__tests__/StepTicketing.test.tsx" "src/app/(dashboard)/__tests__/layout.test.tsx" "src/components/layout/__tests__/DashboardSidebar.test.tsx" "src/components/layout/__tests__/DashboardHeader.test.tsx" "src/components/ai-chat/__tests__/CommandPalette.test.tsx"`
- result: `9 passed`, `30 passed`

### Focused compatibility regression suite

- `npx jest --runInBand --watch=false --runTestsByPath "src/app/(dashboard)/dashboard/incidents/[id]/__tests__/page.soc-case.test.tsx" "src/app/(dashboard)/dashboard/requests/[id]/__tests__/page.test.tsx" "src/components/onboarding/__tests__/OnboardingWizard.test.tsx"`
- result: `3 passed`, `8 passed`

### Production build verification

- `npm run build`
- result:
  - passed
  - Next 15 compiled, type-checked, generated static pages, and finalized build output successfully
  - the prior multiple-lockfile root warning is gone after setting `outputFileTracingRoot`

## Residuals

- A non-blocking `baseline-browser-mapping` staleness warning appeared during the build. It did not block the audit or the final production build.
- `G-08` remains open because the launch-scope backend dependency slices have not yet been closed.

## Decision

For the narrowed launch scope:

- Phase 4 Slice 4A is closed
- the frontend production dependency baseline no longer carries unresolved `high` or `critical` audit findings
- Phase 4 should continue with Slice 4B
