# Frozen source-preview candidate

Task 12 prepares **v0.1.0-preview.1**, a developer source preview for review and
comments. The release plan is [publication/release-plan.json](../../publication/release-plan.json).
The repository remains private during this freeze; a tag, release, and public
visibility require the separate Task 13 review.

## Exact identity and files

The frozen identity is the full commit SHA in the prepared **release-manifest.json**.
That manifest is generated after the source commit so it can name the exact SHA
without a self-reference. It is supplied separately for owner review and proposed
as a release asset. The commit contains these preparation instructions, release
notes, and the reviewed source; generated release assets are not committed.

The manifest binds the commit/tree, every selected file's SHA-256 and executable
mode, module counts/dispositions, dependency and license records, source archive,
actual CI run, local checks, scoped exceptions, and pending public-only gates.
Its source file set must exactly match [the path inventory](../../publication/source-files.json).
Only `main` is selected; original private history and earlier preparation copies
are excluded. A moving branch name is not a replacement for the full commit SHA.

| Proposed release asset | Contents |
| --- | --- |
| `SentinelGrid-v0.1.0-preview.1-source.tar.gz` | Exactly the frozen source files, under a directory named with the full commit SHA |
| `release-manifest.json` | Public verification metadata and per-file hashes; no private scanner evidence |
| `SHA256SUMS` | SHA-256 for the source archive and manifest; it does not attempt to hash itself |

The archive is generated from the committed tree with a fixed prefix and gzip
timestamp. Its file set, bytes, executable modes, and reproducibility are checked.
The checksum file applies to these prepared assets, not GitHub's separately
generated ZIP/tar downloads. No binaries, dependency trees, images, installers,
private evidence, or old repository history are release assets.

## Verification and remaining gates

The exact commit must pass documented setup, 28 Python tests, 13 frontend tests,
source compilation, documentation/inventory checks, Ruff, actionlint, and both
Gitleaks scans in a fresh full clone. All four hosted jobs must succeed at that
same SHA. The manifest records the actual results, rather than treating this
checklist as evidence. Package hashes are fixed; CI's Ubuntu image and requested
Python/Node versions still follow their upstream patch releases.

Task 12 refreshed all 43 Python pins and the full frontend lock audit. Python
has no reported advisories; npm still exits 1 for the same two scoped tooling
exceptions, expiring November 14, 2026. See [the dependency review](dependencies.md).
Runtime graphs and full-stack execution remain unqualified.

Review [the release notes](release-notes.md), [withdrawal procedure](withdrawal.md),
and [public-only protection/reporting gates](repository-protections.md). Actual
channel activation and notification delivery are not claimed at freeze. Task 13
must verify them before tag/release finalization using the single authorized
synthetic report; Task 14 follows up on that same report.

Any source, dependency, workflow, scope, or release-content change invalidates
this freeze: create a new reviewed commit, rerun applicable checks, regenerate
assets/manifest/checksums, and present the new identity. Do not amend a published
tag or silently replace approved assets. No withdrawal or publication operation
is authorized by creating this record.
