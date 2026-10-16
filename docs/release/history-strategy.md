# Publication history strategy

Status: **owner selected and approved**, October 15, 2026. Task 6 is complete.
The owner approved an independent source snapshot at `cellango/SentinelGrid-public`,
the GitHub noreply identity, and private repository creation/initial push in
Task 10. The existing repository and all its hosted material stay private.
Public visibility still requires the final Task 13 review.
Task 10 rebuilt the reviewed source after Tasks 8–9 and created the approved
private repository. See the verification records below; publication remains pending.

## Selected destination and history

| Item | Approved selection |
| --- | --- |
| Destination | `cellango/SentinelGrid-public` |
| Initial visibility | Private during preparation and CI |
| Future public branch | `main` only |
| History origin | A new root commit from the explicit reviewed source inventory |
| Existing repository | Retain privately with its current URL, refs, collaborators, PRs, and logs |
| Initial tags | None; a proposed `v0.1.0-preview.1` tag requires the exact release review in Task 13 |
| Commit identity | `cellango` with `35117197+cellango@users.noreply.github.com`, configured only in the isolated repository |

The authenticated preflight confirmed the existing repository is private and
returned not-found for the proposed destination on October 15, 2026. The name is
not reserved; recheck it before creation. The proposed commit identity uses the
public account's ID-based [GitHub noreply format](https://docs.github.com/en/account-and-profile/reference/email-addresses-reference),
so a local personal email need not enter the new public history.

An independent repository starts from selected files rather than inheriting
commits, refs, fork ancestry, object alternates, or old hosted discussion material.
Task 7 verified that boundary through the ref, object, and content checks below.
All source copyright, Apache-2.0 scope, and third-party notices remain preserved.
The new history will not expose the original granular commit attribution; that
history stays in the private source repository and private backup.

## Why this route

