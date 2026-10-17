# MCP source and protocol checks

These tests cover the [current discovery-only source boundary](../README.md).
They use the real pinned MCP1.x SDK and local memory/stdio sessions. They do not
execute a domain tool or prove a provider action, data-read authorization,
OAuth/HTTP deployment, durable audit or complete migrated feature equivalence.

From the repository root after installing `scripts/requirements-preview.txt`:

```sh
make preview-mcp PYTHON=.venv/bin/python
```

`run_tests.sh` runs the same suite using `PYTHON` (default `python3`). It never
installs packages, selects a container or enables coverage/network dependencies.

The protocol tests require successful initialization, ping and discovery, preserve
all twelve legacy wire names/input schemas, and require explicit tool errors for
declared operations and protocol errors for unknown names. They verify that target arguments are unchanged.
Direct helper, raw client, UUID/body approval, environment identity and flag
attempts are rejected before HTTP clients or database calls. Downstream effects
fail tests rather than being replaced with a success response. The stdio child
uses synthetic environment values and an explicit downstream-effect guard.

Earlier mocked success tests asserted permissive high-risk authorization, and
some integration assertions ran only if a handler lookup succeeded. Those do
not prove the current contract. They are replaced by unconditional actual SDK
session checks and direct rejection assertions. Required operation restoration
must add positive identity/capability/provider tests when its transport and
domain/action contract are implemented; these negatives are not that acceptance.
