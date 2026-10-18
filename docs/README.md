# SentinelGrid documentation

This is a developer source preview. Read [release scope](../RELEASE_SCOPE.md),
[contributing](../CONTRIBUTING.md), and [security reporting](../SECURITY.md) before
running commands. Original code uses [Apache-2.0](../LICENSING.md).

## Current reading order

1. [Architecture and source map](architecture/overview.md): component boundaries and what exists in source.
2. [Frontend ownership](architecture/frontend.md) and [cloud-provider source](architecture/cloud-providers.md).
3. [Code review guide](development/code-review.md) and [database change rules](development/database-changes.md).
4. [Reference index](reference/README.md): identity, agent components, entity/evidence shapes, and catalog fields.
5. [Release review](release/review.md), [dependency review](release/dependencies.md), and [publication tasks](release/tasks.md).

For design review, read the [selected agentic target](architecture/agentic-platform.md),
[authoritative runtime decision](architecture/decisions/0001-case-runtime.md),
[proposed issuer association decision](architecture/decisions/0002-issuer-association-readback.md),
[logical contracts](reference/agentic-contracts.md),
[database compatibility plan](architecture/database-compatibility.md),
[adaptive Playbook and evidence design](architecture/adaptive-playbooks.md), and
[proposed role catalog](reference/agent-registry.md). They are explicitly labeled
as future design; names and accepted decisions do not establish implementation or enablement.

Only the commands in the repository [README](../README.md) are supported preview
entrypoints. The presence of a service, UI route, adapter name, or deployment file
does not establish a supported integration or a runnable platform.

## Documentation classes

| Folder | Purpose |
| --- | --- |
| `architecture/` | Current source layout plus explicitly labeled accepted target decisions; implementation gaps remain visible |
| `development/` | Contributor and documentation maintenance instructions |
| `reference/` | Source references and explicitly labeled design contracts/role definitions |
| `release/` | This publication's scope decisions, evidence, and remaining tasks |
| `archive/` | Clearly marked earlier validation and technical references; no current authority |
| Component-local READMEs/docs | Experimental module reference; root preview scope takes precedence |

Superseded proposals, duplicate progress reports, and retired designs are omitted
from the publication candidate and recoverable privately. Business documents stay
private. See [the documentation review](release/documentation.md) and
[the classification inventory](../publication/documentation.json).
The archive is for investigating history, not choosing a setup guide.
