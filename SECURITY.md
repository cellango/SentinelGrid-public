# Security policy

## Supported versions

This is a developer source preview. No platform release is currently supported
for production, customer telemetry, cloud remediation, pentest execution, or
autonomous response. See [RELEASE_SCOPE.md](RELEASE_SCOPE.md). Component policies,
including AI Shield's, describe their own scope.

## Report vulnerabilities privately

Use this repository's **Security → Advisories → Report a vulnerability** form.
The [private report form](https://github.com/cellango/SentinelGrid-public/security/advisories/new)
routes reports through GitHub. Maintainers manage notification recipients and
delivery preferences in GitHub settings; no reporting email is embedded in source.

**Preparation status:** the repository is still private, so GitHub's reporting
form is not enabled yet. Its form configuration and issue-routing link are
prepared. Activation, reporter access, and notification delivery must be verified
after the approved public visibility change and before release finalization. See
[the reporting verification](docs/release/repository-protections.md#private-reporting-and-delivery).

If the form is unavailable, open an ordinary issue asking maintainers to restore
the private reporting channel, without including vulnerability details. Wait for
that channel before sending a report. Never include credentials, customer data,
exploit payloads, or private scanner reports in public issues or PRs. No
response-time commitment is established for the preview. Include the commit,
affected component, expected/observed behavior, and a synthetic reproduction in
the private report. Suspected real credentials require owner assessment of
rotation and retained copies.

## Limitations and data handling

- The legacy unauthenticated direct-reset path returns HTTP 410 in IAM and the
  frontend. This removes the path; it does not implement token-based recovery.
  Use the identity provider's verified account recovery flow.
- Experimental authentication, tenant isolation, OAuth, approvals, tool execution,
  RAG, agent enrollment, and TLS still need their own validation.
- The experimental agent-runtime token functions and AI Shield Go gateway can
  accept the published internal-token fallback when explicit token configuration
  is absent, including with `ENVIRONMENT=production`. These runtimes remain
  excluded from supported preview execution. See the
  [credential review](docs/release/credentials.md) for the offline findings.
- Preview checks do not send telemetry or call product services. Dependency and
  CI tool installation download packages from upstream registries.
- Experimental deployments may send data to Keycloak, PostgreSQL, OpenSearch,
  embeddings, model/provider APIs, object storage, logs, caches, and backups.
  Unified retention and deletion guarantees have not been verified. Use synthetic
  review data only.
- Scanner evidence stays in ignored `artifacts/private-release-review/`. Even
  redacted reports can expose paths, context, and Git metadata; do not upload
  them as public artifacts.
- Git history and external artifacts require clearance before publication.
  Removing a file from the working tree does not remove historical copies.

Historical hardening, benchmark, compliance, audit, and production-readiness claims
do not establish this snapshot's security. See [the publication review](docs/release/review.md)
for current evidence and open gates.
