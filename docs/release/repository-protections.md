# Repository protections and private reporting

Reviewed October 16, 2026, for the developer source preview. The independent
[`cellango/SentinelGrid-public`](https://github.com/cellango/SentinelGrid-public)
repository is public following owner approval. The original repository and its
history remain private. The current policy is recorded in
[publication/repository-settings.json](../../publication/repository-settings.json).

## Applied and verified

| Control | Verified setting |
| --- | --- |
| Workflow token | Read-only default; workflows cannot approve pull requests |
| Action references | Full commit SHAs required; only the three reviewed checkout/Python/Node SHAs allowed |
| Workflow scope | One source-preview workflow with `contents: read`; no product credentials, deployment or scanner-report uploads |
| `main` branch | Pull requests, up-to-date passing checks, resolved conversations and linear history required; administrators included |
| Required checks | `source-checks`, `frontend-auth`, `secret-scan (snapshot)`, `secret-scan (history)`, bound to GitHub Actions app ID `15368` |
| Ref protection | Force pushes and deletion of `main` disabled |
| Native secret protection | Secret scanning and push protection enabled |
| External-contributor workflows | Maintainer approval required for all external contributors |
| Private vulnerability reporting | Enabled; maintained custom form and issue chooser route reporters to the private channel |
| Maintainer notifications | Custom Security alerts subscription saved; existing email destination and email preferences checked |

API readback verified the repository controls after approved public activation.
Task 14 repeated readback on October 16 and verified the public pages, source
downloads and sign-in gates; see [the final results](review.md#task-14-public-verification).
The GitHub UI verified the custom subscription and existing delivery preferences;
no token scope or account-wide notification preference was changed. Custom-event
subscriptions can return a null GraphQL `viewerSubscription`; that value does not
replace the explicit saved UI selection.

Only `cellango` has maintainer access. Required independent approvals are **zero**
while pull-request/check requirements remain enforced. This does not establish
independent review of the owner's work. Require at least one approval when a
second trusted maintainer is explicitly authorized. No collaborator invitation,
bypass actor, paid plan change, or change to the original repository is included.
Repository administrators can still change settings.

Task 11's private preparation encountered HTTP 403/422/404 availability limits for
branch, native-secret, fork and reporting controls. Those were historical
private-repository results; the public controls above are now active. Native
supported-pattern secret protection complements the local/CI Gitleaks checks.
See GitHub's [branch protection API](https://docs.github.com/en/rest/branches/branch-protection#update-branch-protection)
and [Actions settings API](https://docs.github.com/en/rest/actions/permissions).

## Private reporting and delivery

[SECURITY.md](../../SECURITY.md) is the reporter-facing policy. The maintained
[private form](../../.github/VULNERABILITY_REPORT.yml) and
[issue chooser](../../.github/ISSUE_TEMPLATE/config.yml) contain no reporting email.
Notification recipients remain configurable in GitHub; no product SMTP service
or source-controlled mailbox is required. Ordinary developer feedback retains
its separate issue template.

Verification completed:

- Private vulnerability reporting is enabled.
- A synthetic maintainer-created draft remained private and unpublished, was
  accessible to the maintainer, and returned HTTP 404 to an anonymous request.
- The maintainer's repository Security alerts subscription was saved, and the
  existing notification destination/email preferences were checked.
- The owner confirmed receipt of one separately authorized direct inbox test.

**Still unverified:** access by an external reporter and delivery of GitHub's
notification for an incoming private report. The draft was created by the owner;
there was no incoming-report submission. A direct email reaching an inbox does
not verify GitHub's reporting flow. A separate non-maintainer reporter was not
available. No incoming test or repeated email was sent by the agent.

On October 16 the owner instructed us to document this gap and complete the
source-preview tag and prerelease. This is a scoped exception for
`v0.1.0-preview.1`: incoming-report delivery is follow-up work, not a passed check
or a condition claimed satisfied by publication. The actual repository controls,
source checks and secret scans remain required. No reporting inbox, private
advisory URL, message contents or scanner evidence is published.

## Follow-up test

**Open after Task 14:** maintainer `cellango` will arrange the incoming-report and
notification-receipt check when a separate non-maintainer reporter is available.
Anonymous verification and the publication checklist are complete; this scoped
exception remains unverified. It is not a passed end-to-end reporting test.

When a suitable reporter is available, use the single authorized clearly labeled
synthetic private report. Confirm reporter/maintainer access, privacy, and actual
notification receipt; a submission confirmation alone is not delivery. Preserve
and inspect any existing report before considering a retry. Do not publish the
test advisory or submit duplicates. Record the result without committing personal
contact details. Update this record with the result; the completed anonymous
checks do not satisfy or consume the single incoming-test authorization.

Follow [GitHub's private-reporting and notification guidance](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository#configuring-notifications-for-private-vulnerability-reporting).
