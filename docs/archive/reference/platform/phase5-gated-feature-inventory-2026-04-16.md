# Phase 5 Gated Feature Inventory

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 16, 2026  
**Status:** Canonical GTM and audit reference for launch boundary questions  
**Purpose:** Freeze what is production, controlled, gated, or out of scope before the fresh audit and production launch.

## Inventory

| Area | Status | What Can Be Sold Or Shown | What Must Stay Qualified Or Hidden |
| --- | --- | --- | --- |
| `Protect` | Production | Cloud, identity, posture, baseline detections, and standard onboarding | Do not imply full response or compliance depth beyond the package scope |
| `Protect + Defend` | Production | Core operator workflow, response guidance, incident workflow | Do not imply autonomous response for every playbook |
| Endpoint coverage path | Production with qualification | Guided endpoint coverage and install workflow tied into the main operator flow | Do not imply full EDR/XDR parity or a fully self-contained standalone endpoint stack |
| `Protect + Defend + Comply` | Production with narrowed scope | Evidence workflows, trust artifacts, baseline compliance reporting subset, and audit-facing exports backed by the deployed path | Do not imply full enterprise compliance-suite replacement or unsupported dedicated compliance-service depth |
| AI Shield approved provider path | Controlled add-on | AI runtime monitoring only for the approved launch provider path | Do not imply broad self-serve provider coverage |
| AI Shield unsupported providers | Gated / beta | May be discussed only as future or beta scope if explicitly labeled | Must not be marketed as production-ready |
| Dedicated `ai-security/*` standalone routes | Gated / beta | Can be referenced only as gated launch-boundary surfaces | Must not be sold as the main AI management console |
| Partner / MSP workflows | Qualified sales-assisted scope | Can be sold through the partner motion with explicit qualification and delivery review | Must not be presented as the default self-serve or default website-led launch path |
| Pentest platform | Out of scope | May be positioned later as a separate package or services motion | Must not be included in the initial core SaaS promise |
| `SentinelGridPostureAgent/frontend/` | Non-canonical | Internal or subsystem reference only | Must not create customer-facing console ambiguity |
| `website/` legacy app | Archived / non-canonical | Historical reference only | Must not receive net-new user-facing launch work |
| Broad enterprise parity claims | Out of scope | None | Must not claim full Wiz, CrowdStrike, Okta, or SailPoint category replacement |

## GTM Rules

- Anything marked `Gated / beta`, `Out of scope`, `Archived`, or `Non-canonical` is excluded from the default self-serve launch promise.
- Anything marked `Controlled add-on` requires qualification and explicit scope language.
- Anything marked `Qualified sales-assisted scope` must stay tied to the partner or guided-sales motion rather than self-serve website copy.

## Demo Rules

- Standard demos should lead with `Protect + Defend`.
- Endpoint should be shown as a guided coverage path inside the main workflow, not as a full EDR/XDR replacement story.
- Compliance should be shown only as the baseline evidence and reporting subset backed by the shipped path.
- AI Shield should be shown only when the approved provider path is relevant.
- Pentest should not appear in the default product walkthrough.
- Unsupported AI features or standalone AI surfaces must remain visibly gated if shown for roadmap context.

## Audit Evidence Use

Include this document in the Phase 6 evidence pack alongside:

- the launch scope decision
- the Phase 5 trust pack
- the first-value dry-run document

## Current Recommendation

Use this inventory as the answer key when anyone asks:

- "Is this in production?"
- "Can we sell this now?"
- "Can we show this in a demo?"

If the answer is not already clear from this file, the feature should be treated as qualified scope until owners ratify it explicitly.
