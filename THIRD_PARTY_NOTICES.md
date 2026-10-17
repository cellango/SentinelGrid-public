# Third-party components

The root [Apache-2.0 license](LICENSE) applies to original SentinelGrid code.
Third-party material retains its own terms. See [LICENSING.md](LICENSING.md),
[the component inventory](third_party/components.json), and
[the Task 4 review](docs/release/provenance.md).

| Component | Source and terms | Source-preview disposition |
| --- | --- | --- |
| AI Shield original source | Existing [Apache-2.0 license](SentinelGridAIShield/LICENSE) | Retained under its existing terms |
| Next.js starter assets and derived scaffolding | [Reference revision](https://github.com/vercel/next.js/tree/412eb90b6587ec02e8361c92efa9091487e7348f/packages/create-next-app/templates); complete [2024 MIT notice](third_party/licenses/nextjs-14-MIT.txt) and [2025 MIT notice](third_party/licenses/nextjs-15-MIT.txt) | Six unchanged assets retained with byte-level source records; original SentinelGrid changes remain Apache-2.0 |
| Wazuh 4.8.0 | [Exact upstream license](https://github.com/wazuh/wazuh/blob/038fe11d988fa54cca8a6c3101fc7906fad5da3b/LICENSE); complete copies in [agents/wazuh](agents/wazuh/LICENSE_WAZUH.txt) and [rebranding scripts](scripts/rebrand-agents/LICENSE_WAZUH.txt) | No installer or vendored implementation distributed; upstream copyright, GPL v2, component, and linking notices preserved |
| Heroicons | [Upstream MIT license](https://github.com/tailwindlabs/heroicons/blob/v2.2.0/LICENSE); [local notice](third_party/licenses/heroicons-MIT.txt) | npm import reference; dependency code is not vendored |
| Lucide | [Upstream ISC notice](https://github.com/lucide-icons/lucide/blob/0.294.0/LICENSE), including Feather/MIT attribution; [local notice](third_party/licenses/lucide-ISC.txt) | npm import reference; dependency code is not vendored |
| DM Sans | [Upstream OFL](https://github.com/google/fonts/blob/main/ofl/dmsans/OFL.txt); [local notice](third_party/licenses/dm-sans-OFL.txt) | Font-loading reference only; no font binaries retained |
| IBM Plex Sans | [Upstream OFL](https://github.com/google/fonts/blob/main/ofl/ibmplexsans/OFL.txt); [local notice](third_party/licenses/ibm-plex-sans-OFL.txt) | Font-loading reference only; no font binaries retained |
| JetBrains Mono | [Upstream OFL](https://github.com/google/fonts/blob/main/ofl/jetbrainsmono/OFL.txt); [local notice](third_party/licenses/jetbrains-mono-OFL.txt) | Font-loading reference only; no font binaries retained |
| Python and main frontend preview dependencies | [Resolved license inventory](third_party/preview-dependencies.json) and [Task 8 review](docs/release/dependencies.md) | 54 Python source-test pins and 828 npm entries, including LGPL/MPL and native-package terms; installed implementations and binaries are not redistributed |
| Other Go, Python/npm runtime, CI, container, infrastructure, and tool dependencies | [Manifest catalog](publication/dependency-manifests.json), workflow pins, and upstream projects | Experimental references; complete runtime/bundle resolution and redistribution remain outside this preview |

The six Next.js starter assets are `website/app/favicon.ico` and
`website/public/{file,globe,next,vercel,window}.svg`. Each matches the recorded
upstream reference byte for byte. The MIT notices also cover Next.js-derived
starter portions of `frontend/` and `website/`; they do not relicense original
SentinelGrid additions. Project names and logos identify their respective owners
and do not imply endorsement of SentinelGrid.

Five Wazuh installers remain privately retained: ARM64 and Intel macOS PKGs,
Linux RPM and DEB, and a Windows MSI. The first four also occur in local Git
history and must remain private or be omitted from every published ref. The MSI
was ignored and never tracked. The five local checksum records match those local
files; they are not verification against an upstream signature or digest.

Original SentinelGrid integration and repackaging scripts are source for review.
Their Apache-2.0 terms do not relicense Wazuh or clear any resulting installer.
The complete upstream Wazuh license contains notices beyond the generic GPL text;
rebranding and a source-project URL alone do not establish redistribution
compliance. Package redistribution requires a separate review of exact binaries,
sources, modifications, build inputs, notices, and applicable source-delivery terms.