Tasks 1–5 identified owner-excluded business documents, generated artifacts, four
historical installer blobs, and hosted PR/log material that must remain private.
Changing the original repository's visibility would expose its retained surfaces;
GitHub specifically makes Actions history and logs visible when a repository
becomes public. See [GitHub's visibility documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility).

Keeping existing history would require an additional remediation plan covering
all intended refs and hosted copies before publication. A Git rewrite alone does
not implement the recorded business-document and hosted-material dispositions.
That alternative was not selected by the owner.

## Private recovery copies

A private local-history bundle covers all 41 locally available refs and 359
reachable commits. `git bundle verify` passed, its listed heads are recorded, and
its SHA-256 is retained privately. It covers local refs, rather than remote-only
refs, reflog-only objects, ignored working files, or hosted GitHub data.

A separate verified source archive and per-file hashes preserve the current
selected working files. Task 5's starting archive/diffs and the earlier private
quarantines remain intact. These local backups are under ignored
`artifacts/private-release-review/`; they contain private material and are not
publication inputs. The existing workspace and hosted repository remain retained.

## Approved operations and task boundaries

1. **Task 7 — local preparation:** verify backups and selected hashes, then copy
   only paths in `publication/source-files.json` into a new isolated directory
   under ignored private preparation storage. Preserve reviewed bytes and
   executable modes. Reject symlinks, private patterns, unexpected paths, and
   content drift. Copy source files individually; import no `.git` directory,
   refs, object packs, credentials, private artifacts, or installer files.
2. Initialize that directory with `git init --initial-branch=main`, configure the
   proposed repository-local identity, and create one preparatory root commit.
   Stage only the explicit selected paths with literal path handling. Where an
   existing ignore rule matches reviewed source, force-add only those selected
   files, rather than silently dropping them or broadly adding ignored material.
   Verify one root, one intended branch, no tags, no alternates/shared objects,
   and no old refs. Run source and full available-history secret scans against
   the isolated repository. Record the independent commit/tree and results.
3. **Tasks 8–9 — remaining review:** resolve dependency findings and documentation
   claims using reviewed source changes. Refresh the explicit inventory when
   paths change. Rebuild the still-unpublished isolated snapshot from the final
   reviewed files before its first remote push, so superseded preparation
   commits are not imported into the eventual public history.
4. **Task 10 — private GitHub verification:** recheck the destination is absent,
   then create a new empty private repository and push only the independent
   `main` after source/history gates pass. The proposed remote operation is:

   ```bash
   gh repo create cellango/SentinelGrid-public --private --disable-wiki \
     --description "SentinelGrid developer source preview for review and feedback"
   ```

   Configure `origin` only in the isolated repository as
   `https://github.com/cellango/SentinelGrid-public.git`, verify its private status,
   then run `git push --set-upstream origin main` there. The original workspace's
   remote is not repointed. This operation creates an independent repository,
   rather than a GitHub fork, template import, mirror push, or all-ref push.
   See the [GitHub CLI creation reference](https://cli.github.com/manual/gh_repo_create).
5. **Tasks 10–12:** run actual private CI, configure applicable protections and
   reporting, and freeze exact source/release contents. Preserve the existing
   read-only workflow and disabled deployment/package workflows. Do not transfer
   old repository secrets, webhooks, artifacts, issues, or PRs.
6. **Task 13 — final publication:** present the new repository, exact commit,
   proposed tag, release contents, and visibility change for final owner approval.
   This strategy decision does not approve making either repository public now.
   Task 14 then verifies anonymous access and public feedback/reporting routes.

If private or excluded material is found in any preparation history, keep that
copy private and rebuild the unpublished snapshot from cleared source. If it has
already been pushed, review the concrete remediation before any remote rewrite
or deletion. No existing-history rewrite, repository rename, ref deletion, or
remote replacement is part of the recommended plan.

## Task 7 local verification

Completed October 15, 2026. The local publication repository has one parentless
commit on `main`, the approved noreply author/committer identity, and no tags or
remotes. Its 3,527 tracked files match the reviewed working source byte for byte,
including executable modes. No original commits, alternate object stores, shared
Git directory, symlinks, or hardlinked objects were imported. Every stored Git
object is reachable and accounted for by that single root snapshot; strict
`git fsck` passed. Four excluded historical installer blobs and all 53 quarantined
paths/payloads are absent.

The initial 3,455-file export passed secret scans but failed the documented IAM
test import: broad `models/`, `secrets/`, and `data/` ignore rules had hidden
application Python source from the inventory. Earlier workspace checks could use
those local files. Seventy-two existing Python files were reviewed and restored
through source-only ignore exceptions. Model downloads, payloads, credentials,
and bytecode remain excluded, with a regression checking that distinction. The
restored synthetic SIEM generator uses reserved example domains and documentation
IPv4 ranges. Private copies preserve its original contents and the failed export.

The rebuilt isolated copy passed `make preview-check`: 1,445 Python files compiled,
five inventory tests, three model/migration contract tests, 14 IAM auth tests, and
Ruff checks. Gitleaks 8.30.1 source and full available-history scans both found zero
matches with the unchanged narrow exceptions. This new history result is separate
from the 137 classified rows retained in the original private history.

Detailed commit/tree IDs, per-file hashes/modes, exclusion checks, and scanner
evidence stay in ignored private review storage. The original workspace's HEAD,
refs, and remote were preserved during this task. This is a local preparatory
commit, not the Task 12 release freeze. Tasks 8 and 9 may change reviewed source;
rebuild from those final files before the first private push in Task 10. No remote
repository was created, no push occurred, and no visibility setting changed.

## Task 10 private GitHub verification

Completed October 15, 2026. Rebuilt a fresh independent root from **3,231 selected
files**, including the Task 8 dependency updates and Task 9 documentation cleanup.
The older Task 7 repositories were retained privately and were never pushed.
Verified every selected byte/executable mode, one parentless root on `main`, the
approved noreply identity, independent object storage, strict Git integrity, and
the absence of original commits, four installer blobs, 53 earlier quarantined
paths/payloads, and all 320 documents retired in Task 9 by path and content hash.

The approved new repository is
[`cellango/SentinelGrid-public`](https://github.com/cellango/SentinelGrid-public),
**private**, independent rather than a fork, with the wiki disabled. The original
repository, local refs/remotes, hosted material, and owner working changes were
preserved. No collaborators, messages, product secrets, deployment environments,
tags, releases, or public visibility were added. Only the reviewed source workflow
is active; its token has `contents: read`, checkout credentials are not persisted,
and the repository's inherited workflow default is read-only.

| Verification | Commit-bound result |
| --- | --- |
| Independent root | `f6d703d412cf55d758759a461cb51efe1cb83e02`; 3,231 files, 3,201 unique blobs, 4,009 accounted-for objects, no imported old commits |
| Fresh clone setup/checks | Python 3.13 hash-verified install and `pip check`; 28 Python tests, 1,447 compiled Python files, Ruff, 415 Markdown link/class checks, actionlint 1.7.12, and zero Gitleaks 8.30.1 source/history findings |
| Frontend | Fresh Node.js 22.23.3 `npm ci --ignore-scripts`; 13 tests in three suites passed |
| Actual Ubuntu workflow | [Passing run](https://github.com/cellango/SentinelGrid-public/actions/runs/38846520816) at `5656258fc4f82b35e1d7a639cc6908cbdd7542d3`; `source-checks`, `frontend-auth`, `secret-scan (snapshot)`, and `secret-scan (history)` all passed |
| Deliberate failure checks | [Disposable dispatch run](https://github.com/cellango/SentinelGrid-public/actions/runs/38846593819) at `7b6580cc3139cca639a5783b5ad40ce8a8514ac7`; all four jobs failed at the intended check steps |

The first Ubuntu install failed because SQLAlchemy's Linux dependency on
`greenlet` was absent from the macOS-derived pin list. Added `greenlet` 3.5.6 with
79 official PyPI hashes and both license-file records; the current environment
has **43 pins and 811 artifact hashes**. All 43 pins were audited with no findings
or advisory ignores. The failing install was repaired, rather than skipped.
The [dependency review](dependencies.md) retains the two separate npm tooling
exceptions; passing tests do not turn the raw npm audit into a clean result.

The canary added one unlisted source file, one deliberately false Jest assertion,
and a deterministic SHA-256 string labeled as an API key. That string was derived
from a fixed explanatory phrase and was never a credential. The unlisted file
failed the source inventory; the assertion produced one failed/13 passed tests;
both secret jobs rejected the synthetic canary. The workflow was unchanged, all
four jobs failed rather than succeeding through skips, and the branch was deleted
without merging. Only `main` remains on the remote. No PR or reviewer invitation
was created: the canary used `workflow_dispatch`. The same credential-free jobs
are configured for `pull_request`; actual public fork behavior is not claimed
from this dispatch run.

The separate working copy and raw verification/scanner evidence remain in ignored
private preparation storage. These are preparatory commits, not the Task 12
release freeze. Task 11 must configure applicable protections/reporting; Task 12
must refresh dependencies and bind all checks to the exact release candidate.
Task 13 still requires final approval before public visibility, a tag, or a release.

## Collaborator impact and acceptance

Existing collaborators can continue using their private clones, branches, and PRs.
Their access and remotes are not transferred or changed. Public developer review
will use the new repository URL and a fresh clone; old issue/PR history and
granular commit authorship will not appear there. Any private reviewer invitation
or collaborator announcement is a separate explicit action; none is sent here.

The owner answered "Approve the new snapshot plan" after reviewing the concrete
route, destination, identity, and operations. Task 6 is closed. Actual repository
creation and the initial private push were completed in Task 10. Tasks 7–9
completed local preparation, dependency review, and documentation consolidation. See
[the publication checklist](tasks.md) and
[selected source contents](contents.md).
