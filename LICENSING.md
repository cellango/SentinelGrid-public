# Licensing

Original SentinelGrid code is licensed under the **Apache License, Version 2.0**
([SPDX: Apache-2.0](https://spdx.org/licenses/Apache-2.0.html)). The complete text
is in the root [LICENSE](LICENSE). This is the default license for original
SentinelGrid code unless a file or component states otherwise.

## Component boundaries

- `SentinelGridAIShield/` retains its existing [Apache-2.0 license](SentinelGridAIShield/LICENSE)
  and applicable notices.
- The six Next.js starter assets listed in [the component inventory](third_party/components.json)
  and Next.js-derived scaffolding portions of `frontend/` and `website/` retain
  their MIT terms. Original SentinelGrid changes retain Apache-2.0. Complete
  upstream notices are in `third_party/licenses/nextjs-14-MIT.txt` and
  `third_party/licenses/nextjs-15-MIT.txt`.
- Wazuh upstream material retains the complete upstream 4.8.0 license, including
  GPL version 2 and its component/linking notices, in
  `agents/wazuh/LICENSE_WAZUH.txt` and `scripts/rebrand-agents/LICENSE_WAZUH.txt`.
  Original SentinelGrid integration/repackaging scripts remain Apache-2.0;
  that does not relicense Wazuh or clear generated packages for distribution.
- Other third-party code, dependencies, assets, and generated artifacts retain
  their respective licenses and copyright notices. Their inclusion does not make
  them original SentinelGrid code or relicense them under Apache-2.0.

See [NOTICE](NOTICE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Choosing
Apache-2.0 for original code does not clear third-party installers, dependency
bundles, fonts, images, or generated runtime artifacts for redistribution.
The [Task 4 review](docs/release/provenance.md) records the source-preview
dispositions. The [Task 8 dependency review](docs/release/dependencies.md) and
[resolved inventory](third_party/preview-dependencies.json) record the supported
preview dependencies, including LGPL/MPL components and native-package terms.
Installed dependencies and generated binary/container bundles are not cleared
for redistribution by this source-preview review.
