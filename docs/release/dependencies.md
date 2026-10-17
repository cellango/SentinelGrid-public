# Source-preview dependency review

The original Task8/12/13 dependency reviews are retained as dated release evidence.
On October17, 2026, the MCP source-boundary work extended the Python source-test
environment from43 to54 exact pins without changing any previous package version.
All54 exact package/version OSV queries returned zero findings. A fresh macOS arm64
Python3.13 installation checked each selected wheel against the catalog of959 official PyPI
artifact hashes and passed `pip check`. The current graph was not executed on Linux or
hosted CI. Historical43pin Ubuntu results do not establish that expanded closure.

The unchanged frontend retains two explicitly scoped development-tooling exceptions:
`braces` and `sprintf-js`; its historical raw audit exits1. This slice did not repeat
the frontend audit or change its inputs/exceptions. No application runtime, image,
installer or dependency bundle is cleared.

The machine-readable records are:

- [Resolved dependency/license inventory](../../third_party/preview-dependencies.json)
- [Dependency decisions and exact exceptions](../../publication/dependency-review.json)
- [Selected-source manifest catalog and runtime risks](../../publication/dependency-manifests.json)

## Supported dependency inputs

| Input | Reviewed result |
| --- | --- |
| `scripts/requirements-preview.txt` | 54 exact pins across the main file and included MCP SDK file;959 official PyPI artifact hashes; previous43pins unchanged |
| Python vulnerability check | Current54pin OSV querybatch check: zero findings. Historical pip-audit43pin review retained separately |
| Python installation | Current54pin fresh macOS arm64 install/pip check passed; expanded Linux/hosted checks remain pending. Task10 Ubuntu proof covered the historical43pin graph |
| Python source checks | Current IAM/MCP boundary checks recorded with the candidate; historical Task10 Python/Ubuntu checks retain their original scope |
| `frontend/package.json` and lockfile | 828 locked package entries, all with official npm registry URLs and SHA-512 integrity; 772 installed on the review host |
| Frontend installation/tests | Fresh Node.js 22.23.3 `npm ci --ignore-scripts` and all 13 focused tests passed |
| Frontend parser overrides | Tailwind utility generation, nested-selector transformation, and Next.js resolution of patched PostCSS passed |
| Frontend vulnerability check | Initial 57 affected entries reduced to 40 propagated entries from two unique unpatched advisories; zero critical findings remain |

