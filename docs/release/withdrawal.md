# Withdrawing a source preview

This procedure covers `cellango/SentinelGrid-public` and the proposed
`v0.1.0-preview.1` release. It prepares a response; it does not authorize a
visibility change, public message, deletion, ref rewrite, or credential change.
Keep the original private repository and its recovery copies unchanged.

## Before publication

If a check fails, an exception expires, the candidate changes, or a required
public-only control cannot be verified, stop release/tag finalization. Keep the
prepared assets private and record the reason. Fix the issue in a new commit and
repeat the freeze; do not reuse the old manifest or approval for changed bytes.

## After publication

1. Record the exact affected commit/tag, release and asset IDs, hashes, current
   visibility, and observed issue in private evidence. Preserve recovery copies
   before proposing changes. Report vulnerabilities through the private channel;
   do not post raw scanner reports, credentials, or customer data publicly.
2. Present the owner with the concrete proposed action and its effects: a release
   notice, removal of named assets/release/tag, a visibility change, or a separate
   history-remediation plan. Obtain approval before performing those actions or
   sending notices. Publication approval alone does not approve their deletion.
3. For an ordinary source defect, prefer a clear withdrawal notice and a corrected
   version with a new tag. Never silently move an existing tag or replace an
   approved asset while retaining its old version identity.
4. For sensitive exposure, have the owner assess actual credential use and
   necessary revocation/rotation and hosted copies. Deleting a working file or
   release does not clear commits, PR refs, logs, caches, forks, or downloaded
   archives. Review any rewrite and hosted cleanup separately.
5. Execute only the approved operations, then verify their actual results using
   authenticated and anonymous access as appropriate. Check release assets and
   Git refs separately. If immutable release settings apply, inspect their
   constraints before attempting asset/tag changes.
6. Record what remains accessible and the replacement version, if any. Re-run the
   source/dependency/publication checks before publishing a replacement, and
   preserve the withdrawn version's identity in the review record.

Making a repository private does not make its public forks private or recall
existing clones/downloads. See [GitHub's visibility consequences](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility).
GitHub documents [release editing/deletion and immutable-release limits](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).
Do not promise complete removal from third-party copies.
