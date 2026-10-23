# Contributing to the developer preview

Read [release scope](RELEASE_SCOPE.md) and [licensing status](LICENSING.md) first.
Feedback on architecture, tenant boundaries, code clarity, and reproducibility is
welcome. Original SentinelGrid code is licensed under [Apache-2.0](LICENSE).

Unless explicitly stated otherwise, contributions intentionally submitted for
inclusion in original SentinelGrid code are provided under Apache-2.0, as described
in section 5 of the license. Contributions to separately licensed components must
comply with that component's terms. Preserve existing copyright and attribution
notices and identify the upstream source and license of third-party material.

## Checks

Use Python 3.13 in a virtual environment, install
`scripts/requirements-preview.txt`, and run `make preview-check`. It checks selected paths, source inventory, documentation classes/local links,
Python compilation, Ruff undefined names/syntax, the V013 model/migration contract,
and the named IAM auth suite. It is not the full platform suite. Each FastAPI service has an `app`
package; run service suites in separate processes to avoid import collisions.

For deliberately added or removed files, review the content and scope, then run
`python3 scripts/publication_inventory.py --refresh` and inspect its diff. The
inventory never filters files out of secret scans. See
[selected publication contents](docs/release/contents.md).

Keep one current page per topic in the [documentation folders](docs/README.md).
When adding or moving Markdown, update `publication/documentation.json` as well
as the selected paths. Follow [the documentation rules](docs/development/documentation.md);
do not restore retired design/status documents as current guidance.

Use Node.js 22 and `npm ci --ignore-scripts` in `frontend/`, then `npm run test:preview` for focused
frontend tests. Live integration and other component suites are experimental.
Do not describe mocked or skipped checks as passing end-to-end tests.

Keep the Python pins/artifact hashes and npm lock consistent with
[the dependency review](docs/release/dependencies.md). Recheck dated tooling exceptions
and resolved license records when dependencies or supported commands change.

Install official Gitleaks 8.30.1 and verify its release checksum. Run
`make preview-secrets` and `make preview-history`; both must pass for publication.
Review matches privately. Do not baseline or ignore an unreviewed match to turn
CI green. Maintainers must account for remote-only refs and external artifacts
separately from the locally available Git refs.

## Changes

Use focused branches and explain the problem, resulting behavior, and checks run.
Use synthetic credentials and dedicated tenant UUIDs. Keep local agent state,
environment secrets, databases, scanner exports, and vendor installers out of Git.
Follow [AGENTS.md](AGENTS.md); schema changes require matching model and
consolidated Flyway migration updates.

Use issues for ordinary bugs and review comments. Follow [SECURITY.md](SECURITY.md)
for private vulnerability reporting. Cloud provisioning, active scans, and
destructive tools are outside routine source-review checks.

Legacy deployment and packaging workflows use `.yml.disabled` extensions.
Restoring them requires review of permissions, protected environments, secrets,
provenance, and release tests.
