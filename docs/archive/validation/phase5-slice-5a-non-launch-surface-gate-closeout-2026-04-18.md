# Phase 5 Slice 5A Closeout: Gate Or Remove Non-Launch Surfaces

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 18, 2026  
**Scope:** Narrowed launch scope frontend only  
**Decision:** Closed for the narrowed launch scope  
**Gate impact:** Reduces `G-09` launch-boundary risk, but `G-09` remains open until the broader workflow truthfulness audit in Slice `5B` completes

## Goal

Make it materially harder for a launch buyer to enter dashboard routes that contradict the frozen launch boundary.

## Repo-Backed Changes

### Gated the partner route instead of shipping a demo-backed console

`frontend/src/app/(dashboard)/dashboard/partner/page.tsx` no longer renders the prior partner console with demo tenant portfolio data.

It now renders an explicit launch-boundary notice that states:

- partner workflows are qualified sales-assisted scope
- the route is not part of the default self-serve launch
- the narrowed launch stays centered on the single-tenant operator plane

### Gated internal revenue analytics instead of exposing them as a normal product surface

`frontend/src/app/(dashboard)/dashboard/operations/marketing-funnel/page.tsx` no longer renders customer-visible revenue and activation analytics.

It now renders an internal-route notice so the shipped tenant-facing console no longer presents internal commercial analytics as a normal destination.

### Tightened the AI Shield standalone setup path

`frontend/src/app/(dashboard)/dashboard/ai-security/setup/page.tsx` no longer behaves like a broad self-serve setup guide with code samples and separate AI-console framing.

It now renders a controlled-add-on launch-boundary notice that:

- sends users to `/onboarding`
- points evidence review back to `/dashboard/ai-governance`
- states clearly that unsupported providers and standalone AI management surfaces remain outside the default launch promise

### Removed remaining easy entry points into non-launch surfaces

The canonical frontend now stops advertising the non-launch routes through normal dashboard shortcuts:

- `frontend/src/components/ai-chat/CommandPalette.tsx`
  - removed the `Partner Console` route shortcut
- `frontend/src/components/layout/DashboardHeader.tsx`
  - removed the user-menu admin shortcut to partner workflows
  - changed partner-context exit back to `/dashboard/now` instead of sending users into the partner route
- `frontend/src/app/(dashboard)/dashboard/operations/page.tsx`
  - stopped linking deeper into partner and revenue-only routes
- `frontend/src/app/(dashboard)/dashboard/components/AiRiskSummaryPanel.tsx`
- `frontend/src/app/(dashboard)/dashboard/ai-security/apps/page.tsx`
- `frontend/src/app/(dashboard)/dashboard/ai-security/policies/page.tsx`
  - now send the user back to onboarding or governed launch-safe surfaces instead of deeper standalone AI routes

## Verification

### Focused launch-boundary regression suite

- `npm test -- --runTestsByPath 'src/app/(dashboard)/dashboard/ai-security/__tests__/launch-boundary.test.tsx' 'src/app/(dashboard)/dashboard/operations/__tests__/page.test.tsx' 'src/app/(dashboard)/dashboard/operations/marketing-funnel/__tests__/page.test.tsx' 'src/app/(dashboard)/dashboard/partner/__tests__/page.test.tsx' 'src/app/(dashboard)/dashboard/penetration-testing/__tests__/page.test.tsx' 'src/components/layout/__tests__/DashboardHeader.test.tsx' 'src/components/ai-chat/__tests__/CommandPalette.test.tsx'`
- result: `7` suites passed, `13` tests passed

### Focused lint verification

- `npx next lint --file src/app/'(dashboard)'/dashboard/ai-security/setup/page.tsx --file src/app/'(dashboard)'/dashboard/ai-security/apps/page.tsx --file src/app/'(dashboard)'/dashboard/ai-security/policies/page.tsx --file src/app/'(dashboard)'/dashboard/components/AiRiskSummaryPanel.tsx --file src/app/'(dashboard)'/dashboard/operations/page.tsx --file src/app/'(dashboard)'/dashboard/operations/marketing-funnel/page.tsx --file src/app/'(dashboard)'/dashboard/partner/page.tsx --file src/components/layout/DashboardHeader.tsx --file src/components/ai-chat/CommandPalette.tsx`
- result: no ESLint warnings or errors

### Canonical frontend route-entry sweep

A repo search over the canonical frontend no longer finds runtime links from launch-facing dashboard navigation into:

- `/dashboard/partner`
- `/dashboard/operations/marketing-funnel`

The remaining `ai-security/setup` references are gated launch-boundary pages or tests, not launch-primary navigation.

### Non-canonical console ambiguity sweep

A repo sweep found no canonical frontend routing or integration references that would make `website/` or `SentinelGridPostureAgent/frontend/` appear to be the customer-facing launch console.

## Residuals

- The gated routes still exist by direct URL, but they now resolve to explicit launch-boundary notices rather than broad or demo-backed product surfaces.
- `Slice 5B` still needs to audit other launch-visible stub, mock, and placeholder execution paths beyond pure route exposure.
- `G-09` is not closed by this slice alone.

## Decision

For the narrowed launch scope:

- Phase 5 Slice 5A is closed
- the canonical frontend no longer advertises partner, internal revenue, or standalone AI setup routes as normal launch workflows
- Phase 5 should continue with Slice 5B
