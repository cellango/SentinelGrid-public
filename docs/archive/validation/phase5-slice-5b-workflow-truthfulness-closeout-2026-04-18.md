# Phase 5 Slice 5B Closeout: Workflow Truthfulness Cleanup

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 18, 2026  
**Scope:** Narrowed launch scope  
**Decision:** Closed for the narrowed launch scope  
**Gate impact:** `G-09` is now passed for the narrowed launch scope

## Goal

Remove or gate launch-visible workflows that still relied on stub, mock, placeholder, or synthetic behavior.

## Repo-Backed Changes

### Onboarding no longer marks success when integration health is not real

`backend/agents/iam_agent/app/api/onboarding.py` now fails closed for the launch onboarding path:

- endpoint coverage is no longer auto-completed from placeholder health
- `connect-appsec` only marks completion when the saved integration health is `healthy`
- `connect-ticketing` only marks completion when the handoff validates as `healthy`

The matching canonical frontend onboarding steps were tightened in:

- `frontend/src/components/onboarding/StepEndpointAgent.tsx`
- `frontend/src/components/onboarding/StepAppSec.tsx`

Those screens now stay on the current step when the backend reports degraded or missing health instead of silently advancing.

### Snapshot and posture APIs no longer fabricate launch-visible security data

The launch operator views now proxy real upstream results instead of synthesizing local stand-ins:

- `backend/services/api_gateway/app/api/routes_orchestrator.py`
  - `security-snapshot` now proxies the real orchestrator path
- `backend/services/api_gateway/app/api/routes_posture.py`
  - `dashboard-snapshot` now proxies the orchestrator dashboard snapshot and fails closed if `cloud_posture` is missing

That removed launch-visible synthetic response data from the main operator workflow.

### AI analysis fallbacks are now explicit unavailable states, not invented guidance

`backend/services/orchestrator/app/services/model_gateway_client.py` and `backend/services/orchestrator/app/services/phishing_analyzer.py` now return explicit unavailable or manual-review states when the AI analysis path is missing or malformed.

That means:

- snapshot analysis no longer invents posture or risk conclusions from partial context
- phishing analysis no longer fabricates a classification when the AI path is unavailable
- downstream phishing records now stay in an honest `in_review` style state until a real analysis exists

### Unsupported AI Shield provider calls no longer return mock responses

The direct unsupported-provider paths in:

- `SentinelGridAIShield/gateway/internal/providers/anthropic.go`
- `SentinelGridAIShield/gateway/internal/providers/local.go`

now return explicit unsupported-provider errors. They no longer emit mock completions that could be mistaken for a real supported provider path.

### Playbooks no longer silently invent a stored workflow graph

`backend/services/api_gateway/app/api/routes_playbooks.py` previously serialized a synthetic starter graph whenever a playbook had no stored workflow.

That route now:

- returns `workflow: null` when no stored graph exists
- adds explicit `workflow_status` and `workflow_message`
- stops cloning a placeholder graph into tenant-owned playbooks
- fails validation when a stored workflow is missing instead of validating the synthetic starter graph

The editor in `frontend/src/app/(dashboard)/dashboard/playbooks/[id]/edit/page.tsx` now shows a clear workflow-visibility notice and only uses a local starter graph inside the editor, not as if it were the stored workflow.

### Legacy IAM pages that still depended on placeholder outputs are no longer marketed launch workflows

Two direct dashboard surfaces remained inconsistent with the narrowed launch promise:

- `frontend/src/app/(dashboard)/dashboard/iam/reports/page.tsx`
  - this route previously generated placeholder IAM CSV exports
- `frontend/src/app/(dashboard)/dashboard/iam/devices/page.tsx`
  - this route previously mixed sample-device loading and placeholder device security posture

Both routes now render explicit `LaunchBoundaryNotice` pages instead of behaving like normal production workflows.

To prevent them from being treated as normal launch destinations:

- `frontend/src/components/layout/DashboardSidebar.tsx` no longer advertises `IAM Reports`
- `frontend/src/app/(dashboard)/dashboard/iam/layout.tsx` no longer advertises the admin `Devices` page as a default IAM navigation item

## Verification

### IAM onboarding truthfulness

- `PYTHONPATH=backend/agents/iam_agent:backend/libs pytest backend/agents/iam_agent/tests/test_onboarding_status_api.py backend/agents/iam_agent/tests/test_onboarding_tenant_session.py -q`
- result: `14` passed

- `PYTHONPATH=backend/agents/iam_agent:backend/libs pytest backend/agents/iam_agent/tests/test_onboarding_ticketing_connection.py -q`
- result: `10` passed

### API gateway route truthfulness

- `PYTHONPATH=backend/services/api_gateway:backend/libs pytest backend/services/api_gateway/tests/test_orchestrator_routes_tenant_session.py backend/services/api_gateway/tests/test_posture_routes_tenant_session.py -q`
- result: `12` passed

- `PYTHONPATH=backend/services/api_gateway:backend/libs pytest backend/services/api_gateway/tests/test_playbooks_routes_tenant_session.py -q`
- result: `11` passed

### Orchestrator AI fallback truthfulness

- `PYTHONPATH=backend/services/orchestrator:backend/libs pytest backend/services/orchestrator/tests/test_model_gateway_client.py -q`
- result: `3` passed

### AI Shield unsupported-provider behavior

- `GOCACHE=/path/to/SentinelGrid/.cache/go-build go test ./...`
- working directory: `SentinelGridAIShield/gateway`
- result: passed

### Frontend workflow and launch-boundary verification

- `npm test -- --runTestsByPath src/components/onboarding/__tests__/StepEndpointAgent.test.tsx src/components/onboarding/__tests__/StepAIShield.test.tsx src/components/onboarding/__tests__/StepAppSec.test.tsx`
- result: `3` suites passed, `6` tests passed

- `npm test -- --runTestsByPath src/components/layout/__tests__/DashboardSidebar.test.tsx`
- result: `1` suite passed, `2` tests passed

- `npx next lint --file src/app/'(dashboard)'/dashboard/iam/reports/page.tsx --file src/app/'(dashboard)'/dashboard/iam/devices/page.tsx --file src/app/'(dashboard)'/dashboard/playbooks/'[id]'/edit/page.tsx --file src/components/layout/DashboardSidebar.tsx --file src/app/'(dashboard)'/dashboard/iam/layout.tsx --file src/components/layout/__tests__/DashboardSidebar.test.tsx`
- result: no ESLint warnings or errors

### Canonical route-entry sweep

A repo sweep over the canonical dashboard navigation no longer finds normal launch navigation into:

- `/dashboard/iam/reports`
- `/dashboard/iam/devices`

Those routes still exist by direct URL, but they now resolve to explicit launch-boundary notices instead of silently placeholder-backed workflows.

## Residuals

- Legacy placeholder implementations still exist in non-launch backend endpoints such as `backend/agents/iam_agent/app/api/reports.py` and parts of `backend/agents/iam_agent/app/api/devices.py`. They are no longer part of the marketed launch workflow, but they must be remediated or hard-gated before any future scope expansion.
- Some non-launch helper paths still contain placeholder or fallback wording outside the canonical narrowed launch flow.
- `G-10` remains open.

## Decision

For the narrowed launch scope:

- Phase 5 Slice 5B is closed
- `G-09` is passed
- no marketed launch workflow now silently falls back to stub, mock, or placeholder behavior
- Phase 5 should continue with `Slice 5C`
