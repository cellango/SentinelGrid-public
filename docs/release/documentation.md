# Documentation consolidation and claims review

Task 9 complete, October 15, 2026. The documentation now separates current source
references, contributor guidance, publication evidence, and historical material.
See [the current index](../README.md) and
[the exact classification inventory](../../publication/documentation.json).

## Decisions

The starting inventory contained 718 Markdown/design-text artifacts, including
many competing overall designs, temporary status notes, repeated setup guides,
and old launch signoffs. A complete private source archive was verified before
any move or removal. Each original document has a private path/hash/disposition
record; copies are recoverable without republishing original history.

- Retired 307 superseded design/progress/duplicate documents and kept 13 additional business documents private.
- Moved or consolidated 291 documents into maintained folders; seven current guides were rewritten around source entrypoints and explicit gaps.
- Replaced the giant flat index with a short reading order and one current page per topic.
- Removed the duplicated pentest research/design copies; the retained component source map replaces them.
- Classified unique earlier API, technical, operations, and validation material under `archive/`, with an explicit historical notice and separate indexes.
- Preserved root licensing, attribution, contributor instructions, the private-data exclusions, and existing application/cloud implementation work.

A recent timestamp or "canonical" title was not treated as proof of current
behavior. The new architecture/cloud/frontend/entity/agent references link to
retained implementation paths and distinguish interfaces, declared providers,
mocked tests, experimental runtime, and excluded operations. Former phase-complete
language is not used as current architecture or release evidence.

## Current folders and authority

| Location | Authority |
| --- | --- |
| Root README, scope, contributing, security, licensing | Repository entrypoints and supported preview boundary |
| `docs/architecture/` | Code-linked architecture and current source ownership |
| `docs/development/` | Contributor/database/documentation rules |
| `docs/reference/` | Focused code contracts, with explicit limitations |
| `docs/release/` | This publication's decisions, review evidence, and open gates |
| `docs/archive/` | Earlier records only; no current operating or release authority |
| Component-local docs | Experimental source reference; root preview scope takes precedence |

Abandoned designs and internal business plans are not put into a public historical
folder. Their originals stay private. The public classification lists retained
Markdown files and roles, without disclosing the private recovery inventory.

## Link and source consistency

Moves repair relative links from their original locations and update literal
references only when the referenced file actually moved. Links to retired records
point to the explicit retirement policy. Fourteen already-unavailable historical
links are rendered as text rather than pretending to be live contracts.
The initial relocation pass repaired 387 existing links.

Legacy verification scripts may still require retired private launch artifacts.
Those prerequisites were not silently replaced with unrelated documents to make
old checks pass. They are experimental references, outside supported preview checks.
The root publication checklist and current source checks remain authoritative.

The source check now validates every selected Markdown link and its classification.
Existing ignored/private files cannot satisfy a public link. Tests cover moved
pages, balanced/encoded paths, images, reference definitions, code examples,
private/outside targets, and classification drift. No broad link-ignore baseline
was introduced. Two existing exact-value non-secret scanner exceptions retain
only their old path and an exact alias for the relocated text; default rules and
all other exceptions remain intact.

## Claims and feedback

Component entrypoints no longer advertise supported standalone startup. Other
component references are explicitly labeled experimental before their old commands.
The main UI and archived website now display their source-preview/prototype status.
The landing and trust pages replace unverified SaaS, support, retention, compliance,
and production-ready promises with developer review and private-reporting guidance.
This does not qualify a full frontend build or runtime.

Ordinary feedback uses the repository's Developer review or feedback issue template,
including revision, source area, observation, and synthetic reproduction. Root
[SECURITY.md](../../SECURITY.md) defines private vulnerability reporting; actual
form availability and monitored contact delivery remain Task 11/14 gates. No
contact or notification channel was invented or activated during this task.

## Verification boundary

All 415 retained Markdown files pass link and classification checks. The Python
checks passed 28 tests, compiled 1,447 Python files, and passed Ruff. All 13 focused
frontend tests and five changed-TSX syntax checks passed. Workflow syntax, three
scanner exception canaries, and source secret scanning passed with zero source
findings. Reference-only code diffs and verified private originals are recorded
privately. Full frontend semantic typing/build remains unqualified. The original repository's HEAD, refs, and remote stay
unchanged. No service startup, database migration, active scan, deployment, public
repository, push, tag, or visibility change is part of this documentation task.

Task 10 is the next step: rebuild the independent candidate from these final
reviewed files, then verify its clean clone and actual private GitHub CI. The
retained Task 7 preparation snapshot predates the documentation removals and must
not be pushed. Public visibility still requires the exact Task 13 review.
