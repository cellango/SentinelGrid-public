# Phase 5 First-Value Dry Run

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 16, 2026  
**Status:** Ready to rehearse  
**Purpose:** Freeze the repeatable first-value activation path for the approved launch boundary before the fresh audit.

## Why This Exists

Phase 5 requires more than saying onboarding is "fast." The team needs one default launch path that can be rehearsed, evidenced, and defended in front of buyers, auditors, and support staff.

This document defines that default path.

## Default Launch Scenario

Use this scenario for internal rehearsals, sales walkthroughs, and launch-readiness dry runs unless there is a clear reason to branch.

- package: `Protect + Defend`
- buyer motion: direct customer, not partner-led
- identity path: Microsoft 365 / Entra first
- cloud path: AWS first
- endpoint path: second-wave or pilot follow-up, not a blocker for first findings
- AI Shield: excluded from the default dry run
- retention needs: standard package assumptions, not custom archive requirements
- support model: standard guided onboarding, not custom services

## What Counts As First Value

For the launch boundary, "first value" means all of the following are true:

1. The tenant is provisioned and operators can sign in successfully.
2. Microsoft 365 / Entra and AWS are connected on the standard path.
3. The main queue or incident workflow shows real normalized findings from those connectors.
4. The operator can open one prioritized record and see actionable next steps.
5. The operator can show one output beyond triage:
   - response or ownership handoff,
   - leadership-ready status summary, or
   - trust / evidence export.

## Preconditions

The dry run should not start until these are available:

- fresh test tenant with standard launch entitlements
- valid Microsoft 365 / Entra admin path
- valid AWS onboarding path
- working auth and session flow
- support contact owner for the run
- evidence capture owner for screenshots, request IDs, and timestamps

## Stop And Redirect Conditions

Do not force the default path when the environment actually needs a guided sales or solutions motion.

Redirect to a guided review if any of these are true:

- mixed or undecided identity architecture
- more than one core cloud environment in the first rollout
- full endpoint rollout required on day one
- partner / MSP / multi-tenant managed-service motion
- unusual retention or archival requirements
- AI Shield is the primary buying reason
- buyer expects broad unsupported provider coverage or enterprise-category parity

## Execution Sequence

| Step | Owner | Success Signal | Evidence To Capture |
| --- | --- | --- | --- |
| Tenant provisioned | Onboarding owner | Tenant exists and login succeeds | tenant ID, request ID, timestamp |
| Identity connected | Onboarding owner | Microsoft 365 / Entra connector healthy | connector health view, sync timestamp |
| Cloud connected | Onboarding owner | AWS connector healthy | connector health view, sync timestamp |
| Core connectors ready | Onboarding owner | identity + cloud marked ready | onboarding status screenshot or API payload |
| First normalized findings visible | Operator | queue shows real cloud / identity findings | queue screenshot, record ID |
| One prioritized record reviewed | Operator | record shows why it matters and what to do next | incident / alert screenshot, response suggestions |
| One downstream action shown | Operator | ownership, ticketing, or playbook state is visible | ticket link, action status, or pending approval state |
| One output shared | Customer-facing owner | summary or trust artifact generated from live data | exported report or trust artifact reference |

## Expected Time Windows

These are the launch-default expectations already reflected in the website copy and estimator.

- setup window: `Half day to 1 business day` for the default path
- first findings visible: same day when identity and AWS are both healthy
- first value: `Same day to next day`
- week-one proof point: one prioritized record plus one reusable output by Day 7

## Evidence Checklist

Capture these artifacts on every rehearsal:

- login success and tenant context
- Microsoft 365 / Entra connection state
- AWS connection state
- first queue or incident record ID
- response suggestion or handoff state
- one report, summary, or trust artifact generated from live data
- any support escalation taken during the run

## Failure Handling

If the dry run misses the expected path:

1. Record the exact failing step.
2. Save the request ID, correlation ID, tenant ID, and timestamps.
3. Decide whether the issue is:
   - product defect,
   - onboarding content gap,
   - support/process gap, or
   - out-of-scope environment complexity.
4. Route Sev-1 or suspected isolation / exposure issues through the production incident path immediately.
5. Do not market the blocked path as "standard onboarding" until the defect or scope mismatch is resolved.

## Rehearsal Exit Criteria

The dry run is good enough for the fresh audit only when:

- the default scenario completes without ad hoc engineering intervention
- first findings are visible from Microsoft 365 / Entra and AWS
- the operator can explain the first prioritized record without manual stitching
- at least one downstream output is produced from the same operating record
- support and escalation steps are explicit and repeatable

## Current Recommendation

Keep the default launch dry run narrow.

- Do not use AI Shield as the first rehearsal path.
- Do not use partner / MSP motion as the first rehearsal path.
- Do not expand into complex multi-environment onboarding until the default path is proven repeatedly.
