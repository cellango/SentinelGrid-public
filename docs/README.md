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

Only the commands in the repository [README](../README.md) are supported preview
entrypoints. The presence of a service, UI route, adapter name, or deployment file
does not establish a supported integration or a runnable platform.

## Documentation classes

| Folder | Purpose |
| --- | --- |
| `architecture/` | Current source layout and implemented boundaries, with explicit gaps |
| `development/` | Contributor and documentation maintenance instructions |
| `reference/` | Focused source contracts and review entrypoints |
| `release/` | This publication's scope decisions, evidence, and remaining tasks |
| `archive/` | Clearly marked earlier validation and technical references; no current authority |
| Component-local READMEs/docs | Experimental module reference; root preview scope takes precedence |

Superseded proposals, duplicate progress reports, and retired designs are omitted
from the publication candidate and recoverable privately. Business documents stay
private. See [the documentation review](release/documentation.md) and
[the classification inventory](../publication/documentation.json).
The archive is for investigating history, not choosing a setup guide.
