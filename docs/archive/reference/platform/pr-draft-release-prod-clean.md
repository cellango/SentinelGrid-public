# Release: prod-clean baseline, SentinelGuard, catalog seeds, IAM/SIEM/website updates

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Summary
- Swap legacy SQL migrations for Flyway-style `backend/migrations/V***` with updated seeds/detection versions; add tool registry/jobs plumbing (backend libs + job runner/scheduler + jobs API routes).
- Expand IAM/SIEM coverage: app assignments/catalog/auth/onboarding, detection rule versions, monitors, ingestion pipelines; new detection/playbook catalogs and detection rule service.
- Add SentinelGuard endpoint agent and ingest rationalizer service (SentinelGuard code, packer scripts, infra additions) plus gitleaks sidecar.
- Frontend dashboards and marketing site refresh (alerts/incidents/siem builders, IAM apps/policies, playbooks UI; new `website` app).
- CI/CD and infra: new GitHub workflows for build/push/deploy and terraform plan/apply, chart/Helm values, EKS modules, docker-compose updates.

## Database/migrations
- Legacy `backend/migrations/00x*` removed; new `backend/migrations/V041+` plus large detection/playbook seed files (notably `V057__update_detection_rule_versions_from_catalog.sql`).
- Confirm prod DB baseline matches the new Flyway numbering before applying; capture/execute a one-time baseline or manual migration if prod is behind the new baseline.

## Deployment notes
- Seed scripts updated (`backend/scripts/seed_*`, `backend/scripts/validate_catalog_content.py`); new pipelines/ISM apply scripts under `backend/services/ingestion_service/scripts`.
- Packer images updated for SentinelGuard; see `docs/archive/reference/platform/sentinelguard-packer-runbook.md` for image builds.

## Tests
- Not run in this draft. Recommended: `pytest backend/tests backend/agents/iam_agent/tests backend/tests/siem backend/tests/jobs`, targeted Selenium if feasible, and frontend/website smoke (`npm run lint && npm run build` in `frontend` and `website`).

## Merge strategy
- Open PR from `release/prod-clean` to `main`. After DB baseline decision and targeted tests, fast-forward merge to `main`, tag the release, and deploy from the tag.
- If you keep a `dev` branch, rebase it from `main` after the merge.
