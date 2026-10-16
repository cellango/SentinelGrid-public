# Agent integration and repackaging reference

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Installer repackaging, image publication, and package repositories are outside
supported source-preview execution. The historical Actions workflow is disabled.
Read [release scope](../../../../RELEASE_SCOPE.md) before using any runtime material.

## Retained source

The repository contains original SentinelGrid integration, download, extraction,
branding, scan, test, and upload scripts. It contains no vendored Wazuh agent
implementation or installer in the publication candidate. The scripts remain
source for review; their existence does not qualify a runtime or package release.
See [the script inventory](../../../../scripts/rebrand-agents/README.md).

## Wazuh provenance

The Wazuh reference is tag `v4.8.0`, commit
`038fe11d988fa54cca8a6c3101fc7906fad5da3b`. The complete upstream
[license](../../../../agents/wazuh/LICENSE_WAZUH.txt) preserves Wazuh and Trend Micro
attribution, GPL version 2, and component/linking notices. Original SentinelGrid
code is Apache-2.0; those terms do not replace upstream terms or establish that a
combined package may be distributed.

Five local installers remain private. Four also occur in Git history and must
remain private or be omitted from all publication refs. Local checksum records
match those retained files, but no upstream signature/digest authentication or
corresponding-source verification was completed.

## Package-release boundary

The historical branding script changes upstream configuration, Python, shell,
service, and package metadata files. Broad replacements can alter notices; it is
incorrect to claim that source or behavior stays unchanged merely because an
additional attribution file is included.

Any future package release must record exact upstream artifacts and sources,
actual modifications, build inputs, preserved notices, applicable source-delivery
terms, and functional/signature verification. This review did not run package
builds or approve installer distribution. Referenced tools such as Suricata,
platform base images, and packaging utilities retain their own terms and need
review for the exact release artifact in which they are included.

The earlier example of assigning upstream package copyright to an unverified
SentinelGrid legal entity has been removed. Preserve upstream notices; do not
invent ownership or an unsupported GPL "or later" grant.

See [third-party notices](../../../../THIRD_PARTY_NOTICES.md),
[the component inventory](../../../../third_party/components.json), and
[the Task 4 review](../../../release/provenance.md).
