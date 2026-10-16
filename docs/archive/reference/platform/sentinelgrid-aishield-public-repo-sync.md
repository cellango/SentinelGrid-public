# SentinelGridAIShield Public Repo Sync Workflow

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This repository currently contains the canonical working copy of `SentinelGridAIShield` under:

- `SentinelGridAIShield/`

When the public repository exists, use the scripts below to keep the public repo in sync with this monorepo without manually copying files.

## Scripts

- [export-sentinelgrid-aishield-public.sh](../../../../scripts/export-sentinelgrid-aishield-public.sh)
- [sync-sentinelgrid-aishield-public.sh](../../../../scripts/sync-sentinelgrid-aishield-public.sh)
- [push-sentinelgrid-aishield-public.sh](../../../../scripts/push-sentinelgrid-aishield-public.sh)

## What The Export Includes

The export script copies the public-ready `SentinelGridAIShield` subtree while excluding monorepo-only implementation summaries and generated caches.

## Initial Setup

1. Create the new public GitHub repository.
2. Clone that public repository somewhere on the same machine.
3. The exported subtree already includes the Apache-2.0 `LICENSE` file.

Example:

```bash
git clone git@github.com:<owner>/SentinelGridAIShield.git ~/src/SentinelGridAIShield-public
```

## Dry-Run Sync

This updates the working tree of the public repo checkout but does not commit or push:

```bash
./scripts/sync-sentinelgrid-aishield-public.sh \
  --target ~/src/SentinelGridAIShield-public
```

## Sync And Commit

```bash
./scripts/sync-sentinelgrid-aishield-public.sh \
  --target ~/src/SentinelGridAIShield-public \
  --commit
```

## Sync, Commit, And Push

```bash
./scripts/sync-sentinelgrid-aishield-public.sh \
  --target ~/src/SentinelGridAIShield-public \
  --commit \
  --push \
  --branch main
```

## One-Command Push

When the public repo exists and you want the common path of sync + commit + push, use:

```bash
./scripts/push-sentinelgrid-aishield-public.sh \
  --target ~/src/SentinelGridAIShield-public \
  --branch main
```

Optional custom commit message:

```bash
./scripts/push-sentinelgrid-aishield-public.sh \
  --target ~/src/SentinelGridAIShield-public \
  --branch main \
  --message "Sync AI Shield docs and SIEM export contract"
```

Environment-variable form:

```bash
PUBLIC_REPO_PATH=~/src/SentinelGridAIShield-public \
PUBLIC_REPO_BRANCH=main \
./scripts/push-sentinelgrid-aishield-public.sh
```

## Safety Checks

The sync script:

- requires the target path to be a git repository
- refuses to run if the target repo has uncommitted changes
- preserves an existing `LICENSE` file in the target repo if the exported source does not include one
- prints the target repo diff summary before any commit or push

## Recommended Maintainer Flow

1. make changes under `SentinelGridAIShield/` in this monorepo
2. validate docs, examples, and tests locally
   Suggested commands:
   `cd SentinelGridAIShield/services && pytest tests/test_siem_export.py`
   `python3 -m compileall SentinelGridAIShield/services/app SentinelGridAIShield/services/tests`
3. run the sync script against your local checkout of the public repo
4. review the diff in the public repo checkout
5. commit and push from the script, or commit manually if you want a custom review step
