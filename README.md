# SentinelGrid

SentinelGrid is an experimental security operations platform combining detections, incidents, identity, cloud posture, endpoint telemetry, and AI-assisted workflows.

**Developer source preview:** this repository is being prepared for architecture review and feedback. The full platform is not a supported runnable beta. Start with [release scope](RELEASE_SCOPE.md) and the [publication review](docs/release/review.md). Historical production, compliance, and phase-completion documents are development records, not a current release certification.

## Review the code

Follow the [publication task checklist](docs/release/tasks.md) to work through the remaining release gates one at a time.

| Directory | What to review |
| --- | --- |
| `frontend/` | Canonical Next.js console, onboarding, and marketing UI |
| `backend/` | FastAPI services, shared libraries, IAM, detections, and workflow agents |
| `SentinelGuard/` | Go endpoint collector and ingestion components |
| `SentinelGridAIShield/` | Separately licensed AI runtime security component |
| `SentinelGridPostureAgent/` | Experimental posture subsystem |
| `SentinelGridPenTestAgent/` | Experimental pentest subsystem; execution excluded |
| `infra/`, `terraform/`, `charts/`, `packer/` | Deployment designs retained for inspection; deployment excluded |
| `website/` | Archived marketing/reference application |

Useful review topics include tenant isolation, authorization, approvals, service boundaries, dependency management, and the operator experience. Use synthetic data. Follow [SECURITY.md](SECURITY.md) for vulnerability reports and [CONTRIBUTING.md](CONTRIBUTING.md) for proposed changes.

For ordinary feedback, open an issue with the **Developer review or feedback**
template and include the revision and source area reviewed. The
[documentation index](docs/README.md) separates current guides from historical
references; retired designs and progress reports are recoverable privately.

## Run the source checks

Use Git, Python 3.13, and a POSIX shell. These checks do not start containers, connect to cloud accounts, provision resources, or require product credentials.

The checks verify the [selected source paths](publication/source-files.json),
documentation classification and local links, and
compare the pending V013 migration with its ORM model. See
[publication contents](docs/release/contents.md) for module boundaries and
the owner-selected experimental cloud work.

```bash
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install -r scripts/requirements-preview.txt
make preview-check
```

For frontend tests, use Node.js 22 and the committed npm lockfile:

```bash
cd frontend
npm ci --ignore-scripts
npm run test:preview
```

The Python file requires exact versions and verified artifact hashes. The
[dependency review](docs/release/dependencies.md) records the resolved licenses,
security updates, and two dated exceptions for unpatched development tooling.

Install [Gitleaks 8.30.1](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1) from the official release and verify its published checksum, then run:

```bash
make preview-secrets
make preview-history
```

Secret scans fail on unresolved matches. Reports stay under ignored `artifacts/private-release-review/`; review them privately. A passing source check does not replace the history scan or the publication gates.

## Runtime and licensing

Compose files and deployment scripts are retained as experimental implementation material. There is no supported full-stack quick start for this source preview. Default `make dev` and `make up` stop with an explanation. Legacy GitHub deployment, image, packaging, and integration workflows have a `.yml.disabled` extension.

Original SentinelGrid code is licensed under [Apache-2.0](LICENSE). AI Shield retains its existing Apache-2.0 license, and third-party components retain their respective terms. See [LICENSING.md](LICENSING.md) and [third-party notices](THIRD_PARTY_NOTICES.md) for the boundaries. Wazuh installers are not part of the source preview.

[Documentation index](docs/README.md) · [Agent guidance](docs/AGENTS.md)