Counts include development dependencies. Optional platform packages are included
in the lock/license inventory even when not installed on this host. The
[Task 10 record](history-strategy.md#task-10-private-github-verification) binds the
actual Ubuntu checks to a commit. Windows installation/execution has not been
qualified.

## Security updates and reproducibility

PyJWT moved from 2.10.1 to 2.15.1, pytest from 8.4.2 to 9.1.1, and Starlette from
0.50.0 to 1.8.0. FastAPI 0.143.2 and pytest-asyncio 1.4.0 provide the compatible
framework/test environment. New transitive `opentelemetry-api` 1.45.1 and installer
pip 26.2.1 are also explicitly pinned. The complete file enforces
[pip hash checking](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode);
no dependencies are supplied by an existing developer environment.

Task 10's first actual Ubuntu run found that SQLAlchemy also requires `greenlet`
on Linux x86_64. The earlier macOS arm64 resolution and cross-platform wheel
download did not establish that platform's complete dependency closure. Added
[`greenlet` 3.5.6](https://pypi.org/project/greenlet/3.5.6/) with all 79 unyanked
release-artifact hashes, bringing Task10’s list from42 to43pins. Its MIT
and PSF-2.0 license files are recorded in the resolved inventory. Hash enforcement
remains enabled; the initial installation failure was not skipped or suppressed.

Next.js and its ESLint configuration are pinned to 15.5.28, Axios to 1.20.0, and
PostCSS to 8.5.30. The regenerated lock also resolves sharp 0.35.5. Targeted
overrides prevent Next.js from retaining its old nested PostCSS and use
postcss-selector-parser 7.1.6. The parser smoke checks cover those overrides;
they do not qualify a full frontend build. See the upstream
[Next.js Windows advisory](https://github.com/vercel/next.js/security/advisories/GHSA-p293-qw3h-jr36),
[Next.js image advisory](https://github.com/vercel/next.js/security/advisories/GHSA-2xp9-vwfh-vxw4),
and [sharp advisory](https://github.com/lovell/sharp/security/advisories/GHSA-wq5f-xc86-pv6w).

Frontend dependency lifecycle scripts are disabled for the supported installation
and CI command. The focused tests work with the committed optional packages;
installed dependency code and native binaries remain outside publication contents.
The application, React, Jest, and Tailwind major versions were retained.

## Two scoped tooling exceptions

| Package/advisory | Scope and disposition |
| --- | --- |
| `braces` 3.0.3 — [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm), high | Development-only glob parsing through micromatch/chokidar. The supported one-shot command uses fixed checked-in test paths and repository-controlled patterns. No patched release is available. |
| `sprintf-js` 1.0.3 — [GHSA-hp3w-g68c-fv3c](https://github.com/advisories/GHSA-hp3w-g68c-fv3c), moderate | Development-only formatting through argparse/js-yaml/coverage configuration tooling. The supported command accepts no externally supplied format string. No patched release is available. |

These are the Task 8 technical assessment, maintained by `cellango`, rechecked
at the Task 12 freeze on October 15 and the Task 13 refreeze on October 16,
still expiring November 14, 2026. The
official registries/advisories still report no patch for either issue; supported
inputs and commands are unchanged. Recheck if a patch/advisory appears or the
command/input surface changes; never publish with an expired exception. This
does not record a separate owner approval of runtime use.

A crafted pattern or format can still stop a tooling process. The scope is local
mocked tests and the read-only CI job with a 15-minute timeout. Watch mode, full
builds, arbitrary user patterns/formats, and a server runtime are outside this
disposition. New advisory IDs, packages, versions, or input paths need fresh review.
No audit severity filter, development-dependency omission, or global ignore is used.
The 40 npm entries include dependent packages affected by the same two advisories;
they are not 40 distinct vulnerabilities.

## License boundaries

All 43 Python packages and 828 npm lock entries have a license record. The one
missing npm lock license, `exit` 0.1.2, was resolved to MIT using the published
package's `licenses` field and its installed `LICENSE-MIT`, with its hash recorded.
Python package metadata and installed license/notice files were inspected with
pip-licenses 5.5.5. License metadata is retained as declared rather than treating
every dependency as Apache-2.0.

The environment includes `jwcrypto` under LGPL-3.0-or-later, `psycopg2-binary`
under LGPL-3.0-or-later with its packaged OpenSSL linking exception, and `certifi`
under MPL-2.0. Optional sharp/libvips packages include LGPL terms; npm also includes
MPL-2.0, CC-BY-4.0, and Python license declarations alongside permissive licenses.
See [Psycopg's license](https://www.psycopg.org/license/),
[certifi's license](https://github.com/certifi/python-certifi/blob/master/LICENSE),
and [sharp's prebuilt-package documentation](https://sharp.pixelplumbing.com/install/).

This preview publishes manifests, hashes, original source, and the existing source
notices. It does not redistribute installed dependency trees, Python wheels,
native libraries, container images, fonts, or generated bundles. A future binary
or container release needs review of exact bundled component licenses, notices,
modifications, and applicable source-delivery terms. This record does not grant
that clearance. Preserve [the existing license boundaries](../../LICENSING.md).

## Experimental manifests

The catalog covers 121 selected dependency/build manifests: 52 Python requirement
files, three npm manifests, two npm locks, two Go modules and two sums, 49 container
recipes, ten Compose definitions, and one Helm chart. Only the Python preview file
and main frontend pair receive the resolved-environment disposition above.

The other 51 Python requirement files declare 37 distinct exact package/version
pairs; direct public PyPI metadata checks identify 13 known-affected pairs. Another
375 ranges/includes/options remain unresolved. The catalog lists exact affected
pins and advisory IDs. These checks do not construct or audit complete runtime
graphs. The other npm applications, Go graphs, container bases, models, charts,
and infrastructure providers also remain unqualified. Do not infer runtime or
redistribution safety from passing preview checks.

## Repeat the review

Use a separate audit-tool virtual environment with pip-audit 2.10.1 and
pip-licenses 5.5.5. The public advisory queries require network access:

```bash
pip-audit --no-deps --disable-pip -r scripts/requirements-preview.txt --format=json
cd frontend
npm audit --package-lock-only --json
```

The Python query must report no findings. The npm query currently exits 1; compare
every direct advisory and affected version with the two exact scoped records,
including expiry and input conditions. Any additional finding fails this review
until fixed or separately assessed. Keep raw reports private. After dependency
changes, refresh hashes/license records and installation/tests. Task 12 reran
the audit with fresh advisory data against the frozen inputs. Task 10
rebuilt the independent repository from the reviewed source and verified private
GitHub CI. Task 13 applied the actual public protections and refreezes only
documentation/verification records before the source-preview tag and prerelease.


## MCP protocol-test extension

The selected1.x SDK is explicitly pinned to `mcp==1.30.0`; SDK2 uses a different
API/dependency graph and was not selected or qualified. The eleven additional
packages are MCP, httpx-sse, jsonschema, sse-starlette, uvicorn, attrs,
jsonschema-specifications, referencing, rpds-py, python-multipart and click.
[`requirements-mcp-sdk.txt`](../../scripts/requirements-mcp-sdk.txt) contains exact
pins and148 official PyPI artifact hashes and is included by the existing preview
manifest. Their installed license files and upstream MIT/BSD-3-Clause/Apache-2.0
declarations are recorded in the dependency inventory. Dependencies retain those
terms; no installed package implementation/native binary is published here.

Real MCP initialization/discovery and unavailable-tool errors are required by
`make preview-check`. The new graph has a fresh54package macOS installation and a
current exact-version advisory check. Neither result qualifies all service/runtime
requirements, every platform, provider operations or a redistributable bundle.
The service SDK pin does not resolve the rest of its experimental runtime graph.
