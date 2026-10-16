# Developer source preview scope

Status: **source review only; publication gates still open**. Reviewed October 15,
2026. Preparation started at commit `efdca69` with existing uncommitted
cloud-provider work. Validation describes the working tree, not a release tag.
See [the review record](docs/release/review.md).
The [selected contents](docs/release/contents.md) and
[exact path inventory](publication/source-files.json) record the Task 5 selection,
including owner-approved experimental cloud-provider source.

Original SentinelGrid code is licensed under [Apache-2.0](LICENSE). Existing
third-party terms and component notices are preserved; see [LICENSING.md](LICENSING.md).

| Surface | Included verification | Runtime support |
| --- | --- | --- |
| Main frontend | Focused auth/recovery tests | Full build and backend integration remain separate gates |
| IAM auth | Isolated HTTP regressions with mocked dependencies; direct-reset requests return 410 without account mutation | Other identity, token, realm, and admin paths need further review |
| Backend/shared libraries | Source compilation, undefined-name checks, and offline V013 model/DDL contract | Fresh installation, migration execution, tenant isolation, and startup not certified |
| SentinelGuard | Go source for review | Live enrollment, telemetry, and packaging excluded |
| AI Shield | Existing component source and license | No new bundled-snapshot security clearance |
| Posture/cloud providers | Experimental source, including work in progress | Customer accounts, provisioning, and remediation excluded |
| Pentest | Experimental source | Active scans, autonomous tools, and exploitation excluded |
| Infrastructure/Packer/packaging | Historical designs; AMIs private by default; publication workflows disabled | Cloud apply, image builds, repackaging, and publication excluded |

No UI, API, job, or background worker is advertised as a supported runtime in this
preview. Supported commands run local source checks and mocked tests only. Legacy
Compose files and deployment scripts remain inspectable; invoking them manually
runs experimental code outside this scope. Disabling workflows does not repair
experimental services' authorization or execution boundaries.

## Review environment

- Git and Python 3.13 for inventory, compilation, and targeted IAM auth tests.
- Ruff 0.15.7 for undefined names and Python syntax.
- Node.js 22 with `frontend/package-lock.json` and `npm ci --ignore-scripts` for focused frontend tests.
- Gitleaks 8.30.1 for candidate source and all locally available Git refs.
- GitHub-hosted Ubuntu for public CI; no cloud credentials or OIDC.

Source checks need no Docker, database, identity provider, model, or cloud account.
IAM tests use FastAPI's HTTP client with mocks; they do not establish end-to-end
identity or tenant safety. Historical completion, audit, hardening, and compliance
claims are development records rather than verification of this snapshot.

The [Task 8 dependency review](docs/release/dependencies.md) covers the hashed Python
review environment and locked main frontend installation. It records two scoped,
dated exceptions for unpatched development tooling and the separate third-party
license terms. Other runtime dependency graphs remain unresolved.

## Future runnable beta

The intended demonstration is synthetic event → detection → incident → reviewed
non-destructive response → evidence/report. This preparation does not claim it
passes end to end. Before supporting it, select the exact services, disable other
routes/jobs in that runtime, prove clean-clone installation and Flyway upgrades,
verify two-tenant denials and approval replay protection, and inject model/service
failures without downstream mutations. Bind results to an exact commit before
changing this scope.
