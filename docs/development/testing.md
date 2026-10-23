# Local tests and contract reconciliation

Use the root [preview setup](../../README.md#run-the-source-checks), Python 3.13
with `scripts/requirements-preview.txt`, and Node.js 22 for frontend tests.
Activate the existing `.venv` before invoking Make, or supply
`PYTHON=.venv/bin/python RUFF=.venv/bin/ruff`. Do not use the system Python or
create another environment merely because an import fails. First check the
interpreter and pinned prerequisites. Each service's `app` imports require its
own process and configured test entrypoint.

## Explicit test profiles

| Command from repository root | Scope and prerequisites | What it does not prove |
| --- | --- | --- |
| `make preview-tooling` | Source compilation/inventory/doc links, contract structure and tooling unit tests; pinned Python environment | Application or provider operation |
| `make preview-impact BASE=<reviewed-commit>` | Read-only comparison of base to working tree, including staged, unstaged, deleted and non-ignored new files; unknown paths fail for review | Semantic adequacy or tests passing |
| `make preview-check` | Existing selected source/IAM/MCP/gateway/workload/action/legacy denial regressions and F821 lint; separate service processes | Whole repository collection, actual Temporal, live effects or full E2E |
| `make preview-frontend` | Existing three focused auth suites; frontend dependencies already installed from lockfile | Complete UI or approval workflow coverage |
| Native database profiles | Explicit opt-in disposable PostgreSQL/Flyway tools; follow [application DB](../reference/application-database.md) and [role gate](../reference/action-database-role.md) | Existing-installation adoption or live-provider qualification |

These targets do not install dependencies, enable CI or invoke legacy shell test
runners. `preview-tooling` writes no product state; tests may use temporary
fixture directories. The preview regression tests use synthetic fixtures and
may exercise local test servers. Native database checks create and destroy
only their documented owned lab. Do not run arbitrary repository-wide pytest
collection: imports/fixtures and old runners can contact services or require
product credentials. Inspect prerequisites and side effects before adding a
suite to a supported profile. Legacy `scripts/run-tests.sh`, `run_tests.sh` and
component instructions remain experimental; they are not substitutes for the
root profiles. Preserve their coverage obligations during deliberate migration.

## Contract ledger and review loop

[The scoped ledger](../../publication/contracts.json) maps accepted design to
implementation paths, test files or Python node selectors, current documentation,
owner role and explicit gaps. It begins with selected runtime/action/database
seams and developer tooling, not every repository test. A target row references
its present seam and negative tests; its gap must name missing positive
implementation/qualification. A replacement link records planned coverage;
it does not authorize retiring the old test or establish equivalent behavior.

For every focused change:

1. Inspect the branch/diff; identify affected contract rows, obligations and owner.
2. Implement the bounded change and add/update meaningful positive and negative
   tests. Separate stale expectations, real defects and missing prerequisites.
3. Reconcile documentation, statuses and exact paths/selectors. Use keep, update,
   replace or archive with reasons. For replacement/archive, map a successor and
   review equivalent coverage, compatibility/drain and any remaining gaps before
   retiring anything. Retain historical material with clear non-authority.
4. Run `preview-tooling`, `preview-impact BASE=<reviewed-commit>`, and relevant
   local regression/native integration profiles. New or deleted unmapped paths
   require an explicit contract review; no wildcard ignore baseline is provided.
5. Record commands, interpreter/profile, revision/diff, pass/fail/skip counts and
   limitations in the review evidence. Private logs stay private. Review the diff
   and evidence before requesting the agreed commit/push checkpoint approval.

The validator uses selected source paths and AST lookup for optional Python
`file.py::Class::test_method` selectors. It never imports product modules or
executes ledger commands. Parameterized node suffixes and dynamic selectors must
use file references with the exact invocation recorded in review evidence.
Checks reject missing references, duplicate IDs, unsafe paths, historical docs
as current authority, and absent successor mappings. They cannot prove test
assertions are sufficient. Evidence is deliberately `not_asserted`: passing,
skipped or unrun execution claims are rejected in this static ledger. Actual
results belong in scoped review evidence, not permanent green flags.

`preview-impact` compares the named base directly to the working tree (not a
merge base), so select and record the intended review commit. It includes both
sides of renames and non-ignored new files. Deleted paths require explicit `retired_paths` in the owning row, a reason and
a successor contract with test coverage. Retired paths must be absent and
repository-relative. Review equivalent coverage before removal; this structural
record does not itself authorize deleting a test. The initial ledger is
intentionally incomplete: unrelated changes fail until their contracts are
reviewed and mapped. Do not label all retained tests semantically reviewed.

Keep tenant isolation, exact authority, expiry/revocation and recovery tests.
Do not remove tests to obtain green results. A quarantine retains owner, reason,
replacement coverage and a re-entry criterion; skipped is not passed. Source
checks and simulated effects are never live containment or full E2E evidence.
CI execution is separate from local checks; this tooling does not alter CI state.
