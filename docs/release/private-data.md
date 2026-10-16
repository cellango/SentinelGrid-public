# Private data and retained artifacts review

Task 3 is complete as of October 15, 2026. It reviewed the working source candidate
and recorded what must remain private.
It does not authorize changing the existing repository's visibility. Original
copies and detailed evidence remain local under ignored
`artifacts/private-release-review/task-3/`.

## Source disposition

- The owner confirmed that the AgribotsAI onboarding/account records and Pentest
  friendly-customer beta records are synthetic local examples. Their provenance
  is now stated alongside those fixtures. Historical `live` wording and beta
  contract fields do not establish real customer engagements.
- The owner requested private retention of product pitch, pricing, competitor
  comparisons, and internal roadmap documents. Forty-eight documents, including
  mixed technical/business planning files, were moved out of the candidate.
  Links to omitted documents were removed or marked as privately retained.
- One saved Terraform plan, three browser captures, and local certificate serial
  state were moved to private retention. The plan is a ZIP container with embedded
  state and configuration; it was inspected without executing Terraform.
- Personal absolute clone paths were replaced with portable examples or relative
  links. Installer checksum records retain their digests and use basenames.
- Cloud example endpoints, resource IDs, and two target domains were replaced
  with synthetic fixtures. A broad model-adapter ignore rule had also excluded
  three application adapter source files; a narrow Python-source exception now
  includes them, with their original work preserved privately.
- Report HTML remaining in the candidate consists of application templates.
  JSON/NDJSON fixtures and seed inputs are source examples, rather than retained
  database or telemetry exports. Icons and SVG source assets remain subject to
  the separate third-party provenance review. No confirmed customer dataset was
  found by this review.

Public product UI and pricing implementation remain source code for review.
This document's private-business disposition concerns the internal planning
documents, rather than removing those product capabilities.

## Existing GitHub repository

The authenticated read-only inventory found the existing repository private, with
95 pull requests, no standalone issues, six issue comments, ten inline review
comments, and seven PR review records. Wiki and discussions are disabled. There
are no listed releases, release assets, retained Actions artifacts, deployments,
or linked packages. No attachment URLs were found in the reviewed discussion
text; this is not an inventory of separately retained external uploads.

The repository has 1,060 workflow runs. Representative log downloads were checked
for all nine workflow names: two archives were available and seven requests were
unavailable. The two archives contained 14 log files. Secret scanning found no
matches in the downloaded logs and reviewed discussion text. This limited result
does not clear every historical log or deleted/expired external copy.

Seven hosted discussion records contain business-planning references. Git history
also retains the omitted business documents and generated artifacts. Keep the
existing repository, its history, PR material, and logs private. None is cleared
for a visibility change by the working-tree cleanup. Tasks 6 and 7 must implement
a publication strategy that preserves that disposition, such as a separate
reviewed source snapshot; any proposal to retain existing history must account
for these hosted copies as well.

## Retention and verification

Private evidence includes hashes of quarantined originals, copies of files before
sanitization, the owner's provenance/disposition answers, and GitHub API results.
Ignored local configuration, credentials, databases, captures, logs, backups,
dependencies, and test artifacts remain local. Do not upload those directories
as release archives, container contexts, issue attachments, or CI artifacts.

Candidate inventory checks reject saved plans, Terraform state backups, serial
state, and the browser-capture directory even if somebody force-adds them.
Git and Docker exclusions were updated accordingly. Final source selection,
publication-history scans, and checks bound to the eventual release commit remain
separate tasks in the [publication checklist](tasks.md).

Local verification passed: the source-preview checks compiled 1,371 Python files,
passed three inventory tests and 14 IAM auth tests, and passed Ruff's syntax and
undefined-name checks. All 47 additional cloud tests passed (24 IAM, 14 Gateway,
nine scanner helpers). One initial test import needed the repository-declared
AWS dependency; it was installed only in a temporary test directory before the
successful rerun. The final candidate secret scan found zero matches. No live
cloud calls, deployments, credential changes, remote deletions, history changes,
or visibility changes were performed.

The [Task 4 provenance review](provenance.md) subsequently
recorded retained assets and notices and excluded installer redistribution.
Continue with the remaining tasks in the publication checklist.
