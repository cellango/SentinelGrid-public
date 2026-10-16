# First-Time Experience Must-Haves (Tasks)

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Task list
- [x] Backend API tests: onboarding status (steps, resume pointer, readiness flags) and `recheck-health` targets (`idp`, `endpoint`, `cloud`, `git`, `appsec`, `ai`, `ticketing`).
- [x] Frontend tests: RTL/unit for dashboard banner visibility/resume routing and wizard step completion seeding from backend `steps`.
- [x] Selenium E2E: first login banner visible; partial completion resumes at first incomplete step; header gear opens onboarding at correct step; People & Access readiness banner appears on dashboard and People page; per-step test buttons (IdP, cloud, git, endpoint) update status.
- [x] Demo sanity: ensure onboarding_progress for demo reflects reality (leave git/endpoint false if not connected; backfill if data exists); verify banner behavior aligns.

## Notes
- Backend/state already tenant-aware and supports `recheck-health` for idp/endpoint.
- Frontend banner and wizard consume backend `steps` and show per-step test status; gear icon present.

## Iteration plan
1. Add backend API tests for status + recheck-health.
2. Add frontend RTL for banner/wizard.
3. Add Selenium flows for critical UX.
4. Validate demo status and adjust onboarding_progress if needed.
