# Third-party provenance review

Task 4 is complete as of October 15, 2026 for the source-preview scope, with
installer redistribution excluded. The owner confirmed that, apart from declared
dependencies and Next.js starter assets, remaining source and SentinelGrid logos
are original or created for this project. That is owner attestation, not an
independent authorship determination for every line.

## Retained material

The [component inventory](../../third_party/components.json) records paths, source
revisions, hashes, terms, and distribution boundaries. Original SentinelGrid
source remains Apache-2.0, including AI Shield's existing component license.
Four project SVG/icon assets are recorded against the owner's confirmation.

Six Next.js starter assets match upstream files byte for byte: the website favicon
and `file`, `globe`, `next`, `vercel`, and `window` SVGs. The comparison reference
is Next.js `v15.5.15`, commit `412eb90b6587ec02e8361c92efa9091487e7348f`.
This identifies matching upstream content, rather than the original generator
invocation or installed application version. Complete upstream 2024 and 2025
MIT notices are preserved for the starter assets and Next.js-derived scaffolding
portions of `frontend/` and `website/`. Original SentinelGrid changes retain
Apache-2.0. See [the upstream MIT license](https://github.com/vercel/next.js/blob/412eb90b6587ec02e8361c92efa9091487e7348f/license.md).

Heroicons and Lucide are package references, rather than vendored implementations.
Their MIT and ISC/Feather-attribution texts are preserved locally. DM Sans, IBM
Plex Sans, and JetBrains Mono are font-loading references with recorded OFL 1.1
texts; the candidate contains no font binaries. Those reference notices do not
constitute an inventory of future generated bundles.

The source inventory contains 52 Python requirements files, five npm manifests
and lockfiles, four Go manifests/checksum files, and 87 container/IaC manifests.
These describe dependencies and acquisition paths. Exact resolved dependency
versions, vulnerabilities, and installed-package license records remain Task 8;
runtime containers, installers, model weights, and font bundles are not published
by this source preview. No vendored dependency tree was found in the candidate.

## Wazuh disposition

The reference is Wazuh `v4.8.0`, commit
`038fe11d988fa54cca8a6c3101fc7906fad5da3b`. Both Wazuh license files now preserve
the entire [upstream LICENSE](https://github.com/wazuh/wazuh/blob/038fe11d988fa54cca8a6c3101fc7906fad5da3b/LICENSE)
verbatim. It contains Wazuh and Trend Micro attribution, GPL version 2, and
additional component/linking notices. Generic GPL text alone omitted that
upstream material. File-specific Git whitespace attributes preserve the original
license formatting without relaxing checks on other files.

Five local installers remain privately retained: two macOS PKGs, a Linux RPM,
a Linux DEB, and a Windows MSI. All five match the repository's local checksum
records. No upstream signature or published digest was authenticated, and exact
corresponding-source/build mapping was not established. The MSI was ignored and
never tracked; it was moved alongside the other private installers during this
review. No installer is in the candidate source or approved for redistribution.

The historical-object inventory found 13 asset/installer paths: nine asset paths
and four installer paths. The four installer blobs must remain private or be
omitted from every publication ref. License/asset records apply to the reviewed
working source; they do not clear an arbitrary old branch, tag, PR attachment,
registry artifact, or package output. Tasks 6 and 7 must implement these history
and artifact dispositions alongside Task 3's private-business boundary.

Original integration/rebranding scripts remain reviewable source. They do not
relicense Wazuh or certify resulting packages. The script performs broad edits in
upstream source/configuration and metadata, then removes backups. Claims of
unchanged source, completed compliance, and GPL "or later" permission were removed
from the package notices, templates, status, and guide. Future package distribution
requires exact-content and applicable source-delivery review; no package pipeline
was run or certified here.

## Evidence and remaining work

Private evidence in ignored `artifacts/private-release-review/task-4/` includes the
owner's answer, authenticated upstream file responses, source/blob hashes,
installer checksum comparisons, historical candidate inventory, and recoverable
copies of notices before editing. Public attribution and license texts are in
[THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md) and `third_party/`.

Final publication must preserve these notices and exclusions. A runnable product,
dependency bundle, or installer release requires its own resolved-content review.
Verification passed for ten asset hashes, nine exact upstream license copies,
Apache license boundaries, attribution-template rendering, relative notice links,
and installer/font exclusions. Source hygiene compiled 1,371 Python files without
failure, patch whitespace checks passed, and the candidate secret scan found zero
matches. No package builds, runtime services, or application behavior were changed.

The completed [Task 5 selection](contents.md) records the exact source
paths and experimental cloud-provider bundle. Continue with the
[publication checklist](tasks.md).
