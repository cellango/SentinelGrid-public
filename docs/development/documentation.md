# Maintaining documentation

Each topic has one current page under `docs/architecture`, `docs/development`,
`docs/reference`, or `docs/release`. Link to that page instead of maintaining a
second quick start, status report, or competing overall design. Root README,
release scope, contribution guidance, licensing, and security policy remain the
repository entrypoints. Keep [AGENTS.md](../../AGENTS.md) at the repository root.

## Classification rules

- Describe implemented source with code links and distinguish interface declarations from working behavior.
- Label mocked tests, simulated fixtures, experimental integrations, and excluded runtime operations explicitly.
- Keep evidence tied to its review date/scope; historical signoffs cannot approve a current release.
- Retire an abandoned design when a better one replaces it. Preserve owner-private recovery copies and update incoming links.
- Keep business strategy, pricing research, private roadmaps, customer data, credentials, and local evidence out of public docs.
- Keep a unique historical reference in `docs/archive` only when it helps understand source or prior verification; include a historical notice.
- Keep component READMEs beside source, with a link back to the root preview boundary before any experimental commands.
- Do not add new `FINAL`, `100_PERCENT_COMPLETE`, or date-only progress documents as navigation authorities.

Update [the index](../README.md) and [classification inventory](../../publication/documentation.json)
when moving or adding docs. Review the selected file diff before refreshing
[publication/source-files.json](../../publication/source-files.json). Local links
must target retained source, never ignored private recovery folders.
Ordinary feedback uses this repository's review issue template; vulnerabilities
follow [SECURITY.md](../../SECURITY.md).
