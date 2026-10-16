# SentinelGrid Production Risk Exception Policy

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 16, 2026  
**Status:** Phase 0 canonical exception policy  
**Purpose:** Define the only acceptable way to document, approve, review, and expire residual launch risk during the go-readiness program

## Why This Exists

The production gate contract allows only narrow, explicit exceptions.

Without a policy, teams can blur the difference between:

- an accepted temporary risk
- an unresolved blocker
- a launch-disqualifying condition

This policy removes that ambiguity.

## Default Rule

The default rule is simple:

- fix the issue
- do not waive it
- do not convert schedule pressure into silent risk acceptance

An exception is valid only if it is recorded in the approved exception register and meets every rule below.

## Exceptions That Are Not Allowed

No exception may be used to override any of the following:

1. unsigned JWT trust on any live auth, identity, or authorization path
2. placeholder tenant resolution on any launch-critical route
3. plain-HTTP primary ingress for the public launch path
4. wildcard CORS on a public launch path
5. fake completion, stub execution, or silent mock fallback presented as real production behavior
6. any other condition already listed as an automatic `No-Go` in `docs/archive/reference/platform/production-go-acceptance-contract-2026-04-16.md`

If one of those exists, the state remains `Open`, not excepted.

## Narrow Cases Where An Exception May Be Considered

An exception may be considered only if at least one of these is true:

1. the issue affects a feature that is fully gated from the default launch package
2. the issue affects a controlled add-on that is not in the default self-serve promise
3. the issue is a known dependency finding with clear compensating controls, a bounded blast radius, and a dated remediation plan
4. the issue is a non-launch-critical operational debt item that does not undermine current launch claims

Meeting one of those conditions does not grant approval by itself. It only makes review possible.

## Required Exception Record Fields

Every approved exception must include:

1. exception ID
2. date created
3. direct owner
4. affected gate, service, or feature area
5. clear description of the unresolved issue
6. reason the issue is not launch-disqualifying
7. compensating controls
8. evidence links
9. review date
10. expiration date
11. final approver
12. explicit status

## Approval Rule

An exception is valid only if all of the following are true:

1. the direct owner accepts accountability
2. the Security Lead approves the rationale
3. the Engineering Lead approves the remediation plan
4. the Product Lead confirms the issue does not contradict the current launch promise
5. the exception is entered into `docs/archive/reference/platform/production-approved-exception-register-2026-04-16.md`

If any one of those is missing, the exception is invalid.

## Time Boundaries

- Every exception must have a review date.
- Every exception must have an expiration date.
- Expired exceptions automatically revert to `Open`.
- Exceptions may not silently roll forward.

Default review cadence:

- high-risk residual issues: every 7 days
- lower-risk launch-qualified issues: every 14 days

## Allowed Status Values

- `Proposed`
- `Approved`
- `Expired`
- `Closed`
- `Rejected`

Anything else should be treated as undefined and therefore invalid.

## Relationship To The Gate Contract

- `G-03`, `G-04`, `G-05`, `G-07`, `G-09`, `G-10`, `G-11`, and `G-12` should be treated as non-exceptionable for launch readiness
- `G-06` may be satisfied by fully gating AI Shield from the default launch rather than by excepting weak production support
- `G-08` may use an approved exception only when the affected finding is bounded, compensating controls are real, and the default launch promise remains truthful

## Review Requirement For Phase 7

Every still-open approved exception must be referenced again in the final re-audit package.

If the final re-audit does not restate the exception set, the re-audit is incomplete.

## Phase 0 Exit Condition Covered By This Doc

The exception-policy portion of Phase 0 is complete when:

- teams know which issues can never be excepted
- any allowed exception path has one canonical approval rule
- no residual risk can be hand-waved without an owner, a date, and an approver
