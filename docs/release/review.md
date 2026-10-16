# Public source preview review — October 15, 2026

Decision: **publication pending**. Source cleanup and focused checks do not clear
the existing Git history, third-party history, or externally retained artifacts.
The original repository's visibility and Git history are unchanged. Task 10
rebuilt the independent snapshot after dependency/documentation review and created
the approved **private** `cellango/SentinelGrid-public` repository for CI.
No public visibility change, cloud deployment, release, or tag has occurred.

Work through the remaining gates using [Public Release Tasks](tasks.md).

## Scope and evidence

Preparation started at `efdca69` on `codex-test-suite-ci-hardening` with ongoing
uncommitted cloud-provider work. Those changes were preserved. The new Hetzner
migration was renamed from duplicate V012 to V013 without changing its SQL.
There is no immutable release commit yet.

The supplied HTML checklist described archive `641cd42`; it was treated as review
input, and findings were checked against this newer working tree. Its instructions
did not authorize publication, history rewriting, cloud deployment, or a license
change. Original SentinelGrid code is now licensed under Apache-2.0 following
the maintainer's explicit selection. The root [LICENSE](../../LICENSE),
[NOTICE](../../NOTICE), and [LICENSING.md](../../LICENSING.md) record that choice and
preserve third-party boundaries. [RELEASE_SCOPE.md](../../RELEASE_SCOPE.md) defines
the source-only preview.

## Changes completed

- Retired direct password reset with HTTP 410 in IAM and the frontend proxy;
  removed login UI/API-client use. Anonymous HTTP regression verifies no Keycloak
  client is constructed, including requests with realm/tenant overrides.
- Removed service-account secret retrieval/logging from realm seeding and the
  documentation recommending secret-bearing console output. Debug token tooling
  no longer embeds a named account/password or prints a token prefix.
- Disabled all historical deployment, image, package, and integration workflows
  using `.yml.disabled`. Added a read-only, secret-free public workflow with
  immutable action pins and checksum-verified scanner downloads. Secret findings
  fail CI; no scanner reports are uploaded publicly.
- Removed bundled Wazuh installers and the old unredacted scanner report from the
  candidate source tree. Preserved local copies under ignored
  `artifacts/private-release-review/`; historical copies remain a separate gate.
  Replaced both placeholder Wazuh licenses with the complete upstream license,
  including copyright, GPL v2, and component/linking notices.
- Added root scope, contribution, security, licensing, and third-party documents;
  made the docs index defer to the preview boundary. Historical image/benchmark
  claims do not certify this snapshot. AMI defaults no longer share to `all`.
- Added Git/Docker context hygiene and checks for private artifacts, Python
  compilation, consolidated Flyway versions, and active workflow inventory.
- Repaired current undefined names and syntax defects, including connector mapping
  unpacking, duplicate test keywords, pentest test imports, and entitlement audit
  serialization used before assignment. Removed an orphan duplicate MCP runner;
  the canonical runner remains in `app/main.py`.
- Removed credential-like documentation values and substituted environment
  placeholders. Tasks 1 and 2 recorded owner-confirmed local-only use for the
  reviewed credentials; history and artifact disposition remain open.
  Scanner exceptions are exact-value AND exact-path matches for synthetic tests,
  a rule identifier, a database address, and historical image tags. Default scanner
  rules remain enabled; no history baseline is used.

## Verification

