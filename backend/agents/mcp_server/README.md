# SentinelGrid MCP source preview

This component is the legacy source for the proposed deterministic `tool_gateway`.
It is not an AI reasoning agent. Read the [release scope](../../../RELEASE_SCOPE.md)
and [target ownership](../../../docs/architecture/agentic-platform.md) first.

The stdio server supports protocol initialization, ping and discovery of twelve
existing wire names/input schemas. **Every declared tool call returns `isError=true`; unknown
tool names return a protocol error. No provider or data operation is admitted.** Descriptions identify unavailable tools.
Environment variables, UUID strings, model/body claims, shared service tokens and
approval/audit flags do not authenticate a caller or approve an action. This change
preserves required capabilities for migration; it does not approve their retirement.

| Existing wire names | Intended responsibility |
| --- | --- |
| `search_logs`, `get_detections` | Security logs and detection data |
| `get_incidents`, `create_incident` | Incident retrieval/creation |
| `list_playbooks`, `get_playbook`, `run_playbook`, `get_playbook_execution` | Playbook discovery and execution/status |
| `get_user`, `lock_account` | Identity retrieval and account action |
| `get_observable`, `search_observables` | Observable data |

[The versioned wire mapping](app/core/tool_admission.py) gives each operation a
logical `<domain>.<action>` name and intended effect class. That metadata grants
no capabilities. Reads also need verified tenant/data authority. No renaming of
installed endpoints or external wire names is included.

The core server imports no downstream tool module. Direct legacy tool helpers,
raw service-client properties, arbitrary tenant-header construction and unverified
audit emission also reject before downstream credentials/client/data access.
There is no eager HTTP client initialization. The caller's identity never replaces
a resource's `user_id`; tool arguments are not mutated. Removing text markers is
not a prompt-injection security boundary: retrieved content remains untrusted.

## Optional authenticated HTTP discovery

The [verified HTTP factory](app/verified_http.py) uses the actual MCP1.30.0
stateless Streamable HTTP SDK with owned IAM/user settings, exact host/origin
allowlists, request-bound immutable actor/tenant context and shared ingress/Redis
budget support. It is not mounted by the stdio entrypoint or deployed here. Every
tool remains unavailable. Read the [current HTTP contract](../../../docs/reference/http-boundaries.md)
for configuration, test scope and remaining action/data/issuer gates.

## Source checks

From the repository root, use Python3.13 and the hash-required preview environment:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r scripts/requirements-preview.txt
make preview-mcp PYTHON=.venv/bin/python
```

`make preview-check` also requires these MCP checks in a separate process from
IAM tests, because both services retain the legacy `app` package name. See the
[test scope](tests/README.md). MCP1.30.0 is the selected protocol-test SDK; its
pinned additional dependencies are [hash recorded](../../../scripts/requirements-mcp-sdk.txt).
This does not qualify a container/runtime dependency graph or SDK2 compatibility.

## Remaining admission work

Before restoring any operation, an owned transport must derive caller identity,
tenant UUID and capabilities from verified credentials. Keep resource targets
separate from actors. Bind exact operations to owned configuration and domain
services through the selected single action boundary, with deterministic approval,
durable audit, replay/failure handling and independently verified effects. Qualify
downstream reads/data ownership too; a shared bearer token cannot prove authority.

Full gateway/MCP caller compatibility, additional legacy tools, production ingress/Redis
topology, remaining route contracts, credential/TLS lifecycle and full installation
remain migration work. The shared local HTTP checks cover only the documented source scope. No deployed HTTP/OAuth service, live provider/model,
case runtime, durable audit or complete feature equivalence is qualified here.
All original code remains under the repository's Apache-2.0 terms; dependencies
retain their upstream licenses.
