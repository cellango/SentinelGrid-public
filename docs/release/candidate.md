# Released source-preview candidate

Published October 16, 2026: [v0.1.0-preview.1](https://github.com/cellango/SentinelGrid-public/releases/tag/v0.1.0-preview.1), commit
`7cf4a5766083533517ed3467858dd830ee540ed3`. The release manifest and asset checksums bind this
identity. Later release-tracking commits on `main` do not move the tag or replace
its assets; verify the release by checking out `v0.1.0-preview.1`.

Task 12 prepared **v0.1.0-preview.1**, a developer source preview for review and
comments. Task 13 refreezes the documentation on October 16, 2026, after the owner
approved public visibility and requested completion of tagging and the prerelease
with the reporting limitation documented. The independent repository is now
public; the original repository remains private. See
[publication/release-plan.json](../../publication/release-plan.json).

## Exact identity and files

The frozen identity is the full commit SHA in the prepared **release-manifest.json**.
That manifest was generated after the source commit so it can name the exact SHA
without a self-reference. It was reviewed separately and is a published release
asset. The commit contains these preparation instructions, release
notes, and the reviewed source; generated release assets are not committed.

The manifest binds the commit/tree, every selected file's SHA-256 and executable
mode, module counts/dispositions, dependency and license records, source archive,
actual CI run, local checks, scoped exceptions, verified repository settings, and
the deferred incoming-report test.
Its source file set must exactly match [the path inventory](../../publication/source-files.json).
Only `main` is selected; original private history and earlier preparation copies
are excluded. A moving branch name is not a replacement for the full commit SHA.

| Release asset | Contents |
| --- | --- |
| `SentinelGrid-v0.1.0-preview.1-source.tar.gz` | Exactly the frozen source files, under a directory named with the full commit SHA |
| `release-manifest.json` | Public verification metadata and per-file hashes; no private scanner evidence |
| `SHA256SUMS` | SHA-256 for the source archive and manifest; it does not attempt to hash itself |

The archive is generated from the committed tree with a fixed prefix and gzip
timestamp. Its file set, bytes, executable modes, and reproducibility are checked.
The checksum file applies to these prepared assets, not GitHub's separately
generated ZIP/tar downloads. No binaries, dependency trees, images, installers,
private evidence, or old repository history are release assets.

## Verification and follow-up

Task 14 completed anonymous full-clone/download verification on October 16, 2026.
The 3,239 selected files matched Git, archive and manifest bytes/modes; all three
asset hashes matched, and fresh documented source checks passed. Rendered notices,
feedback/authentication routes and live protections were checked. See
[the final verification results](review.md#task-14-public-verification).
Incoming reporter access and GitHub notification receipt remain deferred in
[the protection review](repository-protections.md#follow-up-test).

The exact commit must pass documented setup, 28 Python tests, 13 frontend tests,
source compilation, documentation/inventory checks, Ruff, actionlint, and both
Gitleaks scans in a fresh full clone. All four hosted jobs must succeed at that
same SHA. The manifest records the actual results, rather than treating this
checklist as evidence. Package hashes are fixed; CI's Ubuntu image and requested
Python/Node versions still follow their upstream patch releases.

Tasks 12 and 13 refreshed all 43 Python pins and the full frontend lock audit. Python
has no reported advisories; npm still exits 1 for the same two scoped tooling
exceptions, expiring November 14, 2026. See [the dependency review](dependencies.md).
Runtime graphs and full-stack execution remain unqualified.

Review [the release notes](release-notes.md), [withdrawal procedure](withdrawal.md),
and [protection/reporting verification](repository-protections.md). Branch, Actions,
secret, fork, and private-reporting settings are active and verified. The saved
security-alert subscription and existing email preferences were checked. The
maintainer could access a private synthetic draft, and a separate direct email
was received. Incoming reporter access and GitHub-generated report notification
delivery remain unverified. The owner accepted that exception for this source
preview on October 16; the protection review retains the remaining test when an
independent reporter is available. No additional test was sent during finalization
or anonymous verification.

Any source, dependency, workflow, scope, or release-content change invalidates
this freeze: create a new reviewed commit, rerun applicable checks, regenerate
assets/manifest/checksums, and record the new identity. The owner explicitly
authorized this documentation refreeze and completion of the existing preview
tag/prerelease. Do not amend a published tag or silently replace release assets.
No withdrawal or unrelated publication operation is authorized by this record.
