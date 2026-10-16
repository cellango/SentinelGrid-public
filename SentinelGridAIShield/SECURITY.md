# AI Shield security reporting in this preview

Follow the root [security policy](../SECURITY.md) for this monorepo snapshot.
Use the private vulnerability form when available; if it is unavailable, request
a private contact without posting vulnerability details. Reporting availability
and monitored notifications remain explicit publication gates.

The gateway, provider-key retrieval, API-key/tenant handling, guardrails, telemetry,
and deployment defaults remain security review targets. The known internal-token
fallback is described in [the credential review](../docs/release/credentials.md).
No standalone AI Shield runtime or production support is qualified by this preview.
Do not commit environment secrets, provider keys, telemetry, or private reports.
