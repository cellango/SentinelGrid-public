# Tasks to publish SentinelGrid for developer review

Target: a public **source preview** for developer review and comments, with
Apache-2.0 for original SentinelGrid code. A supported runnable beta is a separate
milestone. Follow [RELEASE_SCOPE.md](../../RELEASE_SCOPE.md).

Work through these tasks in order, one at a time. Check a task only when its
acceptance check passes, and record evidence without secret values. **Task 10 is
next.** History changes, account changes, and publication will be reviewed as
concrete actions when their tasks are reached; this list does not execute them.

## Preparation already completed

- [x] Add Apache-2.0 for original code and preserve component license boundaries.
- [x] Retire direct password reset and remove secret logging.
- [x] Remove bundled installers, scanner exports, and tracked bytecode from the
  candidate source; preserve local copies privately.
- [x] Disable historical deployment/publication workflows and add read-only CI.
- [x] Pass the current-source secret scan and focused local checks: 30 tests,
  Python compilation/undefined-name checks, and active workflow validation.

These results describe the working tree. Final-commit and GitHub CI verification
remain open. The history scan has **137 potential matches**, not 137 confirmed
live credentials. See [the release review](review.md).

## Task 1 Review historical secret matches

- [x] Complete

Privately classify all 137 findings, starting with the 60 matches in the historical
scanner report. Group duplicates while retaining affected files, commits, and refs.
Distinguish real or potentially real credentials, demonstrably synthetic fixtures,
and non-secret identifiers. Uncertain findings stay open for owner confirmation.
Keep the detailed ledger in ignored `artifacts/private-release-review/`.

**Done when:** every finding has a supported disposition, affected refs are
inventoried, and required remediation is listed without publishing secret values.
Only reviewed false positives receive narrowly scoped scanner exceptions.

Completed October 15, 2026: all 137 scanner rows were classified into 22 distinct
values, with historical source and affected-ref evidence preserved privately.
The owner confirmed the Keycloak and Vault candidates were disposable local
examples. See [the historical secret review](historical-secrets.md).

## Task 2 Revoke or rotate exposed credentials

- [x] Complete

Completed October 15, 2026: the owner confirmed both published defaults were used
only in disposable local development, in addition to the two local examples
confirmed in Task 1. Shared-environment rotation is not applicable for these
reviewed groups; no credentials were changed. See
[the credential rotation review](credentials.md).

