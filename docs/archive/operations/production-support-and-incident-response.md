# Production Support And Incident Response

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Purpose

Define the founder-led support, activation, and incident-response workflow for the narrowed launch scope.

## Launch Support Model

- Launch support is currently a one-person operating model.
- The named owner across Product, Security, Platform, IAM, and Support is `Clement Ellango`, per `docs/PRODUCTION_OWNER_MATRIX_2026-04-15.md`.
- AI assistance may help draft notes or summarize evidence, but final severity, communication, rollback, and disclosure decisions remain human decisions.
- `support@sentinelgrid.ai` is the primary customer-facing intake path for launch.
- This runbook does not imply a staffed 24/7 SOC or blanket SLA. Any stronger response commitment must be explicit in contract or guided-review terms.

## Internal Handling Targets

These are internal launch operating targets, not public SLA claims:

- `Sev-1`
  - first acknowledgment target: 15 minutes
  - first customer update target: 30 minutes
  - containment or rollback decision target: 60 minutes
- `Sev-2`
  - first acknowledgment target: 4 business hours
  - first customer update target: same business day
- `Sev-3`
  - first acknowledgment target: next business day

## First Customer Activation Workflow

The first customer activation path must stay aligned to `docs/archive/reference/platform/phase5-first-value-dry-run-2026-04-16.md` and `docs/PHASE5_SUPPORT_AND_ACTIVATION_REHEARSAL_2026-04-16.md`.

Default launch activation path:

1. confirm the package is `Protect + Defend` or another approved launch-scope variant
2. confirm the default rollout shape: Microsoft 365 / Entra plus AWS first
3. record tenant name, primary customer contact, target start time, and first-value goal
4. drive onboarding until normalized findings appear in the shared queue
5. record first-value timestamp and any launch-boundary qualifications
6. if first value does not appear on time, convert the issue into a formal support intake instead of improvising over email or chat

## Support Intake Record

Every launch-scope support intake must capture:

- reporter name and contact
- tenant name and tenant ID
- package / launch path
- issue start timestamp in UTC
- affected workflow
- exact failing route or endpoint if known
- request ID or correlation ID if known
- recent release, rollback, or config change if applicable
- initial severity assessment
- current customer-visible impact

Suggested intake skeleton:

```text
Reporter:
Customer:
Tenant ID:
Launch package:
Issue started at (UTC):
Affected workflow:
Route / endpoint:
Request ID / correlation ID:
Recent change:
Initial severity:
Current customer impact:
```

## Severity Model

- `Sev-1`: customer-facing outage, suspected tenant isolation failure, suspected data exposure
- `Sev-2`: major degraded workflow without confirmed data exposure
- `Sev-3`: localized defect or lower-impact operational issue

## First 15 Minutes

1. Record the start time and reporter.
2. Classify severity.
3. Capture request IDs, affected tenant IDs, and failing endpoints.
4. Check `/ready` for gateway, IAM, SIEM, orchestrator, model-gateway, and ingestion.
5. Check whether a release, rollback, connector change, or secret rotation happened recently.
6. Decide whether to contain, roll back, or continue investigating live.

## Activation Failure Branches

If the issue occurs during first customer activation, use these defaults before inventing a new process:

### No first findings after onboarding

- confirm the customer is still on the approved launch path
- confirm identity and AWS connectors reached the expected healthy state
- verify queue, alerts, and incident routes through the canonical frontend and API gateway
- capture onboarding completion time and expected first-value time
- if no signal reaches the queue in the expected window, treat the case as a `Sev-2` activation degradation unless data loss or isolation concerns are suspected

### Connector healthy state missing

- capture which connector is missing or stale
- verify onboarding status, downstream connector health, and recent auth changes
- do not mark the customer as activated until the missing state is explained or corrected
- if the connector path is outside the narrowed launch boundary, move immediately to guided review instead of pretending standard launch support applies

## Incident Types

### Login or session failure

- Check `api-gateway` and `iam-agent` `/ready`
- Inspect gateway auth failure counters
- Verify Keycloak health through IAM readiness payload
- If the current release introduced the issue, roll back frontend or IAM/gateway first

### Suspected tenant isolation issue

- Treat as Sev-1 immediately
- Stop rollout activity
- Preserve logs and request/correlation IDs
- Limit affected workflows if possible
- In the current operating model, `Clement Ellango` handles both security and platform decision roles; keep those responsibilities logically distinct in the incident record
- Do not send a customer blast-radius statement until the security review step is complete

### SIEM ingestion or detection degradation

- Check `api-gateway /api/v1/siem/source-health`
- Check `siem-agent /ready`
- Check ingestion queue metrics and OpenSearch health
- If detections are delayed but not lost, communicate degraded state
- If data loss is suspected, escalate to Sev-1

### Queue or scanner backlog

- Check orchestrator `/metrics`
- Review scanner failed and active counts
- Confirm downstream registry availability
- Pause new scan triggers if backlog is unbounded

### Model or AI provider degradation

- Check `model-gateway /ready`
- Check IAM model-provider metrics
- Confirm whether the issue affects launch-required workflows or only add-on/beta paths

### Backup or restore failure

- Stop release activity until backup state is known
- Verify latest successful PostgreSQL and Keycloak artifacts
- Escalate if the current RPO target can no longer be met

## Customer Communication Rules

- Never guess about blast radius.
- Use exact timestamps and affected workflows.
- State whether data exposure is suspected, confirmed, or not indicated.
- If tenant isolation is involved, security owns external communication approval.

## Communication Templates

### Initial acknowledgment

```text
Subject: SentinelGrid support intake received

We received your report at <timestamp UTC>. We are investigating the affected workflow: <workflow>.
Current severity: <severity>.
Current known impact: <exact symptom>.
Next update target: <timestamp UTC>.
```

### Sev-1 holding update

```text
Subject: SentinelGrid Sev-1 investigation update

We are actively investigating a potential Sev-1 issue affecting <workflow>.
At this time, data exposure is <suspected / confirmed / not indicated>.
We have paused rollout activity and are validating tenant scope, request history, and containment steps.
Next update target: <timestamp UTC>.
```

### Resolution update

```text
Subject: SentinelGrid issue resolved

The customer-visible issue affecting <workflow> was resolved at <timestamp UTC>.
Resolution action: <rollback / config fix / service recovery / other>.
Current verification status: <passed checks>.
Follow-up actions still open: <items or none>.
```

## Trust Material Alignment

The customer-facing answer set must stay aligned to:

- `docs/PHASE5_CUSTOMER_TRUST_PACK_2026-04-16.md`
- `docs/PHASE5_SECURITY_REVIEW_FAQ_2026-04-16.md`
- `frontend/src/app/(marketing)/trust/page.tsx`

Support should never promise:

- a staffed 24/7 SOC if none exists
- a broader launch boundary than the approved launch package
- unrestricted partner, AI Shield, endpoint, or retention scope that moved to guided review

If the request exceeds the frozen trust pack, escalate internally before answering.

## Exit Conditions

An incident is not closed until:

- the customer-facing symptom is gone
- verification steps pass
- root cause is recorded
- follow-up work is assigned

## Required Post-Incident Evidence

- intake record
- timeline
- severity changes
- request IDs and affected tenants
- customer communication timestamps and message copies
- remediation and rollback actions
- root cause
- follow-up items
