# Phase 2 Platform Consolidation Closeout

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 15, 2026  
**Phase:** Phase 2 of the production remediation plan  
**Goal:** Finish platform consolidation, tighten the canonical launch boundary, and remove misleading product behavior from the operator surface

## Phase 2 Exit Summary

Phase 2 is now complete for the initial production SaaS launch boundary.

The codebase now reflects three explicit truths:

1. `frontend/` is the only canonical customer-facing operator plane.
2. The sold package model is canonical across signup, billing, and provisioning.
3. Launch-surface routes no longer fabricate live operator data when the tenant has no real data.

## What Closed In Phase 2

### 1. Canonical product contract

The launch package model is now normalized through shared product helpers and no longer depends on conflicting legacy aliases.

Closed in code:

- `backend/libs/sg_core/product_catalog.py`
- `frontend/src/lib/product/catalog.ts`
- IAM lead capture, payment, and provisioning flows now normalize `plan_tier`
- the signup flow now patches the lead before payment instead of silently relying on hidden defaults

Result:

- `plan_tier` is the source of truth
- legacy `protect_comply` aliases are normalized
- provisioning receives a consistent commercial contract

### 2. Canonical entity and evidence model

The shared story contract is now established for operator context.

Closed in code:

- `backend/libs/sg_core/entity_model.py`
- `frontend/src/lib/security/story.ts`
- alert and incident detail pages
- Security Graph contextual launch flow

Result:

- alerts and incidents expose the same normalized `entities`, `evidence`, and `story_domains`
- the Security Graph now launches from real story context instead of seeded demo attack paths

### 3. Launch-boundary cleanup on the dashboard surface

The main console no longer advertises or foregrounds routes that are out of scope for the day-one launch.

Closed in code:

- `frontend/src/components/layout/DashboardSidebar.tsx`
- `frontend/src/components/layout/DashboardHeader.tsx`
- `frontend/src/components/ai-chat/CommandPalette.tsx`
- `frontend/src/app/(dashboard)/dashboard/penetration-testing/page.tsx`
- `frontend/src/app/(dashboard)/dashboard/operations/page.tsx`

Result:

- `Pen Tests` is removed from the primary sidebar
- `Platform Operations` is removed from customer-facing header and command-palette discovery
- the penetration-testing route is now explicitly services-led instead of a fake self-serve SaaS module
- the platform-operations route is now explicitly internal and no longer presents placeholder metrics as if they were production truth

### 4. Demo-fallback removal from core operator routes

Several launch-surface routes previously invented queue items or attack paths when tenant data was empty. That behavior is now removed.

Closed in code:

- `frontend/src/app/(dashboard)/dashboard/alerts/page.tsx`
- `frontend/src/app/(dashboard)/dashboard/war-room/page.tsx`
- `frontend/src/app/(dashboard)/dashboard/security-graph/page.tsx`

Result:

- the alert queue stays empty until real detections exist
- War Room stays empty until real queue items exist
- Security Graph requires real source context and no longer renders seeded demo paths by default

This is a production-truth change, not just a cosmetic copy change.

## Why This Matters

Before this closeout, the operator plane still mixed production-facing workflows with demo-backed behavior. That would have created avoidable buyer risk:

- customers could believe detections existed when they did not
- internal placeholder routes were still discoverable from customer-facing surfaces
- out-of-scope offerings looked more launch-ready than they actually were

Phase 2 removes that ambiguity.

## Remaining Work Handed Off To Phase 3

Phase 2 closes boundary cleanup. It does not claim every route is fully productized.

Phase 3 still owns:

- replacing remaining stubbed or demo-backed workflows outside the canonical launch path
- completing real execution behind marketed response and automation flows
- deepening the `Now` queue and Security Graph beyond the current contextual story contract
- finishing productization work on beta or internal-only surfaces before any future launch expansion

Examples still intentionally deferred:

- partner console demo-backed tenant portfolio data
- non-launch IAM self-service demo fallbacks
- broader playbook execution hardening
- any future self-serve penetration-testing workflow

## Verification

Frontend regressions added or updated:

- `src/components/layout/__tests__/DashboardSidebar.test.tsx`
- `src/components/ai-chat/__tests__/CommandPalette.test.tsx`
- `src/app/(dashboard)/dashboard/alerts/__tests__/page.test.tsx`
- `src/app/(dashboard)/dashboard/war-room/__tests__/page.test.tsx`
- `src/app/(dashboard)/dashboard/security-graph/__tests__/page.test.tsx`
- `src/app/(dashboard)/dashboard/penetration-testing/__tests__/page.test.tsx`
- `src/app/(dashboard)/dashboard/operations/__tests__/page.test.tsx`

Test runs:

- `npm test -- --runInBand --watch=false src/components/layout/__tests__/DashboardSidebar.test.tsx src/components/ai-chat/__tests__/CommandPalette.test.tsx`
- `npm test -- --runInBand --watch=false --runTestsByPath src/app/(dashboard)/dashboard/war-room/__tests__/page.test.tsx src/app/(dashboard)/dashboard/security-graph/__tests__/page.test.tsx src/app/(dashboard)/dashboard/penetration-testing/__tests__/page.test.tsx src/app/(dashboard)/dashboard/operations/__tests__/page.test.tsx src/app/(dashboard)/dashboard/alerts/__tests__/page.test.tsx`

## Phase Gate Decision

For the initial SaaS launch boundary, Phase 2 is closed and Phase 3 can be treated as the next active execution gate.
