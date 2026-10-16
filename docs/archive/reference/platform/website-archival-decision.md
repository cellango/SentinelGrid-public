# Website Archival Decision

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** March 26, 2026  
**Status:** Approved

## Decision

`frontend/` is the only canonical frontend for SentinelGrid product and marketing work.

`website/` is now an archived legacy reference app. It remains in the repository temporarily for migration support and historical reference, but it is no longer an active product surface.

## What This Means

- All net-new marketing, onboarding, pricing, trust, and product-console work belongs in `frontend/`.
- `frontend/src/app/(marketing)/` is the canonical marketing route tree.
- `frontend/src/app/(dashboard)/` is the canonical authenticated product route tree.
- `website/` should not be used for new features, experiments, or route additions.

## Allowed Changes In `website/`

Only the following work is in scope:

- archival labeling and documentation updates
- migration support while equivalent surfaces are confirmed in `frontend/`
- dependency verification needed to keep the legacy app inspectable
- final removal prep

## Disallowed Changes In `website/`

The following work should not be done in `website/`:

- new routes
- new product or marketing features
- new onboarding flows
- new shared UI components
- new auth or session logic
- new analytics, pricing, or trust flows

## Removal Path

`website/` can be removed once all of the following are true:

1. No active traffic, docs, or operator flows depend on `website/`.
2. Canonical documentation consistently points to `frontend/` as the only active frontend.
3. Any reusable assets worth keeping have already been migrated into `frontend/`.
4. Remaining closeout work that referenced `website/` has been recreated in `frontend/` or explicitly descoped.

## Working Rule

If a task touches user-facing UI and you are deciding between `frontend/` and `website/`, the answer is `frontend/` unless the task is explicitly archival or removal-related.
