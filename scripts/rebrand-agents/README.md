# Historical agent repackaging scripts

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


These original SentinelGrid scripts are retained as Apache-2.0 source for review.
Their Wazuh inputs and generated outputs retain the applicable upstream terms;
the scripts do not relicense those inputs. Installer repackaging and publication
remain outside supported source-preview execution, and the historical Actions
workflow is disabled. See [release scope](../../RELEASE_SCOPE.md).

| Path | Historical purpose |
| --- | --- |
| `download/download-wazuh.sh` | Download packages and calculate local digests |
| `extract/extract-agents.sh` | Extract upstream packages |
| `rebrand/rebrand-wazuh.sh` | Apply branding replacements and metadata edits |
| `templates/SENTINELGRID_ATTRIBUTION.txt.tmpl` | Prospective attribution template, not proof of a completed release |
| `scan/scan-packages.sh` | Inspect generated package material |
| `test/test-rebranded-agent.sh` | Historical package checks |
| `upload/upload-to-cdn.sh` | Historical publication path; not approved for this preview |

The downloader calculates checksums from downloaded files; it does not verify an
upstream-signed digest. The rebranding script makes broad replacements in Python,
shell, service, configuration, and package metadata, then deletes its backup files.
That process can alter upstream notices. The retained code has not been validated
as a compliant or functional package pipeline. No package tooling was executed.

The complete upstream [Wazuh 4.8.0 license](LICENSE_WAZUH.txt) is preserved,
including Wazuh/Trend Micro attribution and component/linking notices. The template
no longer claims GPL "or later," unchanged core functionality, or a completed
SentinelGrid release. Any package release must establish its exact sources,
binaries, modifications, build inputs, preserved notices, and applicable
source-delivery terms before distribution. A generic license copy or source URL
alone does not establish that result.

Five installers remain privately retained, and four remain in Git history. They
are excluded from the public source candidate. See
[third-party notices](../../THIRD_PARTY_NOTICES.md) and
[the Task 4 review](../../docs/release/provenance.md).
