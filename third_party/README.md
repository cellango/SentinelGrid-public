# Third-party provenance records

[components.json](components.json) records retained assets, upstream reference
revisions, content hashes, license paths, and excluded installer boundaries.
`licenses/` contains exact upstream license texts for Next.js starter material
and selected referenced icon/font dependencies. These reference notices do not
replace the license records for a future resolved dependency bundle.

The complete Wazuh license remains in `agents/wazuh/LICENSE_WAZUH.txt` and
`scripts/rebrand-agents/LICENSE_WAZUH.txt`. The root
[third-party notices](../THIRD_PARTY_NOTICES.md) and
[Task 4 review](../docs/release/provenance.md) explain the source-preview
scope. No installer, dependency package, font binary, or generated runtime bundle
is included by this directory.
