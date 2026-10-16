# Main frontend source

This is the canonical UI source tree. Read [frontend ownership](../docs/architecture/frontend.md)
for route groups and legacy app boundaries. Product/marketing flows are experimental;
the source preview does not offer a hosted service or a full-stack quick start.

Use the Node.js 22 installation and `test:preview` command in the repository
[README](../README.md). The committed lock and `npm ci --ignore-scripts` are the
reviewed installation path. [Dependency decisions](../docs/release/dependencies.md)
include two dated unpatched development-tooling exceptions. Full build, provisioning,
billing, and live backend/provider integration remain unqualified.
