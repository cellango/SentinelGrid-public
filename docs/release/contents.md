# Selected public source-preview contents

The frozen selection contains **3,239 files** for developer review and comments.
Task 5 originally selected 3,454 files; the later source restoration, dependency
records, and documentation consolidation below explain subsequent changes.
The owner chose to include the sanitized cloud-provider work as **experimental
review source** on October 15, 2026. No application runtime is supported by this
selection. The existing private GitHub repository is not cleared for a visibility
change.

The exact path inventory is [publication/source-files.json](../../publication/source-files.json).
[publication/scope.json](../../publication/scope.json) records module dispositions,
the cloud bundle, and exclusions. Content hashes and the starting diff are retained
privately for this review; Task 12 binds the selected bytes and verification
to the full SHA in the prepared release manifest. The inventory is a selection record, not a secret
scan filter or a release tag.

## Included modules

| Material | Disposition |
| --- | --- |
| Review entrypoints, Makefile, source checks, and one active source-preview workflow | Current local review/CI tooling; no cloud credentials or deployment |
| `backend/` | Service/library source, schemas, migrations, and tests retained as experimental code; documented isolated auth/schema checks supported |
| `frontend/` | Main frontend source and focused auth tests; full build and service/cloud integration unqualified |
| `website/` | Secondary website source and attributed starter assets; runtime/build not supported |
| AI Shield, Pentest, Posture, and SentinelGuard | Experimental source/tests for review; active scans, cloud mutation, enrollment, telemetry, and packaging excluded |
| `docs/` and component documentation | Current public-review records and retained technical/historical documentation; historical claims do not qualify this snapshot |
| Infrastructure, Packer, Terraform, charts, Compose, observability, and remaining scripts | Inspectable reference/experimental source; deployment, cloud apply, images, installer repackaging, and publication excluded |
| Synthetic configuration, seed logic, catalogs, and rules | Source examples for review; no customer datasets or live target configuration selected |
| Licensing, `third_party/`, and Wazuh reference metadata | Complete notices and provenance retained; installers and dependency bundles excluded |

All owner-excluded business documents remain private. Retained historical
documents remain development records, including old production, completion,
benchmark, and audit statements. Task 9 reconciled their claims and navigation
with the preview boundary; inclusion here does not turn those statements into
current evidence. Private test reports referenced by historical docs are not
included as attachments or build artifacts.

## Experimental cloud bundle

The selection includes provider-neutral registry/types, the Hetzner adapter,
target normalization, baseline controls, remediation/change-request helpers, IAM
and Gateway routes, scanner dispatch/jobs, frontend onboarding changes, synthetic
registry examples, the ORM model, its pending V013 migration, and associated tests.
The complete bundle paths are in `publication/scope.json`.

The V013 migration keeps its globally unique version and `public` search path.
The ORM model was aligned with that pending migration: JSONB fields, server
defaults, explicit schema, and four indexes now agree. Three offline contract
tests compare the model with the independent Flyway SQL. The SQL migration itself
was preserved without change. No database was created, upgraded, or migrated.

The example endpoint uses documentation address space and synthetic resource IDs
and domains. Other provider declarations can remain planned/unimplemented;
registry/UI presence is not provider-runtime qualification. No real credentials,
account access, provisioning, approval/apply execution, or customer environment is
part of the supported preview.

## Preserved exclusions and working changes

The reviewed selection preserves the preparation fixes and the owner's cloud work
in shared files. A private starting archive and binary diff preserve the current
changed/new files and starting changes; earlier private copies remain intact.
Nothing was staged, committed, rewritten, pushed, or published for this selection.

Excluded contents include private evidence and business documents, environment
secrets, credential/scanner exports, databases, Terraform state/plans, personal
tool state, browser captures, caches, bytecode, installed dependencies, installers,
and generated bundles. Existing Git history and hosted PR/log material require
the separate publication strategy in Tasks 6 and 7. See the
[private-data review](private-data.md) and
[provenance review](provenance.md).

## Verify or revise the selection

Run `python3 scripts/publication_inventory.py` to verify path membership.
`make preview-check` also checks the inventory and the V013 model contract.
New or removed candidate paths fail the inventory check. Secret scanning still
examines all candidate files, including newly added and force-added ignored files;
the selected inventory cannot hide a file from those scans.

After reviewing a deliberate content change, run
`python3 scripts/publication_inventory.py --refresh`, inspect the resulting
inventory diff, and rerun the source and secret checks. Refresh refuses private
file patterns and symlinks; it does not itself clear content, licensing, or runtime
security. A changed file's contents still require review even when its path stays
the same.

Continue with the [publication checklist](tasks.md).

Local verification passed 81 focused Python tests: four inventory tests, three
model/migration contract tests, 14 IAM auth tests, 56 cloud onboarding/control
tests, and four scanner-dispatch tests. Source hygiene compiled 1,373 Python files
and Ruff checks passed. Syntax transpilation passed for the three cloud frontend
files; this was not semantic type checking or a full build. The candidate secret
scan found zero matches. No live provider, database migration, deployment, or
public visibility change was performed.

The completed [Task 6 strategy](history-strategy.md) preserves the
private history, business-document, hosted-material, and installer dispositions.
It adds the approved strategy record
to the selected source inventory; the original Task 5 count above records that
task's snapshot before this reviewed documentation addition.

Task 7's isolated check exposed application Python packages hidden by broad ignore
rules. Seventy-two reviewed source files were restored with narrow Python-only
exceptions, bringing the Task 7 inventory to **3,527 files**. Private payloads,
caches, downloaded model files, and historical material remain excluded. The
rebuilt independent root snapshot passed source/history scans and the supported
Python checks. See [the Task 7 record](history-strategy.md#task-7-local-verification).
Later reviewed changes still require a refreshed inventory and final release freeze.

Task 8 updates the preview dependencies and adds the dependency/license review,
resolved inventory, manifest catalog, and exact scoped exception record. These
records are selected source metadata; installed dependencies remain excluded.
See [the dependency review](dependencies.md). Task 10 rebuilt the independent
snapshot from reviewed files before its first private push.

Task 9 reorganizes documentation and omits superseded design/progress/business
material, bringing the Task 9 selection to **3,231 files**. The 415 retained
Markdown files have explicit classes and valid selected-source links. See the
[documentation review](documentation.md) and
[classification inventory](../../publication/documentation.json). The prior local
root commit was rebuilt in Task 10; its old tree contains material now excluded.

Task 11 adds the repository-settings policy, its classified release review, and
the configured private-report form/issue chooser, bringing the selection to
**3,235 files and 416 Markdown files**. Applied Actions controls and pending
reporting/public-only controls are distinguished explicitly.
See [the protection review](repository-protections.md). Publication remains pending.

Task 12 adds the candidate/release/withdrawal guides and exact release plan,
bringing the frozen selection to **3,239 files and 419 Markdown files**. Generated
source-only release assets and their commit-bound manifest are prepared separately;
they are not committed or included in the selected source tree. See
[candidate verification](candidate.md).
