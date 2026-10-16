# Repository protections and private reporting

Task 11 is **in progress**, reviewed October 15, 2026. The available Actions
restrictions are applied and verified. A monitored private contact and delivery
confirmation are still missing, so Task 11 and publication remain open.

The target is the independent, **private**
[`cellango/SentinelGrid-public`](https://github.com/cellango/SentinelGrid-public).
The exact applied settings, prepared API payloads, and pending controls are in
[the repository policy](../../publication/repository-settings.json). The original
repository, account billing, collaborators, and public visibility were not changed.

## Applied and verified

| Control | Verified repository setting |
| --- | --- |
| Workflow token | Read-only default; workflows cannot approve pull requests |
| Action references | Full commit SHAs required by repository policy |
| Allowed actions | Only the three exact reviewed checkout/Python/Node action SHAs; broad GitHub-owned and verified-publisher allowances disabled |
| Workflow scope | The existing `contents: read` source workflow remains unchanged; no product credentials, privileged event, deployment, or report upload added |

All four jobs passed under these settings in
[the policy verification run](https://github.com/cellango/SentinelGrid-public/actions/runs/38847508895)
at `bee44c19620e7ed783c9a9cd32d301145025cbd9`. API readback also matched every
applied value. See [GitHub's Actions settings API](https://docs.github.com/en/rest/actions/permissions)
for the policy fields. Repository administrators can still change these settings;
this record does not claim protection from an account administrator.

## Prepared controls that are unavailable while private

| Control | Actual private-repository result | Required publication action |
| --- | --- | --- |
| Branch protection and rulesets | HTTP 403: upgrade or public visibility required | Apply the prepared `main` protection and verify readback immediately after the approved Task 13 visibility change |
| Native secret scanning and push protection | Enabling returned HTTP 422: unavailable for this repository | Enable supported native protections after approved visibility change, read back their status, and verify in Task 14 |
| External fork workflow approval | HTTP 422: this approval setting is unavailable for private repositories | Require maintainer approval for all external contributors after approved visibility change |
| GitHub private vulnerability reports | Status endpoint returned HTTP 404; the feature is for public repositories | Enable the form after approved visibility change and verify researcher access and notification delivery in Task 14 |

These controls are **not currently enforced**. The API did not expose an account
plan name; the availability results above are the actual repository responses.
See GitHub's [branch-protection availability](https://docs.github.com/en/rest/branches/branch-protection#update-branch-protection),
[Secret Protection availability](https://docs.github.com/en/code-security/getting-started/quickstart-for-securing-your-repository),
and [private-reporting requirements](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository).
The existing local/CI Gitleaks checks continue to cover source and available
history; native supported-pattern protection complements them.

The prepared `main` policy requires a pull request, up-to-date passing checks from
the GitHub Actions app, resolved review conversations, and linear history.
Administrators are included; force pushes and branch deletion are disabled.
The four required names are `source-checks`, `frontend-auth`,
`secret-scan (snapshot)`, and `secret-scan (history)`, bound to app ID `15368`.

Only `cellango` currently has maintainer access. The prepared policy therefore
requires **zero independent approvals** while retaining the pull-request/check
requirements; it does not claim independent review of the owner's work. Require
at least one approval once a second trusted maintainer is explicitly authorized.
No collaborator invitation or bypass actor is part of this preparation.

Task 13 must present these public-only operations alongside the exact visibility,
commit, tag, and release proposal. After approval, apply and read back the controls
before finalizing a tag or release. Stop that finalization if any required control
cannot be verified. Task 14 repeats the public/fork/reporting checks. This plan
does not authorize changing visibility now.

## Private reporting and delivery

[SECURITY.md](../../SECURITY.md) remains the reporter-facing policy. The GitHub
form cannot serve as the verified route during private preparation. The owner
must select a reporting email, confirm it is monitored, and confirm receipt of a
synthetic delivery test before Task 11 closes. No email address has been guessed,
and no test message or report has been sent.

The prepared test uses subject **SentinelGrid private-reporting delivery test**
and reference **SG-REPORTING-2026-10-15**. Its body states that it is only a delivery
test and asks for receipt confirmation. It contains no vulnerability details,
credentials, customer data, or attachments. The owner can send the test or
authorize one message to the selected destination. Sending and inbox receipt are
separate checks; a successful send alone does not prove delivery or monitoring.

For the later GitHub form, confirm the owner subscribes to repository security
notifications and that email delivery is enabled for the intended inbox, following
[GitHub's notification guidance](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository#configuring-notifications-for-private-vulnerability-reporting).
Then verify receipt of an authorized synthetic private report in Task 14. Account
notification preferences and inbox delivery have not been verified here.
