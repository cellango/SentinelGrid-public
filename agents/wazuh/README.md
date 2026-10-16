# Wazuh reference material

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


The public source preview contains no Wazuh installer. Five locally retained
Wazuh 4.8.0 packages are excluded from publication. Four tracked installers also
remain in historical Git objects; the ignored MSI was never tracked. Keep those
copies private until the publication repository implements their exclusion.

This directory retains the complete [upstream license](LICENSE_WAZUH.txt),
[provenance notice](SENTINELGRID_ATTRIBUTION.txt), and historical checksum records.
The license is copied verbatim from Wazuh commit
`038fe11d988fa54cca8a6c3101fc7906fad5da3b` (tag `v4.8.0`). It includes Wazuh and
Trend Micro attribution, GPL version 2, and component/linking notices. The root
Apache-2.0 license does not replace those upstream terms.

The five checksum records match privately retained local files. They were not
verified against upstream signatures or published digests and do not authenticate
an installer. No installer or package build was executed during this review.

Historical rebranding scripts edit upstream files and package metadata. Their
outputs are not approved for distribution. Before distributing any original or
rebranded package, review the exact binary/source relationship, modifications,
required notices, build inputs, and applicable source-delivery terms. See
[third-party notices](../../THIRD_PARTY_NOTICES.md) and
[the provenance review](../../docs/release/provenance.md).