Prepare a service-by-service plan for credentials identified in Task 1. Have the
account owner revoke/rotate them, update consumers, and verify old values fail.
Do this before history removal, following
[GitHub's sensitive-data guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).

**Done when:** every affected credential has owner-confirmed remediation and
verification. If none are real, record the supported conclusion and mark this task
not applicable. Never put credential values in chat, issues, or commits.

## Task 3 Review private data and retained artifacts

- [x] Complete

Completed October 15, 2026: the owner confirmed the customer examples are
synthetic and requested private retention of business documents. Forty-eight
documents and five generated artifacts were removed from the candidate, with
originals retained privately. Source metadata was sanitized and hosted material
inventoried. The existing GitHub repository, history, PR material, and logs must
remain private until the publication strategy preserves those dispositions.
See [the private-data review](private-data.md).

Review source/docs for customer data, real telemetry, account identifiers, internal
endpoints, screenshots, database exports, and confidential business material. For
an existing repository, inspect what a visibility change would expose in issues,
PRs, wiki/discussions, Actions logs/artifacts, releases, and attachments. Include
related images/packages where the findings warrant it.

**Done when:** public material is explicitly cleared or sanitized, and retained
copies have a documented disposition. Private local evidence stays out of releases.

## Task 4 Complete third party provenance review

- [x] Complete

Completed October 15, 2026: the owner confirmed the remaining source and project
logos are original or created for this project, apart from declared dependencies
and starter assets. Six Next.js assets were matched to upstream source; complete
MIT, icon/font reference notices, and Wazuh upstream notices were preserved.
Installer redistribution is excluded, including four historical installer blobs.
See [the provenance review](provenance.md) and
[component inventory](../../third_party/components.json). Resolved dependency and
runtime-artifact checks remain separate tasks.

Inventory retained third-party source, assets, scripts, and artifacts in intended
public history. Check upstream sources, licenses, modifications, attribution, and
redistribution obligations, especially Wazuh material. Update
[third-party notices](../../THIRD_PARTY_NOTICES.md); omit material without adequate
provenance or distribution rights.

**Done when:** each retained component has a source/license record and required
notices. Apache-2.0 applies to original SentinelGrid code within the stated scope.

## Task 5 Select the exact publication contents

- [x] Complete

Completed October 15, 2026: the owner selected inclusion of the sanitized cloud
work as experimental review source. The exact inventory lists 3,454 files with
module/historical-document dispositions. The model was aligned with unchanged
V013 SQL, and offline schema, cloud, and source checks passed. Existing work and
excluded material remain recoverable privately. See
[selected contents](contents.md) and
[the exact path inventory](../../publication/source-files.json). This selects the
working source; it does not freeze a release commit or clear existing Git history.

Review the cleanup alongside the existing cloud-provider work. Select the changes
for the first public snapshot and preserve excluded work privately. If cloud work
is included, verify its V013 migration, models, examples, and tests stay consistent.
Create an explicit file/module inventory and disposition for historical docs and
experimental components.

**Done when:** the candidate diff and inventory are reviewable, unrelated work is
preserved, and the contents match the agreed source-preview scope.

## Task 6 Choose the publication history strategy

- [x] Complete

Completed October 15, 2026: the owner approved the
[concrete strategy](history-strategy.md): an
independent `cellango/SentinelGrid-public` snapshot, private during preparation,
with the original repository retained privately. History/source backups and target
preflight are verified. Local isolated preparation is Task 7; approved private
repository creation and the initial `main` push are Task 10. Public visibility
still requires the exact Task 13 release review.

Choose reviewed/remediated existing history or a new repository built from the
reviewed source snapshot, keeping the original private. Use Tasks 1–5 to decide.
Record the destination, public branches/tags, collaborator impact, private backup,
and exact proposed operations. Finding dispositions determine whether a history
rewrite is necessary.

**Done when:** the owner selects the strategy and reviews any proposed rewrite,
remote replacement/deletion, or new repository creation before execution.

## Task 7 Prepare and verify the publication repository

- [x] Complete

Completed October 15, 2026: an isolated local repository contains one independent
root commit on `main`, with the approved noreply identity, no tags/remotes, and
3,527 selected source files matching reviewed bytes and executable modes.
Source and full available-history scans both passed with zero findings. Object
storage and excluded-file checks passed. The first clean export exposed 72
application Python files hidden by broad ignore rules; these were reviewed,
restored to the inventory, and covered by a source-versus-private-payload regression.
The rebuilt copy passed `make preview-check` (22 tests, 1,445 Python files compiled,
and Ruff). See [the Task 7 verification record](history-strategy.md#task-7-local-verification).
Private remote creation/push remains Task 10; this preparatory commit is not a
frozen release candidate.

Implement the approved strategy in an isolated copy. Remediate selected refs and
remote copies when retaining history. For a new snapshot, import only approved
files and keep private history/artifacts out. Preserve recoverable private copies.

**Done when:** source and history scans pass for every ref intended for publication,
with only justified narrow exceptions. Contents match Task 5; no overlooked branch
or tag exposes sensitive or uncleared history.

## Task 8 Audit dependencies used by the preview

- [x] Complete

Completed October 15, 2026: patched the Python preview environment and frontend
lock, verified all 42 Python pins with required artifact hashes, and reviewed
42 Python/828 npm license records. The fresh environment passed 22 Python tests,
13 frontend tests, and parser compatibility checks. Python audit found zero
advisories. Two unpatched development-tooling advisories remain under exact,
dated source-preview exceptions; raw npm audit still exits 1. Experimental
runtime manifests and known affected exact pins are cataloged without runtime
clearance. See [the dependency review](dependencies.md).

Run vulnerability and license checks for the Python review environment and frontend
packages installed by the documented commands. Fix relevant findings and verify
pins/lockfiles. Inventory runtime manifests and record experimental-component risks
against their excluded scope. Keep accepted exceptions specific, owned, and dated.

**Done when:** supported preview commands have no unresolved release-blocking
dependency findings, installation is reproducible, and remaining limitations are
accurately documented.

## Task 9 Finish developer documentation and claims review

- [x] Complete

Completed October 15, 2026: current architecture/development/reference/release docs
are separated from clearly historical archives. Moved/consolidated 291 documents,
retired 307 obsolete/duplicate documents, and retained 13 additional business
records privately with verified originals. All 415 retained Markdown files are
classified and their local links pass; new guard tests prevent private/ignored
link targets and classification drift. Landing/trust/component guidance now
matches the source-preview boundary. Python checks (28 tests, 1,447 files compiled),
13 frontend tests, five TSX syntax checks, workflow syntax, scanner canaries, and
source secret scanning passed. See [the documentation review](documentation.md).
The old Task 7 snapshot contains retired material and must be rebuilt in Task 10.

Align README, scope, contribution guidance, security reporting, examples, docs
index, and relevant UI copy with the candidate. Label or remove stale production,
compliance, benchmark, and completion claims. Identify implemented, simulated,
experimental, and excluded capabilities and provide a useful feedback route.

**Done when:** a developer can identify scope, licensing, checks, ordinary feedback,
and private reporting before running commands. Historical claims do not contradict
the current release boundary.

## Task 10 Verify a clean clone and GitHub CI

- [x] Complete

Completed October 15, 2026: rebuilt the 3,231-file independent snapshot after
Tasks 8–9, created the approved private `cellango/SentinelGrid-public`, and pushed
only `main`. Fresh local/GitHub clones passed the supported checks. Actual Ubuntu
CI exposed a missing Linux-specific `greenlet` pin; added its verified hashes and
license records, audited all 43 Python pins, and passed all four hosted jobs.
A disposable dispatch run failed all four jobs on deliberate inventory, frontend,
and synthetic-secret defects; its branch was removed without merging. See
[the commit-bound verification](history-strategy.md#task-10-private-github-verification).
The original repository stays private; public visibility, tags, and releases
remain unapproved until Task 13. Repository protections/reporting are next.

In a fresh clone of the private candidate, run documented setup, `make preview-check`,
frontend `npm run test:preview`, both secret scans, and actionlint. Run the actual
GitHub workflow. Verify PR checks need no cloud credentials, deployment rights, or
private dependencies. Confirm old publication workflows stay disabled and required
checks fail on deliberate canary defects in a disposable branch.

**Done when:** required checks pass in the clean clone and GitHub, with results
bound to a commit. Required failures cannot turn into successful skips.

## Task 11 Configure repository protections and reporting

- [ ] Complete

In progress October 15, 2026: applied/read back read-only Actions permissions,
disabled automated PR approval, required full action SHAs, and restricted actions
to the three reviewed immutable references. All four hosted jobs passed under
that policy. GitHub rejects private branch/ruleset protection on the current plan,
native secret protection for this private personal repository, and the public-only
fork/reporting controls. Exact public-activation payloads and verification steps
are prepared in [the protection review](repository-protections.md).
**Still required:** owner-selected monitored private contact and confirmed test
delivery. Public-only controls remain explicitly pending; no visibility change
or test message has been performed.

Configure available branch protections/rulesets, required checks/reviews, read-only
Actions permissions, and secret scanning/push protection for the target repository
and account plan. Establish a monitored private vulnerability contact and verify
notification delivery. Prepare GitHub private reporting where available; if it
requires public visibility, use the private contact before publication and enable
and verify the GitHub form in Task 14. See
[branch protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
and [private reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository).

**Done when:** applicable settings are verified, the private reporting route works,
and public-only settings have explicit post-publication verification steps.

## Task 12 Freeze the release candidate

- [ ] Complete

Review and commit the selected changes. Run required checks on that exact commit.
Prepare a public manifest with its SHA, modules, dependency/artifact digests, test
results, licensing, and limitations; write preview release notes and a withdrawal
procedure. Exclude private scanner and remediation evidence.

**Done when:** the candidate is immutable, its release tree is clean, preceding
tasks are closed, and the exact source/release contents are ready for owner review.

## Task 13 Publish the developer preview

- [ ] Complete

Present the destination, commit, visibility change, proposed preview tag, and release
contents for final owner approval. After approval, publish that candidate with
source-review release notes. Keep experimental runtime automation and cloud,
image, and package publication disabled.
Include the [prepared public-only protections](repository-protections.md) in that
approval. After the approved visibility change, apply and read back the required
settings before finalizing a tag or release; stop finalization if verification fails.

**Done when:** the approved commit and preview release are publicly accessible
with the intended refs, scope, and license information.

## Task 14 Verify public access and feedback channels

- [ ] Complete

Clone/download anonymously and repeat the documented checks. Verify the release
commit, rendered notices/links, private reporting and notifications, and ordinary
feedback channels. Complete the public-only settings from Task 11. Confirm private
artifacts and privileged workflows were not exposed during publication.

**Done when:** anonymous verification passes and the release review records the
final commit, results, and feedback channels. Then close this checklist.

## Follow on work for a runnable beta

Keep a separate backlog for service startup, frontend production builds, fresh
database/upgrade/restore checks, identity/tenant boundaries, OAuth, durable approvals,
constrained tools, safe model failure, authenticated RAG/agents, TLS, and the
synthetic end-to-end demo. Add a runtime capability to the supported scope only
after its applicable security and runtime checks pass.
