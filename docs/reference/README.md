# Source and design contract references

These pages identify implementation entrypoints, gaps and explicitly labeled
future contracts. They are not operating runbooks or API/runtime certifications.

- [Identity and tenant boundaries](identity.md)
- [Agent and module categories](agent-components.md)
- [Entity and evidence shapes](entity-model.md)
- [Proposed canonical AI role catalog](agent-registry.md)
- [Case, execution and registry design contracts](agentic-contracts.md)
- [Product catalog compatibility fields](product-catalog.md)
- [Architecture map](../architecture/overview.md) and [cloud adapters](../architecture/cloud-providers.md)

Older API tables, deployment instructions, and protocol notes are classified under
[the historical archive](../archive/README.md). Check the current source before
using them. Supported setup/check commands live only in the root [README](../../README.md).

- [Current HTTP transport boundaries](http-boundaries.md): ingress, proxy forwarding, Redis budgets and authenticated MCP discovery; source qualification only.

- [Shared application database qualification](application-database.md): complete unchanged migration lineage, isolated upgrade/recovery evidence and production adoption limits.

- [Action database role admission](action-database-role.md): dedicated application-role checks and native privilege-denial/recovery evidence.
