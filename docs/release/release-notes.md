# SentinelGrid v0.1.0-preview.1 — developer source preview

SentinelGrid combines security operations, identity, cloud posture, endpoint
telemetry, and AI-assisted workflow source. This preview is for developers to
review architecture and implementation and leave comments. The full platform
is experimental; this release does not provide a supported runnable beta.

## Review scope

The source includes the main Next.js frontend, FastAPI services/shared libraries,
SentinelGuard, AI Shield, Posture and Pentest components, and inspectable
infrastructure. Sanitized cloud-provider/V013 work is included as experimental
source. Current documentation is separated from clearly historical references;
retired business, design, and generated material is excluded.

Start with [README.md](https://github.com/cellango/SentinelGrid-public/blob/v0.1.0-preview.1/README.md), [release scope](https://github.com/cellango/SentinelGrid-public/blob/v0.1.0-preview.1/RELEASE_SCOPE.md),
and [the source map](https://github.com/cellango/SentinelGrid-public/blob/v0.1.0-preview.1/docs/architecture/overview.md). Ordinary feedback belongs in
the **Developer review or feedback** issue template. For vulnerabilities, use the
private GitHub channel described in [SECURITY.md](https://github.com/cellango/SentinelGrid-public/blob/v0.1.0-preview.1/SECURITY.md); recipient
preferences are configured in GitHub, with no reporting email embedded in source.

## Checks and known limits

The frozen manifest identifies the exact commit, all four passing CI jobs, 28
Python tests, 13 frontend tests, source/history scans, dependency inputs, and
source-archive checksums. Use the documented Python 3.13/Node.js 22 source-check
commands. These checks start no product services or cloud resources.

The 43 pinned Python review packages have no reported advisories at freeze.
Raw npm audit remains nonzero: `braces` and `sprintf-js` have two unpatched,
dated exceptions for fixed-input development tooling. They are not runtime
clearance. See [the dependency review](https://github.com/cellango/SentinelGrid-public/blob/v0.1.0-preview.1/docs/release/dependencies.md) for exact versions,
advisory IDs, expiry, and license boundaries.

Full frontend builds, service startup, database migration/upgrade/restore,
two-tenant end-to-end isolation, cloud remediation, live scans, autonomous tools,
enrollment, packaging, and compliance claims are not qualified. Experimental
internal-token fallback behavior remains documented. Legacy deployment/package
workflows remain disabled. Private reporting access and notification receipt
must be verified as publication gates before this release is finalized.

Original code is Apache-2.0; AI Shield retains its existing Apache-2.0 license.
Third-party material retains its own terms. See [LICENSING.md](https://github.com/cellango/SentinelGrid-public/blob/v0.1.0-preview.1/LICENSING.md)
and [THIRD_PARTY_NOTICES.md](https://github.com/cellango/SentinelGrid-public/blob/v0.1.0-preview.1/THIRD_PARTY_NOTICES.md).

The proposed assets are the frozen source archive, `release-manifest.json`, and
`SHA256SUMS`. Verify the downloaded files with `shasum -a 256 -c SHA256SUMS`.
The manifest is a freeze-time record; pending public-only controls are verified
during publication. There are no installer, container, or dependency bundles.