| Check | Result |
| --- | --- |
| `make preview-check` | Passed in a fresh temporary Python 3.13 virtual environment; 1,368 Python files compiled, 3 inventory regression tests and 14 IAM HTTP/auth tests passed, Ruff F821/syntax passed |
| Frontend `npm ci` and `npm run test:preview` | Passed in a clean temporary source copy with checksum-verified Node.js 22.23.3; 3 suites, 13 tests passed |
| Candidate source secret scan, Gitleaks 8.30.1 | Passed: zero findings with reviewed exact-path/exact-value exceptions |
| Scanner exception canaries | 3 checks passed: known fixture allowed; same value elsewhere and changed value at the fixture path both detected |
| Original private history, Gitleaks 8.30.1 | **137 scanner rows remain; all classified in Task 1 and excluded from the independent publication history** |
| Active workflow syntax, actionlint 1.7.12 | Passed |
| Patch whitespace check | Passed |
| Task 3 source and cloud checks | Passed: 1,371 Python files compiled; 3 inventory tests, 14 IAM auth tests, Ruff checks, and 47 additional cloud tests; candidate secret scan found zero matches |
| Task 4 provenance checks | Passed: 10 asset hashes, 9 exact upstream license copies, attribution rendering, notice links, source hygiene/compilation, and candidate secret scan |
| Task 5 contents and cloud consistency | Passed: 3,454 selected paths, 1,373 Python files compiled, 81 focused Python tests, three frontend syntax checks, and zero candidate secret matches; V013 SQL unchanged |
| Task 7 independent local snapshot | Passed: 3,527 files, one root commit/`main`, no tags/remotes/imported commits/shared storage, exact byte/mode checks, strict Git object verification, and zero source/history secret matches |
| Task 7 isolated Python checks | Passed after restoring 72 ignored application source files: 1,445 Python files compiled, 22 tests and Ruff; private-payload ignore regression included |
| Task 8 supported dependencies | 42 hash-verified Python pins with zero reported advisories; frontend refreshed with zero critical findings and two exact unpatched tooling exceptions; 42 Python/828 npm license records |
| Task 8 dependency compatibility | 22 Python tests and 13 frontend tests passed; parser override smoke checks and Python 3.13 Linux wheel resolution passed; actual Ubuntu execution remains Task 10 |
| Task 9 documentation and claims | Passed: 415 classified Markdown files with valid local links, 28 Python tests/1,447 compiled files, 13 frontend tests, five TSX syntax checks, scanner canaries, and zero source secret findings; 320 retired/private docs preserved |
| Task 10 clean clone and actual GitHub CI | Passed: rebuilt 3,231-file root; fresh clone checks; all four Ubuntu jobs passed after adding/auditing the Linux-specific Python pin; deliberate defects failed all four jobs, and the disposable branch was removed. See [commit-bound evidence](history-strategy.md#task-10-private-github-verification) |
| Task 11 protections/reporting | In progress: Actions allowlist/SHA/read-only settings applied and all four jobs passed. Private reporting contact/delivery is pending. Branch/native-secret/fork/form settings are unavailable while private; exact public-activation payloads are prepared in [the protection review](repository-protections.md) |

The Python test run reported existing Pydantic/SQLAlchemy/test-client deprecation
warnings. The clean npm install reported deprecated transitive packages. These
earlier results are focused source-preview checks. Task 8 separately records the
resolved dependency audit, license boundaries, and two unpatched tooling exceptions.
The workflow has run on private GitHub Actions. Full-stack startup/build, cloud
plans, active scans, endpoint enrollment, and adversarial two-tenant E2E are outside
this source preview and were not certified here.

The initial Gitleaks 8.30.1 default-rule history scan reported **156 matches** across
all locally available refs; the initial candidate snapshot reported **87 matches**.
These are potential matches, not a count of exposed live credentials. Redacted
and local-only triage evidence stays in ignored `artifacts/private-release-review/`.
Do not attach that directory to public issues or release artifacts.

Task 1 is complete: [the historical secret review](historical-secrets.md)
records classifications for all 137 rows, representing 22 distinct values.
The owner confirmed the Keycloak and Vault candidates were disposable local
examples.

The completed [Task 2 review](credentials.md) classifies the current
default references and records 26 passing local regression tests plus eight
offline behavior observations. The owner confirmed both published defaults were
local development only, so shared-environment rotation is not applicable for the
reviewed groups. Experimental agent-runtime and AI Shield Go fallback acceptance remains
outside the supported preview; no external credentials have been changed.

The completed [Task 3 review](private-data.md) records the owner's
synthetic-example confirmation and private-business disposition. Forty-eight
business documents and five generated artifacts were removed from the candidate,
with recoverable originals retained locally. Personal paths and real cloud target
metadata were sanitized. The existing private GitHub repository was inventoried;
its history, hosted PR material, and logs are not cleared for public visibility.

The completed [Task 4 review](provenance.md) records the owner's
original-source/logo confirmation, six exact Next.js starter asset matches, and
complete upstream license notices. Five Wazuh installers remain private; four
installer blobs in local history are excluded from publication refs. Existing
local digests do not authenticate upstream packages. Original scripts remain
source for review, with unsupported redistribution claims corrected.

The completed [Task 5 selection](contents.md) records the exact path
inventory and module dispositions. The owner selected the cloud-provider work as
experimental review source. The ORM model now agrees with pending V013 SQL on
JSONB types, server defaults, public schema, and four indexes. Private starting
copies preserve the combined working changes; that selection did not create a
commit or release freeze. Full runtime, database upgrade, and frontend integration remain
outside this selection's verification.

The owner approved the [Task 6 history strategy](history-strategy.md):
an independent `cellango/SentinelGrid-public` snapshot, kept private through
preparation and CI, with only `main` intended for publication. The existing
repository and hosted material remain private. Verified recovery copies cover
all 41 local refs/359 reachable commits and the selected source. Task 7 completed
local isolated preparation; Task 10 rebuilt the snapshot, created the approved
private repository, and pushed its independent `main`. Final visibility/tag
approval remains Task 13.

The [Task 7 record](history-strategy.md#task-7-local-verification)
documents the verified independent root snapshot. Its first isolated test run
found application source hidden by generic ignore rules; 72 reviewed Python files
were restored with source-only exceptions. The rebuilt copy passed the supported
Python checks and both secret scans. Private original history, quarantines,
installer blobs, and hosted material were not imported. The snapshot is local and
preparatory; exact release identity remains open.

The [Task 8 dependency review](dependencies.md) updates the supported Python
and frontend inputs, requires exact Python artifact hashes, and records resolved
licenses. Python audit reports zero findings. Raw npm audit still reports two
unpatched development-tooling advisories through 40 dependent entries; exact,
dated source-preview exceptions preserve those findings and require recheck before
the release freeze. Other runtime manifests remain unresolved, including known
affected declared pins. The Task 7 local snapshot predates these changes and must
be rebuilt before the first private push. Task 10 performed that rebuild; its
first Ubuntu execution also found and fixed the missing Linux-specific `greenlet`
pin. The current Python list contains 43 audited pins with 811 artifact hashes.

The [Task 9 documentation review](documentation.md) replaces competing designs
with code-linked source maps and organizes current guidance under architecture,
development, reference, and release folders. Earlier technical/validation records
are explicitly historical; 307 obsolete/duplicate documents and 13 additional
business documents are omitted with verified private recovery copies. The old
Task 7 snapshot contains retired material and cannot be the pushed candidate.
Task 10 rebuilt a fresh root from its reviewed 3,231 selected files before pushing.

## Remaining publication gates

1. **Preserve the independent publication boundary:** Task 10 rebuilt and verified
   the source-only snapshot after dependency/documentation review. Publish only
   its independent `main`;
   keep all original local/remote refs, hosted business documents, PR material,
   logs, and external copies private. Do not import them into the new repository.
   A change to the approved destination/operations or any original-history rewrite
   requires a separate concrete review; no such rewrite is part of this plan.
2. **Licensing and dependency boundaries:** preserve the completed Task 4 source
   records and exact upstream notices in the selected candidate. Keep historical
   installers out of every publication ref. Apache-2.0 applies to original code;
   third-party material retains its own terms. Task 8 audited resolved preview
   dependencies; refresh that audit and its two dated tooling exceptions for
   Task 12. Runtime bundles and package redistribution remain excluded.
3. **Repository settings:** enable and test private vulnerability reporting with
   monitored notifications; configure required source and secret checks, branch
   protection, available secret protection, and read-only fork/PR workflows.
   Task 11 applied and verified read-only token, exact-action allowlist, and SHA
   restrictions. GitHub blocks private branch/native-secret/fork/form settings;
   [public-activation steps](repository-protections.md) are prepared. The monitored
   fallback contact and delivery test remain required before Task 11 can close.
4. **Release identity:** review and commit the chosen changes, run all preview
   gates on that exact commit, record dependency/artifact digests and limitations,
   then review repository visibility and release contents before publication.
   Verify anonymous clean-clone checks afterward. No release tag has been created.

## Checklist disposition

| Original checklist items | Current disposition |
| --- | --- |
| 01, 19, 27 | Source-only scope and review commands documented; no runnable-beta claim |
| 02 | Logging and candidate-source cleanup performed; history/external-artifact gate open |
| 03 | Publication workflows disabled and AMIs private; credential-free first-boot enrollment remains unverified |
| 04, 23 | Bundled binaries omitted and complete license text retained; history/provenance review still required |
| 05, 24 | Replacement source/auth/secret checks; old deployment/integration gates disabled, not passed |
| 06 | Direct-reset path removed; no replacement recovery implementation claimed |
| 07–16, 20–22, 25–26 | Experimental runtime work excluded from supported preview; security controls not marked fixed |
| 17 | Current compilation/undefined-name gate repaired; service import/startup not certified |
| 18 | Duplicate pending Flyway version resolved; fresh-install/upgrade/restore unverified |
| 28 | Owner/repository publication gates remain open; no tag or visibility change |
