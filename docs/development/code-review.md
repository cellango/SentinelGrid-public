# Code review guide

Start with the root [README](../../README.md) for supported setup/check commands,
[CONTRIBUTING](../../CONTRIBUTING.md) for submissions, and [architecture](../architecture/overview.md)
for ownership. This guide replaces the old full-stack quick-start instructions.

## Useful review questions

- Does the gateway derive tenant identity from authenticated context and forward a UUID?
- Do service queries and mutations enforce that same tenant, including internal routes and jobs?
- Are approvals bound to the exact request, actor, scope, current state, and replay policy?
- Does a declared agent, provider, or feature flag correspond to a concrete implementation?
- Are failures and simulated data represented honestly rather than reported as completed work?
- Do model changes have the matching Flyway migration and offline contract coverage?
- Do dependency changes preserve pins, artifact hashes, licenses, and the dated risk decisions?

## Where checks live

| Check | Entry point |
| --- | --- |
| Selected paths and source hygiene | [check_public_preview.py](../../scripts/check_public_preview.py) |
| Exact publication path membership | [publication_inventory.py](../../scripts/publication_inventory.py) |
| Python review dependency lock | [requirements-preview.txt](../../scripts/requirements-preview.txt) |
| Inventory regressions | [scripts/tests](../../scripts/tests/) |
| Model/DDL contract | [test_infrastructure_change_schema.py](../../backend/tests/test_infrastructure_change_schema.py) |
| Shared IAM receipt boundary | [test_verifier_boundary.py](../../backend/tests/gateway_identity/test_verifier_boundary.py) |
| Named IAM auth regressions | [test_auth_api.py](../../backend/agents/iam_agent/tests/test_auth_api.py) |
| Frontend focused suite | [package.json](../../frontend/package.json), `test:preview` |
| Source/history secret scans | [scan_public_secrets.py](../../scripts/scan_public_secrets.py) |
| Credential-free CI | [source-preview.yml](../../.github/workflows/source-preview.yml) |

Each service uses an `app` package. Run service suites in separate processes;
otherwise imports can resolve to a different service. Supported Python checks
compile source and run isolated mocked/offline tests. Other test folders may need
unqualified runtime dependencies or live services; their presence is not a pass.
Use synthetic data and keep scanner output private. No full-stack runtime is
advertised by the source preview.

Follow [database changes](database-changes.md), [documentation maintenance](documentation.md),
and [the dependency review](../release/dependencies.md) when changing those areas.
